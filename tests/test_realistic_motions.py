# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Invented skies, angular-rate arithmetic, and frozen-pipeline integrity only."""
import builtins
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
import shutil
import socket
import sys

from astropy.io import fits
import numpy as np
import pytest
from gar.workset import digest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import make_realistic_motion_demo as demo
    import realistic_motions as recipe
    import injection_recovery as historical
finally:
    sys.path.pop(0)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def headers():
    return [fits.Header(dict(XPIXSZ=2.9, YPIXSZ=2.9, FOCALLEN=250., EXPTIME=10.)) for _ in range(8)]


def test_nominal_angular_scale_and_fixed_domain():
    scale = recipe.scale_from_headers(headers())
    assert scale == pytest.approx(206264.806247*.0029/250, abs=1e-12)
    assert .1*scale*3600 == pytest.approx(861.361830886, rel=1e-7)
    assert 10/(3600*scale) < .1 and 30/(3600*scale) < .1 and 60/(3600*scale) < .1
    assert .1 <= 900/(3600*scale) <= 1.5


def test_eighteen_predeclared_conditions_keep_technical_controls_separate():
    scale = recipe.scale_from_headers(headers()); rows = recipe.conditions(scale)
    assert len(rows) == 18 and len({r['case_id'] for r in rows}) == 18
    angular = [r for r in rows if r['family'] == 'angular']
    technical = [r for r in rows if r['family'] == 'technical_positive']
    assert len(angular) == 16 and len(technical) == 2
    assert {(r['angular_rate_arcsec_hour'], r['peak_sigma'], r['position_index']) for r in angular} == {
        (rate, peak, position) for rate in (10., 30., 60., 900.) for peak in (6, 12) for position in (0, 1)}
    assert all(r['smear_samples'] == 7 for r in angular)
    assert all(r['smear_samples'] == 1 and r['angular_rate_arcsec_hour'] is None
        and r['speed_native_per_declared_second'] == .5 and r['in_speed_domain'] for r in technical)
    assert all(r['in_speed_domain'] == (r['angular_rate_arcsec_hour'] == 900.) for r in angular)


def test_trajectory_uses_native_coordinates_and_fixed_directions():
    spec = recipe.conditions(recipe.scale_from_headers(headers()))[-2]
    positions, velocity = recipe.trajectory([512, 512], [0., 10.], spec)
    assert np.allclose(positions[0], [.35*512, .35*512])
    assert np.linalg.norm(velocity) == pytest.approx(.5)
    assert np.allclose(positions[1]-positions[0], [5*np.sqrt(3)/2, 2.5])


@pytest.mark.parametrize('problem', ['missing', 'different', 'zero', 'nonsquare', 'nonfinite'])
def test_angular_scale_requires_consistent_declared_headers(problem):
    values = headers()
    if problem == 'missing': del values[0]['XPIXSZ']
    elif problem == 'different': values[0]['FOCALLEN'] = 251.
    elif problem == 'zero':
        for h in values: h['FOCALLEN'] = 0.
    elif problem == 'nonsquare':
        for h in values: h['YPIXSZ'] = 3.
    else:
        values = [dict(h) for h in values]
        values[0]['XPIXSZ'] = float('nan')
    with pytest.raises((ValueError, KeyError, TypeError)):
        recipe.scale_from_headers(values)


def test_smearing_preserves_model_flux_and_spreads_it_without_altering_input():
    plane = np.zeros((128, 128), dtype='float32')
    center = np.array([128.5, 128.5]); peak = 12.
    point = recipe.inject(plane, center, np.array([1., 0.]), 10., peak, smear=False)
    smear = recipe.inject(plane, center, np.array([1., 0.]), 10., peak, smear=True)
    assert point.dtype == smear.dtype == np.dtype('float32')
    assert smear.sum() == pytest.approx(float(point.sum()), rel=1e-4)
    assert smear.max() < point.max() and not plane.any()
    yy, xx = np.mgrid[:128, :128]
    def variance_x(image):
        mean = float((image*xx).sum()/image.sum())
        return float((image*(xx-mean)**2).sum()/image.sum())
    assert variance_x(smear) > variance_x(point)+2.
    assert abs(float((smear*yy).sum()/smear.sum())-64.) < 1e-3


def test_static_injection_and_original_masks_are_preserved():
    plane = np.zeros((128, 128), dtype='float32'); plane[63, 64] = np.nan
    before = plane.copy()
    point = recipe.inject(plane, [128.5, 128.5], np.array([0., 0.]), 10., 12., smear=False)
    smear = recipe.inject(plane, [128.5, 128.5], np.array([0., 0.]), 10., 12., smear=True)
    assert np.allclose(point, smear, atol=2e-6, rtol=0, equal_nan=True)
    assert np.array_equal(plane, before, equal_nan=True) and np.isnan(smear[63, 64])
    assert point[0, 0] == 0.


@pytest.mark.parametrize('exposure,peak', [(0., 12.), (-1., 12.), (float('nan'), 12.), (10., 0.), (10., float('inf'))])
def test_nonphysical_exposure_or_model_amplitude_is_refused(exposure, peak):
    with pytest.raises(ValueError):
        recipe.inject(np.zeros((128, 128), dtype='float32'), [128.5, 128.5], [0., 0.], exposure, peak)


def test_full_trail_support_must_stay_inside_image():
    with pytest.raises(ValueError):
        recipe.inject(np.zeros((128, 128), dtype='float32'), [1., 128.5], [1., 0.], 10., 12.)


def test_generator_placement_is_fixed_and_not_tuned_by_detector():
    first = demo.background_sources(2026111901)
    assert first == demo.background_sources(2026111901)
    assert len(first) > 80
    assert first != demo.background_sources(2026111902)
    assert [s[:2] for s in first] == [s[:2] for s in demo.background_sources(2026111902)]
    with pytest.raises(ValueError): demo.background_sources(123)


def test_interrupted_background_generation_keeps_partial_state(tmp_path, monkeypatch):
    base = tmp_path/'local'; base.mkdir()
    def interrupted(*a, **kw): raise OSError('Invented interrupted background construction')
    monkeypatch.setattr(demo, 'make_context', interrupted)
    with pytest.raises(OSError): demo.make(base/'partial', base)
    result = read(base/'partial/contexts.json')
    assert result['status'] == 'incomplete' and result['contexts'] == []


def test_historical_recipes_and_thresholds_are_unchanged():
    root = Path(__file__).resolve().parents[1]
    for name, value in {
        'src/gar/moving.py': 'f492032e0188310484faaf372db4c96597fd7910ecd3821629edb8365f27be67',
        'examples/injection_recovery.py': '7f0ed216d7822180f88e2f761ffe95968805946f9771cc8b03effa8c8d842b94',
        'examples/run_seestar_pilot.py': '605504751a6bbc25ffd1134b4c55efcebf47baf31ce044b70c229f47c9553e08',
    }.items():
        assert sha256((root/name).read_text(encoding='utf-8').encode()).hexdigest() == value


@pytest.fixture(scope='module')
def experiments(tmp_path_factory):
    base = tmp_path_factory.mktemp('representative')/'local'; base.mkdir()
    created = demo.make(base/'backgrounds', base)
    results = {}
    for context in created['contexts']:
        name = f'context-s{context["seed"]}'
        output = base/name
        recipe.generate(Path(context['pilot_path']), output/'suite', base)
        recipe.analyze(output/'suite/manifest.json', output/'analysis', base)
        result = recipe.score(output/'suite/manifest.json', output/'suite/truth.json',
            output/'analysis/analysis.json', output/'score', base)
        results[context['seed']] = result
    return base, created, results


@pytest.mark.parametrize('seed', demo.SEEDS)
def test_background_headers_and_frozen_baselines_are_explicit(experiments, seed):
    base, created, _ = experiments
    assert created['status'] == 'complete' and created['all_contexts_available']
    assert created['synthetic'] and created['contexts_share_grid_positions']
    assert created['relative_fictitious_seconds'] == [float(k*10) for k in range(8)]
    path = base/'backgrounds'/f'context-s{seed}'
    report = read(path/'pilot/pilot.json')
    assert report['input_kind'] == 'synthetic_demo' and report['candidate_count'] == 0
    for k, item in enumerate(report['copies']):
        p = Path(item['local_copy'])
        assert digest(p) == item['sha256']
        with fits.open(p, mode='readonly', memmap=False) as hdus:
            h = hdus[0].header
            assert h['GARSYNTH'] and h['XPIXSZ'] == h['YPIXSZ'] == 2.9
            assert h['FOCALLEN'] == 250. and h['EXPTIME'] == 10.
            assert hdus[0].data.shape == (512, 512)
    assert len(read(base/f'context-s{seed}'/'suite/manifest.json')['cases']) == 19


@pytest.mark.parametrize('seed', demo.SEEDS)
def test_positive_technical_controls_do_not_validate_the_uncovered_slow_domain(experiments, seed):
    base, _, results = experiments; result = results[seed]
    assert result['status'] == 'complete' and result['inputs_unchanged']
    assert result['technical_recovered'] == result['technical_available'] == 2
    assert result['slow_recovered'] == 0 and result['slow_available'] == 12
    assert not result['slow_domain_covered'] and not result['science_fitness_passed']
    assert result['synthetic_fixture_criteria_passed']
    assert not result['clock_qualified'] and not result['known_natural_positive_tested']
    assert not result['real_data_performance_validated']
    assert result['control_candidates'] == 0 and result['control_identical_to_baseline']
    assert result['planned_injections'] == result['recovered']+result['missed']+result['unavailable'] == 18
    assert result['unavailable'] == 0
    baseline = read(base/'backgrounds'/f'context-s{seed}'/'pilot/pilot.json')
    manifest = read(base/f'context-s{seed}'/'suite/manifest.json')
    assert manifest['models'] == baseline['models']


def test_analysis_is_blind_offline_and_only_reads_existing_copies(experiments, monkeypatch):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    original_open, original_path_open, original_stat = builtins.open, Path.open, Path.stat
    def guard(path, args, kwargs):
        if isinstance(path, (str, Path)):
            p = Path(path)
            assert p.name != 'truth.json' and 'invented-source' not in p.parts
            if p.suffix == '.fit':
                assert (args[0] if args else kwargs.get('mode', 'r')) in ('r', 'rb')
    def opened(path, *a, **kw):
        guard(path, a, kw); return original_open(path, *a, **kw)
    def path_opened(path, *a, **kw):
        guard(path, a, kw); return original_path_open(path, *a, **kw)
    def stated(path, *a, **kw):
        guard(path, (), {}); return original_stat(path, *a, **kw)
    def offline(*a, **kw): raise AssertionError('Analysis must remain offline')
    monkeypatch.setattr(builtins, 'open', opened); monkeypatch.setattr(Path, 'open', path_opened)
    monkeypatch.setattr(Path, 'stat', stated); monkeypatch.setattr(socket.socket, 'connect', offline)
    before = {p: digest(p) for p in (folder/'suite/planes').glob('*.npy')}
    result = recipe.analyze(folder/'suite/manifest.json', folder/'guarded-analysis', base)
    assert not result['truth_opened'] and result['all_available']
    assert all(digest(p) == h for p, h in before.items())


def test_generation_is_deterministic_and_preserves_original_copies(experiments):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    original = read(folder/'suite/manifest.json')
    pilot_path = base/'backgrounds'/f'context-s{demo.SEEDS[0]}'/'pilot/pilot.json'
    regenerated = recipe.generate(pilot_path, folder/'suite-again', base)
    assert original['cases'] == regenerated['cases']
    report = read(pilot_path)
    assert all(digest(Path(item['local_copy'])) == item['sha256'] for item in report['copies'])


@pytest.mark.parametrize('problem', ['scale', 'rate', 'samples', 'wrong_hash', 'external'])
def test_modified_protocol_or_derivative_is_refused(experiments, monkeypatch, problem):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    value = read(folder/'suite/manifest.json')
    if problem == 'scale': value['scale_arcsec_per_native_pixel'] *= 2
    elif problem == 'rate': value['conditions'][0]['angular_rate_arcsec_hour'] = 11.
    elif problem == 'samples': value['exposure_samples'] = 1
    elif problem == 'wrong_hash': value['cases'][0]['frames'][0]['sha256'] = '0'*64
    else:
        outside = base.parent/'outside.npy'
        value['cases'][0]['frames'][0]['local_plane'] = str(outside)
        original = Path.stat
        def stated(path, *a, **kw):
            assert path != outside; return original(path, *a, **kw)
        monkeypatch.setattr(Path, 'stat', stated)
    path = folder/'suite'/f'bad-{problem}.json'; recipe.save(path, value)
    with pytest.raises(ValueError): recipe.analyze(path, folder/f'bad-output-{problem}', base)


def test_corrupted_candidate_is_rejected_before_truth(experiments, monkeypatch):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    shutil.copytree(folder/'analysis', folder/'altered-analysis')
    path = folder/'altered-analysis/cases/technical-p1.json'
    record = read(path); record['candidate_count'] += 1; recipe.save(path, record)
    original = Path.open
    def guarded(path, *a, **kw):
        assert path.name != 'truth.json'; return original(path, *a, **kw)
    monkeypatch.setattr(Path, 'open', guarded)
    with pytest.raises(ValueError):
        recipe.score(folder/'suite/manifest.json', folder/'suite/truth.json',
            folder/'altered-analysis/analysis.json', folder/'not-scored', base)


def test_interrupted_analysis_keeps_progress_and_never_scores_as_complete(experiments, monkeypatch):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    original = historical.process; calls = []
    def stopped(*a, **kw):
        calls.append(1)
        if len(calls) == 2: raise OSError('Invented interruption after the control')
        return original(*a, **kw)
    monkeypatch.setattr(historical, 'process', stopped)
    with pytest.raises(OSError): recipe.analyze(folder/'suite/manifest.json', folder/'partial', base)
    result = read(folder/'partial/analysis.json')
    assert result['status'] == 'incomplete' and len(result['records']) == 1
    with pytest.raises(ValueError):
        recipe.score(folder/'suite/manifest.json', folder/'suite/truth.json',
            folder/'partial/analysis.json', folder/'partial-score', base)


def test_existing_outputs_are_preserved(experiments):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    before = (folder/'analysis/analysis.json').read_bytes()
    with pytest.raises(FileExistsError): recipe.analyze(folder/'suite/manifest.json', folder/'analysis', base)
    assert (folder/'analysis/analysis.json').read_bytes() == before


def test_longer_context_is_refused_without_changing_frozen_time_limit(experiments):
    base, _, _ = experiments
    value = read(base/'backgrounds'/f'context-s{demo.SEEDS[0]}'/'pilot/pilot.json')
    value['relative_declared_seconds'][-1] = 139.
    path = base/'too-long-pilot.json'; recipe.save(path, value)
    with pytest.raises(ValueError): recipe.generate(path, base/'too-long-suite', base)
    assert not (base/'too-long-suite').exists()


def test_blocked_searches_keep_unknown_counts_instead_of_false_zero(experiments, monkeypatch):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    def blocked(*a, **kw): raise ValueError('Invented source-count limit')
    monkeypatch.setattr(historical, 'process', blocked)
    analysis = recipe.analyze(folder/'suite/manifest.json', folder/'blocked-analysis', base)
    assert analysis['status'] == 'complete' and not analysis['all_available']
    result = recipe.score(folder/'suite/manifest.json', folder/'suite/truth.json',
        folder/'blocked-analysis/analysis.json', folder/'blocked-score', base)
    assert result['unavailable'] == 18 and result['available_injections'] == 0
    assert result['control_candidates'] is None and result['unassociated_candidates'] is None
    assert result['false_candidates'] is None and not result['synthetic_fixture_criteria_passed']
    assert all(g['available'] == 0 and g['unassociated_candidates'] is None for g in result['groups'])


def test_candidate_mutation_during_analysis_prevents_complete_seal(experiments, monkeypatch):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    original = historical.process; calls = []
    def mutate_then_block(*a, **kw):
        calls.append(1)
        if len(calls) == 1: return original(*a, **kw)
        if len(calls) == 2:
            path = folder/'mutated-during-analysis/cases/control.json'
            value = read(path); value['changed_after_seal'] = True; recipe.save(path, value)
        raise ValueError('Remaining invented cases blocked after mutation')
    monkeypatch.setattr(historical, 'process', mutate_then_block)
    with pytest.raises(ValueError):
        recipe.analyze(folder/'suite/manifest.json', folder/'mutated-during-analysis', base)
    assert read(folder/'mutated-during-analysis/analysis.json')['status'] == 'incomplete'


def drawing_module():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
    try:
        return importlib.import_module('plot_realistic_motions')
    finally:
        sys.path.pop(0)


def test_figures_repeat_without_detection_or_association(experiments, monkeypatch):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    drawing = drawing_module()
    def forbidden(*a, **kw): raise AssertionError('Drawing cannot search for sources or tracks')
    for name in ('process', 'detect_sources'): monkeypatch.setattr(historical, name, forbidden)
    monkeypatch.setattr(recipe.pilot, 'declared_tracks', forbidden)
    first = drawing.plot(folder/'score/score.json', folder/'figures-first', base)
    second = drawing.plot(folder/'score/score.json', folder/'figures-second', base)
    assert first['figures_sha256'] == second['figures_sha256']
    assert set(first['figures_sha256']) == {'coverage-recovery.png', 'comparison-first.png', 'comparison.gif'}
    assert first['synthetic_background'] and first['input_hashes_unchanged']
    assert not first['detector_called'] and not first['association_called']
    assert first['example_cases_fixed'] == ['control', 'r30-a12-p1', 'r900-a12-p1', 'technical-p1']
    before = (folder/'figures-first/figures.json').read_bytes()
    with pytest.raises(FileExistsError): drawing.plot(folder/'score/score.json', folder/'figures-first', base)
    assert (folder/'figures-first/figures.json').read_bytes() == before


@pytest.mark.parametrize('problem', ['incomplete', 'science', 'clock', 'count', 'group', 'control', 'fixture', 'domain'])
def test_figures_refuse_incomplete_or_falsified_scores(experiments, problem):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    value = read(folder/'score/score.json')
    if problem == 'incomplete': value['status'] = 'incomplete'
    elif problem == 'science': value['science_fitness_passed'] = True
    elif problem == 'clock': value['clock_qualified'] = True
    elif problem == 'count': value['recovered'] += 1
    elif problem == 'group': value['groups'][0]['recovered'] += 1
    elif problem == 'control': value['control_identical_to_baseline'] = False
    elif problem == 'fixture': value['synthetic_fixture_criteria_passed'] = False
    else: value['engine_angular_domain_arcsec_hour'][0] /= 2
    path = folder/f'bad-score-{problem}.json'; recipe.save(path, value)
    with pytest.raises(ValueError): drawing_module().plot(path, folder/f'bad-figures-{problem}', base)


def test_figures_refuse_modified_linked_candidates(experiments):
    base, _, _ = experiments; folder = base/f'context-s{demo.SEEDS[0]}'
    value = read(folder/'score/score.json'); value['analysis_sha256'] = '0'*64
    path = folder/'bad-linked-analysis-score.json'; recipe.save(path, value)
    with pytest.raises(ValueError): drawing_module().plot(path, folder/'bad-linked-figures', base)
