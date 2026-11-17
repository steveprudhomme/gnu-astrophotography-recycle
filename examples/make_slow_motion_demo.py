# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Prepare two predeclared, entirely invented long-cadence Bayer backgrounds."""
import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path

from astropy.io import fits
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest, prepare_workset

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (2026112301, 2026112302)
SHAPE = (512, 512)
TIMES = tuple(float(k*300) for k in range(8))
STARTS = ((.35, .35, 30.), (.65, .65, 150.))
RATES = (10., 30., 60.)
SCALE = 206264.806247*.0029/250.


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def background_sources(seed):
    """The two reserved seeds change brightness, never the predefined positions."""
    if seed not in SEEDS:
        raise ValueError('Choisir une des deux graines réservées du protocole lent.')
    rng = np.random.default_rng(seed)
    starts = [np.array([fx*SHAPE[1], fy*SHAPE[0]]) for fx, fy, _ in STARTS]
    near_stars = [start+[0., -14.] for start in starts]
    corridors = []
    for start, (_, _, angle) in zip(starts, STARTS):
        for rate in RATES:
            vector = (rate/(3600*SCALE))*TIMES[-1]*np.array([
                np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
            corridors.append((start, vector))
    sources = []
    for y in np.linspace(48., 464., 10):
        for x in np.linspace(48., 464., 10):
            point = np.array([x, y])
            if any(np.linalg.norm(point-near) < 20 for near in near_stars):
                continue
            if any(np.linalg.norm(point-start-np.clip(
                    np.dot(point-start, vector)/np.dot(vector, vector), 0, 1)*vector) < 25
                    for start, vector in corridors):
                continue
            sources.append((float(x), float(y), float(rng.uniform(600., 1800.))))
    sources.extend([(*near_stars[0], 900.), (*near_stars[1], 1100.)])
    return sources


def make_context(output, seed, base):
    from slow_motion_profile import prepare

    output.mkdir(parents=True, exist_ok=False)
    source = output/'invented-source'
    source.mkdir()
    sources = background_sources(seed)
    rng = np.random.default_rng(seed+1_000_000)
    yy, xx = np.mgrid[:512, :512]
    response = np.tile([[1., .96], [1.04, 1.]], (256, 256))
    selected = []
    for k, time in enumerate(TIMES):
        angle = np.deg2rad(.5)*k/7
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        center = np.array([255.5, 255.5])
        translation = center-rotation@center+[3.5*k/7, 0.]
        image = np.full(SHAPE, 100.)
        for x, y, peak in sources:
            point = rotation@np.array([x, y])+translation
            image += peak*np.exp(-((xx-point[0])**2+(yy-point[1])**2)/(2*2.2**2))
        pixels = np.clip(image*response+rng.normal(0., 2., SHAPE), 0, 65535).astype('uint16')
        header = fits.Header(dict(OBJECT=f'Invented slow motion background {seed}',
            INSTRUME='Fictional instrument', FILTER='SIMULATED', GAIN=80, EQMODE=0,
            BAYERPAT='GRBG', EXPTIME=10., XPIXSZ=2.9, YPIXSZ=2.9, FOCALLEN=250., GARSYNTH=True))
        header['DATE-OBS'] = (datetime(2025, 1, 1)+timedelta(seconds=time)).isoformat()
        path = source/f'pose-{k+1:02d}.fit'
        fits.writeto(path, pixels, header)
        selected.append(dict(source=str(path.resolve()), expected_sha256=digest(path)))
    selection = dict(selection_schema_version='1.0', files=selected)
    save(output/'selection.json', selection)
    prepare_workset(selection, output/'workset', base)
    baseline = prepare(output/'workset/workset.json', output/'baseline', base)
    return dict(seed=seed, baseline_path=str(output/'baseline/baseline.json'),
        workset_path=str(output/'workset/workset.json'),
        registration_available=baseline['registration_available'], source_count=len(sources))


def make(output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    output.mkdir(parents=True, exist_ok=False)
    result = dict(slow_motion_demo_version='1.0', synthetic=True, status='running',
        generator_sha256_lf=sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        seeds=list(SEEDS), image_shape=list(SHAPE), relative_fictitious_seconds=list(TIMES),
        nominal_pixel_micrometers=2.9, nominal_focal_length_mm=250., exposure_declared_seconds=10.,
        total_rotation_degrees=.5, total_translation_native_pixels=[3.5, 0.],
        fixed_grid=True, contexts_share_grid_positions=True, corridor_margin_native_pixels=25.,
        near_stationary_star_offset_native=[0., -14.],
        controls_are_independent_nights=False, performance_claim=False, contexts=[])
    save(output/'contexts.json', result)
    try:
        for seed in SEEDS:
            result['contexts'].append(make_context(output/f'context-s{seed}', seed, base))
            save(output/'contexts.json', result)
        result.update(status='complete', all_contexts_available=all(
            c['registration_available'] for c in result['contexts']))
        save(output/'contexts.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc))
        save(output/'contexts.json', result)
        raise
    print('Deux séries fictives de huit poses préparées. Les refus restent dans contexts.json.', flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        result = make(args.output)
        if not result['all_contexts_available']:
            parser.exit(2, 'Au moins un recalage est refusé. Conserver son rapport.\n')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
