# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Twelve fictional Bayer-labelled poses for the local preparation tutorial."""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from astropy.io import fits
from gar.astrometry import local_path

ROOT = Path(__file__).resolve().parents[1]


def make_demo(output, base=None):
    output = local_path(output, ROOT/'local' if base is None else base)
    output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(20261117)
    yy, xx = np.mgrid[:256, :256]
    stars = [(float(x), float(y), float(peak)) for x, y, peak in zip(rng.uniform(15, 241, 40), rng.uniform(15, 241, 40), rng.uniform(500, 4000, 40))]
    response = np.tile([[1., .9], [.8, 1.]], (128, 128))  # GRBG-like, not a calibrated sensor.
    for k in range(12):
        image = np.full((256, 256), 100.)
        for x, y, peak in stars:
            image += peak*np.exp(-((xx-x-.08*k)**2+(yy-y)**2)/(2*1.3**2))
        image = np.clip(image*response+rng.normal(0, 2, image.shape), 0, 65535).astype('uint16')
        header = fits.Header(dict(OBJECT='Fictional preparation field', INSTRUME='Fictional instrument',
                                 FILTER='SIMULATED', GAIN=80, EQMODE=0, BAYERPAT='GRBG', EXPTIME=10.,
                                 GARSYNTH=True))
        header['DATE-OBS'] = ((datetime(2025, 1, 1)+timedelta(seconds=13*k)).isoformat(), 'Invented, unqualified timestamp')
        fits.writeto(output/f'pose-{k+1:02d}.fit', image, header)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    make_demo(parser.parse_args().output)
