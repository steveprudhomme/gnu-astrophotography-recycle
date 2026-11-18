# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Independent development pixels; the two new reserved seeds are never searched."""
from copy import deepcopy
from pathlib import Path
import socket
import sys
import numpy as np
import pytest
from astropy.table import Table
from gar.workset import digest
import gar.moving as old
import gar.nearby_moving as detector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
import nearby_motion_profile as recipe
import plot_nearby_motions as drawing
from test_slow_diagnostic import development


def plane(neighbour=False):
    rng=np.random.default_rng(27182818);yy,xx=np.mgrid[:96,:96]
    result=100+rng.normal(0,1,(96,96))+16*np.exp(-((xx-48)**2+(yy-48)**2)/(2*1.1**2))
    if neighbour:result+=900*np.exp(-((xx-48)**2+(yy-41)**2)/(2*1.1**2))
    return result.astype('float32')


def test_only_the_comparison_radius_changes():
    a,b=detector.signature(1.25,5),detector.signature(1.25,3)
    assert a['minimum_separation_reduced']==5 and b['minimum_separation_reduced']==3
    assert {k:v for k,v in a.items() if k!='minimum_separation_reduced'}=={k:v for k,v in b.items() if k!='minimum_separation_reduced'}
    assert a['threshold_sigma']==5 and a['fwhm_reduced']==3


def test_actual_constructors_keep_threshold_kernel_and_shape(monkeypatch):
    called=[];factory=detector.DAOStarFinder
    def recorded(*a,**kw):called.append(kw.copy());return factory(*a,**kw)
    monkeypatch.setattr(old,'DAOStarFinder',recorded);monkeypatch.setattr(detector,'DAOStarFinder',recorded)
    old.detect_sources(plane());detector.detect_sources(plane())
    a,b=called
    assert a.pop('min_separation')==5 and b.pop('min_separation')==3 and a==b


def test_isolated_position_noise_mask_and_original_pixels_are_preserved():
    image=plane();image[1,1]=np.nan;image[2,2]=65535;before=image.copy()
    a,sa=old.detect_sources(image);b,sb=detector.detect_sources(image)
    assert np.allclose(a,b,atol=1e-12,rtol=0)
    assert all(sa[k]==sb[k] for k in ('background','noise_sigma'))
    assert np.array_equal(image,before,equal_nan=True)


def test_separated_bright_neighbor_keeps_an_already_visible_source():
    a,_=old.detect_sources(plane(True));b,_=detector.detect_sources(plane(True))
    target=np.array([48.,48.])
    assert np.min(np.linalg.norm(b-target,axis=1))<.75
    assert np.min(np.linalg.norm(a-target,axis=1))<.75
    assert np.allclose(a,b,atol=1e-12,rtol=0)


def test_radius_three_and_five_differ_on_an_independent_peak_map():
    from photutils.detection import find_peaks
    image=np.zeros((64,64));image[32,32]=10.;image[32,36]=20.
    old_peaks=find_peaks(image,5.,min_separation=5)
    new_peaks=find_peaks(image,5.,min_separation=3)
    assert list(old_peaks['x_peak'])==[36]
    assert set(new_peaks['x_peak'])=={32,36}


@pytest.mark.parametrize('image',[np.zeros((16,16)),np.zeros((64,64)),np.zeros((3,32,32))])
def test_invalid_shape_or_zero_noise_is_refused(image):
    with pytest.raises(ValueError):detector.detect_sources(image)


def test_source_limit_is_a_refusal_without_truncation(monkeypatch):
    table=Table(dict(x_centroid=np.full(501,20.),y_centroid=np.full(501,20.)))
    monkeypatch.setattr(detector,'DAOStarFinder',lambda **kw:lambda *a,**k:table)
    with pytest.raises(ValueError,match='500'):detector.detect_sources(plane())


@pytest.fixture(scope='module')
def compared(development):
    base,folder=development
    recipe.analyze(folder/'suite/manifest.json',folder/'paired-analysis',base)
    result=recipe.score(folder/'suite/manifest.json',folder/'suite/truth.json',folder/'paired-analysis/analysis.json',folder/'paired-score',base)
    return base,folder,result


def test_paired_reference_reproduces_the_original_score(compared):
    base,folder,result=compared
    original=recipe.slow.read(folder/'score/score.json')
    assert result['reference_control_identical_to_baseline'] is True
    assert result['variants']['reference']['rows']==original['rows']
    assert result['variants']['reference']['recovered']==original['recovered']
    assert result['variants']['radius3']['control_candidates']==0
    assert not result['science_fitness_passed'] and not result['known_natural_positive_tested']
    assert recipe.SEEDS==(2026112601,2026112602)


def test_analysis_does_not_open_answers_or_access_source_or_network(compared,monkeypatch):
    base,folder,_=compared;opened=Path.open
    def guarded(p,*a,**kw):
        assert p.name!='truth.json' and 'invented-source' not in p.parts
        return opened(p,*a,**kw)
    def offline(*a,**kw):raise AssertionError('No network')
    monkeypatch.setattr(Path,'open',guarded);monkeypatch.setattr(socket.socket,'connect',offline)
    result=recipe.analyze(folder/'suite/manifest.json',folder/'blind-paired',base)
    assert result['all_available'] and not result['truth_opened'] and not result['models_refitted']
    assert len(result['records'])==26


def test_all_twenty_six_candidates_are_checked_before_truth(compared,monkeypatch):
    base,folder,_=compared;path=folder/'paired-analysis/cases/radius3-r60-a12-p2.json'
    original=path.read_bytes();opened=Path.open
    def guarded(p,*a,**kw):
        assert p.name!='truth.json';return opened(p,*a,**kw)
    try:
        path.write_bytes(original+b' ');monkeypatch.setattr(Path,'open',guarded)
        with pytest.raises(ValueError):recipe.score(folder/'suite/manifest.json',folder/'suite/truth.json',folder/'paired-analysis/analysis.json',folder/'bad-score',base)
    finally:path.write_bytes(original)


@pytest.mark.parametrize('problem',['source_kind','variants','truth','order','hash'])
def test_modified_analysis_is_refused_before_answers(compared,monkeypatch,problem):
    base,folder,_=compared;value=recipe.slow.read(folder/'paired-analysis/analysis.json')
    if problem=='source_kind':value['source_kind']='real_local_copies'
    elif problem=='variants':value['variants'].reverse()
    elif problem=='truth':value['truth_opened']=True
    elif problem=='order':value['records'].reverse()
    else:value['records'][-1]['sha256']='0'*64
    target=folder/'paired-analysis'/f'bad-analysis-{problem}.json';recipe.slow.save(target,value)
    opened=Path.open
    def guarded(p,*a,**kw):
        assert p.name!='truth.json';return opened(p,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    with pytest.raises(ValueError):recipe.score(folder/'suite/manifest.json',folder/'suite/truth.json',target,folder/f'bad-analysis-score-{problem}',base)


def test_blocked_profiles_keep_unknown_counts(compared,monkeypatch):
    base,folder,_=compared
    def blocked(*a,**kw):raise ValueError('Invented source limit')
    monkeypatch.setattr(recipe,'process',blocked)
    result=recipe.analyze(folder/'suite/manifest.json',folder/'blocked-analysis',base)
    assert not result['all_available']
    score=recipe.score(folder/'suite/manifest.json',folder/'suite/truth.json',folder/'blocked-analysis/analysis.json',folder/'blocked-score',base)
    for variant in recipe.VARIANTS:
        value=score['variants'][variant]
        assert value['recovered'] is value['missed'] is value['unassociated_candidates'] is None
        assert value['false_candidates'] is value['control_candidates'] is None
        assert value['unavailable']==12
    assert score['synthetic_criteria_passed'] is False


def test_missing_candidates_after_interruption_never_score_as_complete(compared,monkeypatch):
    base,folder,_=compared;original=recipe.process;calls=[]
    def interrupted(*a,**kw):
        calls.append(1)
        if len(calls)==3:raise OSError('Invented interruption after the paired control')
        return original(*a,**kw)
    monkeypatch.setattr(recipe,'process',interrupted)
    with pytest.raises(OSError):recipe.analyze(folder/'suite/manifest.json',folder/'partial-analysis',base)
    assert recipe.slow.read(folder/'partial-analysis/analysis.json')['status']=='incomplete'
    with pytest.raises(ValueError):recipe.score(folder/'suite/manifest.json',folder/'suite/truth.json',folder/'partial-analysis/analysis.json',folder/'partial-score',base)


@pytest.mark.parametrize('problem',['incomplete','count','threshold','lost','criterion','variant'])
def test_modified_scores_are_refused_before_drawing(compared,problem):
    base,folder,_=compared;value=recipe.slow.read(folder/'paired-score/score.json')
    if problem=='incomplete':value['status']='incomplete'
    elif problem=='count':value['variants']['radius3']['recovered']+=1
    elif problem=='threshold':value['luminosity_threshold_sigma']=4
    elif problem=='lost':value['lost_reference_cases'].append('invented')
    elif problem=='criterion':value['synthetic_criteria_passed']=not value['synthetic_criteria_passed']
    else:value['variants']['reference']['control_candidates']+=1
    target=folder/'paired-score'/f'bad-{problem}.json';recipe.slow.save(target,value)
    with pytest.raises(ValueError):drawing.plot(target,folder/f'bad-figures-{problem}',base)


def test_figures_repeat_without_detection_or_association(compared,monkeypatch):
    base,folder,_=compared
    def forbidden(*a,**kw):raise AssertionError('No search during drawing')
    monkeypatch.setattr(recipe,'process',forbidden);monkeypatch.setattr(recipe,'detect_sources',forbidden)
    monkeypatch.setattr(recipe.slow,'process',forbidden);monkeypatch.setattr(recipe.slow,'find_tracks',forbidden)
    a=drawing.plot(folder/'paired-score/score.json',folder/'paired-figures-1',base)
    b=drawing.plot(folder/'paired-score/score.json',folder/'paired-figures-2',base)
    assert a['figures_sha256']==b['figures_sha256']
    assert set(a['figures_sha256'])=={'recovery.png','comparison-first.png','comparison-static.png','comparison.gif'}
    assert a['static_frames_fixed']==[0,3]


def test_duplicates_count_as_false_candidates_in_synthetic_score(compared):
    base,folder,_=compared
    _,_,_,manifest,records,answers,_,_=recipe.inputs(folder/'suite/manifest.json',folder/'suite/truth.json',folder/'paired-analysis/analysis.json',base)
    records=deepcopy(records)
    selected=next(r for cid,r in records['radius3'].items() if cid!='control' and r['data']['search']['tracks'])
    duplicate=deepcopy(selected['data']['search']['tracks'][0]);duplicate['candidate_id']=9999
    selected['data']['search']['tracks'].append(duplicate)
    baseline=recipe.slow.read(Path(manifest['baseline_report']))
    result=recipe.values(manifest,records,answers,baseline)
    assert result['variants']['radius3']['false_candidates']>=1
    assert result['synthetic_criteria_passed'] is False


def test_lost_reference_recovery_is_visible_and_fails_the_criterion(compared):
    base,folder,score=compared
    _,_,_,manifest,records,answers,_,_=recipe.inputs(folder/'suite/manifest.json',folder/'suite/truth.json',folder/'paired-analysis/analysis.json',base)
    records=deepcopy(records)
    cid=next(r['case_id'] for r in score['variants']['reference']['rows'][1:] if r['recovered']==1)
    records['radius3'][cid]['data']['search']['tracks']=[]
    baseline=recipe.slow.read(Path(manifest['baseline_report']))
    result=recipe.values(manifest,records,answers,baseline)
    assert cid in result['lost_reference_cases'] and result['synthetic_criteria_passed'] is False


def test_existing_outputs_and_historical_sources_are_preserved(compared):
    base,folder,_=compared;path=folder/'score/score.json';before=digest(path)
    with pytest.raises(FileExistsError):recipe.analyze(folder/'suite/manifest.json',folder/'paired-analysis',base)
    assert digest(path)==before and recipe.frozen()


def test_interrupted_reserved_generator_keeps_partial_state(tmp_path,monkeypatch):
    base=tmp_path/'local';base.mkdir()
    def interrupted(*a,**kw):raise OSError('Invented interruption before reserved images')
    monkeypatch.setattr(recipe.demo,'make_context',interrupted)
    with pytest.raises(OSError):recipe.make(base/'partial',base)
    assert recipe.slow.read(base/'partial/contexts.json')['status']=='incomplete'
