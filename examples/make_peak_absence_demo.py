# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Independent invented pixels for the upstream peak-creation trace, never observations."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (2026111801, 2026111802)
SCENARIOS = ('isolated_bright', 'faint', 'brighter_neighbor', 'masked', 'library_border', 'plateau_tie')
SHAPE = (96, 96)


def invented_image(scenario, seed):
    """Fixed fabrication, paired noise; names describe input intent, not outcomes."""
    if scenario not in SCENARIOS or seed not in SEEDS:
        raise ValueError('Scénario et graine prévus du banc fictif requis.')
    image = 100.+np.random.default_rng(seed).normal(0., 2., SHAPE)
    yy, xx = np.mgrid[:96, :96]
    center = np.array([1. if scenario == 'library_border' else 48., 48.])
    def gaussian(x, y, peak):
        return peak*np.exp(-.5*((xx-x)**2+(yy-y)**2)/1.3**2)
    if scenario == 'plateau_tie':
        image += gaussian(46., 48., 120.)+gaussian(50., 48., 120.)
        image[47:50, 47:50] = 220.
    else:
        peak = 3. if scenario == 'faint' else 30. if scenario == 'brighter_neighbor' else 120.
        image += gaussian(*center, peak)
        if scenario == 'brighter_neighbor':
            image += gaussian(51., 48., 240.)
        if scenario == 'masked':
            image[47:50, 47:50] = 65000.
            image[48, 48] = np.nan
    return image.astype('float32'), center


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def make(output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(peak_demo_version='1.0', synthetic=True, status='running', shape=list(SHAPE),
        seeds=list(SEEDS), scenarios=list(SCENARIOS), frames=[],
        generator_sha256_lf=sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        noise_sigma_invented=2., background_invented=100., gaussian_sigma_reduced=1.3,
        paired_noise_across_scenarios=True, performance_claim=False,
        fabrication=dict(isolated_peak=120., faint_peak=3., neighbor_target_peak=30.,
            neighbor_peak=240., neighbor_xy=[51., 48.], ordinary_target_xy=[48., 48.],
            library_border_target_xy=[1., 48.], masked_slice=[47, 50, 47, 50],
            mask_value=65000., masked_center_nan=True,
            plateau_source_xy=[[46., 48.], [50., 48.]], plateau_slice=[47, 50, 47, 50], plateau_value=220.))
    truth = dict(peak_demo_truth_version='1.0', cases=[])
    path = output/'manifest.json'; save(path, manifest)
    try:
        for seed in SEEDS:
            for scenario in SCENARIOS:
                case_id = f'{scenario}-s{seed}'
                image, center = invented_image(scenario, seed)
                plane = output/f'{case_id}.npy'
                with plane.open('xb') as stream:
                    np.save(stream, image, allow_pickle=False)
                manifest['frames'].append(dict(case_id=case_id, scenario=scenario, seed=seed,
                    local_plane=plane.name, sha256=digest(plane)))
                truth['cases'].append(dict(case_id=case_id, target_native=(2*center+.5).tolist()))
                save(path, manifest)
        manifest['status'] = 'complete'; save(path, manifest)
        truth['manifest_sha256'] = digest(path); save(output/'truth.json', truth)
    except Exception as exc:
        manifest.update(status='incomplete', error=str(exc)); save(path, manifest)
        raise
    print('Douze images entièrement fictives pour les maxima préparées, paramètres de fabrication conservés.', flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        make(args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
