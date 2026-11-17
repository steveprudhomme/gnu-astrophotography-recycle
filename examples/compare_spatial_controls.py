# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Frozen paired research experiment; never consumes real FITS or external devices."""
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
from gar.workset import digest
from gar.moving import detect_sources, evaluate_tracks
from gar.registration import detect, register_points
import moving_registration as previous
from moving_limits import add_source, transform, write_json
from spatial_controls import register_spatial

ROOT = Path(__file__).resolve().parents[1]
TIMES = previous.TIMES
SEEDS = (1103, 1201, 1301, 1409, 1511)
PLAN_COMMIT = 'bbe977609ff526f87d13d4181bdc18e108f3fbbe'
METHODS = ('historical', 'spatial')
RECIPE_SHA256 = 'c1f35892be3af3ecdaed09ec88bdcb5f7c7cc24ba69ec5d5b69ab98407f3870f'


def verify_frozen():
    actual = previous.verify_engine()
    name = 'examples/moving_registration.py'
    actual[name] = sha256((ROOT/name).read_text(encoding='utf-8').encode('utf-8')).hexdigest()
    if actual[name] != RECIPE_SHA256:
        raise ValueError('La recette historique a changé : nouveau protocole requis.')
    return actual


def conditions():
    result = [dict(c, field='ordinary') for c in previous.conditions()]
    for name, label, count, field in [('missing-quadrant', 'Quadrant réellement vide', 80, 'missing_quadrant'),
                                      ('narrow-field', 'Bande étroite', 40, 'narrow')]:
        result.append(dict(condition_id=name, label=label, drift_pixels_per_second=.15,
                           rotation_total_degrees=2., mobile=False, star_count=count, scope='negative', field=field))
    return result


def make_sequence(output, condition, seed):
    rng, noise_rng = np.random.default_rng(seed), np.random.default_rng(seed+10000)
    stars = []
    start, vector = np.array([50., 85.]), np.array([35., 14.])
    for _ in range(100000):
        if len(stars) == condition['star_count']:
            break
        x, y = rng.uniform(25, 231, 2)
        if condition['field'] == 'missing_quadrant' and x < 150 and y < 150:
            continue
        if condition['field'] == 'narrow' and not 110 <= y <= 145:
            continue
        along = np.clip(np.dot([x, y]-start, vector)/np.dot(vector, vector), 0, 1)
        if np.linalg.norm([x, y]-start-along*vector) < 14:
            continue
        if stars and min(np.hypot(x-a, y-b) for a, b, _ in stars) < 10:
            continue
        stars.append((x, y, rng.uniform(500, 1500)))
    if len(stars) != condition['star_count']:
        raise ValueError('Placement impossible après 100 000 propositions ; essai conservé, pas de nouvelle graine.')
    name = f'{condition["condition_id"]}-s{seed}'
    frames, before, after = [], [], []
    for k, t in enumerate(TIMES):
        image = noise_rng.normal(100, 2, (256, 256))
        for point, (_, _, peak) in zip(transform(np.array(stars)[:, :2], t, condition), stars):
            add_source(image, *point, peak)
        ref = start+[.5*t, .2*t]
        point = transform(ref, t, condition)
        if condition['mobile']:
            add_source(image, *point, 120.)
            before.append(dict(frame_index=k, x=float(point[0]), y=float(point[1]), visible=True))
            after.append(dict(frame_index=k, x=float(ref[0]), y=float(ref[1]), visible=True))
        path = output/'copies'/f'{name}-{k:02d}.fit'
        fits.writeto(path, image.astype('float32'), fits.Header({'GARSYNTH': True, 'SYNCTIME': float(t)}))
        frames.append(dict(local_copy=f'copies/{path.name}', sha256=digest(path), relative_time_seconds=float(t)))
    def injection(positions):
        if not positions: return []
        xy = np.array([[p['x'], p['y']] for p in positions])
        velocity = np.linalg.lstsq(np.column_stack([np.ones(8), TIMES]), xy, rcond=None)[0][1]
        return [dict(injection_id='mobile-1', positions=positions, velocity_pixels_per_second=velocity.tolist())]
    return (dict(sequence_id=name, condition_id=condition['condition_id'], seed=seed, frames=frames),
            dict(sequence_id=name, before=injection(before), after=injection(after)))


def make_suite(output, base=None):
    output = local_path(output, ROOT/'local' if base is None else base)
    frozen = verify_frozen()
    output.mkdir(parents=True, exist_ok=False)
    (output/'copies').mkdir()
    sequences, answers = [], []
    for c in conditions():
        for seed in SEEDS:
            s, t = make_sequence(output, c, seed)
            sequences.append(s); answers.append(t)
    write_json(output/'manifest.json', dict(spatial_controls_schema_version='1.0', synthetic=True,
                time_kind='fictitious_relative_seconds', plan_commit=PLAN_COMMIT, frozen_sha256_lf=frozen,
                conditions=conditions(), seeds=list(SEEDS), sequences=sequences))
    write_json(output/'truth.json', dict(spatial_truth_schema_version='1.0', manifest_sha256=digest(output/'manifest.json'), sequences=answers))
    print('50 séquences et 400 images fictives créées.', flush=True)


def process_sequence(images):
    """Same detections for both partitions. No truth, seed or condition argument."""
    if len(images) != 8 or any(im.shape != (256, 256) for im in images):
        raise ValueError('Huit images 256×256 requises.')
    native = [detect_sources(image)[0] for image in images]
    stars, selections, errors = [], [], []
    for image in images:
        try:
            p, selection = detect(image)
            stars.append(p); selections.append(selection); errors.append(None)
        except ValueError as exc:
            stars.append(None); selections.append(None); errors.append(str(exc))
    reference = stars[0]
    branches = {}
    for method, fit in [('historical', register_points), ('spatial', register_spatial)]:
        models = [dict(model_usable=reference is not None, kind='reference_identity',
                       rotation_matrix=np.eye(2).tolist(), translation_pixels=[0., 0.], error=errors[0])]
        for k in range(1, 8):
            try:
                if reference is None or stars[k] is None:
                    raise ValueError('Détection stellaire inutilisable.')
                model = fit(stars[k], reference, (256, 256))
                model['kind'] = 'estimated_rigid'
            except ValueError as exc:
                model = dict(model_usable=False, error=str(exc))
            models.append(model)
        available = all(m['model_usable'] for m in models)
        mapped, excluded, after = None, None, None
        if available:
            mapped, excluded = previous.map_detections(native, models)
            after = previous.track_branch(mapped)
        branches[method] = dict(registration=models, after_available=available, after=after,
                                mapped_detections=[p.tolist() for p in mapped] if available else None,
                                overlap_excluded_per_frame=excluded,
                                blocked_frame_indices=[i for i, m in enumerate(models) if not m['model_usable']])
    return dict(before=previous.track_branch(native), raw_detections=[p.tolist() for p in native],
                star_detections=[p.tolist() if p is not None else None for p in stars], star_selection=selections, methods=branches)


def validate_manifest(manifest):
    expected = {f'{c["condition_id"]}-s{s}': (c['condition_id'], s) for c in conditions() for s in SEEDS}
    if (manifest.get('spatial_controls_schema_version') != '1.0' or manifest.get('synthetic') is not True
            or manifest.get('time_kind') != 'fictitious_relative_seconds' or manifest.get('plan_commit') != PLAN_COMMIT
            or manifest.get('conditions') != conditions() or manifest.get('seeds') != list(SEEDS)
            or manifest.get('frozen_sha256_lf') != verify_frozen()):
        raise ValueError('Protocole spatial gelé requis.')
    sequences = manifest.get('sequences')
    if (not isinstance(sequences, list) or len(sequences) != 50
            or {s['sequence_id'] for s in sequences} != set(expected)
            or any((s['condition_id'], s['seed']) != expected[s['sequence_id']] for s in sequences)):
        raise ValueError('50 séquences distinctes condition/graine requises.')
    if any(len(s['frames']) != 8 or [f['relative_time_seconds'] for f in s['frames']] != TIMES.tolist() for s in sequences):
        raise ValueError('Huit temps fictifs 0 à 70 s requis.')


def score(records, truth, manifest_hash):
    if (truth.get('spatial_truth_schema_version') != '1.0' or truth.get('manifest_sha256') != manifest_hash
            or not isinstance(truth.get('sequences'), list)):
        raise ValueError('Vérité incompatible.')
    indexed = {s['sequence_id']: s for s in truth['sequences']}
    if len(indexed) != len(records) or len(indexed) != len(truth['sequences']) or set(indexed) != {s['sequence_id'] for s in records}:
        raise ValueError('Vérité manquante ou dupliquée.')
    result = deepcopy(records)
    for r in result:
        c = next(c for c in conditions() if c['condition_id'] == r['condition_id'])
        answer = indexed[r['sequence_id']]
        for phase in ('before', 'after'):
            injections = answer[phase]
            if not isinstance(injections, list) or len(injections) != int(c['mobile']):
                raise ValueError('Nombre d’injections incorrect.')
            for target in injections:
                if (not isinstance(target.get('injection_id'), str)
                        or np.asarray(target['velocity_pixels_per_second']).shape != (2,)
                        or not np.isfinite(target['velocity_pixels_per_second']).all()
                        or [p['frame_index'] for p in target['positions']] != list(range(8))
                        or any(p['visible'] is not True or not np.isfinite([p['x'], p['y']]).all() for p in target['positions'])):
                    raise ValueError('Positions de vérité incorrectes.')
        r['before']['evaluation'] = evaluate_tracks(r['before']['tracks'], answer['before'])
        for branch in r['methods'].values():
            if branch['after_available']:
                branch['after']['evaluation'] = evaluate_tracks(branch['after']['tracks'], answer['after'])
    return result


def summarize(records):
    expected = {f'{c["condition_id"]}-s{s}': (c['condition_id'], s) for c in conditions() for s in SEEDS}
    if (len(records) != 50 or {r['sequence_id'] for r in records} != set(expected)
            or any((r['condition_id'], r['seed']) != expected[r['sequence_id']] for r in records)):
        raise ValueError('Campagne incomplète.')
    rows = []
    for c in conditions():
        seq = [s for s in records if s['condition_id'] == c['condition_id']]
        row = dict(**c, methods={})
        for method in METHODS:
            branches = [s['methods'][method] for s in seq if s['methods'][method]['after_available']]
            matches = [m for b in branches for m in b['after']['evaluation']['matches']]
            errors = [e for m in matches for e in m['position_errors_pixels']]
            row['methods'][method] = dict(available=len(branches), blocked=5-len(branches),
                recovered=sum(b['after']['evaluation']['recovered'] for b in branches) if branches else None,
                missed_available=sum(b['after']['evaluation']['missed'] for b in branches) if branches else None,
                false_candidates=sum(b['after']['evaluation']['false_candidates'] for b in branches) if branches else None,
                position_p95_pixels=float(np.percentile(errors, 95)) if errors else None)
        common = [s for s in seq if all(s['methods'][m]['after_available'] for m in METHODS)]
        row['paired'] = dict(sequence_count=len(common), methods={m: dict(
            recovered=sum(s['methods'][m]['after']['evaluation']['recovered'] for s in common) if common else None,
            false_candidates=sum(s['methods'][m]['after']['evaluation']['false_candidates'] for s in common) if common else None) for m in METHODS})
        row['transitions'] = dict(refused_to_accepted=sum(not s['methods']['historical']['after_available'] and s['methods']['spatial']['after_available'] for s in seq),
                                 accepted_to_refused=sum(s['methods']['historical']['after_available'] and not s['methods']['spatial']['after_available'] for s in seq))
        rows.append(row)
    primary = [s for s in records if s['condition_id'] in ('aligned', 'drift', 'rotation', 'combined')]
    available = [s['methods']['spatial'] for s in primary if s['methods']['spatial']['after_available']]
    matches = [m for b in available for m in b['after']['evaluation']['matches']]
    errors = [e for m in matches for e in m['position_errors_pixels']]
    p95 = float(np.percentile(errors, 95)) if errors else None
    vmax = max((m['velocity_vector_error_pixels_per_second'] for m in matches), default=None)
    controls = [s for s in records if s['condition_id'].startswith('control-')]
    negatives = [s for s in records if s['condition_id'] in ('insufficient', 'missing-quadrant', 'narrow-field')]
    old_accepted = [s for s in primary if s['methods']['historical']['after_available']]
    preserves = all(s['methods']['spatial']['after_available'] and
                    s['methods']['spatial']['after']['evaluation']['recovered'] >= s['methods']['historical']['after']['evaluation']['recovered'] and
                    s['methods']['spatial']['after']['evaluation']['false_candidates'] <= s['methods']['historical']['after']['evaluation']['false_candidates'] for s in old_accepted)
    checks = dict(twenty_primary_available=len(available) == 20, twenty_mobiles_recovered=len(matches) == 20,
                  zero_primary_false=len(available) == 20 and sum(b['after']['evaluation']['false_candidates'] for b in available) == 0,
                  position_p95=p95 is not None and p95 <= .3, velocity_error=vmax is not None and vmax <= .02,
                  ten_controls_accepted_zero_false=all(s['methods']['spatial']['after_available'] and s['methods']['spatial']['after']['evaluation']['false_candidates'] == 0 for s in controls),
                  fifteen_negatives_blocked=all(not s['methods']['spatial']['after_available'] for s in negatives),
                  old_accepted_primary_preserved=preserves)
    return dict(sequence_count=50, image_count=400, conditions=rows, criteria=checks,
                primary_position_p95_pixels=p95, primary_max_velocity_error_pixels_per_second=vmax,
                primary_historical_available=len(old_accepted), primary_spatial_available=len(available),
                exploratory_criteria_passed=all(checks.values()))


def write_reports(output, result):
    write_json(output/'spatial.json', result)
    text = ('# Contrôles répartis — données synthétiques\n\n'
            '| Condition | Ancienne disponible | Spatiale disponible | Ancienne retrouvés | Spatiale retrouvés | Faux ancienne / spatiale |\n'
            '|---|---:|---:|---:|---:|---:|\n')
    with (output/'comparison.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['sequence_id', 'method', 'available', 'recovered', 'missed', 'false_candidates'])
        for s in result['sequences']:
            for method, b in s['methods'].items():
                e = b['after']['evaluation'] if b['after_available'] else None
                writer.writerow([s['sequence_id'], method, b['after_available'], e['recovered'] if e else '',
                                 e['missed'] if e else '', e['false_candidates'] if e else ''])
    for row in result['summary']['conditions']:
        a, b = [row['methods'][m] for m in METHODS]
        text += f'| {row["label"]} | {a["available"]}/5 | {b["available"]}/5 | {a["recovered"]} | {b["recovered"]} | {a["false_candidates"]} / {b["false_candidates"]} |\n'
    text += '\nCritères exploratoires :\n\n'+json.dumps(result['summary']['criteria'], indent=2)+'\n\n'
    text += ('Une branche bloquée est indisponible (None), pas un zéro faux candidat. '
             'Les comparaisons appariées et transitions sont dans spatial.json ; les mêmes séquences sont comparées des deux côtés. '
             'Contrôles réservés par pose avant ajustement, sans vérité ou résidus ; référence commune et erreurs corrélées. '
             'Aucune image réelle, horloge qualifiée, performance Seestar certifiée ou pixel FITS modifié.\n')
    (output/'report.md').write_text(text, encoding='utf-8')


def run_suite(manifest_path, truth_path, output, base=None):
    base = ROOT/'local' if base is None else base
    mp, tp, output = [local_path(p, base) for p in (manifest_path, truth_path, output)]
    if output.exists(): raise ValueError('Choisir une sortie neuve.')
    frozen = verify_frozen()
    watched = {mp: digest(mp), tp: digest(tp)}
    manifest = json.loads(mp.read_text(encoding='utf-8'))
    validate_manifest(manifest)
    inputs, seen = [], set()
    for s in manifest['sequences']:
        paths = []
        for f in s['frames']:
            p = local_path(mp.parent/f['local_copy'], base)
            if mp.parent not in p.parents or p in seen or digest(p) != f['sha256']:
                raise ValueError('Copie hors lot, dupliquée ou modifiée.')
            paths.append(p); seen.add(p); watched[p] = f['sha256']
        inputs.append((s, paths))
    output.mkdir(parents=True, exist_ok=False)
    progress = dict(status='running', completed_sequences=[])
    write_json(output/'progress.json', progress)
    records = []
    try:
        for s, paths in inputs:
            print('Analyse '+s['sequence_id']+'...', flush=True)
            images = []
            for k, p in enumerate(paths):
                with fits.open(p, mode='readonly', memmap=False) as hdus:
                    if hdus[0].header.get('GARSYNTH') is not True or hdus[0].header.get('SYNCTIME') != TIMES[k]:
                        raise ValueError('Marqueur ou temps synthétique incorrect.')
                    if hdus[0].data is None or hdus[0].data.shape != (256, 256):
                        raise ValueError('Image fictive 256×256 requise.')
                    images.append(hdus[0].data.copy())
            record = process_sequence(images)
            record.update(sequence_id=s['sequence_id'], condition_id=s['condition_id'], seed=s['seed'])
            records.append(record)
            write_json(output/f'{s["sequence_id"]}.json', record)
            progress['completed_sequences'].append(s['sequence_id'])
            write_json(output/'progress.json', progress)
        native = {r['sequence_id']: digest(output/f'{r["sequence_id"]}.json') for r in records}
        # FIRST truth-coordinate parse, after both partitions and all tracks are frozen.
        scored = score(records, json.loads(tp.read_text(encoding='utf-8')), watched[mp])
        if (verify_frozen() != frozen or any(digest(p) != h for p, h in watched.items())
                or any(digest(output/f'{name}.json') != h for name, h in native.items())):
            raise ValueError('Une entrée, recette ou un résultat gelé a changé.')
        result = dict(spatial_result_schema_version='1.0', synthetic_only=True, suite_complete=True,
                      plan_commit=PLAN_COMMIT, frozen_sha256_lf=frozen, manifest_sha256=watched[mp], truth_sha256=watched[tp],
                      sequences=scored, summary=summarize(scored), frozen_report_sha256=native, inputs_unchanged=True,
                      source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      source_tree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
                      recipe_sha256_lf={p.name: sha256(p.read_text(encoding='utf-8').encode('utf-8')).hexdigest()
                                        for p in [Path(__file__), ROOT/'examples/spatial_controls.py']},
                      environment=dict(python=platform.python_version(), numpy=np.__version__, astropy=astropy.__version__, photutils=photutils.__version__, scipy=scipy.__version__),
                      truth_used_for_registration=False, truth_used_for_detection=False, pixels_resampled=False,
                      clock_qualified=False, real_data_performance_validated=False, scientific_submission_certified=False)
        write_reports(output, result)
        progress['status'] = 'complete'
        write_json(output/'progress.json', progress)
    except Exception as exc:
        progress.update(status='incomplete', failed_sequence=s['sequence_id'], error=str(exc))
        write_json(output/'progress.json', progress)
        raise
    print('50 séquences terminées ; critères exploratoires : '+str(result['summary']['exploratory_criteria_passed']), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    make = sub.add_parser('make'); make.add_argument('output', type=Path)
    run = sub.add_parser('run')
    for field in ('manifest', 'truth', 'output'): run.add_argument(field, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'make': make_suite(args.output)
        else:
            result = run_suite(args.manifest, args.truth, args.output)
            raise SystemExit(0 if result['summary']['exploratory_criteria_passed'] else 2)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
