# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: fictional WCS headers for the tutorial.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Create eight small fictional FITS; no existing directory is overwritten."""
from pathlib import Path
import shutil
import sys

from astropy.io import fits
import numpy as np


def make_demo(destination):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    wcs={'CTYPE1':'RA---TAN','CTYPE2':'DEC--TAN','CRPIX1':32.0,'CRPIX2':24.0,
         'CRVAL1':120.0,'CRVAL2':30.0,'CD1_1':-0.001,'CD1_2':0.0,
         'CD2_1':0.0,'CD2_2':0.001,'CUNIT1':'deg','CUNIT2':'deg'}
    variants=[{'RA':120.0,'DEC':30.0},{'CTYPE1':'RA---TAN'},dict(wcs),
              dict(wcs,CD1_1=0.0,CD2_2=0.0),
              dict(wcs,CTYPE1='RA---TAN-SIP',CTYPE2='DEC--TAN-SIP',
                   A_ORDER=2,B_ORDER=2,A_2_0=1e-5,B_0_2=1e-5),
              {k:v for k,v in wcs.items() if k!='CRPIX1'}]
    for i,metadata in enumerate(variants,1):
        hdu=fits.PrimaryHDU(np.full((48,64),i,dtype=np.uint16))
        hdu.header['OBJECT']='Synthetic WCS field'
        for key,value in metadata.items():hdu.header[key]=value
        hdu.writeto(destination/f'frame-{i:02d}.fit')
    shutil.copyfile(destination/'frame-03.fit',destination/'zz-copy.fit')
    extension=fits.ImageHDU(np.zeros((48,64),dtype=np.uint16))
    for key,value in wcs.items():extension.header[key]=value
    fits.HDUList([fits.PrimaryHDU(),extension]).writeto(destination/'multi-hdu.fit')


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python examples/make_wcs_demo.py NOUVEAU_DOSSIER')
    make_demo(sys.argv[1])
