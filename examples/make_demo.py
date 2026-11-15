# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: generate public, synthetic tutorial inputs.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Create small fictional FITS files; never overwrite an existing directory."""
from pathlib import Path
import shutil
import sys

from astropy.io import fits
import numpy as np


def make_demo(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    pixels = np.arange(48 * 64, dtype=np.uint16).reshape(48, 64)
    for index in (1, 2):
        hdu = fits.PrimaryHDU(pixels + index)
        hdu.header['OBJECT'] = 'Synthetic tutorial field'
        hdu.header['DATE-OBS'] = (f'2025-01-01T00:00:{10*index:02d}', 'Synthetic timestamp, unqualified')
        hdu.header['EXPTIME'] = 10.0
        hdu.header['BAYERPAT'] = 'GRBG'
        hdu.header['FILTER'] = 'SIMULATED'
        hdu.writeto(destination / f'pose-{index}.fit')
    shutil.copyfile(destination/'pose-1.fit', destination/'pose-1-copy.fit')
    stacked = fits.PrimaryHDU(np.stack([pixels] * 3))
    stacked.header['STACKCNT'] = 2
    stacked.header['BAYERPAT'] = 'GRBG'
    stacked.writeto(destination/'Stacked-demo.fit')
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(pixels)]).writeto(destination/'multi-hdu.fit')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python examples/make_demo.py NOUVEAU_DOSSIER')
    make_demo(sys.argv[1])
