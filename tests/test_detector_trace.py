# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Independent invented pixels and adversarial checks for the frozen detector trace."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import socket
import shutil
import sys
import numpy as np
import pytest
from gar.workset import digest
import gar.moving as moving

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import make_detector_trace_demo as demo
    import trace_detector_decisions as tracing
    import trace_scored_misses as scored
    import plot_detector_trace as drawing
finally:
    sys.path.pop(0)

from test_miss_diagnostics import cache as scored_cache


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_independent_demo_is_deterministic_and_separates_answers(tmp_path):
    base = tmp_path/'local'; base.mkdir()
    first = demo.make(base/'first', base)
    second = demo.make(base/'second', base)
    assert first == second
    assert len(first['frames']) == 12 and first['synthetic'] and first['status'] == 'complete'
    assert first['seeds'] == [2026111701, 2026111702]
    assert first['paired_noise_across_scenarios'] and not first['performance_claim']
    assert {f['scenario'] for f in first['frames']} == set(demo.SCENARIOS)
    assert all('target_native' not in f for f in first['frames'])
    truth = read(base/'first/truth.json')
    assert truth['manifest_sha256'] == digest(base/'first/manifest.json')
    for frame, answer in zip(first['frames'], truth['cases']):
        a, b = base/'first'/frame['local_plane'], base/'second'/frame['local_plane']
        assert digest(a) == frame['sha256'] == digest(b)
        image = np.load(a, allow_pickle=False)
        assert image.dtype == np.dtype('float32') and image.shape == (96, 96)
        _, center = demo.invented_image(frame['scenario'], frame['seed'])
        assert answer == dict(case_id=frame['case_id'], target_native=(2*center+.5).tolist())


def test_demo_preserves_existing_output_and_does_not_probe_external_paths(tmp_path, monkeypatch):
    base = tmp_path/'local'; base.mkdir()
    demo.make(base/'demo', base)
    before = (base/'demo/manifest.json').read_bytes()
    with pytest.raises(FileExistsError): demo.make(base/'demo', base)
    assert (base/'demo/manifest.json').read_bytes() == before
    outside = tmp_path/'outside'; original = Path.stat
    def stated(path, *a, **kw):
        assert path != outside
        return original(path, *a, **kw)
    monkeypatch.setattr(Path, 'stat', stated)
    with pytest.raises(ValueError, match='local'): demo.make(outside, base)


def test_interrupted_generation_stays_incomplete(tmp_path, monkeypatch):
    base = tmp_path/'local'; base.mkdir()
    def interrupted(*a, **kw): raise OSError('Invented storage interruption')
    monkeypatch.setattr(np, 'save', interrupted)
    with pytest.raises(OSError): demo.make(base/'partial', base)
    manifest = read(base/'partial/manifest.json')
    assert manifest['status'] == 'incomplete' and manifest['frames'] == []
    assert not (base/'partial/truth.json').exists()


def test_historical_detector_source_is_unchanged():
    path = Path(__file__).resolve().parents[1]/'src/gar/moving.py'
    assert sha256(path.read_text(encoding='utf-8').encode()).hexdigest() == 'f492032e0188310484faaf372db4c96597fd7910ecd3821629edb8365f27be67'


@pytest.mark.parametrize('scenario,seed', [(s, k) for k in demo.SEEDS for s in demo.SCENARIOS])
def test_trace_reproduces_frozen_detector_on_independent_pixels(scenario, seed):
    image, _ = demo.invented_image(scenario, seed)
    before = image.copy(); parameters = deepcopy(moving.PARAMETERS)
    expected, _ = moving.detect_sources(image)
    result = tracing.trace_image(image, expected_points=expected)
    assert result['replay_equal'] and result['saved_positions_checked']
    assert np.array_equal(image, before, equal_nan=True) and moving.PARAMETERS == parameters
    assert result['selected_count'] == len(expected)
    assert np.allclose(np.asarray(result['selected_points_reduced']).reshape(-1, 2), expected, atol=1e-9, rtol=0)
    assert result['parameters']['xycoords'] is None
    assert result['threshold_input'] == 5*result['noise_sigma']
    assert result['threshold_effective'] > result['threshold_input']


@pytest.mark.parametrize('scenario,status,reason', [
    ('bright', 'retained', None), ('faint', 'no_near_raw_maximum', None),
    ('hot_pixel', 'raw_rejected', 'sharpness'), ('elongated', 'raw_rejected', 'roundness2'),
    ('border', 'project_margin', 'project_margin'), ('masked', 'no_near_raw_maximum', None)])
def test_known_fabricated_gates_and_unresolved_absences(scenario, status, reason):
    image, center = demo.invented_image(scenario, demo.SEEDS[0])
    trace = tracing.trace_image(image)
    evidence = tracing.evidence_at(trace, 2*center+.5, 3.)
    assert evidence['status'] == status
    assert not evidence['identity_proven'] and not evidence['physical_cause_proven']
    if reason:
        assert evidence['rejection_counts'][reason] >= 1
    if status == 'no_near_raw_maximum':
        assert evidence['raw_seed_count'] == evidence['raw_centroid_count'] == 0
        assert evidence['rejection_counts'] == {}
    if scenario == 'masked': assert trace['masked_pixels'] == 10


def test_native_conversion_and_both_radii_do_not_move_the_target():
    row = dict(seed_xy_reduced=[10., 20.], centroid_xy_reduced=[10.5, 20.],
               project_kept=True, library_kept=True, rejection_reasons=[])
    trace = dict(rows=[row]); before = deepcopy(trace)
    target = [23.5, 40.5]
    near = tracing.evidence_at(trace, target, 1.5)
    context = tracing.evidence_at(trace, target, 3.)
    assert near['selected_count'] == 0 and context['selected_count'] == 1
    assert context['nearest_seed_distance_native'] == 3.
    assert context['nearest_centroid_distance_native'] == 2.
    assert trace == before and target == [23.5, 40.5]
    with pytest.raises(ValueError): tracing.evidence_at(trace, target, 2.)


def test_nonfinite_centroid_retains_seed_evidence_and_cumulative_reasons():
    trace = dict(rows=[dict(seed_xy_reduced=[10., 20.], centroid_xy_reduced=None,
        project_kept=False, library_kept=False, rejection_reasons=['nonfinite', 'sharpness'])])
    result = tracing.evidence_at(trace, [20.5, 40.5], 1.5)
    assert result['raw_seed_count'] == 1 and result['raw_centroid_count'] == 0
    assert result['status'] == 'raw_rejected'
    assert result['rejection_counts'] == dict(nonfinite=1, sharpness=1)
    assert result['nearest_centroid_distance_native'] is None


def test_displaced_centroid_is_not_claimed_as_a_retained_point_near_truth():
    trace = dict(rows=[dict(seed_xy_reduced=[10., 20.], centroid_xy_reduced=[13., 20.],
        project_kept=True, library_kept=True, rejection_reasons=[])])
    result = tracing.evidence_at(trace, [20.5, 40.5], 1.5)
    assert result['status'] == 'centroid_displaced' and result['selected_count'] == 0
    assert result['raw_seed_count'] == 1


def test_bad_images_or_cached_positions_cannot_be_accepted():
    with pytest.raises(ValueError): tracing.trace_image(np.zeros((10, 96)))
    with pytest.raises(ValueError, match='Bruit'): tracing.trace_image(np.zeros((96, 96)))
    image, _ = demo.invented_image('bright', demo.SEEDS[0])
    with pytest.raises(ValueError, match='précédemment'): tracing.trace_image(image, expected_points=[])
    expected, _ = moving.detect_sources(image)
    # A reduced displacement of 8e-10 is 1.6e-9 native, outside the frozen tolerance.
    with pytest.raises(ValueError, match='précédemment'): tracing.trace_image(image, expected_points=expected+[8e-10, 0.])


def test_library_version_and_project_divergence_are_refused(monkeypatch):
    original = tracing.photutils.__version__
    monkeypatch.setattr(tracing.photutils, '__version__', '0.0.invalid')
    with pytest.raises(ValueError, match='3.1.1'): tracing.frozen()
    monkeypatch.setattr(tracing.photutils, '__version__', original)
    image, _ = demo.invented_image('bright', demo.SEEDS[0])
    expected, selection = moving.detect_sources(image)
    monkeypatch.setattr(moving, 'detect_sources', lambda p: (expected+1e-4, selection))
    with pytest.raises(ValueError, match='détecteur gelé'): tracing.trace_image(image)


@pytest.fixture(scope='module')
def demo_cache(tmp_path_factory):
    base = tmp_path_factory.mktemp('detector-demo')/'local'; base.mkdir()
    demo.make(base/'demo', base)
    return base


def test_demo_reads_answers_only_after_all_traces_without_association(demo_cache, monkeypatch):
    base = demo_cache; calls = []; original = tracing.trace_image; parsed = tracing.experiment.read
    def wrapped(*a, **kw):
        calls.append(1); return original(*a, **kw)
    def guarded(path):
        if path == base/'demo/truth.json': assert len(calls) == 12
        return parsed(path)
    def forbidden(*a, **kw): raise AssertionError('No association or network allowed')
    monkeypatch.setattr(tracing, 'trace_image', wrapped)
    monkeypatch.setattr(tracing.experiment, 'read', guarded)
    for name in ('remove_stationary', 'find_tracks'): monkeypatch.setattr(moving, name, forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    before = {p: digest(p) for p in (base/'demo').iterdir() if p.is_file()}
    result = tracing.run_demo(base/'demo/manifest.json', base/'demo/truth.json', base/'guarded', base)
    assert result['status'] == 'complete' and result['truth_opened_after_replay']
    assert len(result['frames']) == 12 and not result['thresholds_changed'] and not result['association_rerun']
    assert all(digest(p) == h for p, h in before.items())
    with pytest.raises(FileExistsError): tracing.run_demo(base/'demo/manifest.json', base/'demo/truth.json', base/'guarded', base)


@pytest.mark.parametrize('problem', ['incomplete', 'seed', 'scenario'])
def test_demo_requires_a_complete_unmodified_protocol(demo_cache, problem):
    base = demo_cache; value = read(base/'demo/manifest.json')
    if problem == 'incomplete': value['status'] = 'incomplete'
    elif problem == 'seed': value['frames'][0]['seed'] += 1
    else: value['frames'][0]['scenario'] = 'invented-but-not-planned'
    path = base/'demo'/f'{problem}-manifest.json'; demo.save(path, value)
    with pytest.raises(ValueError): tracing.load_demo(path, base)


def test_modified_plane_and_external_path_are_refused(demo_cache, monkeypatch):
    base = demo_cache; source = base/'demo'; copy = base/'corrupt'; shutil.copytree(source, copy)
    value = read(copy/'manifest.json'); plane = copy/value['frames'][0]['local_plane']
    with plane.open('ab') as stream: stream.write(b'corruption')
    with pytest.raises(ValueError): tracing.load_demo(copy/'manifest.json', base)
    outside = base.parent/'outside.json'; original = Path.stat
    def stated(path, *a, **kw):
        assert path != outside; return original(path, *a, **kw)
    monkeypatch.setattr(Path, 'stat', stated)
    with pytest.raises(ValueError, match='local'): tracing.load_demo(outside, base)


def test_interrupted_trace_preserves_partial_state_and_skips_truth(demo_cache, monkeypatch):
    base = demo_cache; calls = []; original = tracing.trace_image; parsed = tracing.experiment.read
    def interrupted(*a, **kw):
        calls.append(1)
        if len(calls) == 2: raise OSError('Invented replay interruption')
        return original(*a, **kw)
    def guarded(path):
        assert path != base/'demo/truth.json'; return parsed(path)
    monkeypatch.setattr(tracing, 'trace_image', interrupted); monkeypatch.setattr(tracing.experiment, 'read', guarded)
    with pytest.raises(OSError): tracing.run_demo(base/'demo/manifest.json', base/'demo/truth.json', base/'partial-trace', base)
    result = read(base/'partial-trace/trace.json')
    assert result['status'] == 'incomplete' and len(result['frames']) == 1
    assert not result['truth_opened_after_replay']


@pytest.mark.parametrize('problem', ['category', 'frame', 'incomplete'])
def test_altered_prior_diagnostic_cannot_enter_scored_trace(scored_cache, problem):
    base, _ = scored_cache; value = read(base/'diagnostic/diagnostic.json')
    if problem == 'category': value['cases'][0]['primary'] = 'recovered'
    elif problem == 'frame': value['cases'][0]['frames'][0]['raw_count'] += 1
    else: value['status'] = 'incomplete'
    path = base/f'altered-diagnostic-{problem}.json'; demo.save(path, value)
    with pytest.raises(ValueError): scored.load_diagnosed(base/'score/score.json', path, base)


def test_scored_trace_preserves_saved_candidates_and_matches_all_positions(scored_cache, monkeypatch):
    base, diagnostic_result = scored_cache
    def forbidden(*a, **kw): raise AssertionError('No new track association, injection, or network allowed')
    for name in ('remove_stationary', 'find_tracks'): monkeypatch.setattr(moving, name, forbidden)
    for name in ('process', 'add_injection'): monkeypatch.setattr(scored.experiment, name, forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    watched = {p: digest(p) for folder in ('analysis', 'score', 'diagnostic', 'suite')
        for p in (base/folder).rglob('*') if p.is_file()}
    result = scored.run(base/'score/score.json', base/'diagnostic/diagnostic.json', base/'scored-trace', base)
    assert result['status'] == 'complete' and result['all_replays_equal']
    assert result['expected_cases'] == len(result['cases']) == 15
    assert result['recovered'] == 12 and result['missed'] == 24 and result['outside_speed_misses'] == 9
    assert not result['association_rerun'] and not result['new_injections'] and not result['thresholds_changed']
    originals = {c['case_id']: c for c in diagnostic_result['cases']}
    for case in result['cases']:
        assert all(case['retained_frames_by_radius'][r] == originals[case['case_id']]['radii_evidence'][r]['raw']['count'] for r in ('1.5', '3'))
        sealed = read(base/'scored-trace'/case['file'])
        assert all(f['trace']['saved_positions_checked'] and f['trace']['replay_equal'] for f in sealed['frames'])
    assert all(digest(p) == h for p, h in watched.items())


@pytest.fixture(scope='module')
def drawing_cache(demo_cache):
    base = demo_cache
    tracing.run_demo(base/'demo/manifest.json', base/'demo/truth.json', base/'drawing-trace', base)
    return base


def test_figures_are_deterministic_and_do_not_replay_any_detector(drawing_cache, monkeypatch):
    base = drawing_cache
    def forbidden(*a, **kw): raise AssertionError('Drawing must not replay or detect')
    monkeypatch.setattr(tracing, 'trace_image', forbidden)
    monkeypatch.setattr(moving, 'detect_sources', forbidden)
    first = drawing.plot(base/'drawing-trace/trace.json', base/'figures-first', base)
    second = drawing.plot(base/'drawing-trace/trace.json', base/'figures-second', base)
    assert first['figures_sha256'] == second['figures_sha256']
    assert set(first['figures_sha256']) == {'gates.png', 'examples.png'}
    assert not first['detector_called'] and first['first_seed'] == 2026111701
    assert first['input_hashes_unchanged'] and first['source_kind'] == 'synthetic_demo'
    before = (base/'figures-first/figures.json').read_bytes()
    with pytest.raises(FileExistsError): drawing.plot(base/'drawing-trace/trace.json', base/'figures-first', base)
    assert (base/'figures-first/figures.json').read_bytes() == before


@pytest.mark.parametrize('problem', ['incomplete', 'real', 'count'])
def test_figures_refuse_partial_real_or_inconsistent_trace(drawing_cache, problem):
    base = drawing_cache; value = read(base/'drawing-trace/trace.json')
    if problem == 'incomplete': value['status'] = 'incomplete'
    elif problem == 'real': value['source_kind'] = 'real_local_copies'
    else: value['frames'][0]['evidence_by_radius']['1.5']['selected_count'] += 1
    path = base/f'invalid-drawing-{problem}.json'; demo.save(path, value)
    with pytest.raises(ValueError): drawing.plot(path, base/('bad-figures-'+problem), base)


def test_figure_input_integrity_is_checked_before_drawing(drawing_cache):
    base = drawing_cache; value = read(base/'drawing-trace/trace.json')
    # A claimed linked checksum different from the actual file is rejected without touching that file.
    first_plane = next(p for p in value['inputs_sha256'] if p.endswith('.npy'))
    value['inputs_sha256'][first_plane] = '0'*64
    path = base/'modified-linked-image.json'; demo.save(path, value)
    with pytest.raises(ValueError, match='changé'): drawing.plot(path, base/'bad-modified-image-figures', base)
