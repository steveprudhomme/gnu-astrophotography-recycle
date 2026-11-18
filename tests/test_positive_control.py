# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Development-only fictional control preparation and privacy boundaries."""
from copy import deepcopy
from itertools import combinations
from pathlib import Path
import csv
import socket,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'examples'))
import prepare_positive_control as control
import fetch_control_ephemeris as reference
import make_positive_control_demo as demo
import plot_positive_control as drawing


@pytest.fixture(scope='module')
def sample(tmp_path_factory):
    base=tmp_path_factory.mktemp('positive-control-development')
    with pytest.MonkeyPatch.context() as m:
        m.setattr(demo,'SEED',31415928);demo.make(base/'demo',base)
    plan=base/'demo/plan/plan.json';copies=base/'demo/copies/copies.json';ref=base/'demo/reference/reference.json'
    control.assess(plan,copies,base/'assessment',ref,base)
    return base,plan,copies,ref


def test_selection_respects_fixed_gaps_when_nearest_rounding_fails():
    times=np.array([0,300,600,900,1200,1230,1430,1570,1800,1870,2100,2170],dtype=float)
    chosen=control.choose(times)
    valid=[]
    for tail in combinations(range(1,len(times)),7):
        path=(0,*tail);t=times[list(path)]
        if 1800<=t[-1]<=2700 and np.all((240<=np.diff(t))&(np.diff(t)<=360)):
            valid.append((sum(abs(t-300*np.arange(8))),path))
    assert tuple(chosen)==min(valid)[1]
    assert chosen==control.choose(times)
    nearest=[min(range(len(times)),key=lambda i:(abs(times[i]-300*k),i)) for k in range(8)]
    assert np.any(np.diff(times[nearest])<240) or np.any(np.diff(times[nearest])>360)


@pytest.mark.parametrize('times',[[0]*8,list(range(8)),[0,300,600,900,1200,1500,1800]])
def test_short_or_duplicate_dates_have_no_admissible_sequence(times):
    assert control.choose(times) is None


@pytest.mark.parametrize('times',[[0,np.nan],[300,0],[[0,300]]])
def test_nonfinite_unsorted_or_multidimensional_dates_are_refused(times):
    with pytest.raises(ValueError):control.choose(times)


@pytest.mark.parametrize('path',['../secret','a\\..\\b','C:\\file.fit','/absolute.fit','a//b','a:b'])
def test_legacy_relative_paths_are_bound_lexically(path):
    with pytest.raises(ValueError):control.relative_path(path)


def test_old_windows_separators_are_accepted_without_probing_sources():
    assert control.relative_path('object\\sub\\pose.fit')=='object/sub/pose.fit'


def test_planning_never_opens_images(sample,monkeypatch):
    base,plan,_,_=sample;p=control.slow.read(plan);opened=Path.open
    def guarded(path,*a,**k):
        if path.suffix.lower() in ('.fit','.fits'):raise AssertionError('No source while planning')
        return opened(path,*a,**k)
    monkeypatch.setattr(Path,'open',guarded)
    result=control.plan(p['inventory_path'],p['summary_path'],base/'plan-again',base)
    assert not result['source_accessed'] and result['selected']['indices']==list(range(8))


def test_duplicate_legacy_paths_are_refused(sample):
    base,plan,_,_=sample;p=control.slow.read(plan);rows=control.slow.read(p['inventory_path']);rows.append(rows[0])
    with pytest.raises(ValueError,match='répété'):control.groups(rows)


def test_changed_plan_is_refused(sample):
    base,plan,_,_=sample;p=control.slow.read(plan);p['selected']['indices'][0]=99
    bad=plan.parent/'changed.json';control.slow.save(bad,p)
    with pytest.raises(ValueError):control.checked_plan(bad,base)


def test_outside_rate_and_unknown_reference_do_not_validate_a_control(sample):
    base,plan,copies,_=sample;r,_,_=control.checked_preparation(base/'assessment/preparation.json',base)
    assert r['decision']=='blocked_outside_rate' and r['rate_range_arcsec_hour']==[250.,250.]
    assert not r['positive_control_validated'] and not r['ready_for_blind_test']
    absent=control.assess(plan,copies,base/'missing-reference',base=base)
    assert absent['nominal_rate_compatible'] is None and absent['rate_range_arcsec_hour'] is None
    assert absent['decision']=='needs_reference'


def test_compatible_rate_still_requires_independent_evidence(sample):
    base,plan,copies,_=sample;demo.fixture(plan,base/'compatible-reference',55.,base)
    result=control.assess(plan,copies,base/'compatible-assessment',base/'compatible-reference/reference.json',base)
    assert result['nominal_rate_compatible'] is True and not result['positive_control_validated']
    assert result['decision']=='needs_qualification' and not result['clock_qualified']


def test_parameters_disclose_only_fixed_target_and_eight_dates(sample):
    _,plan,_,_=sample;p=control.slow.read(plan);params=reference.parameters(p)
    assert params['CENTER']=="'500@399'" and params['COMMAND']=="'DES=C/2023 A3;NOFRAG;CAP'"
    assert len(params['TLIST'].split())==8
    assert set(params)=={'format','COMMAND','MAKE_EPHEM','OBJ_DATA','EPHEM_TYPE','CENTER','TLIST','TLIST_TYPE',
        'TIME_TYPE','TIME_DIGITS','CSV_FORMAT','ANG_FORMAT','REF_SYSTEM','RANGE_UNITS','QUANTITIES'}
    assert not any(k in params for k in ('SITE_COORD','RA','DEC','SITELAT','SITELONG','START_TIME','STOP_TIME'))


@pytest.mark.parametrize('allow',[False,True])
def test_fetch_refuses_unapproved_or_synthetic_inputs_without_network(sample,monkeypatch,allow):
    base,plan,_,_=sample
    def forbidden(*a,**k):raise AssertionError('No network')
    monkeypatch.setattr(reference,'build_opener',forbidden)
    with pytest.raises(ValueError):reference.fetch(plan,base/f'refused-network-{allow}',allow,base)
    assert not (base/f'refused-network-{allow}').exists()


@pytest.mark.parametrize('change',['error','target','center','dates','nan','units','source','missing-row'])
def test_reference_errors_and_incompatible_formats_are_refused(sample,change):
    _,plan,_,_=sample;p=control.slow.read(plan);payload=demo.payload(p)
    if change=='error':payload['error']='unavailable'
    elif change=='target':payload['result']=payload['result'].replace('C/2023 A3','C/2021 S3')
    elif change=='center':payload['result']=payload['result'].replace('GEOCENTRIC','TOPOCENTRIC')
    elif change=='dates':payload['result']=payload['result'].replace(f'{reference.dates(p)[0]:.12f}','1.0')
    elif change=='nan':payload['result']=payload['result'].replace(',250.0,',',nan,')
    elif change=='units':payload['result']=payload['result'].replace('dRA*cosD','RA_degrees_second')
    elif change=='source':payload['signature']['source']='UNKNOWN'
    else:payload['result']='\n'.join(s for s in payload['result'].splitlines() if not s.startswith('Invented-7'))
    with pytest.raises(ValueError):reference.parse(payload,p,True)


def test_modified_normalized_reference_is_refused(sample):
    base,plan,_,ref=sample;r=control.slow.read(ref);r['rows'][0]['east_rate_arcsec_hour']=55.
    bad=ref.parent/'changed.json';control.slow.save(bad,r)
    with pytest.raises(ValueError):reference.checked_reference(bad,plan,control.slow.read(plan),base)


def test_altered_decision_is_refused(sample):
    base,_,_,_=sample;r=control.slow.read(base/'assessment/preparation.json');r['positive_control_validated']=True
    bad=base/'assessment/changed.json';control.slow.save(bad,r)
    with pytest.raises(ValueError):control.checked_preparation(bad,base)


def test_assessment_and_drawing_do_not_search_or_access_network(sample,monkeypatch):
    base,plan,copies,ref=sample
    def forbidden(*a,**k):raise AssertionError('No search or network')
    monkeypatch.setattr(control.slow,'detect',forbidden);monkeypatch.setattr(control.slow,'prepare',forbidden)
    monkeypatch.setattr(control.historical.paired,'process',forbidden);monkeypatch.setattr(control.slow,'find_tracks',forbidden)
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    result=control.assess(plan,copies,base/'offline-assessment',ref,base)
    figures=drawing.plot(base/'offline-assessment/preparation.json',base/'offline-figures',base)
    assert not result['detector_called'] and not figures['network_used'] and len(figures['figures_sha256'])==3


def test_existing_outputs_are_preserved(sample):
    base,plan,copies,ref=sample
    with pytest.raises(FileExistsError):control.assess(plan,copies,base/'assessment',ref,base)


def test_valid_copies_preserve_a_legacy_configuration_refusal(sample,monkeypatch):
    base,plan,copies,ref=sample
    def refused(*a,**k):raise ValueError('Configuration différente, refus conservé.')
    monkeypatch.setattr(control.slow,'_read_workset',refused)
    result=control.assess(plan,copies,base/'refused-contract',ref,base)
    assert result['copies_verified'] is True and result['profile_copy_contract_compatible'] is False
    assert result['decision']=='blocked_copy_metadata' and not result['positive_control_validated']


def test_modified_copy_is_not_confused_with_configuration_refusal(sample):
    base,plan,copies,_=sample;r=control.slow.read(copies);wp=Path(r['workset_path']);w=control.slow.read(wp)
    cp=wp.parent/w['files'][0]['local_copy'];before=cp.read_bytes()
    try:
        cp.write_bytes(before[:-1]+bytes([before[-1]^1]))
        with pytest.raises(ValueError,match='modifiée'):control.check_copies(wp,control.slow.read(plan),base)
    finally:cp.write_bytes(before)


def test_reuse_verified_local_workset_does_not_reopen_sources(sample,monkeypatch):
    base,plan,copies,_=sample;r=control.slow.read(copies);opened=Path.open
    def guarded(path,*a,**k):
        if 'invented-source' in path.parts:raise AssertionError('No source during reuse')
        return opened(path,*a,**k)
    monkeypatch.setattr(Path,'open',guarded)
    receipt=control.copy(plan,base/'reused',base,Path(r['workset_path']))
    assert receipt['status']=='complete' and receipt['existing_local_workset_reused'] is True


def test_default_calendar_ut_response_is_supported_without_new_request(sample):
    _,plan,_,_=sample;p=control.slow.read(plan);payload=demo.payload(p)
    lines=payload['result'].splitlines();lines[2]='Date__(UT)__HR:MN:SC.fff,,,R.A._(ICRF),DEC_(ICRF),dRA*cosD,d(DEC)/dt,delta,deldot,'
    for k,frame in enumerate(p['selected']['frames']):
        from astropy.time import Time
        date=Time(frame['DATE-OBS'],format='isot',scale='utc').strftime('%Y-%b-%d %H:%M:%S.000')
        cells=next(csv.reader([lines[4+k]]));lines[4+k]=','.join([date,*cells[2:]])
    payload['result']='\n'.join(lines)
    assert reference.parse(payload,p,True)==reference.parse(demo.payload(p),p,True)


def test_fictitious_reference_positions_follow_the_announced_motion(sample):
    from astropy.coordinates import SkyCoord
    from astropy import units as u
    _,plan,_,_=sample;p=control.slow.read(plan);rows=reference.parse(demo.payload(p),p,True)
    first,last=rows[0],rows[-1]
    coords=SkyCoord(ra=[first['ra_astrometric_icrf_degrees'],last['ra_astrometric_icrf_degrees']]*u.deg,
                   dec=[first['dec_astrometric_icrf_degrees'],last['dec_astrometric_icrf_degrees']]*u.deg)
    east,north=coords[0].spherical_offsets_to(coords[1])
    hours=(last['jd_utc_assumed']-first['jd_utc_assumed'])*24
    assert east.arcsec/hours==pytest.approx(250.,abs=.01)
    assert abs(north.arcsec/hours)<.1
