# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Separate jittered-star slow benchmark; historical recipes remain frozen."""
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from astropy.io import fits
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest, prepare_workset
import slow_motion_profile as slow
from diagnose_slow_misses import historical, rotation_audit, source_hash

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (2026112401, 2026112402)
TIMES = tuple(float(300*k) for k in range(8))
SHAPE = (512, 512)
SCALE = 206264.806247*.0029/250.
STARTS = ((.35, .35, 30.), (.65, .65, 150.))


def background_sources(seed):
    """Independent bounded jitter; exclusion depends only on specified geometry."""
    if type(seed) is not int or seed < 0:
        raise ValueError('Une graine entière positive est requise.')
    rng = np.random.default_rng(seed)
    starts = [np.array([fx*512, fy*512]) for fx, fy, _ in STARTS]
    near_stars = [start+[0., -14.] for start in starts]
    corridors = []
    for start, (_, _, angle) in zip(starts, STARTS):
        for rate in (10., 30., 60.):
            vector = rate/(3600*SCALE)*2100*np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
            corridors.append((start, vector))
    sources = []
    for y in np.linspace(48., 464., 10):
        for x in np.linspace(48., 464., 10):
            point = np.array([x, y])+rng.uniform(-9., 9., 2)
            peak = float(rng.uniform(600., 1800.))
            if any(np.linalg.norm(point-near) < 20 for near in near_stars):
                continue
            if any(np.linalg.norm(point-start-np.clip(np.dot(point-start, vector)/np.dot(vector, vector), 0, 1)*vector) < 25
                   for start, vector in corridors):
                continue
            sources.append((*map(float, point), peak))
    sources.extend([(*near_stars[0], 900.), (*near_stars[1], 1100.)])
    return sources


def make_context(output, seed, base):
    output.mkdir(parents=True, exist_ok=False)
    source = output/'invented-source'; source.mkdir()
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
        header = fits.Header(dict(OBJECT=f'Invented asymmetric slow background {seed}',
            INSTRUME='Fictional instrument', FILTER='SIMULATED', GAIN=80, EQMODE=0,
            BAYERPAT='GRBG', EXPTIME=10., XPIXSZ=2.9, YPIXSZ=2.9, FOCALLEN=250., GARSYNTH=True))
        header['DATE-OBS'] = (datetime(2025, 1, 1)+timedelta(seconds=time)).isoformat()
        path = source/f'pose-{k+1:02d}.fit'
        fits.writeto(path, pixels, header)
        selected.append(dict(source=str(path.resolve()), expected_sha256=digest(path)))
    prepare_workset(dict(selection_schema_version='1.0', files=selected), output/'workset', base)
    baseline = slow.prepare(output/'workset/workset.json', output/'baseline', base)
    audit = rotation_audit(baseline)
    slow.save(output/'registration-audit.json', dict(asymmetric_registration_audit_version='1.0',
        baseline_sha256=digest(output/'baseline/baseline.json'), **audit))
    return dict(seed=seed, baseline_path=str(output/'baseline/baseline.json'),
                registration_available=baseline['registration_available'], search_status=baseline['search_status'],
                geometry_control_passed=audit['passed'],
                experiment_admissible=bool(audit['passed'] and baseline['search_status'] == 'complete'),
                source_count=len(sources))


def make(output, base=None):
    base = ROOT/'local' if base is None else base
    engines = historical(); output = local_path(output, base)
    output.mkdir(parents=True, exist_ok=False)
    result = dict(asymmetric_slow_demo_version='1.0', status='running', synthetic=True,
                  generator_sha256_lf=source_hash(__file__), frozen_sha256_lf=engines,
                  seeds=list(SEEDS), image_shape=list(SHAPE), relative_fictitious_seconds=list(TIMES),
                  jitter_native_pixels=9., total_rotation_degrees=.5, total_translation_native_pixels=[3.5, 0.],
                  fixed_grid=False, positions_chosen_from_detection=False, contexts=[],
                  known_natural_positive_tested=False, scientific_performance_validated=False)
    slow.save(output/'contexts.json', result)
    try:
        for seed in SEEDS:
            result['contexts'].append(make_context(output/f'context-s{seed}', seed, base))
            slow.save(output/'contexts.json', result)
        if engines != historical():
            raise ValueError('Une source historique a changé.')
        result.update(status='complete', all_contexts_admissible=all(c['experiment_admissible'] for c in result['contexts']))
        slow.save(output/'contexts.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); slow.save(output/'contexts.json', result); raise
    print('Deux fonds fictifs irréguliers préparés ; contrôle de fabrication conservé, sans correction des modèles.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        result = make(args.output)
        raise SystemExit(0 if result['all_contexts_admissible'] else 2)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
