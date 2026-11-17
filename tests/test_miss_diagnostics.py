# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Invented stage tables and invented images only, never personal observations."""
from copy import deepcopy
import builtins
from pathlib import Path
import shutil
import socket
import sys
from astropy.io import fits
import numpy as np
import pytest
from gar.workset import digest
import gar.moving as moving

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import diagnose_injection_misses as diagnostic
    import injection_recovery as experiment
    import make_injection_background as demo
    import plot_miss_diagnostics as drawing
    import run_seestar_pilot as pilot
finally:
    sys.path.pop(0)


def invented_tables(raw_count=8, common_count=8, kept_count=8, offset=0., speed=.5, step=13.):
    times = [step*k for k in range(8)]
    positions = [dict(frame_index=k, x=100+speed*t, y=120.) for k, t in enumerate(times)]
    raw, common, kept = [], [], []
    for k, p in enumerate(positions):
        point = [p['x']+offset, p['y']]
        raw.append([point.copy()] if k < raw_count else [])
        common.append([point.copy()] if k < min(raw_count, common_count) else [])
        kept.append([point.copy()] if k < min(raw_count, common_count, kept_count) else [])
    record = dict(case_id='invented-case', search_status='complete', candidate_count=0,
                  data=dict(raw_detections=raw, mapped_detections=common,
                            overlap_excluded_per_frame=[len(a)-len(b) for a, b in zip(raw, common)],
                            search=dict(residual_detections=kept, stationary_removed_per_frame=[len(a)-len(b) for a, b in zip(common, kept)], tracks=[])))
    control = dict(search_status='complete', data=dict(raw_detections=[[[p['x']+20, p['y']]] for p in positions]))
    answer = dict(positions=positions, velocity_native_per_declared_second=[speed, 0.])
    score = dict(available=True, recovered=0, missed=1)
    manifest = dict(relative_declared_seconds=times, models=[dict(rotation_matrix=np.eye(2).tolist(), translation_pixels=[0., 0.]) for _ in times])
    return record, control, answer, score, manifest


@pytest.mark.parametrize('counts,expected', [((4, 4, 4), 'raw_support_limited'),
    ((8, 4, 4), 'overlap_support_lost'), ((8, 8, 4), 'stationary_support_lost'),
    ((8, 8, 8), 'association_unresolved')])
def test_observed_stage_support_is_classified_without_new_search(counts, expected):
    args = invented_tables(*counts)
    if expected == 'association_unresolved':
        # Nearby points alternate: proximity alone does not establish a valid track.
        for stage in (args[0]['data']['raw_detections'], args[0]['data']['mapped_detections'], args[0]['data']['search']['residual_detections']):
            for k, point in enumerate(stage): point[0][0] += (-1)**k*1.4
    result = diagnostic.inspect_case(*args)
    assert result['primary'] == expected and not result['primary_is_proven_physical_cause']
    assert result['limiting_stage_stable_across_radii']


def test_radius_disagreement_stays_ambiguous_and_positions_unchanged():
    args = invented_tables(offset=2.)
    before = deepcopy(args)
    result = diagnostic.inspect_case(*args)
    assert result['primary'] == 'neighborhood_ambiguous'
    assert result['radii_evidence']['1.5']['raw']['count'] == 0
    assert result['radii_evidence']['3']['kept']['count'] == 8 and args == before


def test_slow_protocol_exclusion_preserves_other_observed_losses():
    result = diagnostic.inspect_case(*invented_tables(2, 2, 2, speed=.03))
    assert result['primary'] == 'outside_speed_domain'
    assert result['radii_evidence']['1.5']['limiting_stage'] == 'raw_support_limited'


def test_total_short_span_is_not_faked_into_temporal_support():
    result = diagnostic.inspect_case(*invented_tables(step=1.))
    assert result['primary'] == 'outside_time_span'
    assert result['radii_evidence']['1.5']['raw']['count'] == 8
    assert not result['radii_evidence']['1.5']['raw']['enough']


def test_cached_recovery_is_not_relabelled_as_diagnostic_miss():
    args = invented_tables(5, 5, 5)
    for stage in (args[0]['data']['raw_detections'], args[0]['data']['mapped_detections'], args[0]['data']['search']['residual_detections']):
        stage[0][0][0] += 1.8
    args[3].update(recovered=1, missed=0)
    result = diagnostic.inspect_case(*args)
    assert result['primary'] == 'recovered' and result['radii_evidence']['1.5']['raw']['count'] == 4


def test_close_control_source_is_only_a_possible_confusion_hint():
    args = invented_tables(4, 4, 4)
    args[1]['data']['raw_detections'] = [[[p['x']+.2, p['y']]] for p in args[2]['positions']]
    result = diagnostic.inspect_case(*args)
    assert result['radii_evidence']['1.5']['control']['count'] == 8
    assert result['primary'] == 'raw_support_limited' and not result['primary_is_proven_physical_cause']


def test_unavailable_control_is_unknown_rather_than_zero_neighbors():
    args = invented_tables(4, 4, 4); args[1].update(search_status='blocked', data=None)
    result = diagnostic.inspect_case(*args)
    assert result['radii_evidence']['1.5']['control'] is None and not result['control_evidence_available']


def test_unavailable_case_remains_unknown():
    args = invented_tables(); args[0].update(search_status='blocked', data=None)
    args[3].update(available=False, recovered=None, missed=None)
    result = diagnostic.inspect_case(*args)
    assert result['primary'] == 'unavailable' and result['missed'] is None and result['frames'] == []


@pytest.mark.parametrize('problem', ['reversed', 'duplicate', 'shifted', 'removed_count', 'overlap_count'])
def test_corrupt_stage_subsets_are_rejected(problem):
    args = invented_tables()
    record = args[0]
    if problem == 'removed_count': record['data']['search']['stationary_removed_per_frame'][0] = 1
    elif problem == 'overlap_count': record['data']['overlap_excluded_per_frame'][0] = 1
    elif problem == 'shifted': record['data']['mapped_detections'][0][0][0] += 1e-7
    else:
        p = record['data']['raw_detections'][0][0]
        record['data']['raw_detections'][0].append([p[0]+10, p[1]])
        record['data']['mapped_detections'][0] = list(reversed(record['data']['raw_detections'][0])) if problem == 'reversed' else [p, p]
    with pytest.raises(ValueError): diagnostic.inspect_case(*args)


@pytest.fixture(scope='module')
def cache(tmp_path_factory):
    base = tmp_path_factory.mktemp('misses')/'local'; base.mkdir()
    demo.make(base/'background', base)
    experiment.generate(base/'background/pilot/pilot.json', base/'suite', base)
    experiment.analyze(base/'suite/manifest.json', base/'analysis', base)
    experiment.score(base/'suite/manifest.json', base/'suite/truth.json', base/'analysis/analysis.json', base/'score', base)
    result = diagnostic.diagnose(base/'score/score.json', base/'diagnostic', base)
    return base, result


def test_full_synthetic_diagnostic_reconciles_known_misses(cache):
    _, result = cache
    assert result['recovered'] == 12 and result['missed'] == 24 and result['unavailable'] == 0
    assert result['missed_categories'] == {'outside_speed_domain': 9, 'raw_support_limited': 15}
    assert sum(result['missed_categories'].values()) == result['missed']
    assert result['other_misses'] == 15 and result['outside_speed_misses'] == 9
    assert not result['search_rerun'] and not result['thresholds_changed'] and result['input_hashes_unchanged']


def test_diagnostic_has_no_search_pixel_analysis_archive_or_network_calls(cache, monkeypatch):
    base, _ = cache
    def forbidden(*a, **kw): raise AssertionError('Search or pixel analysis must not be rerun')
    for module, name in [(experiment, 'process'), (experiment, 'detect_sources'), (pilot, 'declared_tracks'),
                         (moving, 'detect_sources'), (moving, 'remove_stationary'), (moving, 'find_tracks'),
                         (np, 'load'), (fits, 'open')]: monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    original_open, original_stat = Path.open, Path.stat
    def opened(path, *a, **kw):
        assert 'invented-source' not in path.parts
        if path.suffix == '.fit': assert (a[0] if a else kw.get('mode', 'r')) in ('r', 'rb')
        return original_open(path, *a, **kw)
    def stated(path, *a, **kw):
        assert 'invented-source' not in path.parts
        return original_stat(path, *a, **kw)
    monkeypatch.setattr(Path, 'open', opened); monkeypatch.setattr(Path, 'stat', stated)
    result = diagnostic.diagnose(base/'score/score.json', base/'guarded-diagnostic', base)
    assert result['missed'] == 24


def test_corrupt_candidate_stops_before_truth_is_opened(cache, monkeypatch):
    base, _ = cache; shutil.copytree(base/'analysis', base/'altered-analysis')
    candidate = base/'altered-analysis/cases/control.json'
    value = experiment.read(candidate); value['candidate_count'] += 1; experiment.save(candidate, value)
    score = experiment.read(base/'score/score.json')
    score['analysis_path'] = str(base/'altered-analysis/analysis.json')
    path = base/'altered-score.json'; experiment.save(path, score)
    original = Path.open
    def opened(path, *a, **kw):
        assert path.name != 'truth.json'
        return original(path, *a, **kw)
    monkeypatch.setattr(Path, 'open', opened)
    with pytest.raises(ValueError, match='modifié'): diagnostic.diagnose(path, base/'bad-candidate', base)


@pytest.mark.parametrize('problem', ['incomplete', 'wrong_count', 'external'])
def test_invalid_score_or_external_input_rejected(cache, monkeypatch, problem):
    base, _ = cache
    value = experiment.read(base/'score/score.json')
    if problem == 'external':
        path = base.parent/'outside-score.json'; original = Path.stat
        def stated(p, *a, **kw):
            assert p != path; return original(p, *a, **kw)
        monkeypatch.setattr(Path, 'stat', stated)
    else:
        if problem == 'incomplete': value['status'] = 'incomplete'
        else: value['missed'] += 1
        path = base/(problem+'.json'); experiment.save(path, value)
    with pytest.raises(ValueError): diagnostic.diagnose(path, base/('bad-'+problem), base)


def test_interrupted_diagnostic_is_incomplete_and_not_plotted(cache, monkeypatch):
    base, _ = cache; original = diagnostic.inspect_case; calls = []
    def interrupted(*a, **kw):
        calls.append(1)
        if len(calls) == 2: raise OSError('Invented interruption')
        return original(*a, **kw)
    monkeypatch.setattr(diagnostic, 'inspect_case', interrupted)
    with pytest.raises(OSError): diagnostic.diagnose(base/'score/score.json', base/'interrupted', base)
    result = experiment.read(base/'interrupted/diagnostic.json')
    assert result['status'] == 'incomplete' and len(result['cases']) == 1
    with pytest.raises(ValueError): drawing.plot(base/'interrupted/diagnostic.json', base/'bad-figures', base)


def test_figures_use_deterministic_representatives_and_preserve_inputs(cache):
    base, result = cache
    watched = {p: digest(p) for p in [base/'diagnostic/diagnostic.json', base/'score/score.json']}
    drawing.plot(base/'diagnostic/diagnostic.json', base/'figures', base)
    journal = experiment.read(base/'figures/figures.json')
    assert journal['representatives'] == result['representatives']
    assert not journal['search_rerun'] and not journal['thresholds_changed'] and journal['input_hashes_unchanged']
    assert all(digest(p) == h for p, h in watched.items())
    before = (base/'diagnostic/diagnostic.json').read_bytes()
    with pytest.raises(FileExistsError): diagnostic.diagnose(base/'score/score.json', base/'diagnostic', base)
    assert (base/'diagnostic/diagnostic.json').read_bytes() == before
