# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
import hashlib
import json
import os
import subprocess
from pathlib import Path

from astropy.io import fits
import numpy as np
import pytest

from gar.workset import prepare_workset,validate_selection


def sample_case(tmp_path):
    source=tmp_path/'source.fit'
    hdu=fits.PrimaryHDU(np.zeros((8,8),dtype=np.uint16))
    hdu.header['HISTORY']='Synthetic calibration history'
    for k,v in {'CTYPE1':'RA---TAN-SIP','CTYPE2':'DEC--TAN-SIP','CRPIX1':4.,'CRPIX2':4.,
                'CRVAL1':120.,'CRVAL2':30.,'CD1_1':-.001,'CD1_2':0.,'CD2_1':0.,'CD2_2':.001,
                'CUNIT1':'deg','CUNIT2':'deg','A_ORDER':2,'B_ORDER':2,'A_2_0':1e-5,'B_0_2':1e-5}.items():hdu.header[k]=v
    hdu.writeto(source)
    selection={'selection_schema_version':'1.0','files':[{'source':str(source),'expected_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]}
    return source,selection,tmp_path/'local'


def test_verified_copy_and_full_cards(tmp_path,monkeypatch):
    source,selection,base=sample_case(tmp_path);before=source.read_bytes();original=Path.open
    def guard(self,*args,**kwargs):
        if self==source:assert (args[0] if args else kwargs.get('mode'))=='rb','Original must only be opened for reading'
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',guard)
    r=prepare_workset(selection,base/'out',base)
    assert r['success'] and source.read_bytes()==before
    f=r['files'][0]
    assert f['sha256_before']==f['sha256_copy']==f['sha256_after']
    cards={c['keyword'] for c in f['hdus'][0]['cards']}
    assert {'HISTORY','CUNIT1','A_2_0'}<=cards
    model=f['hdus'][0]['wcs_model']
    assert model['celestial_model_constructed'] and model['sip_in_model']
    assert not model['scientifically_validated'] and not model['sky_coordinates_computed']
    assert (base/'out'/f['hdus'][0]['header_text']).exists()


@pytest.mark.parametrize('fault',['outside','existing','duplicate','bad_hash','relative'])
def test_refused_selections_and_outputs(tmp_path,fault):
    source,s,base=sample_case(tmp_path);out=base/'out'
    if fault=='outside':out=tmp_path/'elsewhere'
    elif fault=='existing':out.mkdir(parents=True)
    elif fault=='duplicate':s['files']*=2
    elif fault=='bad_hash':s['files'][0]['expected_sha256']='bad'
    elif fault=='relative':s['files'][0]['source']='source.fit'
    with pytest.raises(ValueError):validate_selection(s,out,base)


def test_historical_mismatch_does_not_copy(tmp_path):
    source,s,base=sample_case(tmp_path);before=source.read_bytes()
    s['files'][0]['expected_sha256']='0'*64
    with pytest.raises(ValueError):prepare_workset(s,base/'out',base)
    assert not list((base/'out'/'copies').iterdir())
    assert source.read_bytes()==before
    assert not json.loads((base/'out'/'workset.json').read_text(encoding='utf-8'))['success']


def test_copy_discrepancy_detected(tmp_path,monkeypatch):
    import gar.workset as module
    source,s,base=sample_case(tmp_path);original=module.digest
    def changed(path):
        return '1'*64 if path.parent.name=='copies' else original(path)
    monkeypatch.setattr(module,'digest',changed)
    with pytest.raises(ValueError):prepare_workset(s,base/'out',base)
    assert source.exists()


def test_extensions_kept(tmp_path):
    source,s,base=sample_case(tmp_path)
    fits.HDUList([fits.PrimaryHDU(),fits.ImageHDU(np.zeros((2,2)))]).writeto(source,overwrite=True)
    s['files'][0].pop('expected_sha256')
    r=prepare_workset(s,base/'out',base)
    assert len(r['files'][0]['hdus'])==2


def test_parent_junction_refused(tmp_path):
    source,s,base=sample_case(tmp_path)
    link=tmp_path/'linked'
    if os.name=='nt':
        result=subprocess.run(['cmd','/c','mklink','/J',str(link),str(tmp_path)],capture_output=True)
        assert result.returncode==0
    else:link.symlink_to(tmp_path,target_is_directory=True)
    s['files'][0]['source']=str(link/source.name)
    with pytest.raises(ValueError):validate_selection(s,base/'out',base)


def test_changed_source_hash_refused(tmp_path,monkeypatch):
    import gar.workset as module
    source,s,base=sample_case(tmp_path);original=module.digest;calls=0
    def changed(path):
        nonlocal calls
        if path==source:
            calls+=1
            if calls>1:return '2'*64
        return original(path)
    monkeypatch.setattr(module,'digest',changed)
    with pytest.raises(ValueError):prepare_workset(s,base/'out',base)
