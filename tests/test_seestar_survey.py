# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Fictional development sessions; no external archive or real data required."""
from copy import deepcopy
from pathlib import Path
import socket,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
import seestar_survey as survey
import make_survey_demo as demo
import plot_seestar_survey as drawing
import copy_survey_worksets as copying
from gar.workset import digest


@pytest.fixture(scope='module')
def batch(tmp_path_factory):
    base=tmp_path_factory.mktemp('survey-development')
    with pytest.MonkeyPatch.context() as m:
        m.setattr(demo,'SEEDS',(31415001,31415002));demo.make(base/'demo',base)
    plan=base/'demo/plan/plan.json';index=base/'demo/worksets.json'
    result=survey.run(plan,index,base/'analysis',base)
    return base,plan,index,result


def test_four_windows_are_disjoint_and_use_the_original_cadence(batch):
    base,plan,index,result=batch;p=survey.slow.read(plan)
    assert len(p['rows'])==4 and all(r['selection_available'] for r in p['rows'])
    assert [r['nominal_start_seconds'] for r in p['rows']]==[0,2400,0,2400]
    assert len({f['sha256'] for r in p['rows'] for f in r['frames']})==32
    assert result['summary']['radius3']['available_series']==4
    assert not result['known_natural_positive_tested'] and not result['truth_opened']


def test_planning_reads_only_the_local_manifest(batch,monkeypatch):
    base,plan,_,_=batch;mp=Path(survey.slow.read(plan)['inventory_path']);opened=Path.open
    def guarded(p,*a,**kw):
        if p.suffix.lower() in ('.fit','.fits'):raise AssertionError('No source access while planning')
        return opened(p,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    result=survey.plan(mp,base/'offline-plan',base)
    assert result['source_accessed'] is False


@pytest.mark.parametrize('change',['hash','time','overlap','stack'])
def test_bad_selection_is_preserved_without_replacement(batch,change):
    base,plan,_,_=batch;m=survey.slow.read(survey.slow.read(plan)['inventory_path'])
    # Alter metadata only, never the fictitious pixel files.
    if change=='hash':
        for f in m['files']:
            f['sha256']='a'*64
            for h in f['hdus']:h['frame_id']=f"{f['sha256']}:{h['hdu_index']}"
    elif change=='time':
        for f in m['files']:f['hdus'][0]['metadata']['DATE-OBS']='2025-01-01T00:00:00'
    elif change=='stack':
        for f in m['files']:f['hdus'][0]['metadata']['STACKCNT']=2
    else:
        # Keep the first window only in each session; the second must be refused.
        from gar.contracts import parse_declared_time
        first={}
        for f in m['files']:
            h=f['hdus'][0];date=parse_declared_time(h['metadata']['DATE-OBS']);key=h['metadata']['OBJECT']
            first[key]=min(first.get(key,date),date)
        m['files']=[f for f in m['files'] if (parse_declared_time(f['hdus'][0]['metadata']['DATE-OBS'])-first[f['hdus'][0]['metadata']['OBJECT']]).total_seconds()<=2100]
    rows=survey.select(m)
    assert rows and any(not r['selection_available'] for r in rows)


def test_plan_changes_are_refused(batch):
    base,plan,_,_=batch;r=survey.slow.read(plan);r['rows'][0]['selected_indices'][0]=999
    bad=plan.parent/'changed.json';survey.slow.save(bad,r)
    with pytest.raises(ValueError):survey.checked_plan(bad,base)


@pytest.mark.parametrize('kind',['missing','hash','wrong-series'])
def test_missing_or_wrong_copies_leave_unknown_counts(batch,kind):
    base,plan,index,_=batch;value=survey.slow.read(index);entries=value['entries'];value['entries']={}
    if kind=='hash':value['entries']['S01']=dict(entries['S01'],sha256='0'*64)
    if kind=='wrong-series':value['entries']['S01']=entries['S02']
    path=base/f'index-{kind}.json';survey.slow.save(path,value)
    result=survey.run(plan,path,base/f'blocked-{kind}',base)
    assert all(s['candidate_occurrences'] is None and s['unavailable_series']==4 for s in result['summary'].values())
    survey.checked(base/f'blocked-{kind}/survey.json',base)


def test_repeated_workset_is_refused_before_processing(batch):
    base,plan,index,_=batch;r=survey.slow.read(index);r['entries']['S02']=r['entries']['S01']
    path=base/'repeated-index.json';survey.slow.save(path,r)
    with pytest.raises(ValueError,match='répété'):survey.run(plan,path,base/'repeated',base)
    assert not (base/'repeated').exists()


def test_completed_searches_keep_both_frozen_profiles_and_shared_models(batch):
    base,_,_,_=batch;r,records,_=survey.checked(base/'analysis/survey.json',base)
    assert all(rec['source_kind']=='synthetic_demo' for rec in records)
    for rec in records:
        a,b=[rec['profiles'][v] for v in survey.paired.VARIANTS]
        survey.paired.compare_settings(a['data'],b['data'])
        assert all(d['data']['search']['parameters']==survey.slow.PARAMETERS for d in rec['profiles'].values())


def test_altered_summary_is_refused(batch):
    base,_,_,r=batch;r=deepcopy(r);r['summary']['radius3']['candidate_occurrences']=999
    path=base/'analysis/changed-summary.json';survey.slow.save(path,r)
    with pytest.raises(ValueError,match='Synthèse'):survey.checked(path,base)


def test_sealed_candidate_changes_are_refused(batch):
    base,_,_,r=batch;path=base/'analysis'/r['records'][0]['file'];original=path.read_bytes()
    try:
        path.write_bytes(original+b' ')
        with pytest.raises(ValueError,match='modifié'):survey.checked(base/'analysis/survey.json',base)
    finally:path.write_bytes(original)


def test_incomplete_run_is_preserved(batch,monkeypatch):
    base,plan,index,_=batch
    def crash(*a,**k):raise RuntimeError('interruption de développement')
    monkeypatch.setattr(survey.slow,'prepare',crash)
    with pytest.raises(RuntimeError):survey.run(plan,index,base/'interrupted',base)
    r=survey.slow.read(base/'interrupted/survey.json');assert r['status']=='incomplete'
    with pytest.raises(ValueError):survey.checked(base/'interrupted/survey.json',base)


def test_drawing_is_offline_without_detection_registration_or_association(batch,monkeypatch):
    base,_,_,_=batch
    def forbidden(*a,**k):raise AssertionError('Drawing cannot search or access a network')
    monkeypatch.setattr(survey.paired,'process',forbidden)
    monkeypatch.setattr(survey.slow,'prepare',forbidden)
    monkeypatch.setattr(survey.slow,'detect',forbidden)
    monkeypatch.setattr(survey.slow,'find_tracks',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    result=drawing.plot(base/'analysis/survey.json',base/'figures',base)
    assert not result['detector_called'] and not result['registration_called'] and not result['association_called']
    assert 'overview.png' in result['figures_sha256']
    assert len([n for n in result['figures_sha256'] if n.endswith('.gif')])==8


def test_existing_outputs_are_preserved(batch):
    base,plan,index,_=batch;before=digest(base/'analysis/survey.json')
    with pytest.raises(FileExistsError):survey.run(plan,index,base/'analysis',base)
    assert digest(base/'analysis/survey.json')==before


def test_copy_from_explicit_cache_never_opens_archive_sources(batch,monkeypatch):
    base,plan,index,_=batch;entries=survey.slow.read(index)['entries']
    cache=base/'cache.json';survey.slow.save(cache,dict(survey_copy_cache_version='1.0',worksets=[e['path'] for e in entries.values()]))
    opened=Path.open
    def guarded(p,*a,**kw):
        if 'invented-source' in p.parts:raise AssertionError('Cached copies must suffice')
        return opened(p,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    result=copying.copy(plan,base/'cached-copies',cache,base)
    assert len(result['entries'])==4 and not result['errors']
    assert all(origin=='local_verified_copy' for row in result['copy_origins'].values() for origin in row)


def test_copy_without_cache_reads_only_exact_selected_sources(batch,monkeypatch):
    base,plan,_,_=batch;p=survey.slow.read(plan);m=survey.slow.read(p['inventory_path'])
    allowed={Path(m['input_root'])/f['path'] for row in p['rows'] for f in row['frames']}
    opened=Path.open;reads=set()
    def guarded(path,*a,**kw):
        if 'invented-source' in path.parts:
            assert path in allowed and (a[0] if a else kw.get('mode','r'))=='rb';reads.add(path)
        return opened(path,*a,**kw)
    monkeypatch.setattr(Path,'open',guarded)
    result=copying.copy(plan,base/'direct-copies',base=base)
    assert len(result['entries'])==4 and reads==allowed


def test_modified_cached_copy_is_refused_without_archive_fallback(batch,monkeypatch):
    base,plan,index,_=batch;e=survey.slow.read(index)['entries']['S01'];wp=Path(e['path']);w=survey.slow.read(wp)
    source=wp.parent/w['files'][0]['local_copy'];cached=base/'cache-bad.json'
    survey.slow.save(cached,dict(survey_copy_cache_version='1.0',worksets=[str(wp)]))
    original=copying.digest
    monkeypatch.setattr(copying,'digest',lambda p:'0'*64 if p==source else original(p))
    result=copying.copy(plan,base/'refused-cache',cached,base)
    assert 'S01' not in result['entries'] and 'aucun remplacement' in result['errors']['S01']


def test_empty_cache_schema_is_refused_before_output(batch):
    base,plan,_,_=batch;path=base/'wrong-cache.json';survey.slow.save(path,{})
    with pytest.raises(ValueError):copying.copy(plan,base/'wrong-cache-out',path,base)
    assert not (base/'wrong-cache-out').exists()
