# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Version-pinned diagnostic replay; never changes or searches for a trajectory."""
import argparse
from collections import Counter
from hashlib import sha256
import inspect
from pathlib import Path
import warnings

import numpy as np
from astropy.stats import sigma_clipped_stats
import photutils
from photutils.detection import DAOStarFinder
from photutils.detection import core, daofinder, peakfinder
import gar.moving as moving
from gar.astrometry import local_path
from gar.workset import digest
import diagnose_injection_misses as diagnostic
import injection_recovery as experiment

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = '08219f018968d05479248fab4277144f8c93d45a'
DIAGNOSTIC_HASH = 'f270dd37e1e480f29a5acfa7f98b396c0e54e093bb2bb31adf3664ed133e8dc6'
LIBRARY_HASHES = {
    'photutils.detection.daofinder': '286f4eaaa020f88b16e582c14c83e42578822fdae5773f7c47cd5e656c8b1f0f',
    'photutils.detection.core': '105b2a298725dc73072136e675b36f180da3d6a827dcefb908bdaeb887f7a2d1',
    'photutils.detection.peakfinder': '268a55069baadd9af7bb763ac6c9d0193efc2374377cefc0afc4883c08fd716c',
}
METRICS = ('x_centroid', 'y_centroid', 'hx', 'hy', 'sharpness', 'roundness1', 'roundness2', 'peak', 'flux')
TOLERANCE = 1e-9
STATUSES = ('retained', 'project_margin', 'raw_rejected', 'centroid_displaced', 'no_near_raw_maximum')
LABELS = dict(retained='Point retenu', project_margin='Rejet par la marge du projet',
    raw_rejected='Maximum proposé puis rejet interne', centroid_displaced='Centre ajusté déplacé hors du voisinage',
    no_near_raw_maximum='Aucun maximum brut proche — cause non établie')
DEMO_SEEDS = (2026111701, 2026111702)
DEMO_SCENARIOS = ('bright', 'faint', 'hot_pixel', 'elongated', 'border', 'masked')


def recipe_hash():
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def frozen():
    hashes = diagnostic.frozen()
    if diagnostic.recipe_hash() != DIAGNOSTIC_HASH:
        raise ValueError('Diagnostic du lot 19 modifié : protocole distinct requis.')
    if photutils.__version__ != '3.1.1':
        raise ValueError('La trace exige Photutils 3.1.1 et ses sources épinglées.')
    for module in (daofinder, core, peakfinder):
        actual = sha256(Path(inspect.getsourcefile(module)).read_text(encoding='utf-8').encode()).hexdigest()
        if actual != LIBRARY_HASHES[module.__name__]:
            raise ValueError('Source Photutils différente du protocole de trace.')
    return dict(hashes, **{'examples/diagnose_injection_misses.py': DIAGNOSTIC_HASH}, **LIBRARY_HASHES)


def _xy(catalog):
    if catalog is None:
        return np.empty((0, 2))
    return np.column_stack([catalog.x_centroid, catalog.y_centroid])


def equal_points(left, right, label, tolerance=TOLERANCE):
    left, right = np.asarray(left, dtype=float).reshape(-1, 2), np.asarray(right, dtype=float).reshape(-1, 2)
    if (left.shape != right.shape or not np.isfinite(left).all() or not np.isfinite(right).all()
            or np.any(np.linalg.norm(left-right, axis=1) > tolerance)):
        raise ValueError(f'Positions différentes : {label}. Aucun bilan accepté.')


def trace_image(image, expected_points=None):
    """Replay all raw proposals without any truth coordinate or forced position.

    Only the installed, pinned library computes peaks and shape metrics. The
    independent Boolean reconstruction below is checked against its filters and
    then against the unchanged project detector on the same input image.
    """
    frozen()
    plane = np.asarray(image, dtype=float)
    if plane.ndim != 2 or min(plane.shape) < 32:
        raise ValueError('Image 2D de dimensions au moins 32 requise.')
    mask = ~np.isfinite(plane) | (plane >= 65000)
    _, background, noise = sigma_clipped_stats(plane, mask=mask, sigma=3, maxiters=5)
    if not np.isfinite(noise) or noise <= 0:
        raise ValueError('Bruit non mesurable.')
    finder = DAOStarFinder(threshold=5*noise, fwhm=3, min_separation=5, exclude_border=True)
    data = np.where(mask, background, plane)-background
    rows = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        raw = finder._get_raw_catalog(data, mask=mask)
        if raw is not None:
            metrics = {key: np.asarray(getattr(raw, key), dtype=float) for key in METRICS}
            h, w = plane.shape
            for i, seed in enumerate(raw.xypos):
                values = {key: float(v[i]) if np.isfinite(v[i]) else None for key, v in metrics.items()}
                nonfinite = [key for key, value in values.items() if value is None]
                reasons = ['nonfinite'] if nonfinite else []
                x, y = metrics['x_centroid'][i], metrics['y_centroid'][i]
                centroid_finite = bool(np.isfinite([x, y]).all())
                if centroid_finite and not (-.5 <= x <= w-.5 and -.5 <= y <= h-.5):
                    reasons.append('centroid_outside_image')
                for key, bounds in (('sharpness', finder.sharpness_range), ('roundness1', finder.roundness_range), ('roundness2', finder.roundness_range)):
                    if values[key] is not None and bounds is not None and not bounds[0] <= values[key] <= bounds[1]:
                        reasons.append(key)
                library_kept = not reasons
                margin_ok = centroid_finite and 8 <= x < w-8 and 8 <= y < h-8
                if centroid_finite and not margin_ok:
                    reasons.append('project_margin')
                rows.append(dict(raw_index=i, seed_xy_reduced=np.asarray(seed, dtype=float).tolist(),
                    centroid_xy_reduced=[float(x), float(y)] if centroid_finite else None,
                    metrics=values, nonfinite_metrics=nonfinite, rejection_reasons=reasons,
                    library_kept=library_kept, project_kept=bool(library_kept and margin_ok)))
            library = raw.apply_all_filters()
        else:
            library = None
        reconstructed = np.array([r['centroid_xy_reduced'] for r in rows if r['library_kept']], dtype=float).reshape(-1, 2)
        equal_points(reconstructed, _xy(library), 'filtres de la bibliothèque')
        selected = np.array([r['centroid_xy_reduced'] for r in rows if r['project_kept']], dtype=float).reshape(-1, 2)
        if len(selected) > 500:
            raise ValueError('Plus de 500 sources : limite inchangée du prototype.')
        official, selection = moving.detect_sources(plane)
        equal_points(selected, official, 'détecteur gelé')
        if expected_points is not None:
            equal_points(2*selected+.5, 2*np.asarray(expected_points).reshape(-1, 2)+.5, 'positions natives précédemment enregistrées')
    return dict(image_trace_version='1.0', photutils_version=photutils.__version__, image_shape=list(plane.shape), rows=rows,
        selected_points_reduced=selected.tolist(), background=float(background), noise_sigma=float(noise),
        threshold_input=float(5*noise), threshold_effective=float(finder.threshold_eff),
        parameters=dict(threshold_sigma=5, fwhm_reduced=3, min_separation_reduced=5, exclude_border=True,
            sharpness_range=list(finder.sharpness_range), roundness_range=list(finder.roundness_range),
            project_margin_reduced=8, saturation_adu=65000, scale_threshold=True, xycoords=None),
        masked_pixels=int(mask.sum()), raw_count=len(rows), library_count=len(reconstructed), selected_count=len(selected),
        replay_equal=True, saved_positions_checked=expected_points is not None, warnings=[str(w.message) for w in caught],
        official_selection=selection)


def evidence_at(trace, target_native, radius_native):
    """After replay only: both peak seeds and fitted centroids remain visible."""
    target = np.asarray(target_native, dtype=float)
    if target.shape != (2,) or not np.isfinite(target).all() or radius_native not in diagnostic.RADII:
        raise ValueError('Position native finie et rayon de diagnostic prévu requis.')
    centroid_ids, seed_ids, distances = [], [], []
    for i, row in enumerate(trace['rows']):
        sd = float(np.linalg.norm(2*np.asarray(row['seed_xy_reduced'])+.5-target))
        cd = None if row['centroid_xy_reduced'] is None else float(np.linalg.norm(2*np.asarray(row['centroid_xy_reduced'])+.5-target))
        distances.append(dict(raw_index=i, seed_distance_native=sd, centroid_distance_native=cd))
        if sd <= radius_native:
            seed_ids.append(i)
        if cd is not None and cd <= radius_native:
            centroid_ids.append(i)
    ids = sorted(set(centroid_ids) | set(seed_ids))
    near = [trace['rows'][i] for i in centroid_ids]
    selected_count = sum(r['project_kept'] for r in near)
    library_count = sum(r['library_kept'] for r in near)
    if selected_count:
        status = 'retained'
    elif library_count:
        status = 'project_margin'
    elif centroid_ids or seed_ids:
        status = 'raw_rejected' if any(not trace['rows'][i]['library_kept'] for i in ids) else 'centroid_displaced'
    else:
        status = 'no_near_raw_maximum'
    return dict(target_native=target.tolist(), radius_native=float(radius_native), status=status,
        raw_seed_count=len(seed_ids), raw_centroid_count=len(centroid_ids), library_count=library_count,
        selected_count=selected_count, row_indices=centroid_ids, seed_row_indices=seed_ids,
        rejection_counts=dict(sorted(Counter(reason for i in ids for reason in trace['rows'][i]['rejection_reasons']).items())),
        nearby_rows=[dict(trace['rows'][i], **distances[i]) for i in ids],
        nearest_seed_distance_native=min((d['seed_distance_native'] for d in distances), default=None),
        nearest_centroid_distance_native=min((d['centroid_distance_native'] for d in distances if d['centroid_distance_native'] is not None), default=None),
        proximity_ambiguous=len(ids) > 1 or seed_ids != centroid_ids,
        identity_proven=False, physical_cause_proven=False)


def summarize(frames):
    return {f'{radius:g}': dict(sorted(Counter(f['evidence_by_radius'][f'{radius:g}']['status'] for f in frames).items())) for radius in diagnostic.RADII}


def load_demo(manifest_path, base):
    path = local_path(manifest_path, base); manifest = experiment.read(path)
    if (manifest.get('detector_demo_version') != '1.0' or manifest.get('synthetic') is not True
            or manifest.get('status') != 'complete'):
        raise ValueError('Banc de trace entièrement fictif version 1.0 requis.')
    frames = manifest.get('frames')
    if not isinstance(frames, list) or len(frames) != 12 or len({f['case_id'] for f in frames}) != 12:
        raise ValueError('Douze cas fictifs distincts requis.')
    specs = [(f'{scenario}-s{seed}', scenario, seed) for seed in DEMO_SEEDS for scenario in DEMO_SCENARIOS]
    if (manifest.get('shape') != [96, 96] or manifest.get('seeds') != list(DEMO_SEEDS)
            or manifest.get('scenarios') != list(DEMO_SCENARIOS)
            or [(f['case_id'], f['scenario'], f['seed']) for f in frames] != specs):
        raise ValueError('Le protocole exige six situations prédéfinies et les deux graines réservées.')
    watched = {path: digest(path)}; planes = []
    for frame in frames:
        p = local_path(path.parent/frame['local_plane'], base)
        if path.parent not in p.parents or p.suffix != '.npy' or p in watched or digest(p) != frame['sha256']:
            raise ValueError('Plan fictif modifié, répété ou hors du banc.')
        with p.open('rb') as stream:
            plane = np.load(stream, allow_pickle=False)
            if stream.read(1):
                raise ValueError('Données supplémentaires après le plan.')
        if plane.shape != (96, 96) or plane.dtype != np.dtype('float32'):
            raise ValueError('Plan fictif float32 96×96 requis.')
        watched[p] = frame['sha256']; planes.append(plane)
    return path, manifest, planes, watched


def write_report(output, result):
    text = '# Trace descriptive du détecteur — après rejeu\n\n'
    text += 'Aucun seuil modifié, aucune association de trajectoires. Un maximum brut absent ne suffit pas à expliquer sa cause physique.\n\n'
    text += '| Image fictive | À 1,5 pixel natif | À 3 pixels natifs |\n|---|---|---|\n'
    for frame in result['frames']:
        statuses = [frame.get('evidence_by_radius', {}).get(r, {}).get('status') for r in ('1.5', '3')]
        text += f"| {frame['case_id']} | {LABELS.get(statuses[0], 'Inconnu')} | {LABELS.get(statuses[1], 'Inconnu')} |\n"
    (output/'report.md').write_text(text, encoding='utf-8')


def run_demo(manifest_path, truth_path, output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base); tp = local_path(truth_path, base)
    mp, manifest, planes, watched = load_demo(manifest_path, base)
    if tp in watched:
        raise ValueError('Réponses et entrées d’image doivent être distinctes.')
    watched[tp] = digest(tp)  # Bytes only: no target is parsed before replay.
    hashes = frozen(); output.mkdir(parents=True, exist_ok=False)
    result = dict(detector_trace_version='1.0', status='running', source_kind='synthetic_demo',
        plan_commit=PLAN_COMMIT, trace_recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=hashes,
        manifest_path=str(mp), manifest_sha256=watched[mp], truth_path=str(tp), truth_sha256=watched[tp],
        truth_opened_after_replay=False, thresholds_changed=False, association_rerun=False, frames=[], **experiment.provenance())
    experiment.save(output/'trace.json', result)
    try:
        for frame, plane in zip(manifest['frames'], planes):
            result['frames'].append(dict(case_id=frame['case_id'], scenario=frame['scenario'], seed=frame['seed'], trace=trace_image(plane)))
            experiment.save(output/'trace.json', result)
        experiment.unchanged(watched); truth = experiment.read(tp)
        if (truth.get('detector_demo_truth_version') != '1.0' or truth.get('manifest_sha256') != watched[mp]
                or [r['case_id'] for r in truth.get('cases', [])] != [f['case_id'] for f in manifest['frames']]):
            raise ValueError('Réponses fictives incohérentes ou incomplètes.')
        for frame, answer in zip(result['frames'], truth['cases']):
            frame['evidence_by_radius'] = {f'{r:g}': evidence_at(frame['trace'], answer['target_native'], r) for r in diagnostic.RADII}
            frame['status_stable_across_radii'] = frame['evidence_by_radius']['1.5']['status'] == frame['evidence_by_radius']['3']['status']
        result.update(truth_opened_after_replay=True, summary=summarize(result['frames']))
        experiment.unchanged(watched); frozen()
        result.update(status='complete', input_hashes_unchanged=True, inputs_sha256={str(p): h for p, h in watched.items()})
        write_report(output, result); experiment.save(output/'trace.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); experiment.save(output/'trace.json', result)
        raise
    print(f"Trace de {len(result['frames'])} images fictives terminée, seuils inchangés.", flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path); parser.add_argument('truth', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        run_demo(args.manifest, args.truth, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
