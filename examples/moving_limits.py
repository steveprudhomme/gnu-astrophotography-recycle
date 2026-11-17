# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Frozen, descriptive experiment: fictional pixels only; never tunes the detector."""
import argparse
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
from gar.moving import PARAMETERS, run_moving_synthetic
from gar.workset import digest

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (101, 211, 307, 401, 503)
TIMES = np.arange(8, dtype=float) * 10
ENGINE_SHA256 = {
    'src/gar/moving.py': 'f492032e0188310484faaf372db4c96597fd7910ecd3821629edb8365f27be67',
    'src/gar/moving_reports.py': 'b3b543591ad7cbe35dd0c08a92a8aee67b89888a1488f6b80fdbb354a0b6be0c',
}
PLAN_COMMIT = '6f3e6c524cb3678fea43e42f32e83b651ebca684'


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def verify_engine(root=ROOT):
    actual = {name: sha256((root/name).read_text(encoding='utf-8').encode('utf-8')).hexdigest()
              for name in ENGINE_SHA256}
    if actual != ENGINE_SHA256:
        raise ValueError('Le moteur a changé : nouveau plan et nouvel essai nécessaires.')
    return actual


def conditions():
    result = []

    def add(group, name, label, *, peak=120., speed=.5, noise=2., drift=0., rotation=0., control=None):
        result.append(dict(group=group, condition_id=name, label=label, peak_adu=peak,
                           speed_pixels_per_second=speed, noise_sigma_adu=noise,
                           drift_pixels_per_second=drift, rotation_total_degrees=rotation,
                           control=control, out_of_alignment_domain=bool(drift or rotation)))

    for peak in (12., 30., 120.):
        for speed in (.03, .15, .5, 1.2):
            name = f'grid-p{peak:g}-v{speed:g}'.replace('.', 'p')
            add('grid', name, f'Pic {peak:g} ADU ; vitesse {speed:g} pixel/s', peak=peak, speed=speed)
    for noise in (2., 4., 8., 16.):
        add('noise', f'noise-{noise:g}', f'Bruit sigma {noise:g} ADU', peak=30., noise=noise)
    for name, label, drift, rotation in (
        ('aligned', 'Images alignées', 0., 0.),
        ('drift-small', 'Dérive 0,05 pixel/s', .05, 0.),
        ('drift-large', 'Dérive 0,15 pixel/s', .15, 0.),
        ('rotate-small', 'Rotation totale 0,5 degré', 0., .5),
        ('rotate-large', 'Rotation totale 2 degrés', 0., 2.),
        ('combined', 'Dérive 0,15 + rotation 2 degrés', .15, 2.),
    ):
        add('geometry', name, label, drift=drift, rotation=rotation)
    add('controls', 'control-clean', 'Témoin : étoiles et bruit seuls', control='clean')
    add('controls', 'control-defects', 'Témoin : défauts et flashs', control='defects')
    return result


def transform(points, time, condition):
    """Rotate exact source centres, then translate; no pixel interpolation."""
    angle = np.deg2rad(condition['rotation_total_degrees']) * time / 70
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    return ((np.asarray(points) - 127.5) @ rotation.T + 127.5
            + [condition['drift_pixels_per_second'] * time, 0])


def add_source(image, x, y, peak):
    x0, x1 = max(0, int(x)-6), min(256, int(x)+8)
    y0, y1 = max(0, int(y)-6), min(256, int(y)+8)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    image[y0:y1, x0:x1] += peak * np.exp(-((xx-x)**2+(yy-y)**2)/(2*1.3**2))


def make_sequence(folder, condition, seed):
    rng = np.random.default_rng(seed)
    noise_rng = np.random.default_rng(seed + 10000)
    artifact_rng = np.random.default_rng(seed + 20000)
    stars = []
    # Identical field for a seed across ALL conditions; reserve the full longest path.
    while len(stars) < 40:
        x, y = rng.uniform(15, 241, 2)
        if np.hypot(x-np.clip(x, 50, 134), y-85) < 14:
            continue
        if stars and min(np.hypot(x-a, y-b) for a, b, _ in stars) < 9:
            continue
        stars.append((x, y, rng.uniform(500, 1500)))
    name = f'{condition["condition_id"]}-s{seed}'
    frames, positions = [], []
    for k, t in enumerate(TIMES):
        image = noise_rng.normal(100, condition['noise_sigma_adu'], (256, 256))
        for (x, y), (_, _, peak) in zip(transform(np.array(stars)[:, :2], t, condition), stars):
            add_source(image, x, y, peak)
        point = transform([50+condition['speed_pixels_per_second']*t, 85], t, condition)
        if condition['control'] is None:
            add_source(image, *point, condition['peak_adu'])
            positions.append(dict(frame_index=k, x=float(point[0]), y=float(point[1]), visible=True))
        if condition['control'] == 'defects':
            image[30, 30] = image[210, 40] = 4000
            add_source(image, *artifact_rng.uniform(20, 236, 2), 300)
            if k in (2, 3):
                image[100:101, 130:150] += 3000
        path = folder/'copies'/f'{name}-{k:02d}.fit'
        fits.writeto(path, image.astype('float32'), fits.Header({'GARSYNTH': True, 'SYNCTIME': float(t)}))
        frames.append(dict(local_copy=f'copies/{path.name}', sha256=digest(path), relative_time_seconds=float(t)))
    injections = []
    if positions:
        xy = np.array([[p['x'], p['y']] for p in positions])
        velocity = np.linalg.lstsq(np.column_stack([np.ones(8), TIMES]), xy, rcond=None)[0][1]
        injections = [dict(injection_id='mobile-1', positions=positions,
                           velocity_pixels_per_second=velocity.tolist(), peak_adu=condition['peak_adu'])]
    scenario = {'grid': 'faint_slow', 'noise': 'faint_slow', 'geometry': 'jitter', 'controls': 'control'}[condition['group']]
    return (dict(sequence_id=name, scenario=scenario, seed=seed, frames=frames),
            dict(sequence_id=name, injections=injections))


def make_suite(output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    engine = verify_engine()
    output.mkdir(parents=True, exist_ok=False)
    batches = []
    for group in ('grid', 'noise', 'geometry', 'controls'):
        folder = output/group
        (folder/'copies').mkdir(parents=True)
        sequences, truth = [], []
        for condition in conditions():
            if condition['group'] != group:
                continue
            for seed in SEEDS:
                sequence, injection = make_sequence(folder, condition, seed)
                sequences.append(sequence)
                truth.append(injection)
        mp, tp = folder/'manifest.json', folder/'truth.json'
        write_json(mp, dict(moving_schema_version='1.0', synthetic=True,
                            time_kind='fictitious_relative_seconds', sequences=sequences))
        write_json(tp, dict(truth_schema_version='1.0', manifest_sha256=digest(mp), sequences=truth))
        batches.append(dict(group=group, manifest=f'{group}/manifest.json', truth=f'{group}/truth.json',
                            manifest_sha256=digest(mp), truth_sha256=digest(tp)))
    suite = dict(limits_suite_schema_version='1.0', synthetic_only=True, plan_commit=PLAN_COMMIT,
                 engine_sha256_lf=engine, seeds=list(SEEDS), conditions=conditions(), batches=batches)
    write_json(output/'suite.json', suite)
    print('120 séquences fictives créées dans quatre lots.', flush=True)


def validate_suite(suite):
    if (suite.get('limits_suite_schema_version') != '1.0' or suite.get('synthetic_only') is not True
            or suite.get('plan_commit') != PLAN_COMMIT or suite.get('seeds') != list(SEEDS)
            or suite.get('conditions') != conditions() or suite.get('engine_sha256_lf') != ENGINE_SHA256):
        raise ValueError('Protocole incomplet ou différent du plan publié.')
    batches = suite.get('batches')
    if not isinstance(batches, list) or [b.get('group') for b in batches] != ['grid', 'noise', 'geometry', 'controls']:
        raise ValueError('Les quatre lots gelés sont requis dans leur ordre.')
    for batch in batches:
        group = batch['group']
        if batch.get('manifest') != f'{group}/manifest.json' or batch.get('truth') != f'{group}/truth.json':
            raise ValueError('Chemins du protocole incorrects.')


def aggregate(suite, results):
    """No pass/fail sensitivity threshold; require all planned condition/seed pairs."""
    validate_suite(suite)
    if set(results) != {'grid', 'noise', 'geometry', 'controls'}:
        raise ValueError('Ne pas agréger une campagne interrompue ou incomplète.')
    rows = []
    for group, result in results.items():
        if (result.get('synthetic_only') is not True or result.get('truth_used_for_detection') is not False
                or result.get('parameters') != PARAMETERS
                or result.get('inputs_sha256_before') != result.get('inputs_sha256_after')):
            raise ValueError('Résultat non gelé ou intégrité incohérente.')
        expected = {f'{c["condition_id"]}-s{s}': (c, s) for c in conditions() if c['group'] == group for s in SEEDS}
        sequences = result['sequences']
        if len(sequences) != len(expected) or {s['sequence_id'] for s in sequences} != set(expected):
            raise ValueError('Séquences manquantes ou dupliquées.')
        for sequence in sequences:
            c, seed = expected[sequence['sequence_id']]
            e = sequence['evaluation']
            injected = int(c['control'] is None)
            if (sequence['seed'] != seed or sequence['relative_times_seconds'] != TIMES.tolist()
                    or sequence['image_shape'] != [256, 256] or e['injected'] != injected
                    or e['recovered'] + e['missed'] != injected
                    or e['false_candidates'] + e['recovered'] != len(sequence['tracks'])):
                raise ValueError('Bilan de séquence incohérent.')
            rows.append(dict(group=group, condition_id=c['condition_id'], seed=seed,
                             sequence_id=sequence['sequence_id'], out_of_alignment_domain=c['out_of_alignment_domain'],
                             injected=e['injected'], recovered=e['recovered'], missed=e['missed'],
                             false_candidates=e['false_candidates'], matches=e['matches'],
                             false_candidate_rates=sequence['false_candidate_rates']))
    totals = []
    for c in conditions():
        selected = [r for r in rows if r['condition_id'] == c['condition_id']]
        errors = [e for r in selected for m in r['matches'] for e in m['position_errors_pixels']]
        velocities = [m['velocity_vector_error_pixels_per_second'] for r in selected for m in r['matches']]
        injected = sum(r['injected'] for r in selected)
        recovered = sum(r['recovered'] for r in selected)
        false = sum(r['false_candidates'] for r in selected)
        totals.append(dict(**c, repetitions=len(selected), injected=injected, recovered=recovered,
                           missed=injected-recovered, false_candidates=false,
                           recall=recovered/injected if injected else None,
                           position_p95_pixels=float(np.percentile(errors, 95)) if errors else None,
                           max_velocity_error_pixels_per_second=max(velocities) if velocities else None,
                           false_candidates_per_frame=false/40,
                           false_candidates_per_megapixel_frame=false/(40*256*256/1e6),
                           false_candidates_per_fictitious_hour=false/(5*70/3600)))
    return dict(limits_result_schema_version='1.0', synthetic_only=True, descriptive_only=True,
                suite_complete=True, plan_commit=PLAN_COMMIT, engine_sha256_lf=ENGINE_SHA256,
                detector_parameters=PARAMETERS, sequence_count=len(rows), image_count=len(rows)*8,
                injected_total=sum(r['injected'] for r in rows), rows=rows, conditions=totals,
                clock_qualified=False, real_data_performance_validated=False,
                scientific_submission_certified=False, truth_used_for_detection=False)


def write_summary(output, result):
    write_json(output/'limits.json', result)
    fields = ['group', 'condition_id', 'seed', 'sequence_id', 'out_of_alignment_domain',
              'injected', 'recovered', 'missed', 'false_candidates']
    with (output/'sequences.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(result['rows'])
    text = ('# Limites du détecteur gelé — données synthétiques\n\n'
            '120 séquences complètes ; bilan descriptif, sans verdict scientifique global. '
            'Cinq répétitions par condition ; champs et bruits appariés entre conditions. '
            'Erreurs de position/vitesse calculées uniquement sur les objets appariés.\n\n'
            '| Condition | Retrouvés / injectés | Manqués | Faux candidats | Hors alignement |\n'
            '|---|---:|---:|---:|---|\n')
    for c in result['conditions']:
        text += (f'| {c["label"]} | {c["recovered"]}/{c["injected"]} | {c["missed"]} '
                 f'| {c["false_candidates"]} | {"oui" if c["out_of_alignment_domain"] else "non"} |\n')
    text += ('\nLes témoins 0/0 ont un rappel indéfini. Les cas géométriques non alignés '
             'violent volontairement le domaine du moteur : les étoiles entraînées peuvent devenir '
             'des faux candidats. Une rotation rend aussi la vérité légèrement courbe. '
             'Les secondes, niveaux ADU et objets sont fictifs. Aucune magnitude limite, '
             'probabilité universelle, performance Seestar ou horloge réelle qualifiée. '
             'Les rapports natifs conservent un verdict de suite initiale incomplet (attendu).\n')
    (output/'report.md').write_text(text, encoding='utf-8')


def run_suite(suite_path, output, base=None):
    base = ROOT/'local' if base is None else base
    suite_path, output = [local_path(p, base) for p in (suite_path, output)]
    engine = verify_engine()
    suite_hash = digest(suite_path)
    suite = json.loads(suite_path.read_text(encoding='utf-8'))
    validate_suite(suite)
    # Validate every planned input before creating any result directory.
    inputs = {}
    for batch in suite['batches']:
        for role in ('manifest', 'truth'):
            path = local_path(suite_path.parent/batch[role], base)
            if digest(path) != batch[f'{role}_sha256']:
                raise ValueError('Une entrée du protocole a changé.')
            inputs[f'{batch["group"]}/{role}'] = (path, digest(path))
    output.mkdir(parents=True, exist_ok=False)
    progress = dict(status='running', completed_batches=[], failed_batch=None)
    write_json(output/'progress.json', progress)
    results, native_hashes = {}, {}
    try:
        for batch in suite['batches']:
            group = batch['group']
            print(f'Analyse du lot {group}...', flush=True)
            result = run_moving_synthetic(inputs[f'{group}/manifest'][0], inputs[f'{group}/truth'][0], output/group, base)
            results[group] = result
            native_hashes[group] = digest(output/group/'moving.json')
            progress['completed_batches'].append(group)
            write_json(output/'progress.json', progress)
        result = aggregate(suite, results)
        if (digest(suite_path) != suite_hash or verify_engine() != engine
                or any(digest(p) != h for p, h in inputs.values())
                or any(digest(output/g/'moving.json') != h for g, h in native_hashes.items())):
            raise ValueError('Le protocole, moteur ou un rapport a changé pendant le traitement.')
        for raw in results.values():
            for sequence in raw['sequences']:
                group = next(r['group'] for r in result['rows'] if r['sequence_id'] == sequence['sequence_id'])
                manifest = json.loads(inputs[f'{group}/manifest'][0].read_text(encoding='utf-8'))
                frames = next(s['frames'] for s in manifest['sequences'] if s['sequence_id'] == sequence['sequence_id'])
                for frame in frames:
                    path = local_path(inputs[f'{group}/manifest'][0].parent/frame['local_copy'], base)
                    if digest(path) != frame['sha256']:
                        raise ValueError('Une image a changé avant le bilan final.')
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        result.update(suite_sha256=suite_hash, native_report_sha256=native_hashes, source_revision=revision,
                      source_tree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
                      runner_sha256_lf=sha256(Path(__file__).read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                      environment=dict(python=platform.python_version(), numpy=np.__version__, astropy=astropy.__version__,
                                       photutils=photutils.__version__, scipy=scipy.__version__))
        write_summary(output, result)
        progress['status'] = 'complete'
        write_json(output/'progress.json', progress)
    except Exception as exc:
        progress.update(status='incomplete', failed_batch=batch['group'], error=str(exc))
        write_json(output/'progress.json', progress)
        raise
    print('120 séquences analysées ; bilan descriptif complet, sans qualification réelle.', flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    make = commands.add_parser('make', help='Fabriquer les 120 séquences fictives gelées')
    make.add_argument('output', type=Path)
    run = commands.add_parser('run', help='Mesurer sans modifier le moteur')
    run.add_argument('suite', type=Path)
    run.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'make':
            make_suite(args.output)
        else:
            run_suite(args.suite, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
