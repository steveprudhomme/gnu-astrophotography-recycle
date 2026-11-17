# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Generate local synthetic copies; no original/external path is used."""
from pathlib import Path
import argparse
import json
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.spatial import cKDTree
from gar.workset import digest


def synthetic_points(seed=42, size=768, count=180):
    rng = np.random.default_rng(seed)
    points = rng.uniform(60, size-60, (count*3, 2))
    chosen = []
    for point in points:
        if not chosen or cKDTree(chosen).query(point)[0] > 18:
            chosen.append(point)
        if len(chosen) == count:
            break
    points = np.asarray(chosen)
    flux = rng.uniform(1000, 10000, len(points))
    return points, flux


def render(points, flux, size=768, seed=1, bayer=False):
    rng = np.random.default_rng(seed)
    image = np.full((size, size), 1000.)
    for (x, y), peak in zip(points, flux):
        left, right = max(0, int(x)-8), min(size, int(x)+10)
        bottom, top = max(0, int(y)-8), min(size, int(y)+10)
        if left >= right or bottom >= top:
            continue
        yy, xx = np.mgrid[bottom:top, left:right]
        image[bottom:top, left:right] += peak*np.exp(-((xx-x)**2+(yy-y)**2)/(2*1.6**2))
    if bayer:
        # Synthetic GRBG response, not a real sensor calibration.
        image *= np.tile([[1., .8], [.65, 1.]], (size//2, size//2))
    return np.clip(image+rng.normal(0, 3, image.shape), 0, 65535).astype(np.uint16)


def make_demo(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    copies = output/'copies'
    copies.mkdir()
    points, flux = synthetic_points()
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [384, 384]
    wcs.wcs.crval = [120, 30]
    wcs.wcs.cd = [[-2/3600, 0], [0, 2/3600]]
    wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
    ref = render(points, flux)
    files = []
    truth = []
    for index, (angle, shift) in enumerate([(-12., [35., -20.]), (3., [-8., 12.]), (18., [80., -65.])], 1):
        theta = np.deg2rad(angle)
        rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
        translation = np.array([384., 384.])-rotation@np.array([384., 384.])+shift
        frame_points = (points-translation)@rotation
        image = render(frame_points, flux, seed=index+1, bayer=True)
        path = copies/f'pose-{index}.fit'
        fits.writeto(path, image)
        files.append({'local_copy': f'copies/{path.name}', 'sha256_copy': digest(path),
                      'source': 'UNUSED_EXTERNAL_SOURCE_DO_NOT_OPEN'})
        truth.append({'file_index': index, 'rotation_degrees': angle, 'translation_pixels': translation.tolist()})
    path = copies/'reference.fit'
    fits.writeto(path, np.stack([ref, ref, ref]), wcs.to_header())
    files.append({'local_copy': f'copies/{path.name}', 'sha256_copy': digest(path),
                  'source': 'UNUSED_EXTERNAL_SOURCE_DO_NOT_OPEN'})
    (output/'workset.json').write_text(json.dumps({'success': True, 'files': files}, indent=2), encoding='utf-8')
    (output/'truth.json').write_text(json.dumps(truth, indent=2), encoding='utf-8')
    return truth


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    make_demo(parser.parse_args().output)
