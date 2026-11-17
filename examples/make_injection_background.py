# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Invented background with clear injection corridors; no observations consumed."""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from astropy.io import fits
import numpy as np
from gar.astrometry import local_path
from gar.inventory import inventory
from gar.workset import prepare_workset
from prepare_seestar_series import plan_series, audit_series, save
import injection_recovery as experiment
import run_seestar_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]


def make(output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base); output.mkdir(parents=True, exist_ok=False)
    source = output/'invented-source'; source.mkdir()
    rng = np.random.default_rng(20261119)
    corridors = []
    for p in range(3):
        positions, _ = experiment.trajectory([512, 512], [0., 91.],
            dict(position_index=p, speed_native_per_declared_second=1.2))
        corridors.append(positions)
    stars = []
    for _ in range(100000):
        if len(stars) == 100:
            break
        point = rng.uniform(40, 472, 2)
        too_close = False
        for start, end in corridors:
            vector = end-start
            along = np.clip(np.dot(point-start, vector)/np.dot(vector, vector), 0, 1)
            if np.linalg.norm(point-start-along*vector) < 25:
                too_close = True
        if too_close or (stars and min(np.linalg.norm(point-np.array(s[:2])) for s in stars) < 20):
            continue
        stars.append((*point, rng.uniform(600, 1800)))
    if len(stars) != 100:
        raise ValueError('Placement fictif impossible ; pas de nouveau tirage choisi après résultat.')
    yy, xx = np.mgrid[:512, :512]; response = np.tile([[1., .96], [1.04, 1.]], (256, 256))
    for k in range(8):
        t = 13.*k; angle = np.deg2rad(.5)*k/7
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        translation = np.array([255.5, 255.5])-rotation@np.array([255.5, 255.5])+[.05*t, 0]
        image = np.full((512, 512), 100.)
        for x, y, peak in stars:
            p = rotation@np.array([x, y])+translation
            image += peak*np.exp(-((xx-p[0])**2+(yy-p[1])**2)/(2*2.2**2))
        pixels = np.clip(image*response+rng.normal(0, 2, image.shape), 0, 65535).astype('uint16')
        header = fits.Header(dict(OBJECT='Invented injection background', INSTRUME='Fictional instrument',
                                 FILTER='SIMULATED', GAIN=80, EQMODE=0, BAYERPAT='GRBG', EXPTIME=10., GARSYNTH=True))
        header['DATE-OBS'] = (datetime(2025, 1, 1)+timedelta(seconds=t)).isoformat()
        fits.writeto(source/f'pose-{k+1:02d}.fit', pixels, header)
    files, incidents = inventory(source)
    save(output/'manifest.json', dict(schema_version='1.0', input_root=str(source), files=files, traversal_incidents=incidents))
    plan = plan_series(output/'manifest.json', source, output/'plan', base=base)
    prepare_workset(plan['selection'], output/'workset', base)
    audit_series(output/'plan/plan.json', output/'workset/workset.json', output/'audit', base)
    pilot.run(output/'plan/plan.json', output/'workset/workset.json', output/'audit/series.json', output/'pilot', base)
    print('Fond fictif sans mobile préparé et pilote gelé ; trois couloirs dégagés pour l’exercice.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    make(parser.parse_args().output)
