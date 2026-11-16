# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: fictional timing faults for the tutorial.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Produce eleven tiny fictional FITS, not real clock measurements."""
from pathlib import Path
import shutil
import sys

from astropy.io import fits
import numpy as np


def make_demo(destination):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    dates=['2025-01-01T00:00:00.123456','2025-01-01T00:00:05.123456',
           '2025-01-01T00:00:05.123456','2025-01-01T00:40:00.123456',None,
           '2025-01-01','2016-12-31T23:59:60','2025-01-01T00:40:10.123456',
           '2025-01-01T00:40:20.123456']
    for index,date in enumerate(dates,1):
        hdu=fits.PrimaryHDU(np.full((48,64),index,dtype=np.uint16))
        for key,value in {'OBJECT':'Simulated timing field','INSTRUME':'Simulated camera',
                           'FILTER':'SIMULATED','BAYERPAT':'GRBG','EQMODE':False,
                           'EXPTIME':10.0,'EXPOSURE':20.0 if index==8 else 10.0}.items():
            hdu.header[key]=value
        if date is not None:
            hdu.header['DATE-OBS']=(date,'Start of exposure' if index==9 else 'Image created time')
        if index==9:
            hdu.header['TIMESYS']='UTC'
        hdu.writeto(destination/f'frame-{index:02d}.fit')
    shutil.copyfile(destination/'frame-01.fit',destination/'zz-copy.fit')
    stacked=fits.PrimaryHDU(np.zeros((3,48,64),dtype=np.uint16))
    stacked.header['STACKCNT']=2
    stacked.writeto(destination/'Stacked-demo.fit')


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python examples/make_timing_demo.py NOUVEAU_DOSSIER')
    make_demo(sys.argv[1])
