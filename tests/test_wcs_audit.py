# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: partial WCS declarations and evidence limits.
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
from gar.wcs_audit import audit_wcs


def document(tmp_path):
    return {'schema_version':'1.0','input_root':str(tmp_path/'archive-not-opened'),
            'files':[],'traversal_incidents':[]}


def add(doc,name='a.fit',**changes):
    digest=hashlib.sha256(name.encode()).hexdigest()
    meta={'CTYPE1':'RA---TAN','CTYPE2':'DEC--TAN','CRPIX1':32.0,'CRPIX2':24.0,
          'CRVAL1':120.0,'CRVAL2':30.0,'CD1_1':-0.001,'CD1_2':0.0,
          'CD2_1':0.0,'CD2_2':0.001}
    meta.update(changes)
    hdu={'hdu_index':0,'frame_id':f'{digest}:0','kind':'image_2d_candidate',
         'metadata':meta,'dimensions_fits_order':[64,48]}
    file={'path':name,'sha256':digest,'status':'ok','hdus':[hdu]}
    doc['files'].append(file)
    return file,hdu


def row(doc):
    return audit_wcs(doc)['records'][0]


def test_consistent_block_is_not_validated_sky_wcs(tmp_path):
    doc=document(tmp_path);add(doc)
    result=audit_wcs(doc);r=result['records'][0]
    assert r['status']=='linear_block_consistent_context_incomplete'
    assert r['matrix_condition_number_raw_units']==pytest.approx(1)
    assert r['matrix_nonsingular'] and not r['celestial_transform_reconstructed']
    assert not r['wcs_validated'] and r['astrometric_accuracy_arcsec'] is None
    assert not result['summary']['scientific_position_export_allowed']
    assert 'units_not_observed_no_angular_scale_computed' in r['flags']


def test_pointing_alone_not_wcs(tmp_path):
    doc=document(tmp_path);add(doc,CTYPE1=None,CTYPE2=None,RA=120.0,DEC=30.0)
    r=row(doc)
    assert r['pointing_values_present'] and r['status']=='primary_axes_not_observed'
    assert not r['wcs_validated']


@pytest.mark.parametrize('key',['CTYPE1','CTYPE2'])
def test_single_axis_is_incomplete(tmp_path,key):
    doc=document(tmp_path);add(doc,**{key:None})
    assert row(doc)['status']=='axes_incomplete'


@pytest.mark.parametrize('first,second,status',[
    ('FREQ','DEC--TAN','axis_pair_not_supported'),
    ('RA---TAN','RA---TAN','axis_pair_not_supported'),
    ('RA---TAN','DEC--SIN','axes_inconsistent'),
    ('RA---TAN-SIP','DEC--TAN','axes_inconsistent'),
    ('RA---ZZZ','DEC--ZZZ','projection_outside_audit_set'),
    (12,'DEC--TAN','axis_pair_not_supported')])
def test_axis_declarations(tmp_path,first,second,status):
    doc=document(tmp_path);add(doc,CTYPE1=first,CTYPE2=second)
    assert row(doc)['status']==status


def test_reversed_celestial_axes_allowed(tmp_path):
    doc=document(tmp_path);add(doc,CTYPE1='DEC--TAN',CTYPE2='RA---TAN',CRVAL1=30,CRVAL2=120)
    assert row(doc)['status']=='linear_block_consistent_context_incomplete'


@pytest.mark.parametrize('field',['CRPIX1','CRVAL2','CD1_1','CD1_2'])
def test_missing_parameters_not_silently_defaulted(tmp_path,field):
    doc=document(tmp_path);add(doc,**{field:None})
    r=row(doc);assert r['status']=='parameters_incomplete'
    assert field in r['missing_parameters']


@pytest.mark.parametrize('value',['bad',True])
def test_bad_numeric_value(tmp_path,value):
    doc=document(tmp_path);add(doc,CD1_1=value)
    assert row(doc)['status']=='parameters_invalid'


def test_pc_cdelt_parameterization_not_called_invalid(tmp_path):
    doc=document(tmp_path);add(doc,CD1_1=None,CD1_2=None,CD2_1=None,CD2_2=None,
                               CDELT1=-0.001,CDELT2=0.001,PC1_1=1,PC2_2=1)
    r=row(doc)
    assert r['status']=='parameters_incomplete'
    assert 'other_linear_parameterization_not_evaluated' in r['flags']


@pytest.mark.parametrize('values',[(0,0,0,0),(1,2,2,4)])
def test_singular_matrix(tmp_path,values):
    doc=document(tmp_path);add(doc,**dict(zip(['CD1_1','CD1_2','CD2_1','CD2_2'],values)))
    r=row(doc)
    assert r['status']=='linear_matrix_singular' and r['matrix_nonsingular'] is False


def test_condition_threshold_is_only_numeric(tmp_path):
    doc=document(tmp_path);add(doc,CD1_1=1,CD2_2=1e-9)
    assert row(doc)['status']=='linear_matrix_ill_conditioned'
    result=audit_wcs(doc,1e10)
    assert result['records'][0]['status']=='linear_block_consistent_context_incomplete'
    assert result['summary']['wcs_scientifically_validated']==0


def test_numerical_underflow_not_misreported_exact_singularity(tmp_path):
    doc=document(tmp_path);add(doc,CD1_1=1e308,CD2_2=1e-308)
    r=row(doc)
    assert r['status']=='linear_matrix_ill_conditioned' and r['matrix_nonsingular'] is None


def test_sip_is_not_silently_dropped(tmp_path):
    doc=document(tmp_path);add(doc,CTYPE1='RA---TAN-SIP',CTYPE2='DEC--TAN-SIP')
    r=row(doc)
    assert 'sip_distortion_context_not_captured' in r['flags']
    assert not r['celestial_transform_reconstructed']


def test_outside_reference_pixel_is_not_an_error(tmp_path):
    doc=document(tmp_path);add(doc,CRPIX1=-100)
    r=row(doc)
    assert r['reference_pixel_outside_pixel_center_range']
    assert r['status']=='linear_block_consistent_context_incomplete'


@pytest.mark.parametrize('unit,value,status',[('deg',91,'parameters_invalid'),('rad',2,'parameters_invalid'),
                                             ('deg',90,'linear_block_consistent_context_incomplete'),
                                             (None,91,'linear_block_consistent_context_incomplete')])
def test_declination_range_only_if_units_observed(tmp_path,unit,value,status):
    doc=document(tmp_path);add(doc,CUNIT2=unit,CRVAL2=value)
    assert row(doc)['status']==status


def test_primary_extensions_duplicates_errors_and_rgb(tmp_path):
    doc=document(tmp_path);file,hdu=add(doc)
    primary=deepcopy(hdu);primary['kind']='empty_primary';primary['dimensions_fits_order']=[]
    hdu['hdu_index']=1;hdu['frame_id']=file['sha256']+':1';file['hdus'].insert(0,primary)
    copy=deepcopy(file);copy['path']='copy.fit';doc['files'].append(copy)
    rgb,rgb_hdu=add(doc,'rgb.fit');rgb_hdu['kind']='stacked_candidate';rgb_hdu['dimensions_fits_order']=[64,48,3]
    bad,_=add(doc,'z-bad.fit');bad['status']='error'
    result=audit_wcs(doc)
    assert result['summary']['input_hdus']==6
    assert result['summary']['status_counts']['duplicate_frame']==2
    assert result['summary']['status_counts']['unusable_file']==1
    assert any(r['kind']=='stacked_candidate' and not r['wcs_validated'] for r in result['records'])


@pytest.mark.parametrize('value',[0,0.5,float('inf'),float('nan')])
def test_bad_threshold(tmp_path,value):
    with pytest.raises(ValueError):audit_wcs(document(tmp_path),value)


def test_cli_manifest_only_and_integrity(tmp_path,monkeypatch):
    doc=document(tmp_path);add(doc)
    path=tmp_path/'manifest.json';path.write_text(json.dumps(doc),encoding='utf-8')
    before=path.read_bytes();original=Path.open
    def guard(self,*args,**kwargs):
        assert self.suffix.lower() not in {'.fit','.fits','.fts'},'FITS must not be reopened'
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',guard)
    out=tmp_path/'wcs é'
    assert main(['wcs',str(path),'--output',str(out)])==2
    result=json.loads((out/'wcs.json').read_text(encoding='utf-8'))
    assert result['input_manifest_sha256']==hashlib.sha256(before).hexdigest()
    assert path.read_bytes()==before
    assert (out/'wcs.csv').exists() and (out/'wcs.svg').exists()
    assert main(['wcs',str(path),'--output',str(out)])==1
    assert main(['wcs',str(path),'--output',str(tmp_path/'bad'),'--max-condition','0'])==1
    assert not (tmp_path/'bad').exists()


def test_empty_manifest(tmp_path):
    result=audit_wcs(document(tmp_path))
    assert result['summary']['input_hdus']==0 and result['records']==[]


def test_windows_launcher(tmp_path):
    if os.name!='nt':pytest.skip('Windows launcher')
    doc=document(tmp_path);add(doc)
    path=tmp_path/'manifest é.json';path.write_text(json.dumps(doc),encoding='utf-8')
    project=Path(__file__).resolve().parents[1]
    call=(f'cmd /d /s /c ""{project / "scripts" / "gar-wcs.bat"}" '
          f'"{path}" --output "{tmp_path / "wcs é"}""')
    result=subprocess.run(call,capture_output=True,text=True)
    assert result.returncode==2,result.stderr
