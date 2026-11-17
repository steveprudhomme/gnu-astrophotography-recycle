# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Two independent invented Bayer backgrounds for representative motion trials."""
import argparse
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

from astropy.io import fits
import numpy as np
from gar.astrometry import local_path
from gar.inventory import inventory
from gar.workset import prepare_workset
from prepare_seestar_series import plan_series, audit_series, save
import run_seestar_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (2026111901, 2026111902)
SHAPE = (512, 512)
TIMES = tuple(float(k*10) for k in range(8))
STARTS = ((.35, .35, 30.), (.65, .65, 150.))


def background_sources(seed):
    """Fixed spatial grid and placement rules, with no detector feedback."""
    if seed not in SEEDS:
        raise ValueError('Graine du nouveau protocole fictif requise.')
    rng = np.random.default_rng(seed)
    starts = [np.array([fx*512, fy*512]) for fx, fy, _ in STARTS]
    vectors = [.5*70*np.array([np.cos(np.deg2rad(a)), np.sin(np.deg2rad(a))]) for _, _, a in STARTS]
    near_stars = [start+[0., -14.] for start in starts]
    sources = []
    for y in np.linspace(48., 464., 10):
        for x in np.linspace(48., 464., 10):
            p = np.array([x, y])
            if any(np.linalg.norm(p-q) < 20 for q in near_stars):
                continue
            in_corridor = False
            for start, vector in zip(starts, vectors):
                along = np.clip(np.dot(p-start, vector)/np.dot(vector, vector), 0, 1)
                if np.linalg.norm(p-start-along*vector) < 25:
                    in_corridor = True
            if not in_corridor:
                sources.append((x, y, float(rng.uniform(600., 1800.))))
    sources.extend([(*near_stars[0], 900.), (*near_stars[1], 1100.)])
    return sources


def make_context(output, seed, base):
    output.mkdir(parents=True, exist_ok=False)
    source = output/'invented-source'; source.mkdir()
    sources = background_sources(seed)
    rng = np.random.default_rng(seed+1_000_000)
    yy, xx = np.mgrid[:512, :512]
    response = np.tile([[1., .96], [1.04, 1.]], (256, 256))
    for k, t in enumerate(TIMES):
        angle = np.deg2rad(.5)*k/7
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        center = np.array([255.5, 255.5])
        translation = center-rotation@center+[.05*t, 0.]
        image = np.full(SHAPE, 100.)
        for x, y, peak in sources:
            p = rotation@np.array([x, y])+translation
            image += peak*np.exp(-((xx-p[0])**2+(yy-p[1])**2)/(2*2.2**2))
        pixels = np.clip(image*response+rng.normal(0., 2., SHAPE), 0, 65535).astype('uint16')
        header = fits.Header(dict(OBJECT=f'Invented representative motion background {seed}',
            INSTRUME='Fictional instrument', FILTER='SIMULATED', GAIN=80, EQMODE=0,
            BAYERPAT='GRBG', EXPTIME=10., XPIXSZ=2.9, YPIXSZ=2.9, FOCALLEN=250., GARSYNTH=True))
        header['DATE-OBS'] = (datetime(2025, 1, 1)+timedelta(seconds=t)).isoformat()
        fits.writeto(source/f'pose-{k+1:02d}.fit', pixels, header)
    files, incidents = inventory(source)
    save(output/'manifest.json', dict(schema_version='1.0', input_root=str(source),
        files=files, traversal_incidents=incidents))
    plan = plan_series(output/'manifest.json', source, output/'plan', base=base)
    prepare_workset(plan['selection'], output/'workset', base)
    audit_series(output/'plan/plan.json', output/'workset/workset.json', output/'audit', base)
    result = pilot.run(output/'plan/plan.json', output/'workset/workset.json',
        output/'audit/series.json', output/'pilot', base)
    return dict(seed=seed, pilot_path=str(output/'pilot/pilot.json'),
        registration_available=result['registration_available'],
        natural_candidate_count=result['candidate_count'], source_count=len(sources))


def make(output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    output.mkdir(parents=True, exist_ok=False)
    result = dict(realistic_motion_demo_version='1.0', synthetic=True, status='running',
        generator_sha256_lf=sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        seeds=list(SEEDS), image_shape=list(SHAPE), relative_fictitious_seconds=list(TIMES),
        nominal_pixel_micrometers=2.9, nominal_focal_length_mm=250., exposure_declared_seconds=10.,
        total_rotation_degrees=.5, drift_native_per_fictitious_second=[.05, 0.],
        fixed_grid=True, contexts_share_grid_positions=True, technical_corridor_margin_native=25.,
        near_stationary_star_offset_native=[0., -14.],
        controls_are_independent_nights=False, performance_claim=False, contexts=[])
    save(output/'contexts.json', result)
    try:
        for seed in SEEDS:
            result['contexts'].append(make_context(output/f'context-s{seed}', seed, base))
            save(output/'contexts.json', result)
        result.update(status='complete', all_contexts_available=all(c['registration_available'] for c in result['contexts']))
        save(output/'contexts.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); save(output/'contexts.json', result)
        raise
    print('Deux fonds Bayer entièrement fictifs préparés ; contextes et pilotes gelés, sans objet naturel.', flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        result = make(args.output)
        if not result['all_contexts_available']:
            parser.exit(2, 'Un contexte fictif reste indisponible ; conserver le dossier et ses motifs.\n')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
