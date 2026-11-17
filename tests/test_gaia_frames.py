# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket
import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import SkyCoord
import astropy.units as u
from gar.astrometry import prepare_references
from gar.gaia_frames import compare_frame, run_gaia_frames
from gar.registration import detect, run_registration
from gar.workset import digest

spec = importlib.util.spec_from_file_location('gaia_demo', Path(__file__).resolve().parents[1]/'examples/make_gaia_frames_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.fixture(scope='module')
def case(tmp_path_factory):
    local = tmp_path_factory.mktemp('gaia-frames')/'local'
    demo.make_demo(local/'input')
    registered = run_registration(local/'input/workset.json', 4, [1, 2, 3], local/'registration', local)
    frame = registered['frames'][0]
    with fits.open(local/'input/copies/pose-1.fit', mode='readonly', memmap=False) as hdus:
        points, _ = detect(hdus[0].data)
    cat = Table.read(local/'input/catalog.csv', format='ascii.csv')
    return local, frame, points, cat


def test_reserved_sample_excludes_training_and_keeps_injected_bias(case):
    _, frame, points, cat = case
    before = deepcopy(frame)
    result = compare_frame(points, frame['control_detection_indices'], frame, cat, '2025-01-01')
    assert result['criteria_passed']
    assert .45 < result['control']['metrics']['bias_east_arcsec'] < .6
    assert result['control']['metrics']['matches'] >= 30
    control = {p['detection_index'] for p in result['control']['pairs']}
    assert control <= set(frame['control_detection_indices'])
    assert control.isdisjoint(frame['training_detection_indices'])
    assert result['all_diagnostic']['metrics']['matches'] > len(control)
    assert 'empirical_criteria_passed' not in result['all_diagnostic']['metrics']
    assert frame == before and not result['model_refitted'] and not result['bias_subtracted']


@pytest.mark.parametrize('problem', ['offset', 'wrong_field', 'low_count', 'coverage'])
def test_inadequate_control_cannot_pass(case, problem):
    _, frame, points, cat = case
    model = deepcopy(frame)
    ids = np.array(frame['control_detection_indices'])
    if problem == 'offset':
        model['translation_pixels'][0] += 2.5
    elif problem == 'wrong_field':
        model['translation_pixels'][0] += 50
    elif problem == 'low_count':
        ids = ids[:9]
    else:
        ids = ids[points[ids, 0] < 256]
    result = compare_frame(points, ids, model, cat, '2025-01-01')
    assert not result['criteria_passed']
    if problem == 'offset':
        assert result['control']['metrics']['median_arcsec'] > 4
    if problem == 'wrong_field':
        assert result['control']['metrics']['matches'] < 20


def test_proper_motion_uses_calendar_epoch_without_clock_qualification(case):
    _, _, _, catalog = case
    cat = catalog.copy()
    cat['pmra'][0] = 1000
    before = SkyCoord(cat['ra'][0]*u.deg, cat['dec'][0]*u.deg)
    chosen, coords, info = prepare_references(cat, '2025-01-01')
    i = np.flatnonzero(np.array(chosen['source_id']) == cat['source_id'][0])[0]
    east, north = before.spherical_offsets_to(coords[i])
    assert 8.9 < east.arcsec < 9.1 and abs(north.arcsec) < .01
    assert info['epoch_approx_tcb'].startswith('2025-01-01T12:00:00')


@pytest.mark.parametrize('kind', ['sip', 'ra_wrap'])
def test_distortion_and_ra_wrap_preserve_known_geometry(case, kind):
    from astropy.wcs import WCS
    _, frame, points, cat = case
    model = deepcopy(frame)
    header = fits.Header.fromstring(model['reference_wcs_header'], sep='\n')
    if kind == 'sip':
        header['CTYPE1'] = 'RA---TAN-SIP'; header['CTYPE2'] = 'DEC--TAN-SIP'
        header['A_ORDER'] = 2; header['B_ORDER'] = 2
        header['A_2_0'] = 1e-4; header['B_0_2'] = -8e-5
    else:
        header['CRVAL1'] = .00005
    model['reference_wcs_header'] = header.tostring(sep='\n', endcard=True, padding=False)
    # Independent synthetic truth: same pixel geometry with the known sky bias removed.
    header['CRVAL1'] -= .5/(3600*np.cos(np.deg2rad(30)))
    true_wcs = WCS(header, naxis=2, fix=False)
    true_points, _ = demo.registration_generator.synthetic_points()
    true_sky = true_wcs.pixel_to_world(true_points[:, 0], true_points[:, 1])
    catalog = cat.copy(); catalog['ra'] = true_sky.ra.deg; catalog['dec'] = true_sky.dec.deg
    result = compare_frame(points, frame['control_detection_indices'], model, catalog, '2025-01-01')
    assert result['criteria_passed'] and .35 < result['control']['metrics']['median_arcsec'] < .8
    if kind == 'ra_wrap':
        assert np.any(catalog['ra'] < 1) and np.any(catalog['ra'] > 359)


@pytest.mark.parametrize('problem', ['columns', 'duplicate_ids', 'too_few'])
def test_catalog_integrity(case, problem):
    _, _, _, catalog = case
    cat = catalog.copy()
    if problem == 'columns':
        cat.remove_column('pmra')
    elif problem == 'duplicate_ids':
        cat['source_id'][1] = cat['source_id'][0]
    else:
        cat['ruwe'][:] = 2
    with pytest.raises(ValueError):
        prepare_references(cat, '2025-01-01')


def test_end_to_end_offline_no_refit_and_all_inputs_preserved(case, monkeypatch):
    local, _, _, _ = case
    paths = list((local/'input').rglob('*'))+[local/'registration/registration.json']
    before = {p: digest(p) for p in paths if p.is_file()}
    real_open = fits.open
    def guarded(path, *args, **kwargs):
        assert Path(path).parent == local/'input/copies' and kwargs.get('mode') == 'readonly'
        return real_open(path, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError('Ni réseau ni nouvel ajustement autorisé')
    from gar import registration
    monkeypatch.setattr(fits, 'open', guarded)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(registration, 'solve', forbidden)
    result = run_gaia_frames(local/'input/workset.json', local/'registration/registration.json',
                             local/'input/catalog.csv', local/'gaia-result', local)
    assert result['all_criteria_passed']
    assert all(not f['clock_qualified'] and not f['scientific_submission_certified'] for f in result['frames'])
    assert result['inputs_sha256_before'] == result['inputs_sha256_after']
    assert all(digest(p) == value for p, value in before.items())
    assert any(pair['shared_control_count'] > 0 for pair in result['shared_control_references'])
    assert not result['reference_independence_established']
    from xml.etree import ElementTree
    ElementTree.parse(local/'gaia-result/gaia-frames.svg')


@pytest.mark.parametrize('problem', ['copy', 'catalog', 'model_workset', 'partition', 'centroid', 'transform', 'wcs'])
def test_inconsistent_provenance_and_models_rejected(case, tmp_path, problem):
    import shutil
    original, _, _, _ = case
    local = tmp_path/'local'
    shutil.copytree(original/'input', local/'input')
    shutil.copytree(original/'registration', local/'registration')
    rp = local/'registration/registration.json'
    report = json.loads(rp.read_text(encoding='utf-8'))
    if problem == 'copy':
        with (local/'input/copies/pose-1.fit').open('ab') as stream:
            stream.write(b'changed')
    elif problem == 'catalog':
        with (local/'input/catalog.csv').open('a') as stream:
            stream.write('\nchanged')
    elif problem == 'model_workset':
        report['workset_sha256'] = '0'*64
    elif problem == 'partition':
        report['frames'][0]['control_detection_indices'][0] = 999
    elif problem == 'centroid':
        report['frames'][0]['pairs'][0]['x'] += 1
    elif problem == 'transform':
        report['frames'][0]['translation_pixels'][0] += 1
    else:
        report['frames'][0]['reference_wcs_header'] = ''
    rp.write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError):
        run_gaia_frames(local/'input/workset.json', rp, local/'input/catalog.csv', local/'result', local)
    assert not (local/'result').exists()


def test_refused_registration_remains_a_failed_frame(case):
    local, _, _, _ = case
    rp = local/'registration/registration.json'
    report = json.loads(rp.read_text(encoding='utf-8'))
    report['frames'][0]['model_usable'] = False
    altered = local/'registration/refused.json'
    altered.write_text(json.dumps(report), encoding='utf-8')
    result = run_gaia_frames(local/'input/workset.json', altered, local/'input/catalog.csv', local/'refused-result', local)
    assert not result['all_criteria_passed'] and 'error' in result['frames'][0]
    assert result['frames'][1]['criteria_passed']
