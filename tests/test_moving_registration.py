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

from gar.workset import digest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import moving_registration as recipe
finally:
    sys.path.pop(0)


def model(angle=0, translation=(0, 0), usable=True):
    theta = np.deg2rad(angle)
    return dict(model_usable=usable, rotation_matrix=[[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]],
                translation_pixels=list(translation))


def test_coordinate_rotation_translation_overlap_and_input_preservation():
    p = np.array([[30., 20.], [250., 250.]])
    before = p.copy()
    mapped, dropped = recipe.map_detections([p], [model(90, (240, 0))])
    assert np.allclose(mapped[0], [[220, 30]]) and dropped == [1]
    assert np.array_equal(p, before)


@pytest.mark.parametrize('problem', ['refused', 'nonfinite', 'missing_model'])
def test_unusable_mapping_cannot_turn_into_identity(problem):
    models = [model()]
    if problem == 'refused': models[0]['model_usable'] = False
    elif problem == 'nonfinite': models[0]['translation_pixels'][0] = float('nan')
    else: models = []
    with pytest.raises(ValueError):
        recipe.map_detections([np.array([[20., 30.]])], models)


def test_every_native_detection_is_measured_once_and_failed_pose_blocks_after(monkeypatch):
    calls = []
    times = recipe.TIMES
    def detected(image):
        k = int(image[0, 0]); calls.append(k)
        return np.array([[50+.5*times[k], 85+.2*times[k]]]), {'selected': 1}
    monkeypatch.setattr(recipe, 'detect_sources', detected)
    monkeypatch.setattr(recipe, 'detect', lambda image: (np.array([[20., 30.], [50., 70.], [80., 90.]]), {}))
    def refuse(*args): raise ValueError('Pas assez de contrôles')
    monkeypatch.setattr(recipe, 'register_points', refuse)
    images = [np.full((256, 256), k, dtype=float) for k in range(8)]
    r = recipe.process_sequence(images)
    assert calls == list(range(8))
    assert r['after'] is None and r['after_available'] is False
    assert r['blocked_frame_indices'] == list(range(1, 8))
    assert len(r['before']['tracks']) == 1


@pytest.fixture(scope='module')
def pixel_case(tmp_path_factory):
    folder = tmp_path_factory.mktemp('registered')/'local/input'
    (folder/'copies').mkdir(parents=True)
    c = next(c for c in recipe.conditions() if c['condition_id'] == 'combined')
    sequence, truth = recipe.make_sequence(folder, c, 607)
    images = []
    for frame in sequence['frames']:
        with fits.open(folder/frame['local_copy'], mode='readonly') as hdus:
            images.append(hdus[0].data.copy())
    return folder, sequence, truth, images


def test_real_pixel_chain_uses_reserved_controls_is_offline_and_preserves_images(pixel_case, monkeypatch):
    folder, sequence, truth, images = pixel_case
    copies = [p.copy() for p in images]
    def no_network(*args, **kwargs): raise AssertionError('Réseau interdit')
    monkeypatch.setattr(socket, 'create_connection', no_network)
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    result = recipe.process_sequence(images)
    assert all(np.array_equal(a, b) for a, b in zip(images, copies))
    for m in result['registration'][1:]:
        if 'training_detection_indices' in m:
            assert set(m['training_detection_indices']).isdisjoint(m['control_detection_indices'])
            assert m['criteria'] == recipe.CRITERIA
    result.update(sequence_id=sequence['sequence_id'], condition_id='combined', seed=607)
    answers = dict(registration_truth_schema_version='1.0', manifest_sha256='same', sequences=[truth])
    frozen = deepcopy(result)
    scored = recipe.score_records([result], answers, 'same')[0]
    assert result == frozen  # Evaluation must not rewrite candidates or registration.
    assert scored['before']['evaluation']['false_candidates'] > 0
    for frame in sequence['frames']:
        assert digest(folder/frame['local_copy']) == frame['sha256']


def test_truth_changes_scoring_without_changing_models_or_candidates(pixel_case):
    _, sequence, truth, _ = pixel_case
    before = deepcopy(truth['before'][0])
    track = dict(candidate_id=1, velocity_pixels_per_second=before['velocity_pixels_per_second'],
                 points=[dict(frame_index=p['frame_index'], x=p['x'], y=p['y']) for p in before['positions']])
    record = dict(sequence_id=sequence['sequence_id'], condition_id='combined', seed=607,
                  before={'tracks': [track]}, after=None, after_available=False, registration=[model(usable=False)]*8)
    answers = dict(registration_truth_schema_version='1.0', manifest_sha256='same', sequences=[deepcopy(truth)])
    scored = recipe.score_records([record], answers, 'same')
    assert scored[0]['before']['evaluation']['recovered'] == 1
    for p in answers['sequences'][0]['before'][0]['positions']: p['x'] += 10
    changed = recipe.score_records([record], answers, 'same')
    assert changed[0]['before']['evaluation']['recovered'] == 0
    assert changed[0]['before']['tracks'] == scored[0]['before']['tracks'] == record['before']['tracks']
    assert changed[0]['registration'] == scored[0]['registration']


def fake_scored():
    records = []
    match = dict(position_errors_pixels=[.01]*8, velocity_vector_error_pixels_per_second=.001)
    for c in recipe.conditions():
        for seed in recipe.SEEDS:
            available = c['scope'] != 'negative'
            e = dict(injected=int(c['mobile']), recovered=int(c['mobile']), missed=0,
                     false_candidates=0, matches=[deepcopy(match)] if c['mobile'] else [])
            before = {**deepcopy(e), 'false_candidates': 80 if c['drift_pixels_per_second'] else 0}
            records.append(dict(sequence_id=f'{c["condition_id"]}-s{seed}', condition_id=c['condition_id'], seed=seed,
                                before={'evaluation': before}, after={'evaluation': e} if available else None,
                                after_available=available))
    return records


def test_fixed_criteria_and_unavailable_counts_cannot_look_like_zero_false():
    records = fake_scored()
    summary = recipe.summarize(records)
    assert summary['exploratory_criteria_passed']
    negative = next(c for c in summary['conditions'] if c['scope'] == 'negative')
    assert negative['after_false_candidates'] is None and negative['after_recovered'] is None
    assert negative['after_blocked'] == 5
    records[0].update(after_available=False, after=None)
    result = recipe.summarize(records)
    assert not result['exploratory_criteria_passed'] and not result['criteria']['primary_20_mobiles_recovered']


def test_comparison_uses_the_same_subset_and_keeps_blocked_raw_counts():
    records = fake_scored()
    drift = next(r for r in records if r['condition_id'] == 'drift')
    drift.update(after=None, after_available=False)
    summary = recipe.summarize(records)
    row = next(c for c in summary['conditions'] if c['condition_id'] == 'drift')
    assert row['before_false_candidates'] == 400
    assert row['paired_before_false_candidates'] == 320
    assert row['after_available'] == 4 and row['after_blocked'] == 1
    assert row['after_false_candidates'] == 0
    assert summary['drift_false_reduction_fraction'] is None


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'wrong_condition', 'error', 'false', 'no_before_false'])
def test_no_success_after_incomplete_campaign_or_failed_predeclared_criteria(problem):
    records = fake_scored()
    if problem == 'missing': records.pop()
    elif problem == 'duplicate': records[-1] = records[0]
    elif problem == 'wrong_condition': records[0]['condition_id'] = 'drift'
    elif problem == 'error':
        # More than 5% of points must exceed the limit to force the pooled P95 above it.
        for r in records[:2]: r['after']['evaluation']['matches'][0]['position_errors_pixels'] = [1.]*8
    elif problem == 'false': records[0]['after']['evaluation']['false_candidates'] = 1
    else:
        for r in records: r['before']['evaluation']['false_candidates'] = 0
    if problem in ['missing', 'duplicate', 'wrong_condition']:
        with pytest.raises(ValueError): recipe.summarize(records)
    else:
        r = recipe.summarize(records)
        assert not r['exploratory_criteria_passed']
        if problem == 'no_before_false': assert r['drift_false_reduction_fraction'] is None


def test_truth_is_only_parsed_after_all_frozen_branches_and_partial_outputs_survive(tmp_path, monkeypatch):
    base = tmp_path/'local'
    recipe.make_suite(base/'input', base)
    real_loads = json.loads
    calls = []
    def process(images):
        calls.append(len(images))
        return dict(before={'tracks': []}, after=None, after_available=False, registration=[model(usable=False)]*8)
    monkeypatch.setattr(recipe, 'process_sequence', process)
    def loads(text, *a, **kw):
        data = real_loads(text, *a, **kw)
        if isinstance(data, dict) and 'registration_truth_schema_version' in data:
            assert len(calls) == 40
            assert len(list((base/'report').glob('*-s*.json'))) == 40
        return data
    monkeypatch.setattr(json, 'loads', loads)
    r = recipe.run_suite(base/'input/manifest.json', base/'input/truth.json', base/'report', base)
    assert r['suite_complete'] and not r['summary']['exploratory_criteria_passed']
    assert r['inputs_unchanged'] and not r['truth_used_for_registration']
    def fail(images): raise ValueError('Erreur conservée')
    monkeypatch.setattr(recipe, 'process_sequence', fail)
    with pytest.raises(ValueError, match='Erreur conservée'):
        recipe.run_suite(base/'input/manifest.json', base/'input/truth.json', base/'partial', base)
    progress = real_loads((base/'partial/progress.json').read_text(encoding='utf-8'))
    assert progress['status'] == 'incomplete' and not (base/'partial/comparison.json').exists()


def test_generators_refuse_existing_or_external_destination(tmp_path):
    base = tmp_path/'local'
    (base/'existing').mkdir(parents=True)
    with pytest.raises(FileExistsError): recipe.make_suite(base/'existing', base)
    with pytest.raises(ValueError): recipe.make_suite(tmp_path/'outside', base)
    assert not (tmp_path/'outside').exists()
