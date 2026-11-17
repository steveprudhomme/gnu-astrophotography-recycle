# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Trace peak-creation gates without changing the frozen detector or thresholds."""
import argparse
from collections import Counter
from hashlib import sha256
import inspect
from pathlib import Path
import warnings

import numpy as np
from photutils.detection import DAOStarFinder, peakfinder
from photutils.utils import _convolution
from gar.astrometry import local_path
from gar.workset import digest
import trace_detector_decisions as previous
import trace_scored_misses as scored
import injection_recovery as experiment

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = '4a5bd4b9161056e2ac81d429c130e421801bc0be'
PREVIOUS_HASH = 'f9c69b76f504bed9b54867ef2965fee677708b517131062c0d3fc4171a668de4'
SCORED_HASH = '314b36e8974ed2ec57cf7ace86b93b0f7f78e1efd14ff6424ec21d0ca48cf9b4'
CONVOLUTION_HASH = 'f01036f36af5570f69cecaf4734954cf8948db3b63cda4ead40e91a26e4b9f05'
STAGES = ('samples', 'local_maximum', 'unmasked', 'inside_border', 'above_threshold', 'plateau', 'final')
LABELS = dict(samples='Voisinage non échantillonné', local_maximum='Aucun maximum local proche',
    unmasked='Retrait par le masque', inside_border='Retrait au bord de la bibliothèque',
    above_threshold='Réponse sous ou égale au seuil', plateau='Regroupement de plateau',
    final='Départage des maxima égaux', proposed='Maximum brut proposé')
DEMO_SEEDS = (2026111801, 2026111802)
DEMO_SCENARIOS = ('isolated_bright', 'faint', 'brighter_neighbor', 'masked', 'library_border', 'plateau_tie')


def recipe_hash():
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def frozen():
    result = previous.frozen()
    if previous.recipe_hash() != PREVIOUS_HASH or scored.recipe_hash() != SCORED_HASH:
        raise ValueError('Recette du lot 20 modifiée : nouveau protocole requis.')
    actual = sha256(Path(inspect.getsourcefile(_convolution)).read_text(encoding='utf-8').encode()).hexdigest()
    if actual != CONVOLUTION_HASH:
        raise ValueError('Source de convolution différente du protocole.')
    return dict(result, **{'examples/trace_detector_decisions.py': PREVIOUS_HASH,
        'examples/trace_scored_misses.py': SCORED_HASH, 'photutils.utils._convolution': actual})


def _coordinates(mask):
    yy, xx = np.nonzero(mask)
    return np.column_stack([xx, yy])


def _seed_mask(shape, x, y):
    result = np.zeros(shape, dtype=bool)
    result[y, x] = True
    return result


def trace_convolved(convolved, mask, threshold, border_width=(2, 2)):
    """Record the actual gates; this function has no target-position argument.

    Internal helpers are called at their original radius, including plateau and
    equal-height handling. The reconstructed ordered seeds must equal find_peaks.
    """
    frozen()
    values = np.asarray(convolved, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    border = np.asarray(border_width)
    if (values.ndim != 2 or not values.size or not np.isfinite(values).all() or mask.shape != values.shape
            or not np.isscalar(threshold) or not np.isfinite(threshold)
            or border.shape != (2,) or not np.issubdtype(border.dtype, np.integer)
            or np.any(border < 0) or np.any(border >= values.shape)):
        raise ValueError('Carte finie 2D, masque compatible, seuil et bord valides requis.')
    data = values.copy()
    if mask.any():
        data[mask] = np.min(values)
    constant = bool(np.all(values == values.flat[0]))
    local = np.zeros(values.shape, dtype=bool) if constant else peakfinder._fast_circular_peaks(data, 5)
    inside = np.ones(values.shape, dtype=bool)
    by, bx = map(int, border)
    if by:
        inside[:by] = False; inside[-by:] = False
    if bx:
        inside[:, :bx] = False; inside[:, -bx:] = False
    conditions = dict(local_maximum=local, unmasked=~mask, inside_border=inside, above_threshold=data > threshold)
    maps = {'samples': np.ones(values.shape, dtype=bool)}
    last = maps['samples']
    for name in ('local_maximum', 'unmasked', 'inside_border', 'above_threshold'):
        maps[name] = last & conditions[name]; last = maps[name]
    yy, xx, sizes = peakfinder._collapse_plateaus(last, 5)
    maps['plateau'] = _seed_mask(values.shape, xx, yy)
    xx, yy, _ = peakfinder._remove_tied_peaks(xx, yy, data[yy, xx], 5, n_pixels=sizes)
    maps['final'] = _seed_mask(values.shape, xx, yy)
    seeds = np.column_stack([xx, yy])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        official = peakfinder.find_peaks(values, threshold, mask=mask, border_width=tuple(border), min_separation=5)
    expected = np.empty((0, 2), dtype=int) if official is None else np.column_stack([official['x_peak'], official['y_peak']])
    if seeds.shape != expected.shape or not np.array_equal(seeds, expected):
        raise ValueError('Graines différentes du chercheur de pics gelé.')
    return dict(image_shape=list(values.shape), convolved=values, peak_data=data, maps=maps,
        condition_maps=conditions, seeds_reduced=seeds.tolist(), threshold_effective=float(threshold),
        border_width_reduced=border.tolist(), min_separation_reduced=5,
        stage_counts_global={key: int(value.sum()) for key, value in maps.items()},
        constant_input=constant, seeds_equal=True)


def trace_image(image, expected_trace=None):
    frozen()
    old = previous.trace_image(image, expected_points=None if expected_trace is None else expected_trace['selected_points_reduced'])
    if expected_trace is not None and old != expected_trace:
        raise ValueError('Trace du détecteur différente du lot 20 gelé.')
    plane = np.asarray(image, dtype=float)
    mask = ~np.isfinite(plane) | (plane >= 65000)
    finder = DAOStarFinder(threshold=5*old['noise_sigma'], fwhm=3, min_separation=5, exclude_border=True)
    data = np.where(mask, old['background'], plane)-old['background']
    convolved = _convolution._filter_data(data, finder.kernel.data, mode='constant', fill_value=0., check_normalization=False)
    result = trace_convolved(convolved, mask, finder.threshold_eff, (finder.kernel.y_radius, finder.kernel.x_radius))
    seeds = np.array([row['seed_xy_reduced'] for row in old['rows']], dtype=float).reshape(-1, 2)
    if not np.array_equal(np.asarray(result['seeds_reduced']).reshape(-1, 2), seeds):
        raise ValueError('Graines différentes de DAOStarFinder et de la trace gelée.')
    result.update(background=old['background'], noise_sigma=old['noise_sigma'], threshold_input=old['threshold_input'],
        old_detector_trace=old, saved_trace_checked=expected_trace is not None,
        kernel_data=finder.kernel.data.tolist(), kernel_relative_error=float(finder.kernel.rel_err))
    return result


def serializable_trace(trace):
    return {key: value for key, value in trace.items() if key not in ('maps', 'condition_maps', 'convolved', 'peak_data')}


def evidence_at(trace, target_native, radius_native):
    target = np.asarray(target_native, dtype=float)
    if target.shape != (2,) or not np.isfinite(target).all() or radius_native not in previous.diagnostic.RADII:
        raise ValueError('Position native finie et rayon 1,5 ou 3 requis.')
    h, w = trace['image_shape']; center = (target-.5)/2; radius = radius_native/2
    left = max(0, int(np.ceil(center[0]-radius))); right = min(w-1, int(np.floor(center[0]+radius)))
    bottom = max(0, int(np.ceil(center[1]-radius))); top = min(h-1, int(np.floor(center[1]+radius)))
    samples = []
    for y in range(bottom, top+1):
        for x in range(left, right+1):
            if np.linalg.norm(2*np.array([x, y])+.5-target) > radius_native:
                continue
            samples.append(dict(x_reduced=x, y_reduced=y, value_convolved=float(trace['convolved'][y, x]),
                value_for_peaks=float(trace['peak_data'][y, x]),
                stage_passes={key: bool(trace['maps'][key][y, x]) for key in STAGES},
                conditions_passes={key: bool(value[y, x]) for key, value in trace['condition_maps'].items()}))
    counts = {key: sum(s['stage_passes'][key] for s in samples) for key in STAGES}
    first = next((key for key in STAGES if counts[key] == 0), 'proposed')
    obstacles = {key: sum(not s['conditions_passes'][key] for s in samples) for key in trace['condition_maps']}
    best = max(samples, key=lambda s: s['value_for_peaks'], default=None)
    neighbor = None
    if best is not None:
        x, y = best['x_reduced'], best['y_reduced']; candidates = []
        for ny in range(max(0, y-5), min(h, y+6)):
            for nx in range(max(0, x-5), min(w, x+6)):
                if (nx-x)**2+(ny-y)**2 <= 25 and trace['peak_data'][ny, nx] > best['value_for_peaks']:
                    candidates.append((float(trace['peak_data'][ny, nx]), ny, nx))
        if candidates:
            value, ny, nx = max(candidates, key=lambda item: (item[0], -item[1], -item[2]))
            neighbor = dict(x_reduced=nx, y_reduced=ny, value_for_peaks=value,
                distance_native=float(np.linalg.norm(2*np.array([nx, ny])+.5-target)), identity_proven=False)
    return dict(target_native=target.tolist(), radius_native=float(radius_native), stage_counts=counts,
        first_empty_stage=first, first_empty_label=LABELS[first], simultaneous_obstacles=obstacles,
        independent_pass_counts={key: len(samples)-value for key, value in obstacles.items()},
        best_sample=best, higher_neighbor=neighbor, final_seed_count=counts['final'], samples=samples,
        constant_input=trace['constant_input'], identity_proven=False, physical_cause_proven=False)


def summarize(frames):
    return {f'{r:g}': dict(sorted(Counter(f['evidence_by_radius'][f'{r:g}']['first_empty_stage'] for f in frames).items())) for r in previous.diagnostic.RADII}


def load_demo(manifest_path, base):
    mp = local_path(manifest_path, base); manifest = experiment.read(mp)
    specs = [(f'{scenario}-s{seed}', scenario, seed) for seed in DEMO_SEEDS for scenario in DEMO_SCENARIOS]
    if (manifest.get('peak_demo_version') != '1.0' or manifest.get('synthetic') is not True
            or manifest.get('status') != 'complete' or manifest.get('shape') != [96, 96]
            or manifest.get('seeds') != list(DEMO_SEEDS) or manifest.get('scenarios') != list(DEMO_SCENARIOS)
            or [(f['case_id'], f['scenario'], f['seed']) for f in manifest.get('frames', [])] != specs):
        raise ValueError('Banc fictif complet du protocole de maxima requis.')
    watched = {mp: digest(mp)}; planes = []
    for frame in manifest['frames']:
        path = local_path(mp.parent/frame['local_plane'], base)
        if mp.parent not in path.parents or path in watched or path.suffix != '.npy' or digest(path) != frame['sha256']:
            raise ValueError('Plan modifié, répété ou hors du banc.')
        with path.open('rb') as stream:
            plane = np.load(stream, allow_pickle=False)
            if stream.read(1):
                raise ValueError('Données après le plan refusées.')
        if plane.dtype != np.dtype('float32') or plane.shape != (96, 96):
            raise ValueError('Plan float32 96×96 requis.')
        watched[path] = frame['sha256']; planes.append(plane)
    return mp, manifest, planes, watched


def write_report(output, result):
    text = '# Portes de création des maxima — données fictives\n\nAucun seuil modifié. Les premières portes vides ne sont pas des causes physiques exclusives.\n\n'
    text += '| Image | Rayon 1,5 | Rayon 3 |\n|---|---|---|\n'
    for frame in result['frames']:
        text += f"| {frame['case_id']} | {frame['evidence_by_radius']['1.5']['first_empty_label']} | {frame['evidence_by_radius']['3']['first_empty_label']} |\n"
    (output/'report.md').write_text(text, encoding='utf-8')


def run_demo(manifest_path, truth_path, output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base); tp = local_path(truth_path, base)
    mp, manifest, planes, watched = load_demo(manifest_path, base)
    if tp in watched:
        raise ValueError('Réponses distinctes des images requises.')
    watched[tp] = digest(tp); frozen(); output.mkdir(parents=True, exist_ok=False)
    result = dict(peak_absence_trace_version='1.0', status='running', source_kind='synthetic_demo',
        plan_commit=PLAN_COMMIT, trace_recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=frozen(),
        manifest_path=str(mp), manifest_sha256=watched[mp], truth_path=str(tp), truth_sha256=watched[tp],
        thresholds_changed=False, association_rerun=False, truth_opened_after_replay=False, frames=[], **experiment.provenance())
    experiment.save(output/'trace.json', result)
    traces = []
    try:
        for item, plane in zip(manifest['frames'], planes):
            trace = trace_image(plane); traces.append(trace)
            result['frames'].append(dict(case_id=item['case_id'], scenario=item['scenario'], seed=item['seed'], trace=serializable_trace(trace)))
            experiment.save(output/'trace.json', result)
        experiment.unchanged(watched); truth = experiment.read(tp)
        if (truth.get('peak_demo_truth_version') != '1.0' or truth.get('manifest_sha256') != watched[mp]
                or [a['case_id'] for a in truth.get('cases', [])] != [f['case_id'] for f in manifest['frames']]):
            raise ValueError('Réponses du même banc complet requises.')
        for frame, trace, answer in zip(result['frames'], traces, truth['cases']):
            frame['evidence_by_radius'] = {f'{r:g}': evidence_at(trace, answer['target_native'], r) for r in previous.diagnostic.RADII}
            frame['status_stable_across_radii'] = frame['evidence_by_radius']['1.5']['first_empty_stage'] == frame['evidence_by_radius']['3']['first_empty_stage']
        experiment.unchanged(watched); frozen()
        result.update(status='complete', input_hashes_unchanged=True, truth_opened_after_replay=True,
            summary=summarize(result['frames']), inputs_sha256={str(p): value for p, value in watched.items()})
        write_report(output, result); experiment.save(output/'trace.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); experiment.save(output/'trace.json', result)
        raise
    print('Création des maxima tracée sur douze images fictives ; seuils inchangés.', flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path); parser.add_argument('truth', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        run_demo(args.manifest, args.truth, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
