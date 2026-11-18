# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Two entirely fictional sessions for the four-window survey tutorial."""
import argparse
from datetime import datetime,timedelta
from pathlib import Path
import numpy as np
from astropy.io import fits
from gar.inventory import inventory
from gar.workset import digest,prepare_workset
import seestar_survey as survey
from make_asymmetric_slow_demo import background_sources,SCALE

ROOT=Path(__file__).resolve().parents[1]
SEEDS=(2026112701,2026112702)


def make(output,base=None):
    base=ROOT/'local' if base is None else base;output=survey.slow._new_output(output,base)
    source=output/'invented-source';source.mkdir();yy,xx=np.mgrid[:512,:512]
    for session,seed in enumerate(SEEDS,1):
        rng=np.random.default_rng(seed+1_000_000);stars=background_sources(seed)
        for k in range(16):
            time=300.*k;angle=np.deg2rad(.5)*k/15
            rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
            center=np.array([255.5,255.5]);translation=center-rotation@center+[3.5*k/15,0.]
            mobile=np.array([.35*512,.35*512])+30/(3600*SCALE)*time*np.array([np.cos(np.pi/6),np.sin(np.pi/6)])
            image=np.full((512,512),100.)
            for x,y,peak in [*stars,(*mobile,240.)]:
                point=rotation@np.array([x,y])+translation
                image+=peak*np.exp(-((xx-point[0])**2+(yy-point[1])**2)/(2*2.2**2))
            response=np.tile([[1.,.96],[1.04,1.]],(256,256))
            pixels=np.clip(image*response+rng.normal(0,2,image.shape),0,65535).astype('uint16')
            header=fits.Header(dict(OBJECT=f'Fictional survey {session}',INSTRUME='Fictional instrument',FILTER='SIMULATED',
                GAIN=80,EQMODE=0,BAYERPAT='GRBG',EXPTIME=10.,XPIXSZ=2.9,YPIXSZ=2.9,FOCALLEN=250.,GARSYNTH=True))
            header['DATE-OBS']=(datetime(2025,1,session)+timedelta(seconds=time)).isoformat()
            fits.writeto(source/f'session-{session}-pose-{k+1:02}.fit',pixels,header)
    files,incidents=inventory(source)
    mp=output/'inventory.json';survey.slow.save(mp,dict(schema_version='1.0',input_root=str(source),files=files,traversal_incidents=incidents))
    p=survey.plan(mp,output/'plan',base);pp=output/'plan/plan.json'
    index=dict(survey_worksets_version='1.0',plan_sha256=digest(pp),entries={})
    for row in p['rows']:
        if not row['selection_available']:continue
        wp=output/row['series_id']/'workset';wp.parent.mkdir()
        selection=dict(selection_schema_version='1.0',files=[dict(source=str(source/f['path']),expected_sha256=f['sha256']) for f in row['frames']])
        prepare_workset(selection,wp,base)
        index['entries'][row['series_id']]=dict(path=str(wp/'workset.json'),sha256=digest(wp/'workset.json'))
    survey.slow.save(output/'worksets.json',index)
    survey.slow.save(output/'fabrication.json',dict(synthetic=True,seeds=list(SEEDS),source_images=32,
        mobile_arcsec_per_hour=30.,native_peak=240.,time_step_seconds=300.,
        known_natural_positive=False,positions_provided_to_search=False))
    return index


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args()
    try:make(args.output);print('Deux séances et quatre séries entièrement fictives préparées.')
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
