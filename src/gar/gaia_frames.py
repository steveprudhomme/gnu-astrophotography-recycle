# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Compare pre-reserved frame detections to local Gaia with frozen models."""
import csv
import json
from itertools import combinations

from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
import numpy as np

from .astrometry import local_path, prepare_references, residual_statistics
from .registration import detect, composed_sky, PARAMETERS
from .workset import digest
from .gaia_frames_reports import gaia_frames_svg


CRITERIA = {'min_matches': 20, 'match_radius_arcsec': 8., 'median_max_arcsec': 2.,
            'p95_max_arcsec': 4., 'min_grid_cells': 6, 'required_quadrants': 4}


def verify_redetection(frame, points, reference):
    """Check ordering, partition, saved centroids and transformation consistency."""
    n = len(points)
    expected = np.sort(np.random.default_rng(20261116).permutation(n)[:max(1, n//4)])
    control = frame.get('control_detection_indices')
    training = frame.get('training_detection_indices')
    if (control != expected.tolist() or training != np.setdiff1d(np.arange(n), expected).tolist() or
            frame.get('parameters') != PARAMETERS or frame.get('detection', {}).get('selected') != n):
        raise ValueError('Détections/partition incompatibles avec le recalage gelé.')
    rotation = np.asarray(frame['rotation_matrix'], dtype=float)
    translation = np.asarray(frame['translation_pixels'], dtype=float)
    if (rotation.shape != (2, 2) or translation.shape != (2,) or not np.isfinite(translation).all() or
            not np.isfinite(rotation).all() or not np.allclose(rotation.T@rotation, np.eye(2), atol=1e-10, rtol=0) or
            not np.isclose(np.linalg.det(rotation), 1., atol=1e-10, rtol=0)):
        raise ValueError('Transformation rigide incorrecte.')
    seen = set()
    for pair in frame['pairs']:
        i, j = pair['detection_index'], pair['reference_index']
        if (not isinstance(i, int) or not isinstance(j, int) or not 0 <= i < n or not 0 <= j < len(reference) or i in seen):
            raise ValueError('Indices d’association incorrects.')
        seen.add(i)
        label = 'control' if i in control else 'training'
        residual = points[i]@rotation.T+translation-reference[j]
        if (pair['split'] != label or not np.allclose(points[i], [pair['x'], pair['y']], atol=1e-7, rtol=0) or
                not np.allclose(reference[j], [pair['reference_x'], pair['reference_y']], atol=1e-7, rtol=0) or
                not np.allclose(residual, [pair['dx_pixels'], pair['dy_pixels']], atol=1e-7, rtol=0)):
            raise ValueError('Les associations enregistrées ne sont pas reproduites.')
    if len(seen) != sum(frame['metrics'][key]['matches'] for key in ['training', 'control']):
        raise ValueError('Effectifs d’association incohérents.')
    return np.asarray(control, dtype=int)


def inside(points, shape, margin=10):
    h, w = shape
    return np.isfinite(points).all(axis=1) & (points >= margin).all(axis=1) & (points < [w-margin, h-margin]).all(axis=1)


def compare_frame(points, control_ids, frame, catalog, date_obs):
    """No detector or fit here: fixed positions, fixed split, fixed model."""
    cat, coords, reference_info = prepare_references(catalog, date_obs)
    wcs = WCS(fits.Header.fromstring(frame['reference_wcs_header'], sep='\n'), naxis=2, fix=False)
    rotation = np.asarray(frame['rotation_matrix'])
    translation = np.asarray(frame['translation_pixels'])
    mapped = points@rotation.T+translation
    eligible = inside(points, frame['image_shape']) & inside(mapped, frame['reference_shape'])
    cx, cy = wcs.world_to_pixel(coords)
    reference_pixels = np.column_stack([cx, cy])
    native_pixels = (reference_pixels-translation)@rotation
    keep = inside(reference_pixels, frame['reference_shape']) & inside(native_pixels, frame['image_shape'])
    cat, coords = cat[keep], coords[keep]
    scopes = {}
    for label, ids in [('control', np.asarray(control_ids, dtype=int)), ('all_diagnostic', np.arange(len(points)))]:
        selected = ids[eligible[ids]]
        rows = []
        if len(selected) and len(cat):
            measured = composed_sky(frame, points[selected, 0], points[selected, 1]).icrs
            index, separation, _ = measured.match_to_catalog_sky(coords)
            reverse, _, _ = coords.match_to_catalog_sky(measured)
            good = (separation.arcsec <= 8) & (reverse[index] == np.arange(len(selected)))
            chosen = np.flatnonzero(good)
            east, north = coords[index[chosen]].spherical_offsets_to(measured[chosen])
            for k, j in enumerate(chosen):
                i = int(selected[j])
                rows.append({'detection_index': i, 'source_id': str(cat['source_id'][index[j]]),
                             'x': float(points[i, 0]), 'y': float(points[i, 1]),
                             'east_arcsec': float(east.arcsec[k]), 'north_arcsec': float(north.arcsec[k]),
                             'separation_arcsec': float(separation.arcsec[j])})
        x = np.array([p['x'] for p in rows]); y = np.array([p['y'] for p in rows])
        dx = np.array([p['east_arcsec'] for p in rows]); dy = np.array([p['north_arcsec'] for p in rows])
        h, w = frame['image_shape']
        statistics = residual_statistics(x, y, dx, dy, w, h, min_matches=20)
        if label == 'all_diagnostic':
            # This sample includes fit stars and cannot decide the primary verdict.
            statistics.pop('empirical_criteria_passed')
        scopes[label] = {'metrics': statistics, 'pairs': rows, 'detections_in_split': len(ids),
                         'detections_in_overlap': len(selected), 'unmatched_in_overlap': len(selected)-len(rows),
                         'detections_outside_overlap': len(ids)-len(selected)}
    return {'control': scopes['control'], 'all_diagnostic': scopes['all_diagnostic'],
            'criteria_passed': scopes['control']['metrics']['empirical_criteria_passed'],
            'reference_selection': {**reference_info, 'catalog_inside_overlap': len(cat)},
            'image_shape': frame['image_shape'], 'criteria': CRITERIA,
            'model_refitted': False, 'bias_subtracted': False, 'residuals_clipped': False,
            'clock_qualified': False, 'scientific_submission_certified': False}


def run_gaia_frames(workset_path, registration_path, catalog_path, output, base):
    wp, rp, cp, output = [local_path(path, base) for path in [workset_path, registration_path, catalog_path, output]]
    if output.exists():
        raise ValueError('La sortie existe déjà.')
    provenance_path = local_path(cp.parent/'provenance.json', base)
    inputs = {'workset': wp, 'registration': rp, 'catalog': cp, 'catalog_provenance': provenance_path}
    hashes = {key: digest(path) for key, path in inputs.items()}
    workset = json.loads(wp.read_text(encoding='utf-8'))
    registration = json.loads(rp.read_text(encoding='utf-8'))
    provenance = json.loads(provenance_path.read_text(encoding='utf-8'))
    if (not isinstance(workset, dict) or not workset.get('success') or not isinstance(workset.get('files'), list) or
            not isinstance(registration, dict) or registration.get('schema_version') != '1.0' or
            registration.get('workset_sha256') != hashes['workset'] or registration.get('parameters') != PARAMETERS or
            not isinstance(registration.get('frames'), list) or not registration['frames'] or
            any(not isinstance(f, dict) for f in registration['frames']) or
            any(not isinstance(registration.get(key), dict) for key in ['copies_sha256_before', 'copies_sha256_after'])):
        raise ValueError('Workset ou provenance du recalage incompatibles.')
    if not isinstance(provenance, dict) or provenance.get('sha256') != hashes['catalog']:
        raise ValueError('Provenance du catalogue incorrecte.')
    indices = [registration.get('reference_index'), *[f.get('file_index') for f in registration['frames']]]
    if (any(type(i) is not int or not 1 <= i <= len(workset['files']) for i in indices) or len(set(indices)) != len(indices)):
        raise ValueError('Indices de recalage incorrects ou dupliqués.')
    for i in indices:
        item = workset['files'][i-1]
        if not isinstance(item, dict) or not isinstance(item.get('local_copy'), str):
            raise ValueError('Copie locale requise.')
        path = local_path(wp.parent/item['local_copy'], base)
        if wp.parent.resolve() not in path.parents:
            raise ValueError('Copie hors du lot.')
        value = digest(path)
        if (value != item.get('sha256_copy') or value != registration.get('copies_sha256_before', {}).get(str(i)) or
                value != registration.get('copies_sha256_after', {}).get(str(i))):
            raise ValueError('Empreinte de copie incompatible avec le recalage.')
        inputs[f'copy_{i}'] = path
        hashes[f'copy_{i}'] = value
    catalog = Table.read(cp, format='ascii.csv')
    if len(catalog) >= 20000:
        raise ValueError('Catalogue possiblement tronqué.')
    with fits.open(inputs[f'copy_{indices[0]}'], mode='readonly', memmap=False) as hdus:
        wcs = WCS(hdus[0].header, fobj=hdus, naxis=2, fix=False)
        expected_header = wcs.to_header(relax=True).tostring(sep='\n', endcard=True, padding=False)
        reference, ref_selection = detect(hdus[0].data)
    if ref_selection != registration.get('reference_detection'):
        raise ValueError('La détection de référence a changé.')
    results = []
    for frame in registration['frames']:
        i = frame['file_index']
        if not frame.get('criteria_passed') or not frame.get('model_usable'):
            results.append({'file_index': i, 'criteria_passed': False, 'error': 'Recalage préalable refusé.'})
            continue
        if frame.get('reference_wcs_header') != expected_header or frame.get('reference_shape') != ref_selection['shape']:
            raise ValueError('WCS/forme de référence incompatible avec la copie.')
        with fits.open(inputs[f'copy_{i}'], mode='readonly', memmap=False) as hdus:
            points, selection = detect(hdus[0].data)
            date_obs = hdus[0].header.get('DATE-OBS')
        if selection != frame.get('detection') or selection['shape'] != frame.get('image_shape'):
            raise ValueError('La sélection des détections a changé.')
        control = verify_redetection(frame, points, reference)
        result = compare_frame(points, control, frame, catalog, date_obs)
        result['file_index'] = i
        results.append(result)
    shared = []
    for a, b in combinations(results, 2):
        ids_a = {p['source_id'] for p in a.get('control', {}).get('pairs', [])}
        ids_b = {p['source_id'] for p in b.get('control', {}).get('pairs', [])}
        shared.append({'frame_indices': [a['file_index'], b['file_index']], 'shared_control_source_ids': sorted(ids_a & ids_b),
                       'shared_control_count': len(ids_a & ids_b)})
    for key, path in inputs.items():
        if digest(path) != hashes[key]:
            raise ValueError('Une entrée a changé pendant la comparaison.')
    document = {'schema_version': '1.0', 'frames': results, 'criteria': CRITERIA,
                'parameters': {'detection': PARAMETERS, 'magnitude_g_range': [9, 17.5], 'ruwe_max_exclusive': 1.4,
                               'isolation_arcsec': 16, 'margin_pixels': 10, 'bootstrap_seed': 20261116, 'bootstrap_replicates': 500},
                'inputs_sha256_before': hashes, 'inputs_sha256_after': hashes.copy(),
                'catalog_provenance': provenance, 'registration_source_revision': registration.get('source_revision'),
                'shared_control_references': shared, 'all_criteria_passed': all(r['criteria_passed'] for r in results),
                'offline': True, 'primary_sample': 'pre_registration_reserved_detections',
                'reference_independence_established': False, 'absolute_error_budget_complete': False,
                'model_refitted': False, 'clock_qualified': False, 'scientific_submission_certified': False}
    output.mkdir(parents=True, exist_ok=False)
    (output/'gaia-frames.json').write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    with (output/'matches.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['file_index', 'sample', 'detection_index', 'source_id', 'x', 'y', 'east_arcsec', 'north_arcsec', 'separation_arcsec']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in results:
            for sample in ['control', 'all_diagnostic']:
                for pair in result.get(sample, {}).get('pairs', []):
                    row = dict(pair)
                    if row['source_id'].lstrip().startswith(('=', '+', '-', '@')):
                        row['source_id'] = "'"+row['source_id']
                    writer.writerow({'file_index': result['file_index'], 'sample': sample, **row})
    (output/'gaia-frames.svg').write_text(gaia_frames_svg(document), encoding='utf-8')
    text = '# Comparaison Gaia des poses — modèles gelés\n\n'
    for result in results:
        text += f"## Pose {result['file_index']}\n\n```json\n"+json.dumps(result.get('control', {'error': result.get('error')}).get('metrics', {'error': result.get('error')}), ensure_ascii=False, indent=2)+'\n```\n\n'
    text += ('![Contrôles Gaia réservés](gaia-frames.svg)\n\nVerdict : étoiles réservées avant recalage uniquement ; '
             'le bilan toutes détections inclut les étoiles d’ajustement et reste secondaire. Rayon de sélection 8″ ; aucun réajustement, '
             'biais soustrait ou écrêtage après association. Références partagées et erreurs héritées : pas d’indépendance statistique démontrée. '
             'Bootstrap conditionnel, budget absolu incomplet, horloge non qualifiée et aucune certification MPC. Données privées : ne pas publier.\n')
    (output/'report.md').write_text(text, encoding='utf-8')
    return document
