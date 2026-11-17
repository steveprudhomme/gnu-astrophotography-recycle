# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Experimental intensity-only tracks in verified local copies; never opens archives."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess

from astropy.io import fits
import numpy as np

from gar.astrometry import local_path
from gar.contracts import parse_declared_time
from gar.moving import detect_sources, remove_stationary, find_tracks, PARAMETERS as MOVING_PARAMETERS
from gar.registration import detect, CRITERIA
from gar.workset import digest
from moving_registration import verify_engine
from prepare_seestar_series import audit_series
from spatial_controls import register_spatial

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = '8f5a64b819d301f7c495b5e9903f3c622cf30639'
SPATIAL_HASH = '92655f59af687fb0802f30f4b08f866ddb28e34dcaf4508754576b41132f6617'
BAYER = ('GRBG', 'RGGB', 'GBRG', 'BGGR')


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def frozen():
    hashes = verify_engine()
    value = hashlib.sha256((ROOT/'examples/spatial_controls.py').read_text(encoding='utf-8').encode()).hexdigest()
    if value != SPATIAL_HASH:
        raise ValueError('Partition spatiale modifiée : nouveau protocole requis.')
    return dict(hashes, **{'examples/spatial_controls.py': value})


def intensity_plane(image):
    image = np.asarray(image, dtype=float)
    if image.ndim != 2 or min(image.shape) < 64 or any(n % 2 for n in image.shape):
        raise ValueError('Primaire 2D de dimensions paires, au moins 64×64, requise.')
    h, w = image.shape
    blocks = image.reshape(h//2, 2, w//2, 2)
    masked = (~np.isfinite(blocks) | (blocks >= 65000)).any(axis=(1, 3))
    plane = blocks.mean(axis=(1, 3))
    plane[masked] = np.nan
    return plane


def to_reference(points, model):
    return np.asarray(points).reshape(-1, 2) @ np.asarray(model['rotation_matrix']).T + model['translation_pixels']


def from_reference(points, model):
    return (np.asarray(points).reshape(-1, 2)-model['translation_pixels']) @ np.asarray(model['rotation_matrix'])


def common_points(points, models, shape):
    """Intersection of every inverse field, not merely the reference rectangle."""
    h, w = shape
    mapped, excluded = [], []
    for detections, model in zip(points, models):
        q = to_reference(detections, model)
        keep = np.isfinite(q).all(axis=1)
        for other in models:
            p = from_reference(q, other)
            keep &= (p >= 16).all(axis=1) & (p < [w-16, h-16]).all(axis=1)
        mapped.append(q[keep]); excluded.append(int((~keep).sum()))
    return mapped, excluded


def declared_tracks(points, times):
    remaining, removed = remove_stationary(points)
    legacy, hypotheses = find_tracks(remaining, times)
    tracks = []
    for original in legacy:
        track = dict(original)
        track['epoch_relative_declared_seconds'] = track.pop('epoch_relative_seconds')
        track['velocity_native_pixels_per_declared_second'] = track.pop('velocity_pixels_per_second')
        track['span_declared_seconds'] = track.pop('span_seconds_fictitious')
        track['review_status'] = 'unreviewed_not_a_discovery'
        tracks.append(track)
    return dict(tracks=tracks, hypotheses=hypotheses, stationary_removed_per_frame=removed,
                residual_detections=[p.tolist() for p in remaining])


def write_report(output, result):
    save(output/'pilot.json', result)
    with (output/'candidates.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['candidate_id', 'frame_index', 'detection_index', 'x', 'y', 'review_status']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for track in (result.get('search') or {}).get('tracks', []):
            for point in track['points']:
                writer.writerow(dict(candidate_id=track['candidate_id'], **point, review_status=track['review_status']))
    text = '# Pilote exploratoire local — rapport privé\n\n'
    text += f"État : {result['status']}. Recherche : {result['search_status']}. Candidats : {result['candidate_count']}.\n\n"
    text += '| Pose | Modèle utilisable | Ajustement | Contrôle | P95 contrôle (pixel natif) |\n|---|---|---|---|---|\n'
    for i, model in enumerate(result['models'], 1):
        stats = model.get('metrics', {})
        text += f"| {i} | {model['model_usable']} | {stats.get('training', {}).get('matches', 'référence')} | {stats.get('control', {}).get('matches', 'référence')} | {stats.get('control', {}).get('p95_pixels', '')} |\n"
    text += ('\nLa première pose est la référence relative, sans preuve absolue. Un modèle refusé bloque toute la recherche. '
             'Les associations à trois pixels conditionnent les résidus de contrôle observés. '
             'Moyenne 2×2 sans calibration couleur/photométrique. Temps et vitesses selon les en-têtes déclarés, horloge non qualifiée. '
             'Zéro candidat ne prouve pas absence de mobile. Une candidature reste à revoir, sans identité astronomique confirmée. '
             'FITS inchangés ; aucun accès au support source ni catalogue réseau. Rapport privé, ne pas publier.\n')
    if result.get('blocked_reasons'):
        text += '\nMotifs : '+json.dumps(result['blocked_reasons'], ensure_ascii=False)+'\n'
    (output/'report.md').write_text(text, encoding='utf-8')


def run(plan_path, workset_path, audit_path, output, base=None, pixel_mode='bayer'):
    base = ROOT/'local' if base is None else base
    pp, wp, ap, output = [local_path(p, base) for p in (plan_path, workset_path, audit_path, output)]
    if pixel_mode not in ('bayer', 'mono'):
        raise ValueError('Choisir explicitement bayer ou mono.')
    if output.exists():
        raise ValueError('Choisir un nouveau dossier local de résultats.')
    engines = frozen()
    watched = {p: digest(p) for p in (pp, wp, ap)}
    supplied = json.loads(ap.read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=False)
    result = dict(seestar_pilot_schema_version='1.0', plan_commit=PLAN_COMMIT, status='running',
                  phase='input_audit', search_status='unavailable', motion_searched=False,
                  candidate_count=None, models=[], star_detections=[], star_selection=[],
                  raw_detections=[], motion_selection=[], blocked_reasons=[], search=None,
                  pixel_mode=pixel_mode, pixel_processing='2x2_mean_intensity_not_colour_calibrated',
                  clock_qualified=False, scientific_submission_certified=False,
                  real_data_performance_validated=False, pixels_rewritten=False,
                  source_files_opened=False, frozen_sha256_lf=engines, registration_criteria=CRITERIA,
                  motion_detection_parameters_reduced_pixels={k: MOVING_PARAMETERS[k] for k in (
                      'threshold_sigma', 'fwhm_pixels', 'margin_pixels', 'minimum_separation_pixels', 'saturation_adu')},
                  association_parameters_native_declared_seconds={k: v for k, v in MOVING_PARAMETERS.items() if k not in (
                      'threshold_sigma', 'fwhm_pixels', 'margin_pixels', 'minimum_separation_pixels', 'saturation_adu')},
                  common_field_margin_native_pixels=16)
    save(output/'pilot.json', result)
    try:
        # Revalidate the copies and headers; never trust a copied status flag alone.
        checked = audit_series(pp, wp, output/'inputs-audit', base=base)
        if not checked['copies_prepared'] or checked != supplied:
            raise ValueError('Audit fourni différent du nouvel audit local ou copies non préparées.')
        flags = [f['synthetic_marker_present'] for f in checked['files']]
        if any(flags) != all(flags):
            raise ValueError('Mélange de fichiers fictifs et réels refusé.')
        result['input_kind'] = 'synthetic_demo' if all(flags) else 'real_local_copies'
        if len({f['declared_time_scale'] for f in checked['files']}) != 1:
            raise ValueError('Déclarations d’échelle de temps incompatibles.')
        times = [parse_declared_time(f['date_obs_raw']) for f in checked['files']]
        times = np.array([(t-times[0]).total_seconds() for t in times])
        result['relative_declared_seconds'] = times.tolist()
        result['copies'] = [dict(local_copy=f['local_copy'], sha256=f['sha256']) for f in checked['files']]
        stars, detections = [], []
        shape = None
        for k, item in enumerate(checked['files']):
            path = local_path(item['local_copy'], base)
            watched[path] = item['sha256']
            pattern = item['metadata']['BAYERPAT']
            if ((pixel_mode == 'bayer' and pattern not in BAYER) or
                    (pixel_mode == 'mono' and pattern not in (None, ''))):
                raise ValueError('Déclaration Bayer incompatible avec la voie explicitement choisie.')
            with fits.open(path, mode='readonly', memmap=False) as hdus:
                image = np.asarray(hdus[0].data, dtype=float)
                plane = intensity_plane(image)
                shape = list(image.shape)
                try:
                    points, selection = detect(image)
                    stars.append(points); result['star_selection'].append(selection)
                except ValueError as exc:
                    stars.append(None); result['star_selection'].append(dict(error=str(exc)))
                try:
                    points, selection = detect_sources(plane)
                    detections.append(2*points+.5)
                    result['motion_selection'].append(dict(selection, masked_reduced_pixels=int(np.isnan(plane).sum())))
                except ValueError as exc:
                    detections.append(None); result['motion_selection'].append(dict(error=str(exc)))
                    result['blocked_reasons'].append(dict(frame_index=k, stage='motion_detection', error=str(exc)))
            result['phase'] = f'detection_{k+1}'
            save(output/'pilot.json', result)
        result['image_shape'] = shape
        result['star_detections'] = [p.tolist() if p is not None else None for p in stars]
        result['raw_detections'] = [p.tolist() if p is not None else None for p in detections]
        reference = stars[0]
        result['models'].append(dict(kind='measured_reference_identity', model_usable=reference is not None,
                                     rotation_matrix=np.eye(2).tolist(), translation_pixels=[0., 0.],
                                     independent_control=False))
        for k, points in enumerate(stars[1:], 1):
            try:
                if points is None or reference is None:
                    raise ValueError('Détection stellaire indisponible.')
                model = register_spatial(points, reference, shape)
                model['kind'] = 'estimated_rigid_native_coordinates'
            except ValueError as exc:
                model = dict(model_usable=False, error=str(exc))
            result['models'].append(model)
            if not model['model_usable']:
                result['blocked_reasons'].append(dict(frame_index=k, stage='registration', error=model.get('error', 'criteria_failed')))
            result['phase'] = f'registration_{k+1}'
            save(output/'pilot.json', result)
        result['registration_available'] = all(m['model_usable'] for m in result['models'])
        if not result['blocked_reasons'] and result['registration_available']:
            mapped, excluded = common_points(detections, result['models'], shape)
            result['mapped_detections'] = [p.tolist() for p in mapped]
            result['overlap_excluded_per_frame'] = excluded
            try:
                result['search'] = declared_tracks(mapped, times)
                result.update(motion_searched=True, search_status='complete', candidate_count=len(result['search']['tracks']))
            except ValueError as exc:
                result['blocked_reasons'].append(dict(stage='association', error=str(exc)))
        if not result['motion_searched']:
            result['search_status'] = 'blocked'
        if any(digest(p) != value for p, value in watched.items()) or frozen() != engines:
            raise ValueError('Une entrée ou un moteur a changé pendant le pilote.')
        result.update(status='complete', phase='finished', input_hashes_unchanged=True,
                      inputs_sha256_before={str(p): h for p, h in watched.items()},
                      inputs_sha256_after={str(p): h for p, h in watched.items()})
        result['code_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
        result['tracked_tree_clean'] = not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip()
        write_report(output, result)
    except Exception as exc:
        result.update(status='incomplete', phase='error', search_status='unavailable',
                      motion_searched=False, candidate_count=None, search=None, error=str(exc))
        save(output/'pilot.json', result)
        raise
    print(f"Pilote local terminé ; recherche : {result['search_status']}, candidats : {result['candidate_count']}. Horloge non qualifiée.", flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('plan', 'workset', 'audit'):
        parser.add_argument(field, type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pixel-mode', choices=['bayer', 'mono'], default='bayer')
    args = parser.parse_args()
    try:
        r = run(args.plan, args.workset, args.audit, args.output, pixel_mode=args.pixel_mode)
        raise SystemExit(0 if r['motion_searched'] else 2)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
