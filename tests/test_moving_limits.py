# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

from astropy.io import fits
import numpy as np
import pytest

from gar.moving import PARAMETERS, run_moving_synthetic
from gar.workset import digest

spec = importlib.util.spec_from_file_location('limits', Path(__file__).resolve().parents[1]/'examples/moving_limits.py')
limits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limits)


def protocol():
    return dict(limits_suite_schema_version='1.0', synthetic_only=True, plan_commit=limits.PLAN_COMMIT,
                engine_sha256_lf=limits.ENGINE_SHA256.copy(), seeds=list(limits.SEEDS), conditions=limits.conditions(),
                batches=[dict(group=g, manifest=f'{g}/manifest.json', truth=f'{g}/truth.json')
                         for g in ('grid', 'noise', 'geometry', 'controls')])


def fake_results():
    result = {}
    for group in ('grid', 'noise', 'geometry', 'controls'):
        sequences = []
        for c in limits.conditions():
            if c['group'] != group:
                continue
            for seed in limits.SEEDS:
                injected = int(c['control'] is None)
                # Deliberately all missed, with two false candidates per sequence.
                sequences.append(dict(sequence_id=f'{c["condition_id"]}-s{seed}', seed=seed,
                                      relative_times_seconds=limits.TIMES.tolist(), image_shape=[256, 256],
                                      evaluation=dict(injected=injected, recovered=0, missed=injected,
                                                      false_candidates=2, matches=[]), tracks=[{}, {}],
                                      false_candidate_rates={}))
        result[group] = dict(synthetic_only=True, truth_used_for_detection=False, parameters=deepcopy(PARAMETERS),
                             inputs_sha256_before={'a': 'same'}, inputs_sha256_after={'a': 'same'}, sequences=sequences)
    return result


def test_new_paired_design_is_complete_and_inside_batch_resource_limit():
    cs = limits.conditions()
    assert len(cs) == 24 and set(limits.SEEDS).isdisjoint({17, 23, 41})
    assert [5*sum(c['group'] == g for c in cs) for g in ('grid', 'noise', 'geometry', 'controls')] == [60, 20, 30, 10]
    assert sum(c['control'] is None for c in cs)*5 == 110


def test_known_rigid_geometry_and_input_preservation():
    c = dict(rotation_total_degrees=90., drift_pixels_per_second=.1)
    point = np.array([137.5, 127.5])
    assert np.allclose(limits.transform(point, 70., c), [134.5, 137.5])
    assert np.array_equal(point, [137.5, 127.5])
    assert np.allclose(limits.transform(point, 0., c), point)


def test_engine_freeze_detects_even_comment_change(tmp_path):
    assert limits.verify_engine() == limits.ENGINE_SHA256
    for name in limits.ENGINE_SHA256:
        dest = tmp_path/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text((limits.ROOT/name).read_text(encoding='utf-8'), encoding='utf-8')
    assert limits.verify_engine(tmp_path) == limits.ENGINE_SHA256
    with (tmp_path/'src/gar/moving.py').open('a', encoding='utf-8') as stream:
        stream.write('\n# Different experiment\n')
    with pytest.raises(ValueError, match='moteur a changé'):
        limits.verify_engine(tmp_path)


def test_paired_pixels_have_only_the_injected_gaussian_difference(tmp_path):
    clean = next(c for c in limits.conditions() if c['condition_id'] == 'control-clean')
    bright = next(c for c in limits.conditions() if c['peak_adu'] == 120 and c['group'] == 'grid')
    outputs = []
    for name, c in [('clean', clean), ('bright', bright), ('repeat', bright)]:
        folder = tmp_path/name
        (folder/'copies').mkdir(parents=True)
        outputs.append((folder, *limits.make_sequence(folder, c, 101)))
    a, b, repeat = outputs
    assert b[1]['frames'][0]['sha256'] == repeat[1]['frames'][0]['sha256']
    with fits.open(a[0]/a[1]['frames'][0]['local_copy'], mode='readonly') as h:
        background = h[0].data.copy()
    with fits.open(b[0]/b[1]['frames'][0]['local_copy'], mode='readonly') as h:
        difference = h[0].data-background
    assert difference[85, 50] == pytest.approx(120, abs=2e-5)
    assert difference[85, 51]/difference[85, 50] == pytest.approx(np.exp(-1/(2*1.3**2)), abs=1e-6)
    assert difference[20, 20] == 0
    assert a[2]['injections'] == []
    assert np.allclose(b[2]['injections'][0]['velocity_pixels_per_second'], [.03, 0])


def test_drifting_star_field_produces_false_candidates_without_modifying_pixels(tmp_path):
    base = tmp_path/'local'
    folder = base/'input'
    (folder/'copies').mkdir(parents=True)
    c = next(c for c in limits.conditions() if c['condition_id'] == 'drift-large')
    sequence, truth = limits.make_sequence(folder, c, 101)
    mp, tp = folder/'manifest.json', folder/'truth.json'
    limits.write_json(mp, dict(moving_schema_version='1.0', synthetic=True,
                              time_kind='fictitious_relative_seconds', sequences=[sequence]))
    limits.write_json(tp, dict(truth_schema_version='1.0', manifest_sha256=digest(mp), sequences=[truth]))
    result = run_moving_synthetic(mp, tp, base/'report', base)
    assert result['sequences'][0]['evaluation']['false_candidates'] > 0
    assert not result['summary']['frozen_suite_complete']
    assert result['inputs_sha256_before'] == result['inputs_sha256_after']
    assert np.allclose(truth['injections'][0]['velocity_pixels_per_second'], [.65, 0])


@pytest.mark.parametrize('problem', ['seed', 'condition', 'engine', 'batch', 'path'])
def test_altered_protocol_is_rejected(problem):
    p = protocol()
    if problem == 'seed': p['seeds'][-1] = 17
    elif problem == 'condition': p['conditions'][0]['noise_sigma_adu'] = 1
    elif problem == 'engine': p['engine_sha256_lf'] = {}
    elif problem == 'batch': p['batches'].pop()
    else: p['batches'][0]['manifest'] = '../outside.json'
    with pytest.raises(ValueError):
        limits.validate_suite(p)


def test_all_misses_and_false_candidates_remain_in_descriptive_summary(tmp_path):
    p = protocol()
    result = limits.aggregate(p, fake_results())
    assert result['sequence_count'] == 120 and result['image_count'] == 960
    assert result['injected_total'] == 110 and result['descriptive_only']
    assert sum(c['missed'] for c in result['conditions']) == 110
    assert sum(c['false_candidates'] for c in result['conditions']) == 240
    assert all(c['recall'] is None for c in result['conditions'] if c['group'] == 'controls')
    assert all(c['position_p95_pixels'] is None for c in result['conditions'])
    assert result['conditions'][0]['false_candidates_per_frame'] == .25
    assert not any(result[k] for k in ['clock_qualified', 'real_data_performance_validated', 'scientific_submission_certified'])
    limits.write_summary(tmp_path, result)
    assert '0/0' in (tmp_path/'report.md').read_text(encoding='utf-8')


@pytest.mark.parametrize('problem', ['missing_batch', 'missing_sequence', 'duplicate', 'parameters', 'hash', 'count'])
def test_incomplete_or_incoherent_results_cannot_look_complete(problem):
    results = fake_results()
    if problem == 'missing_batch': results.pop('noise')
    elif problem == 'missing_sequence': results['grid']['sequences'].pop()
    elif problem == 'duplicate': results['grid']['sequences'][-1] = results['grid']['sequences'][0]
    elif problem == 'parameters': results['grid']['parameters']['threshold_sigma'] = 3
    elif problem == 'hash': results['grid']['inputs_sha256_after'] = {'a': 'changed'}
    else: results['grid']['sequences'][0]['evaluation']['recovered'] = 1
    with pytest.raises(ValueError):
        limits.aggregate(protocol(), results)


def test_interrupted_run_keeps_status_and_never_writes_complete_summary(tmp_path):
    base = tmp_path/'local'
    base.mkdir()
    p = protocol()
    for batch in p['batches']:
        folder = base/batch['group']
        folder.mkdir()
        for role in ('manifest', 'truth'):
            path = base/batch[role]
            limits.write_json(path, {})  # Deliberately impossible batch, before any pixel access.
            batch[f'{role}_sha256'] = digest(path)
    limits.write_json(base/'suite.json', p)
    with pytest.raises(ValueError):
        limits.run_suite(base/'suite.json', base/'result', base)
    status = json.loads((base/'result/progress.json').read_text(encoding='utf-8'))
    assert status['status'] == 'incomplete' and status['completed_batches'] == []
    assert not (base/'result/limits.json').exists()


def test_output_outside_local_is_rejected_before_creation(tmp_path):
    with pytest.raises(ValueError):
        limits.make_suite(tmp_path/'outside', tmp_path/'local')
    assert not (tmp_path/'outside').exists()
