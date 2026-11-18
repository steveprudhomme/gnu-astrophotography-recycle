# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Development fixtures only; never analyse the two new reserved seeds here."""
import json
from pathlib import Path
import socket
import sys
import numpy as np
import pytest
from gar.workset import digest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
import diagnose_slow_misses as diagnostic
import make_asymmetric_slow_demo as demo
import plot_slow_diagnostic as drawing
import slow_motion_profile as slow


def fabrication():
    center = np.array([255.5, 255.5]); models = []
    for k in range(8):
        angle = np.deg2rad(.5*k/7)
        r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        t = center-r@center+[3.5*k/7, 0.]
        models.append(dict(model_usable=True, rotation_matrix=r.T.tolist(), translation_pixels=(-r.T@t).tolist()))
    return dict(source_kind='synthetic_demo', image_shape=[512, 512],
                relative_declared_seconds=list(demo.TIMES), models=models)


def test_known_inverse_rotation_and_translation_are_independently_checked():
    result = diagnostic.rotation_audit(fabrication())
    assert result['passed'] and not result['models_replaced']
    assert all(r['spatial_max_native_pixels'] < 1e-10 for r in result['frames'])
    assert all(abs(r['rotation_error_degrees']) < 1e-10 for r in result['frames'])


def test_accepted_half_turn_is_detected_without_replacing_it():
    value = fabrication(); model = value['models'][2]
    model['rotation_matrix'] = (-np.asarray(model['rotation_matrix'])).tolist()
    before = json.dumps(value)
    result = diagnostic.rotation_audit(value)
    assert not result['passed'] and result['frames'][2]['registration_accepted']
    assert abs(result['frames'][2]['rotation_error_degrees']) == pytest.approx(180)
    assert json.dumps(value) == before


def test_real_orientation_truth_is_unknown():
    result = diagnostic.rotation_audit(dict(source_kind='real_local_copies'))
    assert result['passed'] is None and not result['applicable']


@pytest.mark.parametrize('field,value', [('image_shape',[256,256]),('relative_declared_seconds',list(range(8))),('models',[])])
def test_wrong_fabrication_is_refused(field, value):
    baseline = fabrication(); baseline[field] = value
    with pytest.raises(ValueError): diagnostic.rotation_audit(baseline)


@pytest.mark.parametrize('count,span,expected', [(5,1800,False),(6,1500,False),(6,1800,True),(8,2100,True)])
def test_frame_count_and_span_are_both_required(count, span, expected):
    frames = [dict(frame_index=k,mapped=dict(within_radius=k<count)) for k in range(8)]
    times = [k*span/(count-1) for k in range(8)]
    result = diagnostic.support(frames,times,'mapped')
    assert result['sufficient'] is expected


def test_nearby_preserves_absence_and_possible_confusion():
    assert diagnostic.nearby([],np.array([1.,1.]),1.5)['distance'] is None
    result = diagnostic.nearby([[1.,1.],[1.1,1.1]],np.array([1.,1.]),1.5)
    assert result['within_radius'] and result['neighbours_in_radius']==2
    assert not diagnostic.nearby([[3.,1.]],np.array([1.,1.]),1.5)['within_radius']


def test_descriptive_fit_is_not_a_candidate_and_keeps_failed_gates():
    times = np.array(demo.TIMES)
    points = np.array([100.,100.])+times[:,None]*[.002,.001]
    result = diagnostic.descriptive_fit(points,times,demo.SCALE)
    assert not result['candidate'] and result['truth_guided_after_search']
    assert not result['failed_gates']
    stationary = diagnostic.descriptive_fit(np.tile([100.,100.],(8,1)),times,demo.SCALE)
    assert {'nominal_speed','displacement','fixed_linear_improvement'} <= set(stationary['failed_gates'])
    assert diagnostic.descriptive_fit(points[:5],times[:5],demo.SCALE) is None


def test_asymmetric_development_positions_are_deterministic_and_not_a_grid():
    first = demo.background_sources(31415926)
    assert first == demo.background_sources(31415926)
    assert first != demo.background_sources(31415927)
    assert len(first)>70
    assert len(set(round(p[0],5) for p in first))>60
    assert demo.SEEDS==(2026112401,2026112402)


@pytest.fixture(scope='module')
def development(tmp_path_factory):
    base=tmp_path_factory.mktemp('slow-diagnostic')/'local'; base.mkdir()
    folder=base/'development'
    result=demo.make_context(folder,31415926,base)
    assert result['experiment_admissible']
    slow.generate(folder/'baseline/baseline.json',folder/'suite',base)
    slow.analyze(folder/'suite/manifest.json',folder/'analysis',base)
    slow.score(folder/'suite/manifest.json',folder/'suite/truth.json',folder/'analysis/analysis.json',folder/'score',base)
    diagnostic.diagnose(folder/'score/score.json',folder/'diagnostic',base)
    return base,folder


def test_diagnostic_and_drawing_are_offline_and_never_search(development,monkeypatch):
    base,folder=development
    def forbidden(*a,**kw): raise AssertionError('No search, injection, registration or network in diagnostic')
    for name in ('process','find_tracks','detect_sources','register_spatial'):
        monkeypatch.setattr(slow,name,forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    value=diagnostic.diagnose(folder/'score/score.json',folder/'again',base)
    assert value['rows']==slow.read(folder/'diagnostic/diagnostic.json')['rows']
    first=drawing.plot(folder/'again/diagnostic.json',folder/'figures-1',base)
    second=drawing.plot(folder/'again/diagnostic.json',folder/'figures-2',base)
    assert first['figures_sha256']==second['figures_sha256']
    assert not first['association_called'] and not first['detector_called']


@pytest.mark.parametrize('problem',['incomplete','misses','support','rotation','source'])
def test_modified_diagnostic_is_refused_before_drawing(development,problem):
    base,folder=development
    value=slow.read(folder/'diagnostic/diagnostic.json')
    if problem=='incomplete':value['status']='incomplete'
    elif problem=='misses':value['bright_misses'].append('invented')
    elif problem=='support':value['rows'][0]['radii'][0]['mapped_support']['frames']+=1
    elif problem=='rotation':value['registration_audit']['passed']=not value['registration_audit']['passed']
    else:value['diagnostic_source_sha256_lf']='0'*64
    target=folder/f'bad-{problem}.json'; slow.save(target,value)
    with pytest.raises(ValueError):drawing.plot(target,folder/f'bad-figures-{problem}',base)


def test_all_candidates_are_checked_before_truth(development,monkeypatch):
    base,folder=development
    path=folder/'analysis/cases/r60-a12-p2.json'
    original=path.read_bytes(); path.write_bytes(original+b' ')
    opened=Path.open
    def guard(p,*a,**kw):
        assert p.name!='truth.json'
        return opened(p,*a,**kw)
    try:
        monkeypatch.setattr(Path,'open',guard)
        with pytest.raises(ValueError):diagnostic.diagnose(folder/'score/score.json',folder/'bad-score',base)
    finally:
        path.write_bytes(original)


def test_historical_sources_and_original_outputs_are_preserved(development):
    base,folder=development
    before=digest(folder/'score/score.json')
    assert diagnostic.historical()
    with pytest.raises(FileExistsError):diagnostic.diagnose(folder/'score/score.json',folder/'diagnostic',base)
    assert digest(folder/'score/score.json')==before


def test_inconsistent_mapped_positions_are_refused(development,monkeypatch):
    base,folder=development
    checked=slow.checked_score
    def inconsistent(*a,**kw):
        result=checked(*a,**kw)
        result[4]['r10-a12-p1']['data']['mapped_detections'][0][0][0]+=1
        return result
    monkeypatch.setattr(slow,'checked_score',inconsistent)
    with pytest.raises(ValueError,match='recalées'):
        diagnostic.diagnose(folder/'score/score.json',folder/'bad-mapping',base)


def test_blocked_cases_remain_unknown_in_diagnostic_and_figures(development,monkeypatch):
    base,folder=development
    def blocked(*a,**kw):raise ValueError('Invented source limit')
    monkeypatch.setattr(slow,'process',blocked)
    slow.analyze(folder/'suite/manifest.json',folder/'blocked-analysis',base)
    slow.score(folder/'suite/manifest.json',folder/'suite/truth.json',folder/'blocked-analysis/analysis.json',folder/'blocked-score',base)
    result=diagnostic.diagnose(folder/'blocked-score/score.json',folder/'blocked-diagnostic',base)
    assert result['bright_misses']==[]
    assert all(r['status']=='unavailable' and r['originally_recovered'] is None for r in result['rows'])
    drawing.plot(folder/'blocked-diagnostic/diagnostic.json',folder/'blocked-figures',base)


@pytest.mark.parametrize('points,expected', [([[float('nan'),1.]],np.array([1.,1.])),([[1.,1.]],np.array([float('inf'),1.]))])
def test_nonfinite_nearby_coordinates_are_refused(points,expected):
    with pytest.raises(ValueError):diagnostic.nearby(points,expected,1.5)


def test_interrupted_generation_keeps_a_partial_report(tmp_path,monkeypatch):
    base=tmp_path/'local';base.mkdir()
    def interrupted(*a,**kw):raise OSError('Invented interruption before reserved generation')
    monkeypatch.setattr(demo,'make_context',interrupted)
    with pytest.raises(OSError):demo.make(base/'partial',base)
    result=slow.read(base/'partial/contexts.json')
    assert result['status']=='incomplete' and result['contexts']==[]
