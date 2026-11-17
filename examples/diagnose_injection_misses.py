# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Post-score evidence from frozen positions only; never reruns the search."""
import argparse
from collections import Counter
import csv
from hashlib import sha256
from pathlib import Path
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import injection_recovery as experiment
import run_seestar_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = 'b69ca0894acb40c404856ecf482eaf014e799332'
INJECTION_HASH = '7f0ed216d7822180f88e2f761ffe95968805946f9771cc8b03effa8c8d842b94'
RADII = (1.5, 3.)
SUBSET_TOLERANCE = 1e-9
LABELS = dict(recovered='Retrouvée', unavailable='Indisponible',
    outside_speed_domain='Vitesse hors plage prévue', outside_time_span='Durée totale trop courte',
    raw_support_limited='Support limité dès les détections', overlap_support_lost='Support perdu au champ commun',
    stationary_support_lost='Support perdu au filtre stationnaire', association_unresolved='Association : raison interne non établie',
    neighborhood_ambiguous='Voisinage ambigu')


def recipe_hash():
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def frozen():
    if experiment.recipe_hash() != INJECTION_HASH:
        raise ValueError('Recette d’injection modifiée : nouveau diagnostic/version requis.')
    return dict(experiment.frozen(), **{'examples/injection_recovery.py': INJECTION_HASH})


def points(value):
    a = np.asarray(value, dtype=float)
    if a.size == 0:
        return np.empty((0, 2))
    if a.ndim != 2 or a.shape[1] != 2 or not np.isfinite(a).all():
        raise ValueError('Tableau de positions finies à deux coordonnées requis.')
    return a


def subset_indices(parent, child):
    """Validate an ordered subset; tolerance only handles numerical serialization."""
    result, previous = [], -1
    for p in child:
        matches = np.flatnonzero(np.linalg.norm(parent-p, axis=1) <= SUBSET_TOLERANCE)
        if len(matches) != 1 or matches[0] <= previous:
            raise ValueError('Un tableau filtré n’est pas un sous-ensemble ordonné unique.')
        previous = int(matches[0]); result.append(previous)
    return result


def nearest(a, target):
    if not len(a):
        return None
    distances = np.linalg.norm(a-target, axis=1); index = int(np.argmin(distances))
    return dict(index=index, distance_native_pixels=float(distances[index]), x=float(a[index, 0]), y=float(a[index, 1]))


def support(frames, key, radius, times):
    selected = [k for k, f in enumerate(frames) if f[key] is not None and f[key]['distance_native_pixels'] <= radius]
    span = float(times[selected[-1]]-times[selected[0]]) if selected else None
    enough = len(selected) >= pilot.MOVING_PARAMETERS['minimum_frames'] and span >= pilot.MOVING_PARAMETERS['minimum_span_seconds']
    return dict(frame_indices=selected, count=len(selected), span_declared_seconds=span, enough=bool(enough))


def limiting_stage(evidence):
    for stage, category in [('raw', 'raw_support_limited'), ('common', 'overlap_support_lost'), ('kept', 'stationary_support_lost')]:
        if not evidence[stage]['enough']:
            return category
    return 'association_unresolved'


def inspect_case(record, control, answer, score_row, manifest):
    """Truth proximity is diagnostic evidence, not an identity or new candidate."""
    result = dict(case_id=record['case_id'], recovered=score_row['recovered'], missed=score_row['missed'],
                  available=score_row['available'], primary='unavailable', frames=[], radii_evidence={},
                  primary_is_proven_physical_cause=False)
    if not score_row['available']:
        return result
    control_available = control['search_status'] == 'complete'
    result['control_evidence_available'] = control_available
    data = record['data']; times = manifest['relative_declared_seconds']
    if (len(times) != 8 or [p['frame_index'] for p in answer['positions']] != list(range(8))
            or any(len(data[key]) != 8 for key in ('raw_detections', 'mapped_detections'))
            or len(data['search']['residual_detections']) != 8
            or len(data['search']['stationary_removed_per_frame']) != 8
            or len(data['overlap_excluded_per_frame']) != 8
            or (control_available and len(control['data']['raw_detections']) != 8)):
        raise ValueError('Huit tableaux cohérents par étape requis.')
    for k, truth in enumerate(answer['positions']):
        target = np.array([truth['x'], truth['y']], dtype=float)
        raw = pilot.to_reference(points(data['raw_detections'][k]), manifest['models'][k])
        common = points(data['mapped_detections'][k]); kept = points(data['search']['residual_detections'][k])
        control_raw = pilot.to_reference(points(control['data']['raw_detections'][k]), manifest['models'][k]) if control_available else np.empty((0, 2))
        raw_ids = subset_indices(raw, common); kept_ids = subset_indices(common, kept)
        if data['overlap_excluded_per_frame'][k] != len(raw)-len(common):
            raise ValueError('Effectif exclu du champ commun différent des tableaux gelés.')
        if data['search']['stationary_removed_per_frame'][k] != len(common)-len(kept):
            raise ValueError('Effectif retiré différent des tableaux gelés.')
        close_common = nearest(common, target)
        result['frames'].append(dict(frame_index=k, relative_declared_seconds=times[k],
            truth_x=float(target[0]), truth_y=float(target[1]), raw=nearest(raw, target), common=close_common,
            kept=nearest(kept, target), control=nearest(control_raw, target),
            closest_common_was_removed=close_common is not None and close_common['index'] not in kept_ids,
            raw_count=len(raw), common_count=len(common), kept_count=len(kept), common_raw_indices=raw_ids,
            kept_common_indices=kept_ids))
    for radius in RADII:
        evidence = {key: support(result['frames'], key, radius, times) for key in ('raw', 'common', 'kept')}
        evidence['control'] = support(result['frames'], 'control', radius, times) if control_available else None
        evidence['limiting_stage'] = limiting_stage(evidence)
        result['radii_evidence'][f'{radius:g}'] = evidence
    stages = [result['radii_evidence'][f'{r:g}']['limiting_stage'] for r in RADII]
    result['limiting_stage_stable_across_radii'] = stages[0] == stages[1]
    v = float(np.linalg.norm(answer['velocity_native_per_declared_second']))
    params = pilot.MOVING_PARAMETERS
    result['injected_speed_native_per_declared_second'] = v
    result['outside_speed_domain'] = not params['speed_min_pixels_per_second'] <= v <= params['speed_max_pixels_per_second']
    result['outside_time_span'] = times[-1]-times[0] < params['minimum_span_seconds']
    if score_row['recovered']:
        result['primary'] = 'recovered'
    elif result['outside_speed_domain']:
        result['primary'] = 'outside_speed_domain'
    elif result['outside_time_span']:
        result['primary'] = 'outside_time_span'
    elif not result['limiting_stage_stable_across_radii']:
        result['primary'] = 'neighborhood_ambiguous'
    else:
        result['primary'] = stages[0]
    return result


def load_scored(score_path, base):
    frozen()
    sp = local_path(score_path, base); score = experiment.read(sp)
    if score.get('injection_score_version') != '1.0' or score.get('status') != 'complete' or not score.get('inputs_unchanged'):
        raise ValueError('Score complet sur entrées intactes requis.')
    mp, manifest, watched = experiment.load_manifest(score['manifest_path'], base)
    ap, tp = [local_path(score[k], base) for k in ('analysis_path', 'truth_path')]
    for p, key in [(mp, 'manifest_sha256'), (ap, 'analysis_sha256')]:
        if digest(p) != score[key]:
            raise ValueError('Une entrée liée au score est modifiée.')
    records = experiment.sealed_records(ap, watched[mp], base, watched)
    experiment.verify_derivatives(mp, manifest, base, watched)
    # Truth is opened only after the completed score and every candidate hash passed.
    if digest(tp) != score['truth_sha256']:
        raise ValueError('La vérité liée au score est modifiée.')
    watched[tp] = digest(tp); truth = experiment.read(tp); watched[sp] = digest(sp)
    if (truth.get('injection_truth_version') != '1.0' or truth.get('manifest_sha256') != watched[mp]
            or [r['case_id'] for r in truth.get('cases', [])] != [c['case_id'] for c in experiment.conditions()]
            or [r['case_id'] for r in score.get('rows', [])] != list(records)
            or score.get('source_kind') != manifest['source_kind']):
        raise ValueError('Score et vérité liés au même protocole requis.')
    answers = {r['case_id']: r for r in truth['cases']}
    for row, spec in zip(score['rows'], [dict(case_id='control'), *experiment.conditions()]):
        if any(row.get(k) != v for k, v in spec.items()):
            raise ValueError('Description du score incohérente.')
        expected = experiment.score_one(records[row['case_id']], answers.get(row['case_id']))
        if any(row.get(k) != v for k, v in expected.items()):
            raise ValueError('Appariement du score différent des candidats gelés.')
    if (score['recovered'] != sum(r['recovered'] or 0 for r in score['rows'][1:])
            or score['missed'] != sum(r['missed'] or 0 for r in score['rows'][1:])
            or score['unavailable'] != sum(not r['available'] for r in score['rows'][1:])):
        raise ValueError('Comptes du score incohérents.')
    return sp, score, mp, manifest, records, answers, watched


def write_reports(output, result):
    with (output/'diagnostic.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['case_id', 'available', 'recovered', 'missed', 'primary', 'limiting_stage_stable_across_radii']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({k: r.get(k) for k in fields} for r in result['cases'])
    text = '# Diagnostic descriptif après score — rapport local\n\n'
    text += f"Retrouvées : {result['recovered']}. Manquées : {result['missed']}. Indisponibles : {result['unavailable']}.\n\n"
    text += '| Constat principal parmi les manques | Nombre |\n|---|---|\n'
    for name, count in result['missed_categories'].items():
        text += f'| {LABELS[name]} | {count} |\n'
    text += ('\nUne absence de détection proche ne prouve pas un manque de luminosité. Une source dans le témoin '
             'est un indice de confusion possible, pas une identité astrophysique ou une cause établie. '
             'Le rayon de contexte ne change aucun seuil du moteur. Les neuf vitesses trop lentes peuvent cumuler '
             'd’autres pertes ; la catégorie de protocole ne cache pas les preuves par image. Aucun candidat créé ou modifié.\n')
    text += '\n| Injection | Constat | Détections proches (1,5 / 3 pixels) | Après filtre (1,5 / 3) |\n|---|---|---|---|\n'
    for row in result['cases']:
        a, b = row['radii_evidence'].get('1.5'), row['radii_evidence'].get('3')
        text += f"| {row['case_id']} | {LABELS[row['primary']]} | {str(a['raw']['count'])+' / '+str(b['raw']['count']) if a else 'inconnu'} | {str(a['kept']['count'])+' / '+str(b['kept']['count']) if a else 'inconnu'} |\n"
    (output/'report.md').write_text(text, encoding='utf-8')


def diagnose(score_path, output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    sp, score, mp, manifest, records, answers, watched = load_scored(score_path, base)
    output.mkdir(parents=True, exist_ok=False)
    result = dict(miss_diagnostic_version='1.0', status='running', plan_commit=PLAN_COMMIT,
        diagnostic_recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=frozen(), score_path=str(sp), score_sha256=watched[sp],
        source_kind=manifest['source_kind'], diagnostic_radii_native_pixels=list(RADII), subset_tolerance_native_pixels=SUBSET_TOLERANCE,
        search_rerun=False, thresholds_changed=False, physical_causes_proven=False, cases=[],
        **experiment.provenance())
    experiment.save(output/'diagnostic.json', result)
    try:
        for row in score['rows'][1:]:
            result['cases'].append(inspect_case(records[row['case_id']], records['control'], answers[row['case_id']], row, manifest))
            experiment.save(output/'diagnostic.json', result)
        missed = [r for r in result['cases'] if r['missed'] == 1]
        categories = dict(sorted(Counter(r['primary'] for r in missed).items()))
        result.update(recovered=score['recovered'], missed=score['missed'], unavailable=score['unavailable'],
                      missed_categories=categories,
                      outside_speed_misses=sum(r['primary'] == 'outside_speed_domain' for r in missed),
                      other_misses=sum(r['primary'] != 'outside_speed_domain' for r in missed),
                      representatives={name: min(r['case_id'] for r in missed if r['primary'] == name) for name in categories})
        if len(missed) != score['missed'] or sum(categories.values()) != score['missed']:
            raise ValueError('Diagnostic non réconcilié avec les manques gelés.')
        write_reports(output, result)
        experiment.unchanged(watched); frozen()
        result.update(status='complete', input_hashes_unchanged=True)
        experiment.save(output/'diagnostic.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); experiment.save(output/'diagnostic.json', result)
        raise
    print(f"Diagnostic de {result['missed']} manques : {categories}. Recherche et seuils inchangés.", flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('score', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        diagnose(args.score, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
