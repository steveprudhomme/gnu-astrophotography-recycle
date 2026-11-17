# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Offline rigid registration with a split fixed before any pattern matching."""
from itertools import combinations
import csv
import hashlib
import json

from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.wcs import WCS
import numpy as np
from photutils.detection import DAOStarFinder
from scipy.spatial import cKDTree

from .astrometry import local_path
from .workset import digest
from .registration_reports import registration_svg


CRITERIA = {'min_training': 20, 'min_control': 10, 'median_max_pixels': .75,
            'p95_max_pixels': 1.5, 'min_grid_cells': 6, 'required_quadrants': 4}
PARAMETERS = {'threshold_sigma': 5, 'binned_fwhm': 2, 'binning': 2,
              'saturation_adu': 65000, 'margin_pixels': 10, 'isolation_pixels': 8,
              'control_fraction': .25, 'split_seed': 20261116, 'match_radius_pixels': 3,
              'triangle_brightest': 80, 'triangle_tolerance_pixels': 2,
              'max_hypotheses': 1000, 'max_refinements': 10}


def detect(image):
    """Return native zero-based centers, brightness order and selection counts."""
    image = np.asarray(image, dtype=float)
    if image.ndim == 3 and image.shape[0] == 3:
        invalid = np.any(~np.isfinite(image) | (image >= 65000), axis=0)
        plane = image.mean(axis=0)
    elif image.ndim == 2:
        invalid = ~np.isfinite(image) | (image >= 65000)
        plane = image
    else:
        raise ValueError('Image 2D ou cube de trois plans requis.')
    height, width = plane.shape
    h, w = height // 2, width // 2
    if min(h, w) < 16:
        raise ValueError('Image trop petite.')
    reduced = plane[:2*h, :2*w].reshape(h, 2, w, 2).mean(axis=(1, 3))
    mask = invalid[:2*h, :2*w].reshape(h, 2, w, 2).any(axis=(1, 3))
    _, background, noise = sigma_clipped_stats(reduced, mask=mask, sigma=3, maxiters=5)
    if not np.isfinite(noise) or noise <= 0:
        raise ValueError('Bruit non mesurable.')
    finder = DAOStarFinder(threshold=5*noise, fwhm=2, min_separation=4, exclude_border=True)
    found = finder(np.where(mask, background, reduced)-background, mask=mask)
    if found is None:
        raise ValueError('Aucune étoile détectée.')
    xy = 2*np.column_stack([found['x_centroid'], found['y_centroid']])+.5
    flux = np.asarray(found['flux'])
    keep = np.isfinite(xy).all(axis=1) & np.isfinite(flux)
    keep &= (xy[:, 0] >= 10) & (xy[:, 0] < width-10) & (xy[:, 1] >= 10) & (xy[:, 1] < height-10)
    xy, flux = xy[keep], flux[keep]
    if len(xy) < 3:
        raise ValueError('Trop peu de détections.')
    distances, _ = cKDTree(xy).query(xy, k=2)
    keep = distances[:, 1] >= 8
    xy, flux = xy[keep], flux[keep]
    order = np.argsort(-flux, kind='stable')
    return xy[order], {'detected': len(found), 'selected': len(xy),
                       'masked_native_pixels': int(invalid.sum()),
                       'shape': [height, width], 'background_binned': float(background),
                       'noise_binned': float(noise)}


def rigid_fit(source, target):
    """Column-vector convention: target = R @ source + t; determinant +1."""
    a, b = source.mean(axis=0), target.mean(axis=0)
    left, _, right = np.linalg.svd((source-a).T @ (target-b))
    rotation = right.T @ np.diag([1., np.linalg.det(right.T @ left.T)]) @ left.T
    return rotation, b-rotation@a


def triangles(points):
    ids = np.asarray(list(combinations(range(min(len(points), 80)), 3)), dtype=int)
    if not len(ids):
        raise ValueError('Pas assez de points pour les triangles.')
    p = points[ids]
    sides = np.linalg.norm(p[:, [1, 2, 0]]-p[:, [2, 0, 1]], axis=2)
    order = np.argsort(sides, axis=1)
    lengths = np.take_along_axis(sides, order, axis=1)
    canonical = np.take_along_axis(ids, order, axis=1)
    q = points[canonical]
    cross = (q[:, 1, 0]-q[:, 0, 0])*(q[:, 2, 1]-q[:, 0, 1])-(q[:, 1, 1]-q[:, 0, 1])*(q[:, 2, 0]-q[:, 0, 0])
    keep = (lengths[:, 0] > 20) & (np.diff(lengths, axis=1).min(axis=1) > 3) & (abs(cross) > 100)
    return lengths[keep], canonical[keep], np.sign(cross[keep])


def mutual(source, target, rotation, translation):
    mapped = source @ rotation.T + translation
    distance, index = cKDTree(target).query(mapped)
    _, reverse = cKDTree(mapped).query(target)
    keep = (distance <= 3) & (reverse[index] == np.arange(len(source)))
    chosen = np.flatnonzero(keep)
    return chosen, index[chosen]


def solve(training, reference):
    a, ai, sign_a = triangles(training)
    b, bi, sign_b = triangles(reference)
    if not len(a) or not len(b):
        raise ValueError('Aucun triangle utilisable.')
    distance, index = cKDTree(b).query(a)
    candidate = np.flatnonzero((distance <= 2) & (sign_a == sign_b[index]))
    candidate = candidate[np.argsort(distance[candidate], kind='stable')[:1000]]
    tree = cKDTree(reference)
    best = None
    best_score = (-1, -float('inf'))
    for i in candidate:
        rotation, translation = rigid_fit(training[ai[i]], reference[bi[index[i]]])
        d, _ = tree.query(training @ rotation.T+translation)
        close = d <= 3
        score = (int(close.sum()), -float(np.median(d[close])) if close.any() else -float('inf'))
        if score > best_score:
            best_score, best = score, (rotation, translation)
    if best is None:
        raise ValueError('Aucune hypothèse de rotation/translation.')
    rotation, translation = best
    previous = None
    for _ in range(10):
        i, j = mutual(training, reference, rotation, translation)
        if len(i) < 3:
            raise ValueError('Hypothèse sans assez d’associations uniques.')
        pairs = tuple(zip(i.tolist(), j.tolist()))
        rotation, translation = rigid_fit(training[i], reference[j])
        if pairs == previous:
            break
        previous = pairs
    return rotation, translation, len(candidate)


def metrics(points, residuals, shape):
    h, w = shape
    n = len(points)
    r = np.linalg.norm(residuals, axis=1)
    cells = len(set(map(tuple, np.floor(points*[3/w, 3/h]).astype(int)))) if n else 0
    quadrants = len(set(map(tuple, points >= [w/2, h/2]))) if n else 0
    return {'matches': n, 'median_pixels': float(np.median(r)) if n else None,
            'p95_pixels': float(np.percentile(r, 95)) if n else None,
            'rms_pixels': float(np.sqrt(np.mean(r*r))) if n else None,
            'grid_cells_occupied': cells, 'quadrants_occupied': quadrants}


def register_points(points, reference, shape):
    if len(points) < 4 or len(reference) < 3:
        raise ValueError('Effectif insuffisant pour séparer et ajuster.')
    # The split precedes triangle generation, matching, hypothesis scoring and fitting.
    permutation = np.random.default_rng(20261116).permutation(len(points))
    control_ids = np.sort(permutation[:max(1, len(points)//4)])
    train_ids = np.setdiff1d(np.arange(len(points)), control_ids)
    rotation, translation, hypotheses = solve(points[train_ids], reference)
    rows, statistics = [], {}
    for label, ids in [('training', train_ids), ('control', control_ids)]:
        i, j = mutual(points[ids], reference, rotation, translation)
        chosen = ids[i]
        residual = points[chosen] @ rotation.T+translation-reference[j]
        statistics[label] = metrics(points[chosen], residual, shape)
        for k, p in enumerate(chosen):
            rows.append({'split': label, 'detection_index': int(p), 'reference_index': int(j[k]),
                         'x': float(points[p, 0]), 'y': float(points[p, 1]),
                         'reference_x': float(reference[j[k], 0]), 'reference_y': float(reference[j[k], 1]),
                         'dx_pixels': float(residual[k, 0]), 'dy_pixels': float(residual[k, 1])})
    t, c = statistics['training'], statistics['control']
    passed = (t['matches'] >= 20 and c['matches'] >= 10 and c['median_pixels'] <= .75 and
              c['p95_pixels'] <= 1.5 and c['grid_cells_occupied'] >= 6 and c['quadrants_occupied'] == 4)
    return {'rotation_matrix': rotation.tolist(), 'translation_pixels': translation.tolist(),
            'rotation_degrees': float(np.rad2deg(np.arctan2(rotation[1, 0], rotation[0, 0]))),
            'metrics': statistics, 'criteria_passed': bool(passed), 'pairs': rows,
            'control_detection_indices': control_ids.tolist(), 'training_detection_indices': train_ids.tolist(),
            'selection_counts': {'training_detections': len(train_ids), 'control_detections': len(control_ids),
                                 'unmatched_training': len(train_ids)-t['matches'],
                                 'unmatched_control': len(control_ids)-c['matches']},
            'hypotheses_scored': hypotheses, 'criteria': CRITERIA, 'parameters': PARAMETERS,
            'image_shape': list(shape), 'model_usable': bool(passed),
            'clock_qualified': False, 'scientific_submission_certified': False}


def composed_sky(result, x, y):
    """Use only an accepted composition, on the overlap of the two images."""
    if not result.get('model_usable'):
        raise ValueError('Modèle refusé : critères non satisfaits.')
    x, y = np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    points = np.stack([x, y], axis=-1)
    h, w = result['image_shape']
    mapped = points @ np.asarray(result['rotation_matrix']).T + result['translation_pixels']
    rh, rw = result['reference_shape']
    if (not np.isfinite(points).all() or np.any(points < 0) or np.any(points >= [w, h]) or
            np.any(mapped < 0) or np.any(mapped >= [rw, rh])):
        raise ValueError('Position hors du domaine de recouvrement.')
    header = fits.Header.fromstring(result['reference_wcs_header'], sep='\n')
    return WCS(header, naxis=2, fix=False).pixel_to_world(mapped[..., 0], mapped[..., 1])


def run_registration(workset_path, reference_index, frame_indices, output, base):
    wp, output = local_path(workset_path, base), local_path(output, base)
    if output.exists():
        raise ValueError('La sortie existe déjà.')
    raw = wp.read_bytes()
    workset = json.loads(raw)
    indices = [reference_index, *frame_indices]
    if (not isinstance(workset, dict) or not workset.get('success') or not isinstance(workset.get('files'), list)):
        raise ValueError('Lot local complet requis.')
    if (not frame_indices or any(not isinstance(i, int) for i in indices) or len(set(indices)) != len(indices) or
            any(i < 1 or i > len(workset['files']) for i in indices)):
        raise ValueError('Lot ou indices incorrects/dupliqués.')
    paths, hashes = {}, {}
    for i in indices:
        item = workset['files'][i-1]
        if (not isinstance(item, dict) or not isinstance(item.get('local_copy'), str) or
                not isinstance(item.get('sha256_copy'), str)):
            raise ValueError('Chemin de copie et empreinte requis.')
        path = local_path(wp.parent/item['local_copy'], base)
        if wp.parent.resolve() not in path.parents:
            raise ValueError('Copie hors du lot.')
        hashes[i] = digest(path)
        if hashes[i] != item['sha256_copy']:
            raise ValueError('Empreinte de copie incorrecte.')
        paths[i] = path
    with fits.open(paths[reference_index], mode='readonly', memmap=False) as hdus:
        wcs = WCS(hdus[0].header, fobj=hdus, naxis=2, fix=False)
        if not wcs.has_celestial or any(getattr(wcs, k) is not None for k in ['cpdis1', 'cpdis2', 'det2im1', 'det2im2']):
            raise ValueError('WCS céleste sérialisable (linéaire/SIP) requise.')
        header = wcs.to_header(relax=True).tostring(sep='\n', endcard=True, padding=False)
        reference, ref_detection = detect(hdus[0].data)
    results = []
    for i in frame_indices:
        try:
            with fits.open(paths[i], mode='readonly', memmap=False) as hdus:
                points, selection = detect(hdus[0].data)
            result = register_points(points, reference, selection['shape'])
            result.update(detection=selection, reference_shape=ref_detection['shape'], reference_wcs_header=header,
                          model_kind='rigid_pixels_then_frozen_reference_wcs', reference_wcs_refitted=False)
        except ValueError as exc:
            result = {'criteria_passed': False, 'model_usable': False, 'error': str(exc),
                      'clock_qualified': False, 'scientific_submission_certified': False}
        result['file_index'] = i
        results.append(result)
    for i, path in paths.items():
        if digest(path) != hashes[i]:
            raise ValueError('Une copie a changé pendant le recalage.')
    document = {'schema_version': '1.0', 'reference_index': reference_index, 'frames': results,
                'reference_detection': ref_detection, 'workset_sha256': hashlib.sha256(raw).hexdigest(),
                'copies_sha256_before': hashes, 'copies_sha256_after': hashes.copy(),
                'all_criteria_passed': all(r['criteria_passed'] for r in results),
                'criteria': CRITERIA, 'parameters': PARAMETERS, 'offline': True,
                'reference_independence_established': False, 'absolute_error_budget_complete': False}
    output.mkdir(parents=True, exist_ok=False)
    (output/'registration.json').write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    with (output/'matches.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['file_index', 'split', 'detection_index', 'reference_index', 'x', 'y',
                  'reference_x', 'reference_y', 'dx_pixels', 'dy_pixels']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in results:
            for row in result.get('pairs', []):
                writer.writerow({'file_index': result['file_index'], **row})
    (output/'registration.svg').write_text(registration_svg(document), encoding='utf-8')
    text = '# Recalage relatif exploratoire\n\n'
    for result in results:
        text += f"## Pose {result['file_index']}\n\n```json\n"+json.dumps(result.get('metrics', {'error': result.get('error')}), ensure_ascii=False, indent=2)+'\n```\n\n'
    text += ('![Contrôle réservé](registration.svg)\n\nRotation et translation uniquement. Les étoiles réservées ne servent jamais au modèle. '
             'Les associations à 3 pixels sélectionnent néanmoins les résidus observables. Aucune WCS FITS copiée/exportée. '
             'La composition hérite des erreurs de la référence ; indépendance et budget absolu non établis. '
             'Horloge non qualifiée, aucune certification MPC. Rapport privé : ne pas publier.\n')
    (output/'report.md').write_text(text, encoding='utf-8')
    return document
