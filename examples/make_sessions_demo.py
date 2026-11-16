# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: fictional observations for session grouping.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Generate nine local FITS files, without overwriting any directory."""
from pathlib import Path
import shutil
import sys

from astropy.io import fits
import numpy as np


def make_demo(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    scenarios = [
        ('2025-01-01T20:00:00', 'Simulated A', 'SIMULATED-CLEAR'),
        ('2025-01-01T20:00:10', 'Simulated A', 'SIMULATED-CLEAR'),
        ('2025-01-01T21:00:00', 'Simulated A', 'SIMULATED-CLEAR'),
        ('2025-01-02T20:00:00', 'Simulated A', 'SIMULATED-CLEAR'),
        ('2025-01-01T20:00:05', 'Simulated A', 'SIMULATED-LP'),
        ('2025-01-01T20:00:00', 'Simulated B', 'SIMULATED-CLEAR'),
        (None, 'Simulated A', 'SIMULATED-CLEAR'),
    ]
    for index, (date, target, filter_name) in enumerate(scenarios, 1):
        hdu = fits.PrimaryHDU(np.full((48, 64), index, dtype=np.uint16))
        for key, value in {'OBJECT':target, 'FILTER':filter_name, 'INSTRUME':'Simulated camera',
                           'BAYERPAT':'GRBG', 'EQMODE':False, 'EXPTIME':10.0}.items():
            hdu.header[key] = value
        if date is not None:
            hdu.header['DATE-OBS'] = (date, 'Synthetic declared timestamp')
        hdu.writeto(destination/f'frame-{index:02d}.fit')
    shutil.copyfile(destination/'frame-01.fit', destination/'zz-copy.fit')
    stacked = fits.PrimaryHDU(np.zeros((3,48,64), dtype=np.uint16))
    stacked.header['STACKCNT'] = 2
    stacked.writeto(destination/'Stacked-demo.fit')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python examples/make_sessions_demo.py NOUVEAU_DOSSIER')
    make_demo(sys.argv[1])
