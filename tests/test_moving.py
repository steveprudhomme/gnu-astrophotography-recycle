# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket
import numpy as np
import pytest
from astropy.io import fits
from gar.moving import find_tracks, remove_stationary, evaluate_tracks, detect_sources, run_moving_synthetic
from gar.workset import digest

spec=importlib.util.spec_from_file_location('moving_demo',Path(__file__).resolve().parents[1]/'examples/make_moving_demo.py')
demo=importlib.util.module_from_spec(spec); spec.loader.exec_module(demo)


def point_case():
    times=np.arange(8)*10.
    points=[np.array([[50+.4*t,80+.2*t]]) for t in times]
    return times,points


def test_known_linear_motion_recovered_without_truth():
    times,points=point_case(); tracks,_=find_tracks(points,times)
    assert len(tracks)==1 and len(tracks[0]['points'])==8
    assert np.allclose(tracks[0]['velocity_pixels_per_second'],[.4,.2],atol=1e-10)
    assert tracks[0]['rms_pixels']<1e-10


def test_stationary_filter_removes_stars_and_very_slow_sources():
    times,points=point_case()
    full=[np.vstack([p,[20,20],[150+.01*t,150]]) for p,t in zip(points,times)]
    moving,removed=remove_stationary(full)
    assert removed==[2]*8 and all(len(p)==1 for p in moving)


def test_missing_frames_can_still_form_a_track():
    times,points=point_case(); points[2]=points[5]=np.empty((0,2))
    tracks,_=find_tracks(points,times)
    assert len(tracks)==1 and len(tracks[0]['points'])==6


@pytest.mark.parametrize('speed',[.01,2.])
def test_outside_search_speed_cannot_form_track(speed):
    times,_=point_case(); points=[np.array([[30+speed*t,80]]) for t in times]
    assert find_tracks(points,times)[0]==[]


def test_insufficient_support_and_time_span_fail():
    times,points=point_case()
    points[4:]=[np.empty((0,2)) for _ in range(4)]
    assert find_tracks(points,times)[0]==[]
    with pytest.raises(ValueError): find_tracks(points[:4],times[:4])


def test_truth_only_changes_scoring_never_candidates():
    times,points=point_case(); tracks,_=find_tracks(points,times); before=deepcopy(tracks)
    target={'injection_id':'fiction','velocity_pixels_per_second':[.4,.2],
            'positions':[{'frame_index':k,'x':float(p[0,0]),'y':float(p[0,1]),'visible':True} for k,p in enumerate(points)]}
    assert evaluate_tracks(tracks,[target])['recovered']==1
    changed=deepcopy(target)
    for p in changed['positions']: p['x']+=10
    assert evaluate_tracks(tracks,[changed])['recovered']==0 and tracks==before
    second={**target,'injection_id':'second'}
    assert evaluate_tracks(tracks,[target,second])['recovered']==1


def test_flat_and_non_monoplane_inputs_rejected():
    with pytest.raises(ValueError): detect_sources(np.ones((64,64)))
    with pytest.raises(ValueError): detect_sources(np.ones((3,64,64)))


@pytest.fixture(scope='module')
def suite(tmp_path_factory):
    local=tmp_path_factory.mktemp('moving')/'local'; demo.make_demo(local/'input')
    return local


def test_complete_pixel_pipeline_is_offline_preserves_inputs_and_reports_limits(suite,monkeypatch):
    local=suite
    files=list((local/'input').rglob('*.fit')); before={p:digest(p) for p in files}
    real_open=fits.open
    def guarded(path,*args,**kwargs):
        assert Path(path) in files and kwargs.get('mode')=='readonly'
        return real_open(path,*args,**kwargs)
    def forbidden(*args,**kwargs): raise AssertionError('Réseau interdit')
    monkeypatch.setattr(fits,'open',guarded); monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    result=run_moving_synthetic(local/'input/manifest.json',local/'input/truth.json',local/'result',local)
    assert result['summary']['exploratory_criteria_passed']
    assert result['summary']['nominal_recovered']==6 and result['summary']['missing_recovered']==3
    assert result['summary']['control_false_candidates']==0
    assert not result['truth_used_for_detection'] and not result['real_data_performance_validated']
    assert result['inputs_sha256_before']==result['inputs_sha256_after']
    assert before=={p:digest(p) for p in files}
    assert any(s['evaluation']['missed'] for s in result['sequences'] if s['scenario']=='faint_slow')
    from xml.etree import ElementTree
    ElementTree.parse(local/'result/moving.svg')


@pytest.mark.parametrize('problem',['declaration','hash','time','marker','shape','outside','truth','existing'])
def test_bad_inputs_cannot_generate_valid_report(tmp_path,problem):
    local=tmp_path/'local'; demo.make_demo(local/'input',seeds=(17,),scenarios=('nominal',))
    mp=local/'input/manifest.json'; tp=local/'input/truth.json'; manifest=json.loads(mp.read_text())
    frame=manifest['sequences'][0]['frames'][0]; path=local/'input'/frame['local_copy']
    if problem=='declaration': manifest['synthetic']=False
    elif problem=='hash': frame['sha256']='0'*64
    elif problem=='time': manifest['sequences'][0]['frames'][1]['relative_time_seconds']=0
    elif problem in ('marker','shape'):
        data=np.zeros((3,256,256)) if problem=='shape' else np.random.default_rng(1).normal(100,2,(256,256))
        fits.writeto(path,data,fits.Header({'GARSYNTH':problem!='marker','SYNCTIME':0.}),overwrite=True)
        frame['sha256']=digest(path)
    elif problem=='outside': frame['local_copy']=str(tmp_path/'outside.fit')
    elif problem=='truth':
        truth=json.loads(tp.read_text()); truth['manifest_sha256']='0'*64; tp.write_text(json.dumps(truth))
    else: (local/'result').mkdir()
    mp.write_text(json.dumps(manifest))
    with pytest.raises(ValueError): run_moving_synthetic(mp,tp,local/'result',local)


def test_subset_is_reported_without_claiming_complete_benchmark(tmp_path):
    local=tmp_path/'local'; demo.make_demo(local/'input',seeds=(17,),scenarios=('nominal',))
    result=run_moving_synthetic(local/'input/manifest.json',local/'input/truth.json',local/'result',local)
    assert result['summary']['nominal_recovered']==2
    assert not result['summary']['frozen_suite_complete'] and not result['summary']['exploratory_criteria_passed']
