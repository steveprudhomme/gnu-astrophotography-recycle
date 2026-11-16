# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: evidence boundaries and timestamp diagnostics.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from gar.cli import main
from gar.sessions import group_sessions
from gar.timing import audit_timing, date_status


def make_document(tmp_path):
    return {'schema_version':'1.0','input_root':str(tmp_path/'archive-not-opened'),
            'files':[],'traversal_incidents':[]}


def add(document, name, time, comment='Image created time', **changes):
    digest=hashlib.sha256(name.encode()).hexdigest()
    meta={'OBJECT':'Synthetic A','INSTRUME':'Simulated camera','FILTER':'SIMULATED',
          'BAYERPAT':'GRBG','EQMODE':False,'TIMESYS':None,'DATE-OBS':time,
          'EXPTIME':10.0,'EXPOSURE':10.0}
    meta.update(changes)
    hdu={'hdu_index':0,'frame_id':f'{digest}:0','kind':'image_2d_candidate',
         'dimensions_fits_order':[64,48],'metadata':meta,
         'raw_cards':[{'keyword':'DATE-OBS','value':time,'comment':comment}]}
    file={'path':name,'sha256':digest,'status':'ok','hdus':[hdu]}
    document['files'].append(file)
    return file,hdu


def audit(doc,gap=1800):
    return audit_timing(doc,group_sessions(doc,gap),gap)


def test_written_resolution_is_not_clock_accuracy(tmp_path):
    doc=make_document(tmp_path)
    add(doc,'a.fit','2025-01-01T00:00:00.123456')
    result=audit(doc);row=result['records'][0]
    assert row['decimal_places_written']==6
    assert row['written_quantum_seconds']==1e-6
    assert row['clock_accuracy_seconds'] is None
    assert row['fits_scale_default_hint']=='UTC'
    assert row['timesys_declared'] is None
    assert row['comment_hint']=='creation_wording_not_exposure_reference'
    assert row['mid_exposure_utc'] is None and not row['time_validated']
    assert not result['summary']['scientific_time_export_allowed']


@pytest.mark.parametrize('scale,classification',[('UTC','recognized_declaration'),('TAI','recognized_declaration'),
                                                ('TT','recognized_declaration'),('GPS','recognized_declaration'),
                                                ('LOCAL','outside_supported_scale_set'),('UTC(NIST)','outside_supported_scale_set'),
                                                ('bad','outside_supported_scale_set'),(None,'missing')])
def test_declared_scale_never_qualifies_clock(tmp_path,scale,classification):
    doc=make_document(tmp_path);add(doc,'a.fit','2025-01-01T00:00:00',TIMESYS=scale)
    row=audit(doc)['records'][0]
    assert row['scale_status']==classification and row['timesys_declared']==scale
    assert row['clock_accuracy_seconds'] is None and not row['time_validated']


@pytest.mark.parametrize('value,status',[(None,'missing'),('2025-01-01','date_only_not_supported'),
                                        ('2025-01-01T00:00:00Z','timezone_suffix_not_supported'),
                                        ('2025-01-01T00:00:00+01:00','timezone_suffix_not_supported'),
                                        ('2016-12-31T23:59:60','leap_second_not_supported'),
                                        ('2025-01-01T00:00:00.1234567','precision_not_supported'),
                                        ('2025-02-30T00:00:00','invalid_or_unsupported_date'),
                                        (5,'invalid_type')])
def test_unsupported_time_preserved_and_excluded(tmp_path,value,status):
    doc=make_document(tmp_path);add(doc,'a.fit',value)
    result=audit(doc);row=result['records'][0]
    assert row['date_parse_status']==status and row['date_obs_raw']==value
    assert not row['eligible_for_cadence'] and not result['sequences']


@pytest.mark.parametrize('comment,hint',[('Start of exposure','start_wording_unverified'),
                                       ('End of exposure','end_wording_unverified'),
                                       ('Mid-exposure time','midpoint_wording_unverified'),
                                       ('start or end','conflicting_wording'),('', 'unspecified'),
                                       ('Time spent rendering','unspecified')])
def test_comment_is_declaration_not_proof(tmp_path,comment,hint):
    doc=make_document(tmp_path);add(doc,'a.fit','2025-01-01T00:00:00',comment)
    row=audit(doc)['records'][0]
    assert row['comment_hint']==hint and not row['exposure_reference_verified']


def test_cadence_across_gap_and_duplicate_timestamp(tmp_path):
    doc=make_document(tmp_path)
    for name,time in [('a','00:00:00'),('b','00:00:05'),('c','00:00:05'),('d','01:00:00')]:
        add(doc,name+'.fit','2025-01-01T'+time)
    result=audit(doc)
    assert len(result['sequences'])==1
    assert result['summary']['gap_count']==1
    assert result['summary']['short_interval_count']==1
    assert result['summary']['duplicate_timestamp_count']==1
    assert result['sequences'][0]['median_positive_delta_seconds']==1800
    assert result['sequences'][0]['interval_count']==3


def test_threshold_equality_is_not_interruption(tmp_path):
    doc=make_document(tmp_path)
    add(doc,'a.fit','2025-01-01T00:00:00');add(doc,'b.fit','2025-01-01T00:30:00')
    assert audit(doc)['summary']['gap_count']==0
    assert audit(doc,1799)['summary']['gap_count']==1


def test_durations_and_duplicate_file_excluded_from_metrics(tmp_path):
    doc=make_document(tmp_path)
    file,hdu=add(doc,'a.fit','2025-01-01T00:00:00',EXPOSURE=20)
    copy=deepcopy(file);copy['path']='z-copy.fit';doc['files'].append(copy)
    add(doc,'b.fit','2025-01-01T00:00:05',EXPTIME=None,EXPOSURE=10)
    result=audit(doc)
    assert result['summary']['cadence_hdus']==2 and result['summary']['excluded_hdus']==1
    assert result['summary']['duration_conflicts']==1
    assert 'missing_or_invalid_exptime' in result['records'][2]['flags']


def test_no_comparison_across_configuration_or_date(tmp_path):
    doc=make_document(tmp_path)
    add(doc,'a.fit','2025-01-01T23:59:59')
    add(doc,'b.fit','2025-01-02T00:00:00')
    add(doc,'c.fit','2025-01-02T00:00:01',FILTER='OTHER')
    result=audit(doc)
    assert len(result['sequences'])==3
    assert all(s['interval_count']==0 and s['median_positive_delta_seconds'] is None for s in result['sequences'])


def test_empty_and_malformed_cards(tmp_path):
    doc=make_document(tmp_path)
    assert audit(doc)['summary']['candidate_hdus']==0
    _,hdu=add(doc,'a.fit','2025-01-01T00:00:00');hdu['raw_cards']=None
    with pytest.raises(ValueError):group_sessions(doc)


def test_multiple_date_cards_and_pre_1972_hint(tmp_path):
    doc=make_document(tmp_path);_,hdu=add(doc,'a.fit','1971-01-01T00:00:00')
    hdu['raw_cards'].append({'keyword':'DATE-OBS','value':'1971-01-01T00:00:10','comment':'end'})
    row=audit(doc)['records'][0]
    assert 'multiple_date_obs_cards' in row['flags']
    assert row['fits_scale_default_hint']=='UT_legacy_date_rule'


def test_timing_cli_manifest_only_and_no_overwrite(tmp_path,monkeypatch):
    doc=make_document(tmp_path);add(doc,'=pose.fit','2025-01-01T00:00:00')
    path=tmp_path/'manifest.json';path.write_text(json.dumps(doc),encoding='utf-8')
    before=path.read_bytes();original=Path.open
    def guard(self,*args,**kwargs):
        assert self.suffix.lower() not in {'.fit','.fits','.fts'},'FITS access forbidden'
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',guard)
    output=tmp_path/'timing é'
    assert main(['timing',str(path),'--output',str(output)])==2
    result=json.loads((output/'timing.json').read_text(encoding='utf-8'))
    assert result['input_manifest_sha256']==hashlib.sha256(before).hexdigest()
    assert before==path.read_bytes()
    assert (output/'timing.csv').exists() and (output/'timing.svg').exists()
    assert main(['timing',str(path),'--output',str(output)])==1
    assert main(['timing',str(path),'--gap-seconds','0','--output',str(tmp_path/'bad')])==1
    assert not (tmp_path/'bad').exists()


def test_timing_windows_launcher(tmp_path):
    if os.name!='nt':pytest.skip('Windows launcher')
    doc=make_document(tmp_path);add(doc,'a.fit','2025-01-01T00:00:00')
    path=tmp_path/'manifest é.json';path.write_text(json.dumps(doc),encoding='utf-8')
    project=Path(__file__).resolve().parents[1]
    command=(f'cmd /d /s /c ""{project / "scripts" / "gar-timing.bat"}" '
             f'"{path}" --output "{tmp_path / "timing é"}""')
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==2,result.stderr


@pytest.mark.parametrize('fault',['repeated_path','non_string_status'])
def test_ambiguous_manifest_file_records_rejected(tmp_path,fault):
    doc=make_document(tmp_path);file,_=add(doc,'a.fit','2025-01-01T00:00:00')
    if fault=='repeated_path':
        doc['files'].append(deepcopy(file))
    else:
        file['status']=[]
    with pytest.raises(ValueError):group_sessions(doc)
