# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Pipeline development fixtures; the two reserved seeds are never analysed here."""
import builtins
from datetime import datetime, timedelta
import json
import importlib
from pathlib import Path
import shutil
import socket
import sys

from astropy.io import fits
import numpy as np
import pytest
from gar.workset import digest, prepare_workset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import make_slow_motion_demo as demo
    import slow_motion_profile as recipe
finally:
    sys.path.pop(0)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def development_workset(base, name='development', clock_step=300., problem=None):
    folder = base/name
    folder.mkdir()
    source = folder/'invented-development-source'
    source.mkdir()
    rng = np.random.default_rng(271828)
    yy, xx = np.mgrid[:512, :512]
    image = np.full((512, 512), 100.)
    for y in np.linspace(48, 464, 10):
        for x in np.linspace(48, 464, 10):
            px, py = np.array([x, y])+rng.uniform(-2, 2, 2)
            peak = rng.uniform(600, 1800)
            image += peak*np.exp(-((xx-px)**2+(yy-py)**2)/(2*2.2**2))
    files = []
    for k in range(8):
        header = fits.Header(dict(OBJECT='Invented development fixture', INSTRUME='Fictional',
            FILTER='SIMULATED', GAIN=80, EQMODE=0, BAYERPAT='GRBG', EXPTIME=10.,
            XPIXSZ=2.9, YPIXSZ=2.9, FOCALLEN=250., GARSYNTH=True))
        header['DATE-OBS'] = (datetime(2025, 1, 1)+timedelta(seconds=k*clock_step)).isoformat()
        if problem == 'optic' and k == 7:
            header['FOCALLEN'] = 251.
        if problem == 'mixed' and k == 7:
            del header['GARSYNTH']
        pixels = np.clip(image+rng.normal(0., 2., image.shape), 0, 65535).astype('uint16')
        path = source/f'pose-{k+1:02d}.fit'
        fits.writeto(path, pixels, header)
        files.append(dict(source=str(path.resolve()), expected_sha256=digest(path)))
    prepare_workset(dict(selection_schema_version='1.0', files=files), folder/'workset', base)
    return folder/'workset/workset.json'


def test_reserved_background_construction_is_predeclared_without_search():
    assert demo.SEEDS == (2026112301, 2026112302)
    assert demo.TIMES == tuple(float(k*300) for k in range(8))
    first = demo.background_sources(demo.SEEDS[0])
    second = demo.background_sources(demo.SEEDS[1])
    assert first == demo.background_sources(demo.SEEDS[0])
    assert [p[:2] for p in first] == [p[:2] for p in second]
    assert first != second and len(first) > 70
    with pytest.raises(ValueError):
        demo.background_sources(271828)


def test_generator_interruption_preserves_partial_state(tmp_path, monkeypatch):
    base = tmp_path/'local'
    base.mkdir()
    def interrupted(*a, **kw):
        raise OSError('Invented interruption')
    monkeypatch.setattr(demo, 'make_context', interrupted)
    with pytest.raises(OSError):
        demo.make(base/'partial', base)
    result = read(base/'partial/contexts.json')
    assert result['status'] == 'incomplete' and result['contexts'] == []


@pytest.fixture(scope='module')
def experiment(tmp_path_factory):
    base = tmp_path_factory.mktemp('slow-development')/'local'
    base.mkdir()
    workset = development_workset(base)
    folder = workset.parent.parent
    baseline = recipe.prepare(workset, folder/'baseline', base)
    assert baseline['registration_available']
    recipe.generate(folder/'baseline/baseline.json', folder/'suite', base)
    recipe.analyze(folder/'suite/manifest.json', folder/'analysis', base)
    recipe.score(folder/'suite/manifest.json', folder/'suite/truth.json',
        folder/'analysis/analysis.json', folder/'score', base)
    return base, folder


def test_existing_outputs_are_preserved(experiment):
    base, folder = experiment
    before = (folder/'analysis/analysis.json').read_bytes()
    with pytest.raises((ValueError, FileExistsError)):
        recipe.analyze(folder/'suite/manifest.json', folder/'analysis', base)
    assert (folder/'analysis/analysis.json').read_bytes() == before


def test_complete_development_results_keep_all_cases_and_scientific_limits(experiment):
    _, folder = experiment
    baseline = read(folder/'baseline/baseline.json')
    manifest = read(folder/'suite/manifest.json')
    analysis = read(folder/'analysis/analysis.json')
    score = read(folder/'score/score.json')
    assert baseline['registration_available'] and baseline['search_status'] == 'complete'
    assert manifest['models'] == baseline['models']
    assert len(manifest['conditions']) == 12 and len(manifest['cases']) == 13
    assert [r['case_id'] for r in analysis['records']] == [c['case_id'] for c in manifest['cases']]
    assert analysis['truth_opened'] is False and analysis['models_refitted'] is False
    assert analysis['status'] == score['status'] == 'complete'
    assert score['planned_injections'] == score['recovered']+score['missed']+score['unavailable'] == 12
    assert score['control_identical_to_baseline']
    assert not score['clock_qualified'] and not score['science_fitness_passed']
    assert not score['known_natural_positive_tested'] and not score['real_data_performance_validated']
    for row in score['rows']:
        assert row['recovered'] in (0, 1, None)


@pytest.mark.parametrize('problem', ['short', 'optic', 'mixed'])
def test_invalid_time_optics_or_source_kind_are_refused_before_prepare_output(tmp_path, problem):
    base = tmp_path/'local'
    base.mkdir()
    workset = development_workset(base, clock_step=10. if problem == 'short' else 300.,
        problem=problem)
    with pytest.raises(ValueError):
        recipe.prepare(workset, base/'refused', base)
    assert not (base/'refused').exists()


def test_duplicate_workset_copy_is_refused(experiment):
    base, folder = experiment
    path = folder/'workset/workset.json'
    value = read(path)
    value['files'][-1] = value['files'][0]
    bad = path.parent/'repeated.json'
    recipe.save(bad, value)
    with pytest.raises(ValueError):
        recipe.prepare(bad, folder/'repeated-output', base)


def test_analysis_is_blind_offline_and_uses_only_copies_and_derivatives(experiment, monkeypatch):
    base, folder = experiment
    original_open, original_path_open, original_stat = builtins.open, Path.open, Path.stat
    def guard(path, args, kwargs):
        if isinstance(path, (str, Path)):
            path = Path(path)
            assert path.name != 'truth.json'
            assert 'invented-development-source' not in path.parts
            if path.suffix.lower() in ('.fit', '.fits', '.npy'):
                assert (args[0] if args else kwargs.get('mode', 'r')) in ('r', 'rb')
    def opened(path, *args, **kwargs):
        guard(path, args, kwargs)
        return original_open(path, *args, **kwargs)
    def path_opened(path, *args, **kwargs):
        guard(path, args, kwargs)
        return original_path_open(path, *args, **kwargs)
    def stated(path, *args, **kwargs):
        guard(path, (), {})
        return original_stat(path, *args, **kwargs)
    def offline(*args, **kwargs):
        raise AssertionError('Aucune connexion réseau pendant la recherche.')
    before = {p: digest(p) for p in (folder/'suite/planes').glob('*.npy')}
    monkeypatch.setattr(builtins, 'open', opened)
    monkeypatch.setattr(Path, 'open', path_opened)
    monkeypatch.setattr(Path, 'stat', stated)
    monkeypatch.setattr(socket.socket, 'connect', offline)
    result = recipe.analyze(folder/'suite/manifest.json', folder/'guarded-analysis', base)
    assert not result['truth_opened'] and result['all_available']
    assert all(digest(p) == expected for p, expected in before.items())


@pytest.mark.parametrize('problem', ['scale', 'parameters', 'hash', 'order', 'external'])
def test_modified_manifest_or_derivative_is_refused(experiment, problem):
    base, folder = experiment
    value = read(folder/'suite/manifest.json')
    if problem == 'scale':
        value['scale_arcsec_per_native_pixel'] *= 2
    elif problem == 'parameters':
        value['profile_parameters']['minimum_frames'] = 5
    elif problem == 'hash':
        value['cases'][0]['frames'][0]['sha256'] = '0'*64
    elif problem == 'order':
        value['cases'].reverse()
    else:
        value['cases'][0]['frames'][0]['local_plane'] = str(base.parent/'outside.npy')
    path = folder/'suite'/f'bad-{problem}.json'
    recipe.save(path, value)
    with pytest.raises(ValueError):
        recipe.analyze(path, folder/f'refused-{problem}', base)


def test_all_candidate_hashes_are_checked_before_truth(experiment, monkeypatch):
    base, folder = experiment
    altered = folder/'altered-analysis'
    shutil.copytree(folder/'analysis', altered)
    item = read(altered/'analysis.json')['records'][-1]
    path = altered/item['file']
    record = read(path)
    record['candidate_count'] += 1
    recipe.save(path, record)
    original = Path.open
    def guarded(path, *args, **kwargs):
        assert path.name != 'truth.json'
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    with pytest.raises(ValueError):
        recipe.score(folder/'suite/manifest.json', folder/'suite/truth.json',
            altered/'analysis.json', folder/'not-scored', base)


def test_interruption_keeps_partial_analysis_and_refuses_score(experiment, monkeypatch):
    base, folder = experiment
    original = recipe.process
    calls = []
    def stopped(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise OSError('Invented interruption after first record')
        return original(*args, **kwargs)
    monkeypatch.setattr(recipe, 'process', stopped)
    with pytest.raises(OSError):
        recipe.analyze(folder/'suite/manifest.json', folder/'partial-analysis', base)
    result = read(folder/'partial-analysis/analysis.json')
    assert result['status'] == 'incomplete' and len(result['records']) == 1
    with pytest.raises(ValueError):
        recipe.score(folder/'suite/manifest.json', folder/'suite/truth.json',
            folder/'partial-analysis/analysis.json', folder/'partial-score', base)


def test_blocked_search_preserves_unknowns_instead_of_zero(experiment, monkeypatch):
    base, folder = experiment
    def blocked(*args, **kwargs):
        raise ValueError('Invented hypothesis ceiling')
    monkeypatch.setattr(recipe, 'process', blocked)
    analysis = recipe.analyze(folder/'suite/manifest.json', folder/'blocked-analysis', base)
    assert analysis['status'] == 'complete' and not analysis['all_available']
    for item in analysis['records']:
        record = read(folder/'blocked-analysis'/item['file'])
        assert record['candidate_count'] is None and record['data'] is None
    score = recipe.score(folder/'suite/manifest.json', folder/'suite/truth.json',
        folder/'blocked-analysis/analysis.json', folder/'blocked-score', base)
    assert score['unavailable'] == 12 and score['available_injections'] == 0
    assert score['control_candidates'] is None and score['unassociated_candidates'] is None
    assert score['false_candidates'] is None and not score['synthetic_fixture_criteria_passed']


@pytest.mark.parametrize('problem', ['nan', 'repeated_index', 'velocity', 'order'])
def test_modified_truth_is_refused_after_search(experiment, problem):
    base, folder = experiment
    value = read(folder/'suite/truth.json')
    if problem == 'nan':
        value['cases'][0]['positions'][0]['x'] = float('nan')
    elif problem == 'repeated_index':
        value['cases'][0]['positions'][1]['frame_index'] = 0
    elif problem == 'velocity':
        value['cases'][0]['velocity_native_per_declared_second'][0] += .0001
    else:
        value['cases'].reverse()
    path = folder/f'bad-truth-{problem}.json'
    path.write_text(json.dumps(value, allow_nan=True), encoding='utf-8')
    with pytest.raises(ValueError):
        recipe.score(folder/'suite/manifest.json', path, folder/'analysis/analysis.json',
            folder/f'bad-truth-score-{problem}', base)


def test_generation_is_repeatable_and_preserves_original_copies(experiment):
    base, folder = experiment
    baseline = read(folder/'baseline/baseline.json')
    original = read(folder/'suite/manifest.json')
    repeated = recipe.generate(folder/'baseline/baseline.json', folder/'suite-again', base)
    assert original['cases'] == repeated['cases']
    assert all(digest(Path(item['local_copy'])) == item['sha256'] for item in baseline['copies'])


def test_checked_score_recalculates_values_without_any_search(experiment, monkeypatch):
    base, folder = experiment
    def forbidden(*args, **kwargs):
        raise AssertionError('Aucun recalcul de détection ou association pour vérifier un score.')
    monkeypatch.setattr(recipe, 'process', forbidden)
    monkeypatch.setattr(recipe, 'find_tracks', forbidden)
    monkeypatch.setattr(recipe, 'detect_sources', forbidden)
    checked = recipe.checked_score(folder/'score/score.json', base)
    assert checked[1] == read(folder/'score/score.json')
    value = read(folder/'score/score.json')
    value['recovered'] += 1
    path = folder/'score/corrupted-score.json'
    recipe.save(path, value)
    with pytest.raises(ValueError):
        recipe.checked_score(path, base)


def drawing_module():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
    try:
        return importlib.import_module('plot_slow_motions')
    finally:
        sys.path.pop(0)


def test_figures_repeat_without_search_and_have_static_alternative(experiment, monkeypatch):
    base, folder = experiment
    drawing = drawing_module()
    def forbidden(*args, **kwargs):
        raise AssertionError('Le dessin ne doit pas rechercher de source ou de trajectoire.')
    for name in ('process', 'find_tracks', 'detect_sources', 'register_spatial'):
        monkeypatch.setattr(recipe, name, forbidden)
    first = drawing.plot(folder/'score/score.json', folder/'figures-first', base)
    second = drawing.plot(folder/'score/score.json', folder/'figures-second', base)
    assert first['figures_sha256'] == second['figures_sha256']
    assert set(first['figures_sha256']) == {
        'recovery.png', 'comparison-first.png', 'comparison-static.png', 'comparison.gif'}
    assert first['synthetic_background'] and first['input_hashes_unchanged']
    assert not first['detector_called'] and not first['association_called']
    assert first['example_cases_fixed'] == ['control', 'r10-a12-p1', 'r30-a12-p1', 'r60-a12-p1']
    assert first['static_eight_frame_case'] == 'r30-a12-p1'
    assert first['playback_milliseconds_per_frame'] == 600
    before = (folder/'figures-first/figures.json').read_bytes()
    with pytest.raises(FileExistsError):
        drawing.plot(folder/'score/score.json', folder/'figures-first', base)
    assert (folder/'figures-first/figures.json').read_bytes() == before


@pytest.mark.parametrize('problem', ['status', 'clock', 'count', 'group', 'domain'])
def test_figures_refuse_incomplete_or_modified_score(experiment, problem):
    base, folder = experiment
    value = read(folder/'score/score.json')
    if problem == 'status':
        value['status'] = 'incomplete'
    elif problem == 'clock':
        value['clock_qualified'] = True
    elif problem == 'count':
        value['recovered'] += 1
    elif problem == 'group':
        value['groups'][0]['recovered'] += 1
    else:
        value['nominal_angular_domain_arcsec_hour'][0] /= 2
    path = folder/f'bad-drawing-score-{problem}.json'
    recipe.save(path, value)
    with pytest.raises(ValueError):
        drawing_module().plot(path, folder/f'bad-figures-{problem}', base)
