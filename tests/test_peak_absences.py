# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Independent invented maps, pixels, and cached studies; no private observations."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import socket
import sys
import warnings
import numpy as np
import pytest
from photutils.detection import find_peaks
from gar.workset import digest
import gar.moving as moving

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import make_peak_absence_demo as demo
    import trace_peak_creation as tracing
    import diagnose_peak_absences as diagnosis
    import trace_detector_decisions as old_trace
    import trace_scored_misses as old_scored
    import plot_peak_absences as drawing
finally:
    sys.path.pop(0)

from test_detector_trace import scored_cache


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def blank_map():
    return np.zeros((96, 96), dtype=float)


def official_seeds(data, mask, threshold, border=(2, 2)):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        found = find_peaks(data, threshold, mask=mask, border_width=border, min_separation=5)
    return [] if found is None else np.column_stack([found['x_peak'], found['y_peak']]).tolist()


def test_fixed_independent_demo_reproduces_pixels_and_separates_answers(tmp_path):
    base = tmp_path/'local'; base.mkdir()
    first = demo.make(base/'first', base); second = demo.make(base/'second', base)
    assert first == second and first['status'] == 'complete' and first['synthetic']
    assert first['seeds'] == [2026111801, 2026111802]
    assert len(first['frames']) == 12 and len(first['scenarios']) == 6
    assert not first['performance_claim'] and first['paired_noise_across_scenarios']
    assert all('target_native' not in frame for frame in first['frames'])
    truth = read(base/'first/truth.json')
    assert truth['manifest_sha256'] == digest(base/'first/manifest.json')
    for frame, answer in zip(first['frames'], truth['cases']):
        path = base/'first'/frame['local_plane']
        assert digest(path) == frame['sha256'] == digest(base/'second'/frame['local_plane'])
        plane = np.load(path, allow_pickle=False)
        assert plane.shape == (96, 96) and plane.dtype == np.dtype('float32')
        _, center = demo.invented_image(frame['scenario'], frame['seed'])
        assert answer == dict(case_id=frame['case_id'], target_native=(2*center+.5).tolist())


def test_demo_refuses_existing_and_external_outputs_before_probe(tmp_path, monkeypatch):
    base = tmp_path/'local'; base.mkdir(); demo.make(base/'demo', base)
    before = (base/'demo/manifest.json').read_bytes()
    with pytest.raises(FileExistsError): demo.make(base/'demo', base)
    assert (base/'demo/manifest.json').read_bytes() == before
    outside = tmp_path/'outside'; original = Path.stat
    def stated(path, *args, **kwargs):
        assert path != outside; return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'stat', stated)
    with pytest.raises(ValueError, match='local'): demo.make(outside, base)


def test_interrupted_demo_keeps_incomplete_state(tmp_path, monkeypatch):
    base = tmp_path/'local'; base.mkdir()
    def fail(*args, **kwargs): raise OSError('Invented disk interruption')
    monkeypatch.setattr(np, 'save', fail)
    with pytest.raises(OSError): demo.make(base/'partial', base)
    result = read(base/'partial/manifest.json')
    assert result['status'] == 'incomplete' and result['frames'] == []
    assert not (base/'partial/truth.json').exists()


@pytest.mark.parametrize('value,expected', [(9., []), (10., []), (11., [[48, 48]])])
def test_effective_threshold_is_strict_and_matches_official_seeds(value, expected):
    data = blank_map(); data[48, 48] = value; mask = np.zeros(data.shape, dtype=bool)
    result = tracing.trace_convolved(data, mask, 10.)
    assert result['seeds_reduced'] == expected == official_seeds(data, mask, 10.)
    assert result['maps']['local_maximum'][48, 48]
    assert bool(result['maps']['above_threshold'][48, 48]) == (value > 10)
    assert data[48, 48] == value and not mask.any()


def test_higher_neighbor_and_simultaneous_threshold_obstacle_are_visible():
    data = blank_map(); data[48, 48] = 9.; data[48, 51] = 20.
    result = tracing.trace_convolved(data, np.zeros(data.shape, bool), 10.)
    assert result['seeds_reduced'] == [[51, 48]]
    assert not result['condition_maps']['local_maximum'][48, 48]
    assert not result['condition_maps']['above_threshold'][48, 48]
    assert result['maps']['samples'][48, 48] and not result['maps']['local_maximum'][48, 48]


def test_masked_stronger_pixel_does_not_suppress_unmasked_neighbor():
    data = blank_map(); data[48, 48] = 100.; data[48, 49] = 20.
    mask = np.zeros(data.shape, bool); mask[48, 48] = True
    result = tracing.trace_convolved(data, mask, 10.)
    assert result['seeds_reduced'] == [[49, 48]] == official_seeds(data, mask, 10.)
    assert not result['condition_maps']['unmasked'][48, 48]
    assert data[48, 48] == 100. and mask[48, 48]


def test_library_border_removes_peak_without_changing_threshold():
    data = blank_map(); data[48, 1] = 20.
    mask = np.zeros(data.shape, bool)
    result = tracing.trace_convolved(data, mask, 10.)
    assert result['seeds_reduced'] == [] == official_seeds(data, mask, 10.)
    assert result['maps']['unmasked'][48, 1] and not result['maps']['inside_border'][48, 1]


def test_plateau_representative_and_equal_peaks_keep_exact_order():
    data = blank_map(); data[47:50, 47:50] = 20.
    data[20, 20] = 15.; data[20, 25] = 15.
    mask = np.zeros(data.shape, bool)
    result = tracing.trace_convolved(data, mask, 10.)
    assert result['seeds_reduced'] == [[20, 20], [48, 48]] == official_seeds(data, mask, 10.)
    assert result['maps']['above_threshold'][47:50, 47:50].sum() == 9
    assert result['maps']['plateau'][47:50, 47:50].sum() == 1
    assert result['maps']['plateau'][20, 25] and not result['maps']['final'][20, 25]


def test_constant_response_uses_library_special_case():
    data = np.full((96, 96), 20.)
    result = tracing.trace_convolved(data, np.zeros(data.shape, bool), 10.)
    assert result['constant_input'] and result['seeds_reduced'] == []
    assert official_seeds(data, None, 10.) == []


def test_historical_detector_is_preserved():
    path = Path(__file__).resolve().parents[1]/'src/gar/moving.py'
    assert sha256(path.read_text(encoding='utf-8').encode()).hexdigest() == 'f492032e0188310484faaf372db4c96597fd7910ecd3821629edb8365f27be67'


@pytest.mark.parametrize('scenario', demo.SCENARIOS)
@pytest.mark.parametrize('seed', demo.SEEDS)
def test_all_invented_images_reproduce_library_and_old_detector(scenario, seed):
    image, _ = demo.invented_image(scenario, seed)
    before = image.copy(); original = old_trace.trace_image(image)
    result = tracing.trace_image(image)
    assert result['old_detector_trace'] == original
    expected = [row['seed_xy_reduced'] for row in original['rows']]
    assert result['seeds_reduced'] == expected and result['seeds_equal']
    assert result['stage_counts_global']['final'] == len(expected)
    assert np.array_equal(image, before, equal_nan=True)
    encoded = tracing.serializable_trace(result)
    assert not any(key in encoded for key in ('maps', 'condition_maps', 'convolved', 'peak_data'))
    json.dumps(encoded, allow_nan=False)


def test_native_sampling_and_both_radii_keep_obstacles_separate():
    data = blank_map(); data[48, 48] = 9.; data[48, 51] = 20.
    result = tracing.trace_convolved(data, np.zeros(data.shape, bool), 10.)
    small = tracing.evidence_at(result, [96.5, 96.5], 1.5)
    large = tracing.evidence_at(result, [96.5, 96.5], 3.)
    assert small['stage_counts']['samples'] == 1 and large['stage_counts']['samples'] == 9
    assert small['first_empty_stage'] == 'local_maximum'
    assert small['simultaneous_obstacles']['local_maximum'] == 1
    assert small['simultaneous_obstacles']['above_threshold'] == 1
    assert small['best_sample']['value_for_peaks'] == 9.
    assert small['higher_neighbor']['x_reduced'] == 51
    assert small['higher_neighbor']['value_for_peaks'] == 20.
    assert not small['identity_proven'] and not small['physical_cause_proven']
    outside = tracing.evidence_at(result, [-100., -100.], 3.)
    assert outside['stage_counts']['samples'] == 0 and outside['first_empty_stage'] == 'samples'
    with pytest.raises(ValueError): tracing.evidence_at(result, [np.nan, 1.], 1.5)
    with pytest.raises(ValueError): tracing.evidence_at(result, [96.5, 96.5], 2.)


def test_first_empty_gate_changes_with_radius_without_changing_any_rule():
    data = blank_map(); data[48, 49] = 9.
    result = tracing.trace_convolved(data, np.zeros(data.shape, bool), 10.)
    small = tracing.evidence_at(result, [96.5, 96.5], 1.5)
    large = tracing.evidence_at(result, [96.5, 96.5], 3.)
    assert small['first_empty_stage'] == 'local_maximum'
    assert large['first_empty_stage'] == 'above_threshold'
    assert small['independent_pass_counts']['above_threshold'] == large['independent_pass_counts']['above_threshold'] == 0
    assert small['final_seed_count'] == large['final_seed_count'] == 0
    assert not small['physical_cause_proven'] and not large['physical_cause_proven']


def test_seed_divergence_cannot_be_reported_as_success(monkeypatch):
    data = blank_map(); data[48, 48] = 20.
    original = tracing.peakfinder.find_peaks
    def divergent(*args, **kwargs):
        table = original(*args, **kwargs); table['x_peak'][0] += 1; return table
    monkeypatch.setattr(tracing.peakfinder, 'find_peaks', divergent)
    with pytest.raises(ValueError, match='Graines'): tracing.trace_convolved(data, np.zeros(data.shape, bool), 10.)


def test_saved_detector_trace_divergence_is_refused():
    image, _ = demo.invented_image('isolated_bright', demo.SEEDS[0])
    original = old_trace.trace_image(image)
    saved = old_trace.trace_image(image, expected_points=original['selected_points_reduced'])
    tracing.trace_image(image, expected_trace=saved)
    bad = deepcopy(saved); bad['noise_sigma'] += 1
    with pytest.raises(ValueError): tracing.trace_image(image, expected_trace=bad)


@pytest.fixture(scope='module')
def demo_cache(tmp_path_factory):
    base = tmp_path_factory.mktemp('peak-demo')/'local'; base.mkdir()
    demo.make(base/'demo', base)
    return base


@pytest.mark.parametrize('problem', ['incomplete', 'seed', 'scenario'])
def test_demo_protocol_changes_are_refused(demo_cache, problem):
    base = demo_cache; value = read(base/'demo/manifest.json')
    if problem == 'incomplete': value['status'] = 'incomplete'
    elif problem == 'seed': value['frames'][0]['seed'] += 1
    else: value['frames'][0]['scenario'] = 'not-in-the-fixed-protocol'
    path = base/'demo'/f'bad-{problem}.json'; demo.save(path, value)
    with pytest.raises(ValueError): tracing.load_demo(path, base)


def test_corrupt_plane_and_external_path_are_refused(demo_cache, monkeypatch):
    base = demo_cache; shutil.copytree(base/'demo', base/'corrupt-demo')
    document = read(base/'corrupt-demo/manifest.json'); path = base/'corrupt-demo'/document['frames'][0]['local_plane']
    with path.open('ab') as stream: stream.write(b'changed')
    with pytest.raises(ValueError): tracing.load_demo(base/'corrupt-demo/manifest.json', base)
    original = Path.stat; outside = base.parent/'outside.json'
    def stated(path, *args, **kwargs):
        assert path != outside; return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'stat', stated)
    with pytest.raises(ValueError, match='local'): tracing.load_demo(outside, base)


def test_demo_never_reads_answers_before_all_maps_and_has_no_association(demo_cache, monkeypatch):
    base = demo_cache; calls = []; real_trace = tracing.trace_image; parsed = tracing.experiment.read
    def wrapped(*args, **kwargs):
        calls.append(1); return real_trace(*args, **kwargs)
    def guarded(path):
        if path == base/'demo/truth.json': assert len(calls) == 12
        return parsed(path)
    def forbidden(*args, **kwargs): raise AssertionError('No new association, injection, or network')
    monkeypatch.setattr(tracing, 'trace_image', wrapped); monkeypatch.setattr(tracing.experiment, 'read', guarded)
    for name in ('remove_stationary', 'find_tracks'): monkeypatch.setattr(moving, name, forbidden)
    monkeypatch.setattr(tracing.experiment, 'add_injection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    before = {p: digest(p) for p in (base/'demo').iterdir() if p.is_file()}
    result = tracing.run_demo(base/'demo/manifest.json', base/'demo/truth.json', base/'guarded-trace', base)
    assert result['status'] == 'complete' and result['truth_opened_after_replay']
    assert len(result['frames']) == 12 and not result['thresholds_changed'] and not result['association_rerun']
    assert all(digest(p) == expected for p, expected in before.items())
    with pytest.raises(FileExistsError): tracing.run_demo(base/'demo/manifest.json', base/'demo/truth.json', base/'guarded-trace', base)


def test_interrupted_replay_preserves_progress_without_opening_answers(demo_cache, monkeypatch):
    base = demo_cache; calls = []; original = tracing.trace_image; parsed = tracing.experiment.read
    def stopped(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2: raise OSError('Invented replay interruption')
        return original(*args, **kwargs)
    def guarded(path):
        assert path != base/'demo/truth.json'; return parsed(path)
    monkeypatch.setattr(tracing, 'trace_image', stopped); monkeypatch.setattr(tracing.experiment, 'read', guarded)
    with pytest.raises(OSError): tracing.run_demo(base/'demo/manifest.json', base/'demo/truth.json', base/'partial-trace', base)
    report = read(base/'partial-trace/trace.json')
    assert report['status'] == 'incomplete' and len(report['frames']) == 1 and not report['truth_opened_after_replay']


@pytest.fixture(scope='module')
def old_trace_cache(scored_cache):
    base, _ = scored_cache
    old_scored.run(base/'score/score.json', base/'diagnostic/diagnostic.json', base/'old-peak-trace', base)
    return base


@pytest.mark.parametrize('problem', ['incomplete', 'summary', 'case_evidence', 'checksum', 'outside_speed'])
def test_old_trace_changes_cannot_enter_new_diagnostic(old_trace_cache, problem):
    base = old_trace_cache; value = read(base/'old-peak-trace/trace.json')
    if problem == 'incomplete': value['status'] = 'incomplete'
    elif problem == 'summary': value['summary']['1.5']['no_near_raw_maximum'] += 1
    elif problem == 'case_evidence': value['cases'][0]['frames'][0]['evidence_by_radius']['1.5']['status'] = 'retained'
    elif problem == 'checksum': value['cases'][0]['sha256'] = '0'*64
    else: value['outside_speed_misses'] += 1
    path = base/'old-peak-trace'/f'altered-{problem}.json'; demo.save(path, value)
    with pytest.raises(ValueError): diagnosis.load_traced(base/'score/score.json', base/'diagnostic/diagnostic.json', path, base)


def test_cached_pipeline_reconciles_fixed_cohort_and_preserves_all_old_inputs(old_trace_cache, monkeypatch):
    base = old_trace_cache
    def forbidden(*args, **kwargs): raise AssertionError('No association, generation, or network allowed')
    for name in ('remove_stationary', 'find_tracks'): monkeypatch.setattr(moving, name, forbidden)
    for name in ('process', 'add_injection'): monkeypatch.setattr(diagnosis.experiment, name, forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    before = {p: digest(p) for folder in ('analysis', 'score', 'diagnostic', 'suite', 'old-peak-trace')
        for p in (base/folder).rglob('*') if p.is_file()}
    result = diagnosis.run(base/'score/score.json', base/'diagnostic/diagnostic.json',
                           base/'old-peak-trace/trace.json', base/'peak-diagnostic', base)
    assert result['status'] == 'complete' and result['all_replays_equal']
    assert result['expected_cases'] == len(result['cases']) == 15
    assert result['recovered'] == 12 and result['missed'] == 24
    assert result['outside_speed_misses'] == 9
    assert result['absent_cohort_count']+result['context_count'] == 120
    assert not result['thresholds_changed'] and not result['association_rerun'] and not result['new_injections']
    old = read(base/'old-peak-trace/trace.json')
    old_cases = {c['case_id']: read(base/'old-peak-trace'/c['file']) for c in old['cases']}
    absent_count = 0
    for case in result['cases']:
        sealed = read(base/'peak-diagnostic'/case['file'])
        assert digest(base/'peak-diagnostic'/case['file']) == case['sha256']
        for frame in sealed['frames']:
            original = old_cases[case['case_id']]['frames'][frame['frame_index']]
            expected = all(original['evidence_by_radius'][r]['status'] == 'no_near_raw_maximum' for r in ('1.5', '3'))
            assert frame['in_absent_cohort'] == expected
            assert frame['trace']['old_detector_trace'] == original['trace']
            assert frame['trace']['seeds_equal'] and frame['trace']['saved_trace_checked']
            absent_count += expected
    assert absent_count == result['absent_cohort_count']
    assert all(sum(result['summary'][r].values()) == absent_count for r in ('1.5', '3'))
    assert all(digest(p) == expected for p, expected in before.items())
    with pytest.raises(FileExistsError):
        diagnosis.run(base/'score/score.json', base/'diagnostic/diagnostic.json', base/'old-peak-trace/trace.json', base/'peak-diagnostic', base)


@pytest.fixture(scope='module')
def drawing_cache(demo_cache):
    base = demo_cache
    tracing.run_demo(base/'demo/manifest.json', base/'demo/truth.json', base/'drawing-trace', base)
    return base


def test_public_figures_are_reproducible_without_detector_convolution_or_peakfinding(drawing_cache, monkeypatch):
    base = drawing_cache
    def forbidden(*args, **kwargs): raise AssertionError('No replay, convolution, or peak finding during plotting')
    for name in ('trace_image', 'trace_convolved'): monkeypatch.setattr(tracing, name, forbidden)
    monkeypatch.setattr(moving, 'detect_sources', forbidden)
    monkeypatch.setattr(tracing._convolution, '_filter_data', forbidden)
    monkeypatch.setattr(tracing.peakfinder, 'find_peaks', forbidden)
    first = drawing.plot(base/'drawing-trace/trace.json', base/'figures-first', base)
    second = drawing.plot(base/'drawing-trace/trace.json', base/'figures-second', base)
    assert first['figures_sha256'] == second['figures_sha256']
    assert set(first['figures_sha256']) == {'gates.png', 'examples.png'}
    assert not first['detector_called'] and not first['convolution_called']
    assert first['first_seed'] == 2026111801 and first['input_hashes_unchanged']
    before = (base/'figures-first/figures.json').read_bytes()
    with pytest.raises(FileExistsError): drawing.plot(base/'drawing-trace/trace.json', base/'figures-first', base)
    assert (base/'figures-first/figures.json').read_bytes() == before


@pytest.mark.parametrize('problem', ['incomplete', 'real', 'count', 'condition', 'threshold', 'seed'])
def test_plot_rejects_partial_real_or_inconsistent_recordings(drawing_cache, problem):
    base = drawing_cache; value = read(base/'drawing-trace/trace.json')
    first = value['frames'][0]
    if problem == 'incomplete': value['status'] = 'incomplete'
    elif problem == 'real': value['source_kind'] = 'real_local_copies'
    elif problem == 'count': first['evidence_by_radius']['1.5']['stage_counts']['samples'] += 1
    elif problem == 'condition':
        sample = first['evidence_by_radius']['1.5']['samples'][0]
        sample['conditions_passes']['above_threshold'] = not sample['conditions_passes']['above_threshold']
    elif problem == 'threshold': first['trace']['threshold_effective'] *= 1000
    else: first['trace']['seeds_reduced'].append([20, 20])
    path = base/f'bad-plot-{problem}.json'; demo.save(path, value)
    with pytest.raises(ValueError): drawing.plot(path, base/f'bad-figures-{problem}', base)


def test_plot_refuses_modified_linked_inputs(drawing_cache):
    base = drawing_cache; value = read(base/'drawing-trace/trace.json')
    plane = next(p for p in value['inputs_sha256'] if p.endswith('.npy'))
    value['inputs_sha256'][plane] = '0'*64
    path = base/'bad-linked-input.json'; demo.save(path, value)
    with pytest.raises(ValueError): drawing.plot(path, base/'bad-linked-figures', base)
