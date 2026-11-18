# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Replay and cache checks on independent fictitious development pixels."""
from pathlib import Path
import socket
import sys
import numpy as np
import pytest
from gar.workset import digest
import gar.moving as moving

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
import trace_slow_detector as tracing
import plot_slow_detector as drawing
from test_slow_diagnostic import development


@pytest.fixture(scope='module')
def traced(development):
    base,folder=development
    result=tracing.run(folder/'score/score.json',folder/'detector-trace',base)
    return base,folder,result


def test_all_native_positions_and_fixed_comparison_cohorts_are_preserved(traced):
    base,folder,result=traced
    assert result['status']=='complete' and result['replay_count']==16
    assert result['truth_opened_after_replay'] and result['all_saved_points_equal']
    assert [p['focus'] for p in result['pairs']]==[True]*3+[False]*5
    assert result['summary']['1.5']['focus']['images']==3
    assert result['summary']['3']['later']['images']==5
    assert len(result['pair_records'])==8 and len(result['replay_records'])==16
    checked,cached,_=tracing.checked(folder/'detector-trace/trace.json',base)
    assert checked==result and len(cached)==16
    for cid in tracing.VARIANTS:
        for k in range(8):
            assert cached[cid,k][0]['trace']['old_detector_trace']['replay_equal']


def test_native_comparison_uses_one_billionth_pixel_tolerance():
    original=np.array([[100.,100.]])
    tracing.peaks.previous.equal_points(original,original+1e-10,'development')
    with pytest.raises(ValueError):
        tracing.peaks.previous.equal_points(original,original+2e-9,'development')


def test_above_threshold_sample_can_fail_local_maximum_with_higher_neighbor():
    image=np.zeros((96,96),dtype=float);image[48,48]=10.;image[48,52]=20.
    trace=tracing.peaks.trace_convolved(image,np.zeros_like(image,dtype=bool),5.)
    evidence=tracing.peaks.evidence_at(trace,np.array([96.5,96.5]),1.5)
    assert evidence['first_empty_stage']=='local_maximum'
    assert evidence['independent_pass_counts']['above_threshold']>0
    assert evidence['higher_neighbor']['value_for_peaks']==20.
    assert not evidence['physical_cause_proven']


def test_truth_is_not_opened_until_every_raw_replay_is_sealed(development,monkeypatch):
    base,folder=development;out=folder/'blind-replay';calls=[];reads=[]
    opened=Path.open;trace=tracing.peaks.trace_image
    def guarded(p,*a,**kw):
        if p.name=='truth.json':
            assert len(calls)==16
            files=[p for p in (out/'frames').glob('*.json') if not p.name.startswith('evidence-')]
            assert len(files)==16
            reads.append(str(p))
        return opened(p,*a,**kw)
    def recorded(*a,**kw):
        assert len(a)==1 and not kw
        result=trace(*a,**kw);calls.append(1);return result
    def forbidden(*a,**kw):raise AssertionError('No association, registration, injection or network')
    monkeypatch.setattr(Path,'open',guarded)
    monkeypatch.setattr(tracing.peaks,'trace_image',recorded)
    for name in ('find_tracks','process','register_spatial'):
        monkeypatch.setattr(tracing.slow,name,forbidden)
    monkeypatch.setattr(moving,'find_tracks',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    result=tracing.run(folder/'score/score.json',out,base)
    assert reads and result['truth_opened_after_replay']


def test_divergent_replay_is_refused_and_keeps_incomplete_state(development,monkeypatch):
    base,folder=development;original=tracing.peaks.trace_image
    def changed(*a,**kw):
        result=original(*a,**kw)
        result['old_detector_trace']['selected_points_reduced'][0][0]+=.01
        return result
    monkeypatch.setattr(tracing.peaks,'trace_image',changed)
    with pytest.raises(ValueError,match='Positions différentes'):
        tracing.run(folder/'score/score.json',folder/'divergence',base)
    result=tracing.slow.read(folder/'divergence/trace.json')
    assert result['status']=='incomplete' and not result['truth_opened_after_replay']
    assert result['pairs']==[]


@pytest.mark.parametrize('problem',['incomplete','summary','threshold','pair','crop','display','cohort','recovered'])
def test_modified_trace_is_refused_before_drawing(traced,problem):
    base,folder,_=traced
    value=tracing.slow.read(folder/'detector-trace/trace.json')
    if problem=='incomplete':value['status']='incomplete'
    elif problem=='summary':value['summary']['1.5']['focus']['images']+=1
    elif problem=='threshold':value['thresholds_changed']=True
    elif problem=='pair':value['pair_records'][0]['sha256']='0'*64
    elif problem=='crop':value['pairs'][0]['variants']['control']['view']['original_pixels'][0][0]+=1
    elif problem=='display':value['display_noise']*=2
    elif problem=='cohort':value['pairs'][0]['focus']=False
    else:value['original_recovered']=1-value['original_recovered']
    p=folder/'detector-trace'/f'bad-{problem}.json';tracing.slow.save(p,value)
    with pytest.raises(ValueError):drawing.plot(p,folder/f'bad-figures-{problem}',base)


def test_modified_raw_cache_is_refused(traced):
    base,folder,result=traced
    path=folder/'detector-trace'/result['replay_records'][-1]['file']
    original=path.read_bytes()
    try:
        path.write_bytes(original+b' ')
        with pytest.raises(ValueError):tracing.checked(folder/'detector-trace/trace.json',base)
    finally:path.write_bytes(original)


def test_modified_candidates_are_refused_before_truth(traced,monkeypatch):
    base,folder,_=traced
    path=folder/'analysis/cases/r60-a12-p2.json';original=path.read_bytes();opened=Path.open
    def guard(p,*a,**kw):
        assert p.name!='truth.json'
        return opened(p,*a,**kw)
    try:
        path.write_bytes(original+b' ');monkeypatch.setattr(Path,'open',guard)
        with pytest.raises(ValueError):tracing.run(folder/'score/score.json',folder/'bad-candidates',base)
        assert not (folder/'bad-candidates').exists()
    finally:path.write_bytes(original)


def test_real_or_incomplete_score_is_refused_before_output(traced):
    base,folder,_=traced
    value=tracing.slow.read(folder/'score/score.json');value['source_kind']='real_local_copies'
    p=folder/'score/wrong-source.json';tracing.slow.save(p,value)
    with pytest.raises(ValueError):tracing.run(p,folder/'no-real-replay',base)
    assert not (folder/'no-real-replay').exists()


def test_figures_repeat_without_detector_or_convolution(traced,monkeypatch):
    base,folder,_=traced
    def forbidden(*a,**kw):raise AssertionError('Drawing cannot replay a detector or convolve pixels')
    monkeypatch.setattr(tracing.peaks,'trace_image',forbidden)
    monkeypatch.setattr(tracing.peaks,'trace_convolved',forbidden)
    monkeypatch.setattr(tracing.peaks.previous,'trace_image',forbidden)
    monkeypatch.setattr(tracing.slow,'find_tracks',forbidden)
    first=drawing.plot(folder/'detector-trace/trace.json',folder/'trace-figures-1',base)
    second=drawing.plot(folder/'detector-trace/trace.json',folder/'trace-figures-2',base)
    assert first['figures_sha256']==second['figures_sha256']
    assert first['comparison_frames_fixed']==[0,3]
    assert not first['detector_called'] and not first['convolution_called']


def test_existing_outputs_and_historical_sources_are_preserved(traced):
    base,folder,_=traced;path=folder/'score/score.json';before=digest(path)
    with pytest.raises(FileExistsError):tracing.run(path,folder/'detector-trace',base)
    assert digest(path)==before and tracing.frozen()
