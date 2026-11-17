# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""All pixels are invented; no personal observations are used by these tests."""
import builtins
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
import sys

import numpy as np
from PIL import Image
import pytest
from gar.workset import digest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import injection_recovery as recipe
    import make_injection_background as demo
    import plot_injection_recovery as drawing
finally:
    sys.path.pop(0)


@pytest.fixture(scope='module')
def experiment(tmp_path_factory):
    base = tmp_path_factory.mktemp('injection')/'local'; base.mkdir()
    demo.make(base/'background', base)
    recipe.generate(base/'background/pilot/pilot.json', base/'suite', base)
    recipe.analyze(base/'suite/manifest.json', base/'analysis', base)
    result = recipe.score(base/'suite/manifest.json', base/'suite/truth.json', base/'analysis/analysis.json', base/'score', base)
    return base, result


def test_known_bright_injections_recovered_and_slow_outside_search_kept(experiment):
    _, result = experiment
    group = next(g for g in result['groups'] if g['peak_sigma'] == 12 and g['speed_native_per_declared_second'] == .5)
    assert group['recovered'] == group['available'] == 3
    assert all(g['recovered'] == 0 for g in result['groups'] if g['speed_native_per_declared_second'] == .03)
    assert result['control_candidates'] == 0 and result['synthetic_fixture_criteria_passed']
    assert result['control_identical_to_baseline']
    assert result['recovered'] + result['missed'] == 36 and result['unavailable'] == 0


def test_mask_amplitude_and_original_array_preserved():
    background = np.zeros((128, 128), dtype='float32'); background[63, 64] = np.nan
    before = background.copy()
    result = recipe.add_injection(background, [128.5, 128.5], 12.)
    assert result[64, 64] == 12. and np.isnan(result[63, 64])
    assert result[0, 0] == 0 and np.array_equal(background, before, equal_nan=True)
    assert result.dtype == np.dtype('float32')


def test_fixed_trajectory_and_inverse_field_margin():
    positions, velocity = recipe.trajectory([512, 512], [0, 10], dict(position_index=0, speed_native_per_declared_second=.5))
    assert np.allclose(positions[0], [153.6, 153.6])
    assert np.allclose(positions[1]-positions[0], [5*np.sqrt(3)/2, 2.5])
    identity = dict(rotation_matrix=np.eye(2), translation_pixels=[0, 0])
    shifted = dict(rotation_matrix=np.eye(2), translation_pixels=[100, 0])
    assert recipe.covered(np.array([[32., 40.]]), [identity], [512, 512])
    assert not recipe.covered(np.array([[31., 40.]]), [identity], [512, 512])
    assert not recipe.covered(np.array([[40., 40.]]), [identity, shifted], [512, 512])


def test_single_match_and_other_candidate_remain_nonassociated(experiment):
    base, _ = experiment
    record = recipe.read(base/'analysis/cases/a12-v0p5-p1.json')
    truth = next(t for t in recipe.read(base/'suite/truth.json')['cases'] if t['case_id'] == record['case_id'])
    duplicate = deepcopy(record['data']['search']['tracks'][0]); duplicate['candidate_id'] = 100
    record['data']['search']['tracks'].append(duplicate)
    before = deepcopy(record)
    result = recipe.score_one(record, truth)
    assert result['recovered'] == 1 and result['unassociated_candidates'] == 1
    assert result['match']['candidate_id'] < 100 and record == before


@pytest.mark.parametrize('problem', ['wrong_velocity', 'fewer_than_five'])
def test_wrong_or_short_track_not_counted_as_recovered(experiment, problem):
    base, _ = experiment
    record = recipe.read(base/'analysis/cases/a12-v0p5-p1.json')
    truth = next(t for t in recipe.read(base/'suite/truth.json')['cases'] if t['case_id'] == record['case_id'])
    track = record['data']['search']['tracks'][0]
    if problem == 'wrong_velocity': track['velocity_native_pixels_per_declared_second'] = [10., 10.]
    else: track['points'] = track['points'][:4]
    result = recipe.score_one(record, truth)
    assert result['recovered'] == 0 and result['missed'] == 1


def test_analysis_never_reads_truth_archives_or_network_and_fits_are_readonly(experiment, monkeypatch):
    base, _ = experiment
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
    def offline(*a, **kw): raise AssertionError('No network')
    monkeypatch.setattr(builtins, 'open', opened); monkeypatch.setattr(Path, 'open', path_opened)
    monkeypatch.setattr(Path, 'stat', stated); monkeypatch.setattr(socket.socket, 'connect', offline)
    result = recipe.analyze(base/'suite/manifest.json', base/'guarded-analysis', base)
    assert result['truth_opened'] is False and result['all_available']


def test_generation_deterministic_and_inputs_unchanged(experiment):
    base, _ = experiment
    original = recipe.read(base/'suite/manifest.json')
    regenerated = recipe.generate(base/'background/pilot/pilot.json', base/'suite-again', base)
    assert original['cases'] == regenerated['cases']
    report = recipe.read(base/'background/pilot/pilot.json')
    assert all(digest(Path(f['local_copy'])) == f['sha256'] for f in report['copies'])


def test_incomplete_analysis_kept_and_score_refuses_before_truth(experiment, monkeypatch):
    base, _ = experiment
    original = recipe.process; calls = []
    def interrupted(*a, **kw):
        calls.append(1)
        if len(calls) == 2: raise OSError('Invented interruption')
        return original(*a, **kw)
    monkeypatch.setattr(recipe, 'process', interrupted)
    with pytest.raises(OSError): recipe.analyze(base/'suite/manifest.json', base/'interrupted-analysis', base)
    result = recipe.read(base/'interrupted-analysis/analysis.json')
    assert result['status'] == 'incomplete' and len(result['records']) == 1
    original_open = Path.open
    def no_truth(path, *a, **kw):
        assert path.name != 'truth.json'; return original_open(path, *a, **kw)
    monkeypatch.setattr(Path, 'open', no_truth)
    with pytest.raises(ValueError, match='complète'):
        recipe.score(base/'suite/manifest.json', base/'suite/truth.json', base/'interrupted-analysis/analysis.json', base/'not-scored', base)


def test_tampered_frozen_candidate_refused(experiment):
    base, _ = experiment
    shutil.copytree(base/'analysis', base/'altered-analysis')
    path = base/'altered-analysis/cases/a12-v0p5-p1.json'
    r = recipe.read(path); r['candidate_count'] += 1; recipe.save(path, r)
    with pytest.raises(ValueError, match='modifié'):
        recipe.score(base/'suite/manifest.json', base/'suite/truth.json', base/'altered-analysis/analysis.json', base/'altered-score', base)


@pytest.mark.parametrize('problem', ['object_array', 'external', 'wrong_hash', 'wrong_case'])
def test_unsafe_derivatives_or_protocol_rejected(experiment, monkeypatch, problem):
    base, _ = experiment; r = recipe.read(base/'suite/manifest.json')
    if problem == 'object_array':
        p = base/'suite/planes/invented-object.npy'; np.save(p, np.array([{'invented': True}], dtype=object))
        r['cases'][0]['frames'][0] = dict(local_plane='planes/'+p.name, sha256=digest(p))
    elif problem == 'external':
        outside = base.parent/'outside.npy'; r['cases'][0]['frames'][0]['local_plane'] = str(outside)
        original = Path.stat
        def stated(path, *a, **kw):
            assert path != outside; return original(path, *a, **kw)
        monkeypatch.setattr(Path, 'stat', stated)
    elif problem == 'wrong_hash': r['cases'][0]['frames'][0]['sha256'] = '0'*64
    else: r['cases'][1]['peak_sigma'] = 999
    mp = base/'suite'/f'bad-{problem}.json'; recipe.save(mp, r)
    with pytest.raises(ValueError): recipe.analyze(mp, base/('bad-output-'+problem), base)


def test_refused_baseline_not_turned_into_accepted_alignment(experiment):
    base, _ = experiment
    r = recipe.read(base/'background/pilot/pilot.json'); r['models'][1]['model_usable'] = False
    path = base/'refused-pilot.json'; recipe.save(path, r)
    with pytest.raises(ValueError): recipe.generate(path, base/'refused-suite', base)


def test_limit_blocks_keep_null_and_do_not_invent_false_positive_zero(experiment, monkeypatch):
    base, _ = experiment
    def limited(*a, **kw): raise ValueError('Invented source-count limit')
    monkeypatch.setattr(recipe, 'detect_sources', limited)
    result = recipe.analyze(base/'suite/manifest.json', base/'limited-analysis', base)
    assert result['status'] == 'complete' and not result['all_available']
    record = recipe.read(base/'limited-analysis/cases/control.json')
    assert record['candidate_count'] is None and record['data'] is None
    result = recipe.score(base/'suite/manifest.json', base/'suite/truth.json', base/'limited-analysis/analysis.json', base/'limited-score', base)
    assert result['unavailable'] == 36 and result['available_injections'] == 0 and result['missed'] == 0
    assert result['false_candidates'] is None and result['unassociated_candidates'] is None


def test_scoring_failure_keeps_incomplete_status(experiment, monkeypatch):
    base, _ = experiment
    def interrupted(*a, **kw): raise OSError('Invented report-write interruption')
    monkeypatch.setattr(recipe, 'write_score_outputs', interrupted)
    with pytest.raises(OSError):
        recipe.score(base/'suite/manifest.json', base/'suite/truth.json', base/'analysis/analysis.json', base/'score-interrupted', base)
    assert recipe.read(base/'score-interrupted/score.json')['status'] == 'incomplete'


def test_figures_are_labelled_invented_and_do_not_change_inputs(experiment):
    base, _ = experiment
    drawing.plot(base/'score/score.json', base/'figures', base)
    journal = recipe.read(base/'figures/figures.json')
    assert journal['synthetic_background'] and not journal['mixed_real_artificial']
    assert journal['truth_used_after_score_only'] and journal['input_hashes_unchanged']
    with Image.open(base/'figures/injection-comparison.gif') as image:
        assert image.n_frames == 8 and image.info['duration'] == 600
