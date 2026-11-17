# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Research recipe: frozen rigid registration of coordinates, then frozen tracks."""
import argparse
from copy import deepcopy
import csv
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess

import astropy
from astropy.io import fits
import numpy as np
import photutils
import scipy

from gar.astrometry import local_path
from gar.moving import detect_sources, remove_stationary, find_tracks, evaluate_tracks, PARAMETERS as MOVING_PARAMETERS
from gar.registration import detect, register_points, CRITERIA, PARAMETERS as REGISTRATION_PARAMETERS
from gar.workset import digest
from moving_limits import add_source, transform, write_json

ROOT = Path(__file__).resolve().parents[1]
TIMES = np.arange(8, dtype=float)*10
SEEDS = (607, 701, 809, 907, 1009)
PLAN_COMMIT = '286af43976e85140a663e1019779731c40153262'
ENGINE_SHA256 = {
    'src/gar/registration.py': '23828292730f324a4a06ba5b247187fd21aa1eeb01bd8e4dfda90c46d3d709da',
    'src/gar/moving.py': 'f492032e0188310484faaf372db4c96597fd7910ecd3821629edb8365f27be67',
    'src/gar/moving_reports.py': 'b3b543591ad7cbe35dd0c08a92a8aee67b89888a1488f6b80fdbb354a0b6be0c',
}


def verify_engine():
    actual = {p: sha256((ROOT/p).read_text(encoding='utf-8').encode('utf-8')).hexdigest() for p in ENGINE_SHA256}
    if actual != ENGINE_SHA256:
        raise ValueError('Moteur modifié : nouveau plan et nouvel essai nécessaires.')
    return actual


def conditions():
    specs = [
        ('aligned', 'Alignées', 0., 0., True, 80, 'primary'),
        ('drift', 'Dérive 0,15 pixel/s', .15, 0., True, 80, 'primary'),
        ('rotation', 'Rotation totale 2 degrés', 0., 2., True, 80, 'primary'),
        ('combined', 'Dérive + rotation 2 degrés', .15, 2., True, 80, 'primary'),
        ('rotation-large', 'Rotation totale 8 degrés', 0., 8., True, 80, 'descriptive'),
        ('control-drift', 'Sans mobile : dérive', .15, 0., False, 80, 'control'),
        ('control-combined', 'Sans mobile : dérive + rotation', .15, 2., False, 80, 'control'),
        ('insufficient', 'Seulement 12 étoiles', .15, 2., True, 12, 'negative'),
    ]
    return [dict(condition_id=n, label=l, drift_pixels_per_second=d, rotation_total_degrees=r,
                 mobile=m, star_count=s, scope=sc) for n, l, d, r, m, s, sc in specs]


def make_sequence(output, condition, seed):
    rng = np.random.default_rng(seed)
    noise_rng = np.random.default_rng(seed+10000)
    stars = []
    path = np.column_stack([50+.5*TIMES, 85+.2*TIMES])
    while len(stars) < condition['star_count']:
        x, y = rng.uniform(25, 231, 2)
        # Distance to the full continuous segment, including its endpoints.
        start, vector = path[0], path[-1]-path[0]
        along = np.clip(np.dot([x, y]-start, vector)/np.dot(vector, vector), 0, 1)
        if np.linalg.norm([x, y]-start-along*vector) < 14:
            continue
        if stars and min(np.hypot(x-a, y-b) for a, b, _ in stars) < 10:
            continue
        stars.append((x, y, rng.uniform(500, 1500)))
    name = f'{condition["condition_id"]}-s{seed}'
    frames, raw_positions, ref_positions, exact_models = [], [], [], []
    for k, t in enumerate(TIMES):
        image = noise_rng.normal(100, 2, (256, 256))
        for point, (_, _, peak) in zip(transform(np.array(stars)[:, :2], t, condition), stars):
            add_source(image, *point, peak)
        reference_point = np.array([50+.5*t, 85+.2*t])
        point = transform(reference_point, t, condition)
        if condition['mobile']:
            add_source(image, *point, 120.)
            raw_positions.append(dict(frame_index=k, x=float(point[0]), y=float(point[1]), visible=True))
            ref_positions.append(dict(frame_index=k, x=float(reference_point[0]), y=float(reference_point[1]), visible=True))
        angle = np.deg2rad(condition['rotation_total_degrees'])*t/70
        r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        forward_t = np.array([127.5, 127.5])-r@np.array([127.5, 127.5])+[condition['drift_pixels_per_second']*t, 0]
        exact_models.append(dict(rotation_matrix=r.T.tolist(), translation_pixels=(-r.T@forward_t).tolist()))
        file = output/'copies'/f'{name}-{k:02d}.fit'
        fits.writeto(file, image.astype('float32'), fits.Header({'GARSYNTH': True, 'SYNCTIME': float(t)}))
        frames.append(dict(local_copy=f'copies/{file.name}', sha256=digest(file), relative_time_seconds=float(t)))

    def injection(positions):
        if not positions:
            return []
        xy = np.array([[p['x'], p['y']] for p in positions])
        slope = np.linalg.lstsq(np.column_stack([np.ones(8), TIMES]), xy, rcond=None)[0][1]
        return [dict(injection_id='mobile-1', positions=positions, velocity_pixels_per_second=slope.tolist())]

    return (dict(sequence_id=name, condition_id=condition['condition_id'], seed=seed, frames=frames),
            dict(sequence_id=name, before=injection(raw_positions), after=injection(ref_positions), exact_models=exact_models))


def make_suite(output, base=None):
    output = local_path(output, ROOT/'local' if base is None else base)
    engine = verify_engine()
    output.mkdir(parents=True, exist_ok=False)
    (output/'copies').mkdir()
    sequences, truth = [], []
    for condition in conditions():
        for seed in SEEDS:
            sequence, answers = make_sequence(output, condition, seed)
            sequences.append(sequence)
            truth.append(answers)
    manifest = dict(moving_registration_schema_version='1.0', synthetic=True,
                    time_kind='fictitious_relative_seconds', plan_commit=PLAN_COMMIT,
                    engine_sha256_lf=engine, conditions=conditions(), seeds=list(SEEDS), sequences=sequences)
    write_json(output/'manifest.json', manifest)
    write_json(output/'truth.json', dict(registration_truth_schema_version='1.0',
                                        manifest_sha256=digest(output/'manifest.json'), sequences=truth))
    print('40 séquences fictives, 320 images créées.', flush=True)


def track_branch(points):
    moving, removed = remove_stationary(points)
    tracks, hypotheses = find_tracks(moving, TIMES)
    return dict(tracks=tracks, detections=[p.tolist() for p in moving],
                stationary_removed_per_frame=removed, hypotheses=hypotheses)


def map_detections(points, models):
    if len(points) != len(models) or not all(m.get('model_usable') is True for m in models):
        raise ValueError('Une pose refusée bloque toute la branche après.')
    mapped, excluded = [], []
    for p, model in zip(points, models):
        r = np.asarray(model['rotation_matrix'])
        t = np.asarray(model['translation_pixels'])
        if r.shape != (2, 2) or t.shape != (2,) or not np.isfinite(r).all() or not np.isfinite(t).all():
            raise ValueError('Transformation non finie ou incorrecte.')
        q = np.asarray(p)@r.T+t
        keep = (q >= 8).all(axis=1) & (q < 248).all(axis=1) & np.isfinite(q).all(axis=1)
        mapped.append(q[keep])
        excluded.append(int((~keep).sum()))
    return mapped, excluded


def process_sequence(images):
    """Candidates and registration use pixels only. No condition or truth argument."""
    if len(images) != 8 or any(image.shape != (256, 256) for image in images):
        raise ValueError('Huit images fictives 256×256 requises.')
    detections, selections = [], []
    for image in images:
        points, selection = detect_sources(image)
        detections.append(points)
        selections.append(selection)
    before = track_branch(detections)
    try:
        reference, ref_selection = detect(images[0])
        ref_error = None
    except ValueError as exc:
        reference, ref_selection, ref_error = None, None, str(exc)
    models = [dict(model_usable=reference is not None, kind='reference_identity',
                   rotation_matrix=np.eye(2).tolist(), translation_pixels=[0., 0.], error=ref_error)]
    for image in images[1:]:
        try:
            if reference is None:
                raise ValueError('Référence inutilisable : '+ref_error)
            stars, selection = detect(image)
            model = register_points(stars, reference, image.shape)
            model.update(kind='estimated_rigid', detection=selection)
        except ValueError as exc:
            model = dict(model_usable=False, error=str(exc))
        models.append(model)
    available = all(m['model_usable'] for m in models)
    after, mapped, excluded = None, None, None
    if available:
        mapped, excluded = map_detections(detections, models)
        after = track_branch(mapped)
    return dict(raw_detections=[p.tolist() for p in detections], detection=selections,
                reference_detection=ref_selection, registration=models, before=before, after=after,
                after_available=available, mapped_detections=[p.tolist() for p in mapped] if available else None,
                overlap_excluded_per_frame=excluded,
                blocked_frame_indices=[i for i, m in enumerate(models) if not m['model_usable']])


def validate_manifest(manifest):
    if (manifest.get('moving_registration_schema_version') != '1.0' or manifest.get('synthetic') is not True
            or manifest.get('time_kind') != 'fictitious_relative_seconds' or manifest.get('plan_commit') != PLAN_COMMIT
            or manifest.get('engine_sha256_lf') != ENGINE_SHA256 or manifest.get('conditions') != conditions()
            or manifest.get('seeds') != list(SEEDS)):
        raise ValueError('Le manifeste doit respecter le protocole publié.')
    expected = {f'{c["condition_id"]}-s{s}': (c['condition_id'], s) for c in conditions() for s in SEEDS}
    records = manifest.get('sequences')
    if (not isinstance(records, list) or len(records) != 40
            or {s['sequence_id'] for s in records} != set(expected)):
        raise ValueError('Les 40 séquences distinctes sont requises.')
    for sequence in records:
        if (sequence['condition_id'], sequence['seed']) != expected[sequence['sequence_id']]:
            raise ValueError('Condition/graine incohérente.')
        frames = sequence['frames']
        if len(frames) != 8 or [f['relative_time_seconds'] for f in frames] != TIMES.tolist():
            raise ValueError('Huit temps fictifs 0 à 70 s requis.')


def validate_truth(truth, records, manifest_hash):
    if (truth.get('registration_truth_schema_version') != '1.0' or truth.get('manifest_sha256') != manifest_hash
            or not isinstance(truth.get('sequences'), list)):
        raise ValueError('Vérité incompatible avec le manifeste.')
    indexed = {s['sequence_id']: s for s in truth['sequences']}
    if len(indexed) != len(records) or len(truth['sequences']) != len(records) or set(indexed) != {s['sequence_id'] for s in records}:
        raise ValueError('Vérité incomplète ou dupliquée.')
    for sequence in records:
        answer = indexed[sequence['sequence_id']]
        condition = next(c for c in conditions() if c['condition_id'] == sequence['condition_id'])
        for branch in ('before', 'after'):
            injections = answer[branch]
            if len(injections) != int(condition['mobile']):
                raise ValueError('Nombre d’injections incorrect.')
            for injection in injections:
                positions = injection['positions']
                if (not isinstance(injection.get('injection_id'), str)
                        or np.asarray(injection['velocity_pixels_per_second']).shape != (2,)
                        or not np.isfinite(injection['velocity_pixels_per_second']).all()
                        or [p['frame_index'] for p in positions] != list(range(8))
                        or any(p.get('visible') is not True or not np.isfinite([p['x'], p['y']]).all() for p in positions)):
                    raise ValueError('Positions ou vitesse de vérité incorrectes.')
        if len(answer['exact_models']) != 8:
            raise ValueError('Huit modèles exacts requis pour le bilan géométrique.')
        for model in answer['exact_models']:
            if (np.asarray(model['rotation_matrix']).shape != (2, 2)
                    or np.asarray(model['translation_pixels']).shape != (2,)
                    or not np.isfinite(model['rotation_matrix']).all() or not np.isfinite(model['translation_pixels']).all()):
                raise ValueError('Géométrie de vérité incorrecte.')
    return indexed


def score_records(records, truth, manifest_hash):
    """Only called after ALL candidates are frozen; preserve their values."""
    indexed = validate_truth(truth, records, manifest_hash)
    scored = deepcopy(records)
    grid = np.array([(x, y) for x in (25., 127.5, 231.) for y in (25., 127.5, 231.)])
    for sequence in scored:
        answers = indexed[sequence['sequence_id']]
        for branch in ('before', 'after'):
            if sequence[branch] is not None:
                evaluation = evaluate_tracks(sequence[branch]['tracks'], answers[branch])
                false = evaluation['false_candidates']
                evaluation['false_candidate_rates'] = dict(per_frame=false/8, per_megapixel_frame=false/(8*256*256/1e6),
                                                            per_fictitious_hour=false/(70/3600))
                sequence[branch]['evaluation'] = evaluation
        for model, exact in zip(sequence['registration'], answers['exact_models']):
            if model['model_usable']:
                mapped = grid@np.asarray(model['rotation_matrix']).T+model['translation_pixels']
                target = grid@np.asarray(exact['rotation_matrix']).T+exact['translation_pixels']
                model['truth_grid_max_mapping_error_pixels'] = float(np.linalg.norm(mapped-target, axis=1).max())
    return scored


def summarize(records):
    expected = {f'{c["condition_id"]}-s{s}': (c['condition_id'], s) for c in conditions() for s in SEEDS}
    if (len(records) != 40 or {s['sequence_id'] for s in records} != set(expected)
            or any((s['condition_id'], s['seed']) != expected[s['sequence_id']] for s in records)):
        raise ValueError('Campagne incomplète : pas de bilan complet.')
    rows = []
    for c in conditions():
        seq = [s for s in records if s['condition_id'] == c['condition_id']]
        available = [s for s in seq if s['after_available']]
        rows.append(dict(**c, sequence_count=len(seq), after_available=len(available), after_blocked=len(seq)-len(available),
                         before_recovered=sum(s['before']['evaluation']['recovered'] for s in seq),
                         before_injected=sum(s['before']['evaluation']['injected'] for s in seq),
                         before_false_candidates=sum(s['before']['evaluation']['false_candidates'] for s in seq),
                         paired_before_false_candidates=sum(s['before']['evaluation']['false_candidates'] for s in available) if available else None,
                         paired_before_recovered=sum(s['before']['evaluation']['recovered'] for s in available) if available else None,
                         after_recovered=sum(s['after']['evaluation']['recovered'] for s in available) if available else None,
                         after_injected_available=sum(s['after']['evaluation']['injected'] for s in available),
                         after_missed_available=sum(s['after']['evaluation']['missed'] for s in available),
                         after_false_candidates=sum(s['after']['evaluation']['false_candidates'] for s in available) if available else None))
    primary = [s for s in records if s['condition_id'] in ('aligned', 'drift', 'rotation', 'combined')]
    usable = [s for s in primary if s['after_available']]
    matches = [m for s in usable for m in s['after']['evaluation']['matches']]
    errors = [e for m in matches for e in m['position_errors_pixels']]
    vmax = max((m['velocity_vector_error_pixels_per_second'] for m in matches), default=None)
    p95 = float(np.percentile(errors, 95)) if errors else None
    controls = [s for s in records if s['condition_id'] in ('control-drift', 'control-combined')]
    negative = [s for s in records if s['condition_id'] == 'insufficient']
    drift = [s for s in primary if s['condition_id'] in ('drift', 'combined')]
    before_false = sum(s['before']['evaluation']['false_candidates'] for s in drift)
    after_false = sum(s['after']['evaluation']['false_candidates'] for s in drift) if all(s['after_available'] for s in drift) else None
    reduction = (1-after_false/before_false) if before_false and after_false is not None else None
    criteria = dict(primary_all_models_accepted=len(usable) == 20,
                    primary_20_mobiles_recovered=len(matches) == 20,
                    primary_zero_false_after=len(usable) == 20 and sum(s['after']['evaluation']['false_candidates'] for s in usable) == 0,
                    primary_position_p95=p95 is not None and p95 <= .3,
                    primary_velocity_error=vmax is not None and vmax <= .02,
                    ten_controls_accepted_zero_false=all(s['after_available'] and s['after']['evaluation']['false_candidates'] == 0 for s in controls),
                    five_negative_cases_blocked=all(not s['after_available'] for s in negative),
                    false_candidate_reduction_at_least_90_percent=reduction is not None and reduction >= .9)
    return dict(sequence_count=40, image_count=320, conditions=rows, criteria=criteria,
                primary_position_p95_pixels=p95, primary_max_velocity_error_pixels_per_second=vmax,
                drift_false_before=before_false, drift_false_after=after_false, drift_false_reduction_fraction=reduction,
                exploratory_criteria_passed=all(criteria.values()))


def write_reports(output, result):
    write_json(output/'comparison.json', result)
    fields = ['sequence_id', 'condition_id', 'seed', 'after_available', 'before_recovered', 'before_false', 'after_recovered', 'after_false']
    with (output/'comparison.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for s in result['sequences']:
            b = s['before']['evaluation']
            a = s['after']['evaluation'] if s['after_available'] else None
            writer.writerow(dict(sequence_id=s['sequence_id'], condition_id=s['condition_id'], seed=s['seed'],
                                 after_available=s['after_available'], before_recovered=b['recovered'], before_false=b['false_candidates'],
                                 after_recovered=a['recovered'] if a else '', after_false=a['false_candidates'] if a else ''))
    text = ('# Recalage des coordonnées puis recherche — données fictives\n\n'
            '| Condition | Avant retrouvés/injectés | Avant faux | Après disponible | Après retrouvés/injectés disponibles | Après faux |\n'
            '|---|---:|---:|---:|---:|---:|\n')
    for row in result['summary']['conditions']:
        after = f'{row["after_recovered"]}/{row["after_injected_available"]}' if row['after_available'] else 'indisponible'
        false = row['after_false_candidates'] if row['after_available'] else 'indisponible'
        text += (f'| {row["label"]} | {row["before_recovered"]}/{row["before_injected"]} | {row["before_false_candidates"]} '
                 f'| {row["after_available"]}/5 | {after} | {false} |\n')
    text += '\nCritères exploratoires préenregistrés :\n\n'
    text += '\n'.join(f'- {key} : {value}' for key, value in result['summary']['criteria'].items())
    text += ('\n\nUne branche bloquée ne vaut pas zéro faux candidat. Vérité lue après gel des modèles et candidats. '
             'Contrôles réservés par pose ; référence mesurée commune, erreurs corrélées. Aucun pixel rééchantillonné, '
             'aucune heure ou position céleste qualifiée, aucune performance réelle ou découverte confirmée. '
             'Les erreurs sur les appariés ne décrivent pas les objets manqués.\n')
    text += '\nComparaisons sur les mêmes séquences disponibles des deux côtés :\n\n'
    for row in result['summary']['conditions']:
        if row['after_available']:
            text += (f'- {row["label"]} : {row["after_available"]}/5 séquences comparables ; '
                     f'faux candidats {row["paired_before_false_candidates"]} → {row["after_false_candidates"]}.\n')
        else:
            text += f'- {row["label"]} : comparaison indisponible.\n'
    (output/'report.md').write_text(text, encoding='utf-8')


def run_suite(manifest_path, truth_path, output, base=None):
    base = ROOT/'local' if base is None else base
    mp, tp, output = [local_path(p, base) for p in (manifest_path, truth_path, output)]
    if output.exists():
        raise ValueError('Choisir une nouvelle sortie.')
    engine = verify_engine()
    watched = {mp: digest(mp), tp: digest(tp)}
    manifest = json.loads(mp.read_text(encoding='utf-8'))
    validate_manifest(manifest)
    inputs, seen = [], set()
    for sequence in manifest['sequences']:
        paths = []
        for frame in sequence['frames']:
            p = local_path(mp.parent/frame['local_copy'], base)
            if mp.parent not in p.parents or p in seen or digest(p) != frame['sha256']:
                raise ValueError('Image hors du lot, répétée ou modifiée.')
            watched[p] = frame['sha256']
            seen.add(p)
            paths.append(p)
        inputs.append((sequence, paths))
    output.mkdir(parents=True, exist_ok=False)
    progress = dict(status='running', completed_sequences=[], failed_sequence=None)
    write_json(output/'progress.json', progress)
    records = []
    try:
        for sequence, paths in inputs:
            print(f'Analyse {sequence["sequence_id"]}...', flush=True)
            images = []
            for k, p in enumerate(paths):
                with fits.open(p, mode='readonly', memmap=False) as hdus:
                    if hdus[0].header.get('GARSYNTH') is not True or hdus[0].header.get('SYNCTIME') != TIMES[k]:
                        raise ValueError('Marqueur ou temps synthétique incohérent.')
                    if hdus[0].data is None or hdus[0].data.shape != (256, 256):
                        raise ValueError('Image fictive 256×256 requise.')
                    images.append(hdus[0].data.copy())
            record = process_sequence(images)
            record.update(sequence_id=sequence['sequence_id'], condition_id=sequence['condition_id'], seed=sequence['seed'])
            records.append(record)
            write_json(output/f'{sequence["sequence_id"]}.json', record)
            progress['completed_sequences'].append(sequence['sequence_id'])
            write_json(output/'progress.json', progress)
        frozen_hashes = {s['sequence_id']: digest(output/f'{s["sequence_id"]}.json') for s in records}
        # This is the FIRST parse of the truth coordinates, after ALL branches are frozen.
        truth = json.loads(tp.read_text(encoding='utf-8'))
        scored = score_records(records, truth, watched[mp])
        if (verify_engine() != engine or any(digest(p) != h for p, h in watched.items())
                or any(digest(output/f'{name}.json') != h for name, h in frozen_hashes.items())):
            raise ValueError('Une entrée ou un moteur a changé pendant le traitement.')
        result = dict(moving_registration_result_schema_version='1.0', synthetic_only=True, suite_complete=True,
                      plan_commit=PLAN_COMMIT, engine_sha256_lf=engine, sequences=scored, summary=summarize(scored),
                      parameters=dict(moving=MOVING_PARAMETERS, registration=REGISTRATION_PARAMETERS, registration_criteria=CRITERIA),
                      manifest_sha256=watched[mp], truth_sha256=watched[tp],
                      inputs_sha256_before={str(p.relative_to(mp.parent)) if p.is_relative_to(mp.parent) else 'truth_file': h for p, h in watched.items()},
                      inputs_unchanged=True, frozen_candidate_report_sha256=frozen_hashes,
                      source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      source_tree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
                      recipe_sha256_lf=sha256(Path(__file__).read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                      environment=dict(python=platform.python_version(), numpy=np.__version__, astropy=astropy.__version__,
                                       photutils=photutils.__version__, scipy=scipy.__version__),
                      truth_used_for_detection=False, truth_used_for_registration=False, pixels_resampled=False,
                      clock_qualified=False, real_data_performance_validated=False, scientific_submission_certified=False)
        write_reports(output, result)
        progress['status'] = 'complete'
        write_json(output/'progress.json', progress)
    except Exception as exc:
        progress.update(status='incomplete', failed_sequence=sequence['sequence_id'], error=str(exc))
        write_json(output/'progress.json', progress)
        raise
    print('40 séquences analysées ; critères exploratoires : '+str(result['summary']['exploratory_criteria_passed']), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    make = sub.add_parser('make')
    make.add_argument('output', type=Path)
    run = sub.add_parser('run')
    run.add_argument('manifest', type=Path)
    run.add_argument('truth', type=Path)
    run.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'make':
            make_suite(args.output)
        else:
            report = run_suite(args.manifest, args.truth, args.output)
            raise SystemExit(0 if report['summary']['exploratory_criteria_passed'] else 2)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
