# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Fictional stars and reference catalog, with a known 0.5 arcsec WCS offset."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
from gar.workset import prepare_workset


if __name__=='__main__':
    root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=False)
    w=WCS(naxis=2);w.wcs.crpix=[256,256];w.wcs.crval=[120,30]
    w.wcs.cd=np.array([[-2/3600,0],[0,2/3600]]);w.wcs.ctype=['RA---TAN','DEC--TAN']
    x,y=np.meshgrid(np.arange(50,451,80),np.arange(50,451,80));x=x.ravel();y=y.ravel()
    sky=w.pixel_to_world(x,y);yy,xx=np.indices((512,512));image=np.random.default_rng(7).normal(100,2,(512,512))
    for a,b in zip(x,y):image+=1000*np.exp(-((xx-a)**2+(yy-b)**2)/(2*(3/2.355)**2))
    w.wcs.crval[0]+=.5/(3600*np.cos(np.deg2rad(30)))
    header=w.to_header();header['DATE-OBS']='2025-01-01T00:00:00'
    fits.PrimaryHDU(image.astype('float32'),header=header).writeto(root/'synthetic.fit')
    n=len(x);catalog=Table({'source_id':np.arange(n),'ra':sky.ra.deg,'dec':sky.dec.deg,
        'pmra':np.zeros(n),'pmdec':np.zeros(n),'ref_epoch':np.full(n,2016.),
        'phot_g_mean_mag':np.full(n,13.),'ruwe':np.ones(n)})
    catalog.write(root/'catalog.csv',format='ascii.csv')
    (root/'provenance.json').write_text(json.dumps({'provider':'Synthetic tutorial; not actual Gaia sources',
        'sha256':hashlib.sha256((root/'catalog.csv').read_bytes()).hexdigest(),'injected_wcs_east_arcsec':.5}),encoding='utf-8')
    prepare_workset({'selection_schema_version':'1.0','files':[{'source':str(root/'synthetic.fit')}]},
                    root/'workset',Path(__file__).resolve().parents[1]/'local')
