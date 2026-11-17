# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Invented Bayer intensity pilot, independent of observations; truth stays separate."""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from astropy.io import fits
from gar.astrometry import local_path
from gar.inventory import inventory
from gar.workset import prepare_workset
from prepare_seestar_series import plan_series, audit_series, save

ROOT = Path(__file__).resolve().parents[1]


def make(output, base=None, case='mobile'):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    if case not in ('mobile', 'control', 'insufficient'):
        raise ValueError('Cas fictif inconnu.')
    output.mkdir(parents=True, exist_ok=False)
    source = output/'invented-source'; source.mkdir()
    rng = np.random.default_rng(20261118)
    stars = []
    start, velocity = np.array([90., 160.]), np.array([.5, .2])
    segment = velocity*91
    target = 12 if case == 'insufficient' else 100
    for _ in range(100000):
        if len(stars) == target:
            break
        p = rng.uniform(40, 472, 2)
        along = np.clip(np.dot(p-start, segment)/np.dot(segment, segment), 0, 1)
        if np.linalg.norm(p-start-along*segment) < 25:
            continue
        if stars and min(np.linalg.norm(p-np.array(s[:2])) for s in stars) < 20:
            continue
        stars.append((*p, rng.uniform(600, 1800)))
    if len(stars) != target:
        raise ValueError('Placement fictif impossible ; ne pas changer de graine.')
    yy, xx = np.mgrid[:512, :512]
    response = np.tile([[1., .96], [1.04, 1.]], (256, 256))
    truths = []
    for k in range(8):
        t = 13.*k
        angle = np.deg2rad(.5)*k/7
        r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        offset = np.array([255.5, 255.5])-r@np.array([255.5, 255.5])+[.05*t, 0]
        image = np.full((512, 512), 100.)
        sources = list(stars)
        if case != 'control':
            position = start+velocity*t
            sources.append((*position, 400.))
            truths.append(dict(frame_index=k, x=float(position[0]), y=float(position[1])))
        for x, y, peak in sources:
            p = r@np.array([x, y])+offset
            image += peak*np.exp(-((xx-p[0])**2+(yy-p[1])**2)/(2*2.2**2))
        image = np.clip(image*response+rng.normal(0, 2, image.shape), 0, 65535).astype('uint16')
        header = fits.Header(dict(OBJECT='Invented pilot '+case, INSTRUME='Fictional instrument',
                                 FILTER='SIMULATED', GAIN=80, EQMODE=0, BAYERPAT='GRBG',
                                 EXPTIME=10., GARSYNTH=True))
        header['DATE-OBS'] = (datetime(2025, 1, 1)+timedelta(seconds=t)).isoformat()
        fits.writeto(source/f'pose-{k+1:02d}.fit', image, header)
    files, incidents = inventory(source)
    save(output/'manifest.json', dict(schema_version='1.0', input_root=str(source), files=files, traversal_incidents=incidents))
    plan = plan_series(output/'manifest.json', source, output/'plan', base=base)
    prepare_workset(plan['selection'], output/'workset', base)
    audit_series(output/'plan/plan.json', output/'workset/workset.json', output/'audit', base=base)
    save(output/'truth.json', dict(synthetic=True, case=case, reference_positions=truths,
                                  velocity_native_pixels_per_declared_second=velocity.tolist()))
    print('Huit poses fictives préparées ; réponses séparées de l’analyse.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    parser.add_argument('--case', choices=['mobile', 'control', 'insufficient'], default='mobile')
    args = parser.parse_args(); make(args.output, case=args.case)
