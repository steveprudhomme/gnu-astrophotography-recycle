# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
import importlib.util
import json
from pathlib import Path
import socket
import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from gar.registration import register_points, rigid_fit, detect, run_registration, composed_sky
from gar.workset import digest


spec = importlib.util.spec_from_file_location('registration_demo', Path(__file__).resolve().parents[1]/'examples/make_registration_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def point_case(angle=17):
    points, _ = demo.synthetic_points()
    theta = np.deg2rad(angle)
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    translation = np.array([384, 384])-rotation@np.array([384, 384])+[8, -12]
    reference = points@rotation.T+translation
    return points, reference, rotation, translation


@pytest.mark.parametrize('angle', [-120, -12, 0, 18, 145])
def test_rotations_recovered_with_unused_control(angle):
    points, reference, rotation, translation = point_case(angle)
    result = register_points(points, reference, (768, 768))
    assert result['criteria_passed']
    assert np.allclose(result['rotation_matrix'], rotation, atol=1e-9)
    assert np.allclose(result['translation_pixels'], translation, atol=1e-8)
    assert result['metrics']['control']['p95_pixels'] < 1e-8
    assert set(result['control_detection_indices']).isdisjoint(result['training_detection_indices'])


def test_control_perturbation_never_changes_model_and_can_fail():
    points, reference, _, _ = point_case()
    first = register_points(points, reference, (768, 768))
    modified = points.copy()
    modified[first['control_detection_indices']] += [1.9, 0]
    second = register_points(modified, reference, (768, 768))
    assert second['rotation_matrix'] == first['rotation_matrix']
    assert second['translation_pixels'] == first['translation_pixels']
    assert second['metrics']['control']['p95_pixels'] > 1.5
    assert not second['criteria_passed'] and not second['model_usable']


@pytest.mark.parametrize('kind', ['reflection', 'unrelated', 'too_few', 'narrow'])
def test_unsuitable_fields_cannot_pass(kind):
    points, reference, _, _ = point_case()
    if kind == 'reflection':
        reference = points*np.array([-1, 1])+[768, 0]
    elif kind == 'unrelated':
        reference = np.random.default_rng(123).uniform(0, 768, reference.shape)
    elif kind == 'too_few':
        points, reference = points[:15], reference[:15]
    else:
        points[:, 0] *= .1
        reference = points+[10, 20]
    try:
        result = register_points(points, reference, (768, 768))
    except ValueError:
        return
    assert not result['criteria_passed']


def test_rigid_fit_disallows_reflection_and_scale():
    points, _, _, _ = point_case()
    rotation, _ = rigid_fit(points, points*[-1, 1])
    assert np.linalg.det(rotation) == pytest.approx(1)
    assert np.allclose(rotation.T@rotation, np.eye(2))
    rotation, translation = rigid_fit(points, points*1.1)
    assert np.linalg.norm(points@rotation.T+translation-points*1.1, axis=1).mean() > 10


def test_bayer_detection_preserves_native_coordinates_and_inputs():
    points, flux = demo.synthetic_points()
    image = demo.render(points, flux, bayer=True)
    before = image.copy()
    centers, selection = detect(image)
    from scipy.spatial import cKDTree
    distance, _ = cKDTree(points).query(centers)
    assert len(centers) > 150 and np.percentile(distance, 95) < .5
    assert np.array_equal(before, image)
    assert selection['shape'] == [768, 768]


def test_invalid_images_and_saturation():
    with pytest.raises(ValueError):
        detect(np.ones((128, 128)))
    with pytest.raises(ValueError):
        detect(np.ones((2, 128, 128)))
    points, flux = demo.synthetic_points()
    image = demo.render(points, flux)
    image[100:104, 100:104] = 65535
    _, selection = detect(image)
    assert selection['masked_native_pixels'] == 16


def test_complete_run_offline_local_only_integrity_and_composition(tmp_path, monkeypatch):
    local = tmp_path/'local'
    truth = demo.make_demo(local/'input')
    files = list((local/'input/copies').glob('*.fit'))
    before = {p: digest(p) for p in files}
    real_open = fits.open
    def restricted_open(path, *args, **kwargs):
        assert Path(path) in files
        assert kwargs.get('mode') == 'readonly'
        return real_open(path, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError('Réseau interdit')
    monkeypatch.setattr(fits, 'open', restricted_open)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    result = run_registration(local/'input/workset.json', 4, [1, 2, 3], local/'result', local)
    assert result['all_criteria_passed']
    assert before == {p: digest(p) for p in files}
    assert result['copies_sha256_before'] == result['copies_sha256_after']
    frame = result['frames'][0]
    assert abs(frame['rotation_degrees']-truth[0]['rotation_degrees']) < .01
    assert not frame['clock_qualified'] and not frame['scientific_submission_certified']
    sky = composed_sky(frame, 384, 384)
    expected = WCS(fits.Header.fromstring(frame['reference_wcs_header'], sep='\n')).pixel_to_world(419, 364)
    assert sky.separation(expected).arcsec < .2
    with pytest.raises(ValueError):
        composed_sky(frame, -1, 384)
    with pytest.raises(ValueError):
        composed_sky({**frame, 'model_usable': False}, 384, 384)
    from xml.etree import ElementTree
    ElementTree.parse(local/'result/registration.svg')
    assert len(list((local/'result').iterdir())) == 4


@pytest.mark.parametrize('problem', ['hash', 'indices', 'existing_output', 'outside_copy'])
def test_input_protections(tmp_path, problem):
    local = tmp_path/'local'
    demo.make_demo(local/'input')
    wp = local/'input/workset.json'
    workset = json.loads(wp.read_text())
    indices = [1, 2, 3]
    if problem == 'hash':
        workset['files'][0]['sha256_copy'] = '0'*64
    if problem == 'indices':
        indices = [1, 1]
    if problem == 'outside_copy':
        workset['files'][0]['local_copy'] = '../../elsewhere.fit'
    if problem == 'existing_output':
        (local/'result').mkdir()
    wp.write_text(json.dumps(workset))
    with pytest.raises(ValueError):
        run_registration(wp, 4, indices, local/'result', local)


def test_failed_pose_is_reported_not_overwritten(tmp_path):
    local = tmp_path/'local'
    demo.make_demo(local/'input')
    wp = local/'input/workset.json'
    workset = json.loads(wp.read_text())
    path = local/'input'/workset['files'][0]['local_copy']
    fits.writeto(path, np.ones((768, 768), dtype=np.uint16), overwrite=True)
    workset['files'][0]['sha256_copy'] = digest(path)
    wp.write_text(json.dumps(workset))
    result = run_registration(wp, 4, [1, 2], local/'result', local)
    assert not result['all_criteria_passed']
    assert 'error' in result['frames'][0] and not result['frames'][0]['model_usable']
    assert result['frames'][1]['criteria_passed']


def test_external_path_rejected_before_filesystem_probe(tmp_path, monkeypatch):
    from gar import astrometry
    def forbidden(*args):
        raise AssertionError('Ne pas sonder un chemin hors de local/')
    monkeypatch.setattr(astrometry, 'no_links', forbidden)
    with pytest.raises(ValueError):
        astrometry.local_path(tmp_path/'external/image.fit', tmp_path/'local')


def test_sip_composition_retains_distortion(tmp_path):
    from astropy.wcs import Sip
    local = tmp_path/'local'
    demo.make_demo(local/'input')
    wp = local/'input/workset.json'
    workset = json.loads(wp.read_text())
    path = local/'input/copies/reference.fit'
    with fits.open(path, memmap=False) as hdus:
        data = hdus[0].data.copy()
        wcs = WCS(hdus[0].header, naxis=2)
    a = np.zeros((3, 3)); b = a.copy()
    a[2, 0] = 3e-5; b[0, 2] = -2e-5
    wcs.sip = Sip(a, b, None, None, wcs.wcs.crpix)
    wcs.wcs.ctype = ['RA---TAN-SIP', 'DEC--TAN-SIP']
    fits.writeto(path, data, wcs.to_header(relax=True), overwrite=True)
    workset['files'][3]['sha256_copy'] = digest(path)
    wp.write_text(json.dumps(workset))
    document = run_registration(wp, 4, [1], local/'result', local)
    frame = document['frames'][0]
    points = np.array([[200., 200.], [384., 384.], [500., 500.]])
    mapped = points@np.asarray(frame['rotation_matrix']).T+frame['translation_pixels']
    sky = composed_sky(frame, points[:, 0], points[:, 1])
    expected = wcs.pixel_to_world(mapped[:, 0], mapped[:, 1])
    assert np.max(sky.separation(expected).arcsec) < 1e-7
    linear = WCS(naxis=2)
    linear.wcs = wcs.wcs
    assert sky[0].separation(linear.pixel_to_world(*mapped[0])).arcsec > 1
