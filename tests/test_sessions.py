# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: synthetic session grouping and reconciliation.
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
from gar.sessions import group_sessions, load_manifest, parse_declared_time


def manifest(tmp_path):
    return {'schema_version':'1.0', 'input_root':str(tmp_path/'never-opened-archive'),
            'files':[], 'traversal_incidents':[]}


def add_frame(document, name, date, **changes):
    digest = hashlib.sha256(name.encode()).hexdigest()
    meta = {'OBJECT':'Synthetic A', 'INSTRUME':'Simulated camera', 'FILTER':'SIMULATED',
            'BAYERPAT':'GRBG', 'EQMODE':False, 'TIMESYS':None,
            'DATE-OBS':date, 'EXPTIME':10.0}
    meta.update(changes)
    hdu = {'hdu_index':0, 'frame_id':f'{digest}:0', 'kind':'image_2d_candidate',
           'dimensions_fits_order':[64,48], 'metadata':meta}
    file = {'path':name, 'status':'ok', 'sha256':digest, 'hdus':[hdu]}
    document['files'].append(file)
    return file, hdu


def test_gap_boundary_and_stable_order(tmp_path):
    doc=manifest(tmp_path)
    add_frame(doc,'b.fit','2025-01-01T00:30:00')
    add_frame(doc,'a.fit','2025-01-01T00:00:00')
    add_frame(doc,'c.fit','2025-01-01T01:00:01')
    result=group_sessions(doc)
    assert [s['frame_count'] for s in result['sessions']]==[2,1]
    assert result['sessions'][0]['timestamp_span_seconds']==1800
    assert result['sessions'][0]['total_exposure_seconds_declared']==20
    assert 'missing_timesys' in result['sessions'][0]['flags']
    assert not result['sessions'][0]['time_validated']
    shuffled=deepcopy(doc);shuffled['files'].reverse()
    assert group_sessions(shuffled)==result
    assert len(group_sessions(doc,1801)['sessions'])==1


@pytest.mark.parametrize('key,value',[('OBJECT','Other'),('FILTER','Other'),('INSTRUME','Other'),
                                     ('BAYERPAT','RGGB'),('EQMODE',True),('TIMESYS','UTC'),
                                     ('GAIN',90),('SITELAT',1.2),('BZERO',32768)])
def test_configuration_changes_split(tmp_path,key,value):
    doc=manifest(tmp_path)
    add_frame(doc,'a.fit','2025-01-01T00:00:00')
    add_frame(doc,'b.fit','2025-01-01T00:00:10',**{key:value})
    assert len(group_sessions(doc)['sessions'])==2


def test_midnight_and_separate_directories(tmp_path):
    doc=manifest(tmp_path)
    add_frame(doc,'one/a.fit','2025-01-01T23:59:55')
    add_frame(doc,'one/b.fit','2025-01-02T00:00:05')
    add_frame(doc,'two/c.fit','2025-01-02T00:00:10')
    assert len(group_sessions(doc)['sessions'])==3


@pytest.mark.parametrize('value',[None,'','2025-01-01','2025-01-01T00:00:00Z',
                                  '2025-01-01T00:00:00+01:00','2025-02-30T00:00:00',
                                  '2016-12-31T23:59:60','2025-01-01T00:00:00.1234567'])
def test_invalid_or_unsupported_time_is_excluded(tmp_path,value):
    doc=manifest(tmp_path);add_frame(doc,'a.fit',value)
    result=group_sessions(doc)
    assert result['summary']['excluded_hdus']==1
    assert result['excluded'][0]['reason']=='missing_invalid_or_unsupported_date'
    with pytest.raises(ValueError):parse_declared_time(value)


def test_binary_duplicates_and_bad_files_are_reconciled(tmp_path):
    doc=manifest(tmp_path)
    file,hdu=add_frame(doc,'a.fit','2025-01-01T00:00:00')
    copy=deepcopy(file);copy['path']='copy.fit';doc['files'].append(copy)
    _,stacked=add_frame(doc,'stacked.fit','2025-01-01T00:00:10');stacked['kind']='stacked_candidate'
    bad,_=add_frame(doc,'bad.fit','2025-01-01T00:00:20');bad['status']='error'
    doc['files'].append({'path':'unreadable.fit','status':'error','hdus':[],'sha256':None})
    result=group_sessions(doc)
    assert result['summary']['grouped_hdus']==1
    assert result['summary']['excluded_hdus']==3
    assert result['summary']['input_hdus']==4
    assert result['summary']['file_incidents']==2
    assert result['sessions'][0]['total_exposure_seconds_declared']==10


def test_extensions_do_not_collapse(tmp_path):
    doc=manifest(tmp_path)
    file,hdu=add_frame(doc,'extensions.fit','2025-01-01T00:00:00')
    second=deepcopy(hdu);second['hdu_index']=1;second['frame_id']=f"{file['sha256']}:1"
    second['metadata']['DATE-OBS']='2025-01-01T00:00:10';file['hdus'].append(second)
    assert group_sessions(doc)['summary']['grouped_hdus']==2


@pytest.mark.parametrize('value',[None,0,-1,'10',True])
def test_missing_exposure_not_fabricated(tmp_path,value):
    doc=manifest(tmp_path)
    add_frame(doc,'a.fit','2025-01-01T00:00:00')
    add_frame(doc,'b.fit','2025-01-01T00:00:10',EXPTIME=value)
    session=group_sessions(doc)['sessions'][0]
    assert session['total_exposure_seconds_declared'] is None
    assert session['known_exposure_sum_seconds']==10
    assert session['unknown_exposure_count']==1


def test_duplicate_timestamps_are_flagged(tmp_path):
    doc=manifest(tmp_path)
    add_frame(doc,'a.fit','2025-01-01T00:00:00')
    add_frame(doc,'b.fit','2025-01-01T00:00:00')
    session=group_sessions(doc)['sessions'][0]
    assert session['duplicate_timestamp_count']==1
    assert session['frame_count']==2


@pytest.mark.parametrize('value',[0,-1,float('inf'),float('nan')])
def test_bad_threshold_rejected(tmp_path,value):
    with pytest.raises(ValueError):group_sessions(manifest(tmp_path),value)


@pytest.mark.parametrize('mutation',['schema','files','metadata','frame_id','index','dimensions','root'])
def test_bad_manifest_rejected_before_output(tmp_path,mutation):
    doc=manifest(tmp_path);_,hdu=add_frame(doc,'a.fit','2025-01-01T00:00:00')
    if mutation=='schema':doc['schema_version']='99'
    elif mutation=='files':doc['files']=[None]
    elif mutation=='metadata':hdu['metadata']=[]
    elif mutation=='frame_id':hdu['frame_id']='not-a-frame'
    elif mutation=='index':hdu['hdu_index']=-1
    elif mutation=='dimensions':hdu['dimensions_fits_order']=None
    elif mutation=='root':doc['input_root']='relative'
    source=tmp_path/'manifest.json';source.write_text(json.dumps(doc),encoding='utf-8')
    out=tmp_path/'output'
    assert main(['sessions',str(source),'--output',str(out)])==1
    assert not out.exists()


def test_nonstandard_json_rejected(tmp_path):
    path=tmp_path/'invalid.json';path.write_text('{"value": NaN}',encoding='utf-8')
    with pytest.raises(ValueError):load_manifest(path)


def test_cli_reads_only_manifest_and_preserves_it(tmp_path,monkeypatch):
    doc=manifest(tmp_path);add_frame(doc,'a.fit','2025-01-01T00:00:00')
    path=tmp_path/'manifest.json';path.write_text(json.dumps(doc),encoding='utf-8')
    before=path.read_bytes()
    original=Path.open
    def protected(self,*args,**kwargs):
        assert self.suffix.lower() not in {'.fit','.fits','.fts'},'FITS must not be opened'
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',protected)
    output=tmp_path/'rapport é'
    assert main(['sessions',str(path),'--output',str(output)])==0
    result=json.loads((output/'sessions.json').read_text(encoding='utf-8'))
    assert result['input_manifest_sha256']==hashlib.sha256(before).hexdigest()
    assert path.read_bytes()==before
    assert (output/'sessions.csv').exists() and (output/'sessions.svg').exists()
    assert main(['sessions',str(path),'--output',str(output)])==1
    assert main(['sessions',str(path),'--output',str(Path(doc['input_root'])/'bad')])==1


def test_sessions_empty_and_partial_exit_codes(tmp_path):
    doc=manifest(tmp_path)
    source=tmp_path/'manifest.json';source.write_text(json.dumps(doc),encoding='utf-8')
    assert main(['sessions',str(source),'--output',str(tmp_path/'empty')])==2
    add_frame(doc,'a.fit','2025-01-01T00:00:00')
    _,hdu=add_frame(doc,'b.fit',None)
    source.write_text(json.dumps(doc),encoding='utf-8')
    assert main(['sessions',str(source),'--output',str(tmp_path/'partial')])==2


def test_windows_session_launcher(tmp_path):
    if os.name!='nt':pytest.skip('Windows launcher')
    doc=manifest(tmp_path);add_frame(doc,'a.fit','2025-01-01T00:00:00')
    source=tmp_path/'manifeste é.json';source.write_text(json.dumps(doc),encoding='utf-8')
    project=Path(__file__).resolve().parents[1]
    call=(f'cmd /d /s /c ""{project / "scripts" / "gar-sessions.bat"}" '
          f'"{source}" --output "{tmp_path / "sortie é"}""')
    result=subprocess.run(call,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
