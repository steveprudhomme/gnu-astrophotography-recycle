# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys

from astropy.io import fits
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import spatial_controls as spatial
    import compare_spatial_controls as recipe
finally:
    sys.path.pop(0)


def points():
    return np.random.default_rng(99).uniform(25, 231, (80, 2))


def test_partition_is_deterministic_unique_complete_and_spatially_spread():
    p = points(); before = p.copy()
    chosen = spatial.select_controls(p, (256, 256))
    assert np.array_equal(chosen, spatial.select_controls(p, (256, 256)))
    train = np.setdiff1d(np.arange(len(p)), chosen)
    assert len(chosen) == 20 and len(set(chosen)) == 20
    assert set(train).isdisjoint(chosen) and set(train) | set(chosen) == set(range(80))
    assert len(set(map(tuple, p[chosen] >= 128))) == 4
    assert len(set(map(tuple, np.floor(p[chosen]*3/256)))) >= 6
    assert np.array_equal(p, before)


@pytest.mark.parametrize('kind', ['missing_quadrant', 'narrow'])
def test_real_missing_coverage_is_never_invented(kind):
    p = points()
    if kind == 'missing_quadrant': p = p[(p[:, 0] >= 150) | (p[:, 1] >= 150)]
    else: p[:, 1] = 110 + np.arange(80)%35
    ids = spatial.select_controls(p, (256, 256))
    if kind == 'missing_quadrant': assert len(set(map(tuple, p[ids] >= 128))) == 3
    else: assert len(set(map(tuple, np.floor(p[ids]*3/256)))) <= 3


@pytest.mark.parametrize('kind', ['nonfinite', 'outside', 'few'])
def test_bad_centres_cannot_be_selected(kind):
    p = points()
    if kind == 'nonfinite': p[0, 0] = np.nan
    elif kind == 'outside': p[0, 1] = 256
    else: p = p[:3]
    with pytest.raises(ValueError): spatial.select_controls(p, (256, 256))


def test_holdout_is_chosen_before_solve_and_never_enters_training(monkeypatch):
    p = points(); ids = spatial.select_controls(p, (256, 256)); calls = []
    def solve(train, reference):
        assert np.array_equal(train, p[np.setdiff1d(np.arange(80), ids)])
        calls.append(1)
        return np.eye(2), np.zeros(2), 1
    monkeypatch.setattr(spatial, 'solve', solve)
    r = spatial.register_spatial(p, p, (256, 256))
    assert len(calls) == 1 and r['model_usable']
    assert r['criteria'] == recipe.previous.CRITERIA
    assert 'rms_pixels' not in r['selected_control_coverage']


def test_perturbing_fixed_controls_changes_verdict_never_the_fitted_model():
    p = points(); ids = spatial.select_controls(p, (256, 256))
    first = spatial.fit_partition(p, p.copy(), (256, 256), ids)
    changed = p.copy(); changed[ids] += [1.9, 0]
    second = spatial.fit_partition(changed, p.copy(), (256, 256), ids)
    assert first['rotation_matrix'] == second['rotation_matrix']
    assert first['translation_pixels'] == second['translation_pixels']
    assert first['model_usable'] and not second['model_usable']
    assert second['metrics']['control']['p95_pixels'] > 1.5


@pytest.mark.parametrize('ids', [[1, 1], [-1], [80], [1.5]])
def test_invalid_control_indices_are_rejected(ids):
    with pytest.raises(ValueError): spatial.fit_partition(points(), points(), (256, 256), ids)


def test_both_methods_share_native_and_stellar_detection(monkeypatch):
    native_calls, star_calls = [], []
    def native(image):
        k = int(image[0, 0]); native_calls.append(k)
        return np.array([[50+5*k, 85+2*k]]), {}
    def stars(image):
        star_calls.append(int(image[0, 0])); return points(), {}
    def reject(*args): return {'model_usable': False}
    monkeypatch.setattr(recipe, 'detect_sources', native)
    monkeypatch.setattr(recipe, 'detect', stars)
    monkeypatch.setattr(recipe, 'register_points', reject)
    monkeypatch.setattr(recipe, 'register_spatial', reject)
    r = recipe.process_sequence([np.full((256, 256), k) for k in range(8)])
    assert native_calls == star_calls == list(range(8))
    assert all(b['after'] is None for b in r['methods'].values())
    assert len(r['before']['tracks']) == 1


def fake_records():
    result = []
    for c in recipe.conditions():
        for seed in recipe.SEEDS:
            branches = {}
            for method in recipe.METHODS:
                available = c['scope'] != 'negative'
                e = dict(injected=int(c['mobile']), recovered=int(c['mobile']), missed=0, false_candidates=0,
                         matches=[dict(position_errors_pixels=[.01]*8, velocity_vector_error_pixels_per_second=.001)] if c['mobile'] else [])
                branches[method] = dict(after_available=available, after={'evaluation': e} if available else None)
            result.append(dict(sequence_id=f'{c["condition_id"]}-s{seed}', condition_id=c['condition_id'], seed=seed, methods=branches))
    return result


def test_summary_reports_transitions_and_only_same_sequence_pairs():
    records = fake_records()
    records[0]['methods']['historical'] = dict(after_available=False, after=None)
    r = recipe.summarize(records)
    row = r['conditions'][0]
    assert row['transitions']['refused_to_accepted'] == 1 and row['paired']['sequence_count'] == 4
    assert row['methods']['historical']['available'] == 4 and row['methods']['spatial']['available'] == 5
    assert r['exploratory_criteria_passed']
    for row in r['conditions']:
        if row['scope'] == 'negative': assert row['methods']['spatial']['false_candidates'] is None


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'unblock_negative', 'lose_old', 'position_error'])
def test_incomplete_or_failed_criteria_cannot_become_success(problem):
    records = fake_records()
    if problem == 'missing': records.pop()
    elif problem == 'duplicate': records[-1] = records[0]
    elif problem == 'unblock_negative': records[-1]['methods']['spatial'] = deepcopy(records[0]['methods']['spatial'])
    elif problem == 'lose_old': records[0]['methods']['spatial'] = dict(after_available=False, after=None)
    else:
        for r in records[:2]: r['methods']['spatial']['after']['evaluation']['matches'][0]['position_errors_pixels'] = [1.]*8
    if problem in ['missing', 'duplicate']:
        with pytest.raises(ValueError): recipe.summarize(records)
    else: assert not recipe.summarize(records)['exploratory_criteria_passed']


def test_full_pixel_inputs_readonly_truth_after_both_methods_frozen_and_interruption(tmp_path, monkeypatch):
    base = tmp_path/'local'
    recipe.make_suite(base/'input', base)
    real_loads, real_open = json.loads, fits.open
    calls = []
    def process(images):
        calls.append(1)
        return dict(before={'tracks': []}, methods={m: dict(after_available=False, after=None) for m in recipe.METHODS})
    monkeypatch.setattr(recipe, 'process_sequence', process)
    def loads(text, *args, **kwargs):
        data = real_loads(text, *args, **kwargs)
        if isinstance(data, dict) and 'spatial_truth_schema_version' in data:
            assert len(calls) == 50
            assert len(list((base/'output').glob('*-s*.json'))) == 50
        return data
    def opened(path, *args, **kwargs):
        assert Path(path).is_relative_to(base/'input/copies') and kwargs['mode'] == 'readonly'
        return real_open(path, *args, **kwargs)
    def forbidden(*args, **kwargs): raise AssertionError('Réseau interdit')
    monkeypatch.setattr(json, 'loads', loads); monkeypatch.setattr(fits, 'open', opened)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    r = recipe.run_suite(base/'input/manifest.json', base/'input/truth.json', base/'output', base)
    assert r['inputs_unchanged'] and not r['truth_used_for_registration'] and r['suite_complete']
    assert not r['summary']['exploratory_criteria_passed']
    def fail(images): raise ValueError('Interruption conservée')
    monkeypatch.setattr(recipe, 'process_sequence', fail)
    with pytest.raises(ValueError): recipe.run_suite(base/'input/manifest.json', base/'input/truth.json', base/'partial', base)
    assert real_loads((base/'partial/progress.json').read_text())['status'] == 'incomplete'
    assert not (base/'partial/spatial.json').exists()
