# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Experimental linear tracks in declared synthetic, pre-aligned image sequences."""
import json
import math
import warnings
import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from .astrometry import local_path
from .workset import digest
from .moving_reports import write_moving_reports

PARAMETERS = {'threshold_sigma': 5., 'fwhm_pixels': 3., 'margin_pixels': 8,
              'minimum_separation_pixels': 5, 'saturation_adu': 65000,
              'stationary_radius_pixels': 2., 'stationary_fraction': .5,
              'speed_min_pixels_per_second': .1, 'speed_max_pixels_per_second': 1.5,
              'association_radius_pixels': 1.5, 'minimum_frames': 5, 'minimum_span_seconds': 40.,
              'rms_max_pixels': .75, 'p95_max_pixels': 1.5, 'max_hypotheses': 100000}


def finite_number(value):
    try: return type(value) in (int, float) and math.isfinite(value)
    except OverflowError: return False


def detect_sources(image):
    plane = np.asarray(image, dtype=float)
    if plane.ndim != 2 or min(plane.shape) < 32: raise ValueError('Image 2D synthétique requise.')
    mask = ~np.isfinite(plane) | (plane >= 65000)
    _, background, noise = sigma_clipped_stats(plane, mask=mask, sigma=3, maxiters=5)
    if not np.isfinite(noise) or noise <= 0: raise ValueError('Bruit synthétique non mesurable.')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        found = DAOStarFinder(threshold=5*noise, fwhm=3, min_separation=5, exclude_border=True)(
            np.where(mask, background, plane)-background, mask=mask)
    xy = np.empty((0, 2)) if found is None else np.column_stack([found['x_centroid'], found['y_centroid']])
    h, w = plane.shape
    keep = np.isfinite(xy).all(axis=1) & (xy >= 8).all(axis=1) & (xy < [w-8, h-8]).all(axis=1)
    xy = xy[keep]
    if len(xy) > 500: raise ValueError('Plus de 500 sources par image : hors limites du prototype.')
    return xy, {'selected': len(xy), 'background': float(background), 'noise_sigma': float(noise),
                'warnings': [str(v.message) for v in caught]}


def remove_stationary(detections):
    trees = [cKDTree(p) if len(p) else None for p in detections]
    result, counts = [], []
    for points in detections:
        support = np.zeros(len(points), dtype=int)
        for tree in trees:
            if tree is not None: support += tree.query(points)[0] <= 2
        keep = support < math.ceil(len(detections)*.5)
        result.append(points[keep]); counts.append(int((~keep).sum()))
    return result, counts


def fit_track(points, times):
    epoch = float(times[0]); design = np.column_stack([np.ones(len(times)), times-epoch])
    coefficients = np.linalg.lstsq(design, points, rcond=None)[0]
    residual = np.linalg.norm(points-design@coefficients, axis=1)
    return epoch, coefficients, residual


def find_tracks(detections, times):
    """No truth argument: hypotheses depend only on measured positions and fake times."""
    times = np.asarray(times, dtype=float)
    if len(detections) != len(times) or len(times) < 5 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError('Au moins cinq temps relatifs strictement croissants requis.')
    trees = [cKDTree(p) if len(p) else None for p in detections]
    hypotheses, candidates = 0, {}
    def associate(epoch, offset, velocity):
        rows = []
        for k, tree in enumerate(trees):
            if tree is not None:
                d, j = tree.query(offset+(times[k]-epoch)*velocity)
                if d <= 1.5: rows.append((k, int(j)))
        return rows
    for a in range(len(times)):
        for b in range(a+1, min(a+3, len(times))):
            for p in detections[a]:
                for q in detections[b]:
                    velocity = (q-p)/(times[b]-times[a]); speed = np.linalg.norm(velocity)
                    if not .1 <= speed <= 1.5: continue
                    hypotheses += 1
                    if hypotheses > 100000: raise ValueError('Trop d’hypothèses : analyse arrêtée sans troncature silencieuse.')
                    rows = associate(times[a], p, velocity)
                    if len(rows) < 5: continue
                    xy = np.array([detections[k][j] for k, j in rows]); t = np.array([times[k] for k, _ in rows])
                    epoch, coefficients, _ = fit_track(xy, t)
                    rows = associate(epoch, coefficients[0], coefficients[1])
                    if len(rows) < 5: continue
                    xy = np.array([detections[k][j] for k, j in rows]); t = np.array([times[k] for k, _ in rows])
                    epoch, coefficients, residual = fit_track(xy, t)
                    rms = float(np.sqrt(np.mean(residual**2))); p95 = float(np.percentile(residual, 95))
                    if t[-1]-t[0] < 40 or not .1 <= np.linalg.norm(coefficients[1]) <= 1.5 or rms > .75 or p95 > 1.5: continue
                    key = tuple(rows)
                    candidates[key] = {'epoch_relative_seconds': epoch, 'position_at_epoch_pixels': coefficients[0].tolist(),
                        'velocity_pixels_per_second': coefficients[1].tolist(), 'rms_pixels': rms, 'p95_pixels': p95,
                        'span_seconds_fictitious': float(t[-1]-t[0]),
                        'points': [{'frame_index': k, 'detection_index': j, 'x': float(detections[k][j, 0]),
                                    'y': float(detections[k][j, 1])} for k, j in rows]}
    chosen, used = [], []
    for key, track in sorted(candidates.items(), key=lambda item: (-len(item[0]), item[1]['rms_pixels'], item[0])):
        identities = set(key)
        if any(len(identities & old) >= 3 for old in used): continue
        track['candidate_id'] = len(chosen)+1; chosen.append(track); used.append(identities)
    return chosen, hypotheses


def evaluate_tracks(tracks, injections):
    """Post hoc one-to-one scoring; does not modify the frozen candidates."""
    costs = np.full((len(tracks), len(injections)), 1e6); details = {}
    for i, track in enumerate(tracks):
        measured = {p['frame_index']: np.array([p['x'], p['y']]) for p in track['points']}
        for j, injection in enumerate(injections):
            true = {p['frame_index']: np.array([p['x'], p['y']]) for p in injection['positions'] if p['visible']}
            common = sorted(set(measured) & set(true))
            if len(common) < 5: continue
            errors = [float(np.linalg.norm(measured[k]-true[k])) for k in common]
            rms = float(np.sqrt(np.mean(np.square(errors))))
            velocity_error = float(np.linalg.norm(np.asarray(track['velocity_pixels_per_second'])-injection['velocity_pixels_per_second']))
            if rms <= 1 and velocity_error <= .05:
                costs[i, j] = rms; details[i, j] = (errors, velocity_error)
    matches = []
    if costs.size:
        ii, jj = linear_sum_assignment(costs)
        for i, j in zip(ii, jj):
            if costs[i, j] < 1e6:
                errors, velocity_error = details[i, j]
                matches.append({'candidate_id': tracks[i]['candidate_id'], 'injection_id': injections[j]['injection_id'],
                                'position_errors_pixels': errors, 'position_p95_pixels': float(np.percentile(errors, 95)),
                                'velocity_vector_error_pixels_per_second': velocity_error})
    recovered = {p['injection_id'] for p in matches}
    return {'injected': len(injections), 'recovered': len(matches), 'missed': len(injections)-len(matches),
            'missed_injection_ids': [t['injection_id'] for t in injections if t['injection_id'] not in recovered],
            'false_candidates': len(tracks)-len(matches), 'recall': len(matches)/len(injections) if injections else None,
            'matches': matches}


def summarize_benchmark(sequences):
    nominal = [s for s in sequences if s['scenario'] == 'nominal']
    gaps = [s for s in sequences if s['scenario'] == 'missing']
    controls = [s for s in sequences if s['scenario'] == 'control']
    target_cases = nominal+gaps
    errors = [e for s in target_cases for m in s['evaluation']['matches'] for e in m['position_errors_pixels']]
    velocity = [m['velocity_vector_error_pixels_per_second'] for s in target_cases for m in s['evaluation']['matches']]
    nominal_recovered = sum(s['evaluation']['recovered'] for s in nominal)
    gaps_recovered = sum(s['evaluation']['recovered'] for s in gaps)
    control_false = sum(s['evaluation']['false_candidates'] for s in controls)
    p95 = float(np.percentile(errors, 95)) if errors else None
    vmax = max(velocity) if velocity else None
    complete = (len(sequences) == 18 and {s['seed'] for s in sequences} == {17, 23, 41} and
        all({s['seed'] for s in sequences if s['scenario'] == name} == {17,23,41} for name in ['nominal','missing','control','faint_slow','blend','jitter']) and
        all(s['image_shape'] == [256,256] and s['relative_times_seconds'] == [float(k*10) for k in range(8)] for s in sequences))
    return {'sequence_count': len(sequences), 'injected_total': sum(s['evaluation']['injected'] for s in sequences),
        'recovered_total': sum(s['evaluation']['recovered'] for s in sequences),
        'false_candidates_total': sum(s['evaluation']['false_candidates'] for s in sequences),
        'nominal_recovered': nominal_recovered, 'nominal_expected': 6, 'missing_recovered': gaps_recovered,
        'missing_expected': 3, 'control_false_candidates': control_false, 'primary_position_p95_pixels': p95,
        'primary_max_velocity_vector_error_pixels_per_second': vmax, 'frozen_suite_complete': complete,
        'exploratory_criteria_passed': bool(complete and nominal_recovered == 6 and gaps_recovered == 3 and
            control_false == 0 and p95 is not None and p95 <= .75 and vmax is not None and vmax <= .03)}


def run_moving_synthetic(manifest_path, truth_path, output, base):
    mp, tp, output = [local_path(p, base) for p in (manifest_path, truth_path, output)]
    if output.exists(): raise ValueError('La sortie existe déjà.')
    hashes = {'manifest': digest(mp), 'truth': digest(tp)}
    manifest = json.loads(mp.read_text(encoding='utf-8'))
    if (not isinstance(manifest, dict) or manifest.get('moving_schema_version') != '1.0' or manifest.get('synthetic') is not True or
            manifest.get('time_kind') != 'fictitious_relative_seconds' or not isinstance(manifest.get('sequences'), list) or
            not 1 <= len(manifest['sequences']) <= 64): raise ValueError('Manifeste synthétique 1.0 requis.')
    records, paths, seen_ids = [], {}, set()
    for sequence in manifest['sequences']:
        if not isinstance(sequence, dict) or not isinstance(sequence.get('sequence_id'), str) or sequence['sequence_id'] in seen_ids:
            raise ValueError('Identifiant de séquence incorrect ou répété.')
        if sequence.get('scenario') not in ('nominal','control','missing','faint_slow','blend','jitter') or type(sequence.get('seed')) is not int:
            raise ValueError('Scénario ou graine incorrect.')
        seen_ids.add(sequence['sequence_id']); frames = sequence.get('frames')
        if not isinstance(frames, list) or not 5 <= len(frames) <= 64: raise ValueError('Séquence de 5 à 64 images requise.')
        times = [f.get('relative_time_seconds') for f in frames if isinstance(f, dict)]
        if (len(times) != len(frames) or any(not finite_number(t) for t in times) or
                np.any(np.diff(times) <= 0)): raise ValueError('Temps fictifs croissants requis.')
        detections, selections, shape = [], [], None
        for k, frame in enumerate(frames):
            if not isinstance(frame.get('local_copy'), str): raise ValueError('Copie synthétique requise.')
            path = local_path(mp.parent/frame['local_copy'], base)
            if mp.parent.resolve() not in path.parents or path in paths.values(): raise ValueError('Copie hors du lot ou répétée.')
            key = f'{sequence["sequence_id"]}:{k}'; value = digest(path)
            if value != frame.get('sha256'): raise ValueError('Empreinte d’image incorrecte.')
            paths[key] = path; hashes[key] = value
            with fits.open(path, mode='readonly', memmap=False) as hdus:
                if hdus[0].header.get('GARSYNTH') is not True or hdus[0].header.get('SYNCTIME') != times[k]:
                    raise ValueError('Marqueur/temps synthétique absent ou incohérent.')
                image = hdus[0].data
                if image is None or image.ndim != 2 or image.size > 1048576: raise ValueError('Image synthétique 2D trop grande ou absente.')
                if shape is not None and list(image.shape) != shape: raise ValueError('Dimensions incohérentes.')
                shape = list(image.shape); points, selection = detect_sources(image)
            detections.append(points); selections.append(selection)
        moving, removed = remove_stationary(detections)
        tracks, hypotheses = find_tracks(moving, times)
        records.append({'sequence_id': sequence['sequence_id'], 'scenario': sequence.get('scenario'), 'seed': sequence.get('seed'),
                        'image_shape': shape, 'relative_times_seconds': times, 'detections': [p.tolist() for p in moving],
                        'selection': selections, 'stationary_removed_per_frame': removed, 'hypotheses': hypotheses, 'tracks': tracks})
    # Truth bytes were hashed earlier; coordinates are parsed only after candidates are frozen.
    truth = json.loads(tp.read_text(encoding='utf-8'))
    if (not isinstance(truth, dict) or truth.get('truth_schema_version') != '1.0' or truth.get('manifest_sha256') != hashes['manifest'] or
            not isinstance(truth.get('sequences'), list) or
            any(not isinstance(s,dict) or not isinstance(s.get('sequence_id'),str) for s in truth['sequences'])):
        raise ValueError('Vérité synthétique incompatible avec le manifeste.')
    indexed = {s['sequence_id']: s for s in truth['sequences']}
    if len(indexed) != len(truth['sequences']) or set(indexed) != seen_ids: raise ValueError('Vérité de séquences incomplète ou dupliquée.')
    for record in records:
        injections = indexed[record['sequence_id']]['injections']
        if not isinstance(injections,list) or len(injections)>32: raise ValueError('Liste d’injections requise, limitée à 32.')
        for target in injections:
            if (not isinstance(target,dict) or not isinstance(target.get('injection_id'),str) or
                    not isinstance(target.get('velocity_pixels_per_second'),list) or len(target['velocity_pixels_per_second']) != 2 or
                    not all(finite_number(v) for v in target['velocity_pixels_per_second']) or not isinstance(target.get('positions'),list)):
                raise ValueError('Injection ou vitesse de vérité incorrecte.')
            if any(not isinstance(p,dict) or type(p.get('frame_index')) is not int or
                   not 0 <= p['frame_index'] < len(record['relative_times_seconds']) or type(p.get('visible')) is not bool or
                   not all(finite_number(p.get(axis)) for axis in ['x','y']) for p in target['positions']):
                raise ValueError('Positions de vérité incorrectes.')
            if len({p['frame_index'] for p in target['positions']}) != len(target['positions']):
                raise ValueError('Positions de vérité incorrectes.')
        if len({t['injection_id'] for t in injections}) != len(injections): raise ValueError('Injection dupliquée.')
        record['evaluation'] = evaluate_tracks(record['tracks'], injections)
        fp = record['evaluation']['false_candidates']; h, w = record['image_shape']; n = len(record['relative_times_seconds'])
        span = record['relative_times_seconds'][-1]-record['relative_times_seconds'][0]
        record['false_candidate_rates'] = {'per_frame': fp/n, 'per_megapixel_frame': fp/(n*h*w/1e6),
                                            'per_fictitious_hour': fp/(span/3600)}
    for key, path in {'manifest': mp, 'truth': tp, **paths}.items():
        if digest(path) != hashes[key]: raise ValueError('Une entrée a changé pendant le traitement.')
    result = {'moving_result_schema_version': '1.0', 'synthetic_only': True, 'parameters': PARAMETERS,
              'sequences': records, 'summary': summarize_benchmark(records), 'inputs_sha256_before': hashes,
              'inputs_sha256_after': hashes.copy(), 'truth_used_for_detection': False, 'clock_qualified': False,
              'scientific_submission_certified': False, 'real_data_performance_validated': False}
    output.mkdir(parents=True, exist_ok=False); write_moving_reports(output, result)
    return result
