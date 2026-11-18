# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Invented eight-frame comet and a local 250 arcsec/hour reference, offline."""
import argparse
from datetime import datetime,timedelta
from pathlib import Path
import numpy as np
from astropy.io import fits
from gar.workset import digest
import prepare_positive_control as control
import fetch_control_ephemeris as reference

ROOT=Path(__file__).resolve().parents[1]
SEED=2026112801


def payload(plan,rate=250.):
    header='Date__(UT),Date_________JDUT,,,R.A._(ICRF),DEC_(ICRF),dRA*cosD,d(DEC)/dt,delta,deldot,'
    times=reference.dates(plan);lines=[]
    for k,jd in enumerate(times):
        east_arcsec=rate*(jd-times[0])*24.
        ra=10.+east_arcsec/(3600*np.cos(np.deg2rad(20.)))
        lines.append(f'Invented-{k},{jd:.12f},,,{ra:.12f},20.0,{rate},0.0,1.0,0.0,')
    return dict(signature=dict(source='LOCAL SYNTHETIC',version='1.0'),
        result='Target body name: FICTITIOUS (C/2023 A3)\nCenter-site name: GEOCENTRIC\n'+header+'\n$$SOE\n'+'\n'.join(lines)+'\n$$EOE\n')


def fixture(plan_path,output,rate=250.,base=None):
    base=ROOT/'local' if base is None else base;pp,p,watched=control.checked_plan(plan_path,base)
    if not p['synthetic']:raise ValueError('Une référence inventée exige un plan entièrement fictif.')
    output=control.slow._new_output(output,base);raw=output/'response.json';data=payload(p,rate);control.slow.save(raw,data)
    result=dict(control_reference_version='1.0',status='complete',plan_path=str(pp),plan_sha256=watched[pp],
        parameters=reference.parameters(p),endpoint=reference.ENDPOINT,synthetic=True,geocentric=True,
        frozen_sha256_lf=control.frozen(),response_file='response.json',response_sha256=digest(raw),
        rows=reference.parse(data,p,True),input_dates_assumed_utc=True,inputs_unchanged=True)
    control.slow.save(output/'reference.json',result)
    return result


def make(output,base=None):
    base=ROOT/'local' if base is None else base;output=control.slow._new_output(output,base)
    source=output/'invented-source';source.mkdir();rng=np.random.default_rng(SEED);yy,xx=np.mgrid[:512,:512]
    stars=rng.uniform(35,477,(30,2));scale=206264.806247*.0029/250.;rows=[]
    for k in range(8):
        seconds=300*k;image=100+rng.normal(0,2,(512,512))
        for x,y in stars:image+=600*np.exp(-((xx-x)**2+(yy-y)**2)/(2*2.2**2))
        point=np.array([180.,240.])+np.array([250./(3600*scale)*seconds,0.])
        image+=500*np.exp(-((xx-point[0])**2+(yy-point[1])**2)/(2*4.9**2))
        h=fits.Header(dict(OBJECT='C-2023 A3',INSTRUME='Fictional instrument',FILTER='SIMULATED',BAYERPAT='GRBG',
            EXPTIME=10.,XPIXSZ=2.9,YPIXSZ=2.9,FOCALLEN=250.,GAIN=80,EQMODE=0,GARSYNTH=True))
        h['DATE-OBS']=(datetime(2025,1,1)+timedelta(seconds=seconds)).isoformat()
        path=source/f'pose-{k+1:02}.fit';fits.writeto(path,np.clip(image,0,65535).astype('uint16'),h)
        with fits.open(path,mode='readonly',memmap=False) as hdus:header=hdus[0].header
        row={key:header.get(key) for key in (*control.CONFIG,'OBJECT','DATE-OBS','NAXIS','STACKCNT')}
        rows.append(dict(row,path=path.name,group='FICTITIOUS',hdu=0,status='header_read',kind='individual_candidate',size_bytes=path.stat().st_size))
    control.slow.save(output/'inventory.json',rows)
    control.slow.save(output/'summary.json',dict(schema_version='exploratory-1',input_root=str(source),synthetic=True))
    control.plan(output/'inventory.json',output/'summary.json',output/'plan',base)
    control.copy(output/'plan/plan.json',output/'copies',base)
    fixture(output/'plan/plan.json',output/'reference',base=base)
    control.slow.save(output/'fabrication.json',dict(synthetic=True,seed=SEED,reference_rate_arcsec_hour=250.,
        image_point_rate_arcsec_hour=250.,new_source_images=8,new_copies=8,network_used=False,positive_control_natural=False))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args()
    try:make(args.output);print('Exercice entièrement fictif préparé sans réseau.')
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
