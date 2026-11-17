# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Twelve invented images for inspecting frozen detector gates, never observations."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (2026111701, 2026111702)
SCENARIOS = ('bright', 'faint', 'hot_pixel', 'elongated', 'border', 'masked')
SHAPE = (96, 96)


def invented_image(scenario, seed):
    """Predetermined paired backgrounds; no choice based on detector outcomes."""
    if scenario not in SCENARIOS or seed not in SEEDS:
        raise ValueError('Scénario et graine du protocole fictif requis.')
    rng = np.random.default_rng(seed)
    image = 100.+rng.normal(0., 2., SHAPE)
    yy, xx = np.mgrid[:SHAPE[0], :SHAPE[1]]
    center = np.array([4.25 if scenario == 'border' else 48.25, 47.75])
    if scenario == 'hot_pixel':
        center = np.array([48., 48.]); image[48, 48] += 120.
    else:
        peak = 3. if scenario == 'faint' else 120.
        sx, sy = (4., .8) if scenario == 'elongated' else (1.3, 1.3)
        image += peak*np.exp(-.5*(((xx-center[0])/sx)**2+((yy-center[1])/sy)**2))
        if scenario == 'masked':
            image[47:50, 47:50] = 65000.
            image[48, 48] = np.nan
            image[10, 10] = np.inf
    return image.astype('float32'), center


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def make(output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(detector_demo_version='1.0', synthetic=True, status='running',
        shape=list(SHAPE), seeds=list(SEEDS), scenarios=list(SCENARIOS),
        generator_sha256_lf=sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        noise_sigma_invented=2., background_invented=100., frames=[],
        paired_noise_across_scenarios=True,
        performance_claim=False)
    truth = dict(detector_demo_truth_version='1.0', cases=[])
    mp = output/'manifest.json'
    save(mp, manifest)
    try:
        for seed in SEEDS:
            for scenario in SCENARIOS:
                case_id = f'{scenario}-s{seed}'
                image, center = invented_image(scenario, seed)
                path = output/f'{case_id}.npy'
                with path.open('xb') as stream:
                    np.save(stream, image, allow_pickle=False)
                manifest['frames'].append(dict(case_id=case_id, scenario=scenario,
                    seed=seed, local_plane=path.name, sha256=digest(path)))
                truth['cases'].append(dict(case_id=case_id, target_native=(2*center+.5).tolist()))
                save(mp, manifest)
        manifest['status'] = 'complete'
        save(mp, manifest)
        truth['manifest_sha256'] = digest(mp)
        save(output/'truth.json', truth)
    except Exception as exc:
        manifest.update(status='incomplete', error=str(exc))
        save(mp, manifest)
        raise
    print('Douze images entièrement fictives préparées : six situations, deux graines, aucun réglage du détecteur.', flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        make(args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
