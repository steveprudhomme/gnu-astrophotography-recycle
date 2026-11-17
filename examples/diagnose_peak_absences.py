# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Diagnose the frozen cohort of absent raw peaks using existing local caches."""
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
import trace_detector_decisions as previous
import trace_scored_misses as scored
import trace_peak_creation as tracing

ROOT = Path(__file__).resolve().parents[1]


def recipe_hash():
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def load_traced(score_path, diagnostic_path, trace_path, base):
    tracing.frozen()
    sp, dp, score, mp, manifest, records, answers, watched, selected = scored.load_diagnosed(score_path, diagnostic_path, base)
    tp = local_path(trace_path, base); old = experiment.read(tp)
    if (old.get('scored_detector_trace_version') != '1.0' or old.get('status') != 'complete'
            or old.get('source_kind') != manifest['source_kind'] or old.get('score_sha256') != watched[sp]
            or old.get('diagnostic_sha256') != watched[dp] or old.get('manifest_sha256') != watched[mp]
            or local_path(old['score_path'], base) != sp or local_path(old['diagnostic_path'], base) != dp
            or local_path(old['manifest_path'], base) != mp
            or old.get('trace_recipe_sha256_lf') != previous.recipe_hash() or old.get('scored_recipe_sha256_lf') != scored.recipe_hash()
            or old.get('frozen_sha256_lf') != previous.frozen() or old.get('input_hashes_unchanged') is not True
            or old.get('all_replays_equal') is not True or old.get('thresholds_changed') is not False
            or old.get('association_rerun') is not False or old.get('new_injections') is not False
            or old.get('pixel_replay') is not True or old.get('expected_cases') != len(selected)
            or [r['case_id'] for r in old.get('cases', [])] != [r['case_id'] for r in selected]
            or old.get('inputs_sha256') != {str(p): value for p, value in watched.items()}):
        raise ValueError('Trace complète du lot 20 liée aux mêmes entrées intactes requise.')
    for key in ('recovered', 'missed'):
        if old.get(key) != score[key]:
            raise ValueError('Contexte du score modifié dans la trace.')
    outside = sum(row['primary'] == 'outside_speed_domain' for row in experiment.read(dp)['cases'])
    if old.get('outside_speed_misses') != outside:
        raise ValueError('Exclusions de vitesse modifiées dans la trace.')
    rows = {}; all_frames = []; cohort_count = 0
    for item, original in zip(old['cases'], selected):
        cid = item['case_id']; path = local_path(tp.parent/item['file'], base)
        if tp.parent not in path.parents or path in watched or digest(path) != item['sha256']:
            raise ValueError('Trace individuelle modifiée, répétée ou hors du lot.')
        case = experiment.read(path); watched[path] = digest(path)
        if case.get('case_id') != cid or [f['frame_index'] for f in case.get('frames', [])] != list(range(8)):
            raise ValueError('Huit traces distinctes par cas requises.')
        short_frames = []
        for k, frame in enumerate(case['frames']):
            trace = frame['trace']; saved = np.asarray(records[cid]['data']['raw_detections'][k], dtype=float).reshape(-1, 2)
            if trace.get('replay_equal') is not True or trace.get('saved_positions_checked') is not True:
                raise ValueError('Preuve du rejeu précédent absente.')
            previous.equal_points(2*np.asarray(trace['selected_points_reduced']).reshape(-1, 2)+.5, saved, 'trace gelée contre positions enregistrées')
            raw_indices = [row.get('raw_index') for row in trace['rows']]
            if raw_indices != list(range(len(raw_indices))):
                raise ValueError('Indices de maxima bruts incohérents.')
            reconstructed = np.asarray([row['centroid_xy_reduced'] for row in trace['rows'] if row['project_kept']], dtype=float).reshape(-1, 2)
            previous.equal_points(reconstructed, trace['selected_points_reduced'], 'points conservés de la trace')
            answer = answers[cid]['positions'][k]
            target = pilot.from_reference([[answer['x'], answer['y']]], manifest['models'][k])[0]
            evidence = {f'{r:g}': previous.evidence_at(trace, target, r) for r in previous.diagnostic.RADII}
            stable = evidence['1.5']['status'] == evidence['3']['status']
            if frame['evidence_by_radius'] != evidence or frame.get('status_stable_across_radii') != stable:
                raise ValueError('Preuves de proximité du lot 20 altérées.')
            short_frames.append(dict(frame_index=k, evidence_by_radius=evidence, status_stable_across_radii=stable))
            cohort = all(evidence[r]['status'] == 'no_near_raw_maximum' for r in ('1.5', '3'))
            cohort_count += cohort
            frame['in_absent_cohort'] = cohort
        if item['frames'] != short_frames:
            raise ValueError('Résumé individuel différent de la trace gelée.')
        counts = {f'{r:g}': sum(f['evidence_by_radius'][f'{r:g}']['selected_count'] > 0 for f in case['frames']) for r in previous.diagnostic.RADII}
        expected_counts = {f'{r:g}': original['radii_evidence'][f'{r:g}']['raw']['count'] for r in previous.diagnostic.RADII}
        if item.get('retained_frames_by_radius') != counts or case.get('retained_frames_by_radius') != counts or counts != expected_counts:
            raise ValueError('Supports de la trace différents du diagnostic gelé.')
        all_frames.extend(case['frames']); rows[cid] = case
    if old.get('summary') != previous.summarize(all_frames):
        raise ValueError('Bilan de la trace gelée incohérent.')
    expected_rejections = {f'{r:g}': dict(sorted(sum((Counter(f['evidence_by_radius'][f'{r:g}']['rejection_counts']) for f in all_frames), Counter()).items())) for r in previous.diagnostic.RADII}
    if old.get('rejection_counts_by_radius') != expected_rejections:
        raise ValueError('Bilan des rejets de la trace gelée incohérent.')
    if manifest['source_kind'] == 'real_local_copies' and (len(all_frames) != 136 or cohort_count != 115):
        raise ValueError('La cohorte réelle gelée doit contenir 115 absences et 21 situations contextuelles.')
    watched[tp] = digest(tp)
    return sp, dp, tp, score, mp, manifest, records, answers, watched, rows, cohort_count


def write_reports(output, result):
    fields = ['case_id', 'frame_index', 'in_absent_cohort', 'first_empty_1p5', 'first_empty_3', 'threshold', 'independent_passes_1p5', 'independent_passes_3']
    with (output/'trace.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for case in result['cases']:
            for frame in case['frames']:
                a, b = [frame['evidence_by_radius'][key] for key in ('1.5', '3')]
                writer.writerow(dict(case_id=case['case_id'], frame_index=frame['frame_index'],
                    in_absent_cohort=frame['in_absent_cohort'], first_empty_1p5=a['first_empty_stage'], first_empty_3=b['first_empty_stage'],
                    threshold=frame['threshold_effective'], independent_passes_1p5=str(a['independent_pass_counts']), independent_passes_3=str(b['independent_pass_counts'])))
    text = '# Diagnostic privé des absences de maxima\n\n'
    text += f"Cohorte fixe : {result['absent_cohort_count']} situations ; contexte : {result['context_count']}.\n\n"
    text += f"Scores conservés : {result['recovered']} ajouts retrouvés, {result['missed']} manqués, dont {result['outside_speed_misses']} hors vitesse.\n\n"
    text += '| Première porte vide, cohorte seulement | Rayon 1,5 | Rayon 3 |\n|---|---|---|\n'
    for stage in tracing.LABELS:
        text += f"| {tracing.LABELS[stage]} | {result['summary']['1.5'].get(stage, 0)} | {result['summary']['3'].get(stage, 0)} |\n"
    text += '\nLe premier zéro est une étape descriptive. Les obstacles simultanés, seuils numériques, meilleurs échantillons et voisins restent dans le JSON. Une réponse convoluée n’est ni flux ni rapport signal/bruit photométrique. Les images réutilisent les mêmes fonds ; aucune cause physique exclusive ou identité de voisin n’est démontrée. Seuils, scores et candidats inchangés.\n'
    (output/'report.md').write_text(text, encoding='utf-8')


def run(score_path, diagnostic_path, trace_path, output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    sp, dp, tp, score, mp, manifest, records, answers, watched, old_cases, cohort_count = load_traced(score_path, diagnostic_path, trace_path, base)
    output.mkdir(parents=True, exist_ok=False); (output/'cases').mkdir()
    result = dict(peak_absence_diagnostic_version='1.0', status='running', plan_commit=tracing.PLAN_COMMIT,
        trace_recipe_sha256_lf=tracing.recipe_hash(), diagnostic_recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=tracing.frozen(),
        source_kind=manifest['source_kind'], score_path=str(sp), score_sha256=watched[sp],
        diagnostic_path=str(dp), diagnostic_sha256=watched[dp], prior_trace_path=str(tp), prior_trace_sha256=watched[tp],
        thresholds_changed=False, association_rerun=False, new_injections=False, pixel_replay=True,
        recovered=score['recovered'], missed=score['missed'], absent_cohort_count=cohort_count,
        outside_speed_misses=sum(row['primary'] == 'outside_speed_domain' for row in experiment.read(dp)['cases']),
        context_count=8*len(old_cases)-cohort_count, expected_cases=len(old_cases), cases=[], **experiment.provenance())
    experiment.save(output/'trace.json', result)
    try:
        specs = {item['case_id']: item for item in manifest['cases']}
        for cid, old_case in old_cases.items():
            loaded = {}; planes = experiment.load_planes(mp, manifest, specs[cid], base, loaded)
            case = dict(case_id=cid, frames=[])
            for k, plane in enumerate(planes):
                old_frame = old_case['frames'][k]
                trace = tracing.trace_image(plane, expected_trace=old_frame['trace'])
                target = old_frame['evidence_by_radius']['1.5']['target_native']
                evidence = {f'{r:g}': tracing.evidence_at(trace, target, r) for r in previous.diagnostic.RADII}
                case['frames'].append(dict(frame_index=k, in_absent_cohort=old_frame['in_absent_cohort'],
                    trace=tracing.serializable_trace(trace), evidence_by_radius=evidence,
                    status_stable_across_radii=evidence['1.5']['first_empty_stage'] == evidence['3']['first_empty_stage']))
            experiment.unchanged(loaded)
            path = output/'cases'/f'{cid}.json'; experiment.save(path, case)
            result['cases'].append(dict(case_id=cid, file='cases/'+path.name, sha256=digest(path),
                frames=[dict(frame_index=f['frame_index'], in_absent_cohort=f['in_absent_cohort'], threshold_effective=f['trace']['threshold_effective'],
                    evidence_by_radius=f['evidence_by_radius'], status_stable_across_radii=f['status_stable_across_radii']) for f in case['frames']]))
            experiment.save(output/'trace.json', result)
            print(f"Création des maxima retracée {len(result['cases'])}/{len(old_cases)} : {cid}.", flush=True)
        frames = [frame for case in result['cases'] for frame in case['frames']]
        cohort = [f for f in frames if f['in_absent_cohort']]
        if len(cohort) != cohort_count:
            raise ValueError('La cohorte gelée a changé pendant le diagnostic.')
        result.update(summary=tracing.summarize(cohort), context_summary=tracing.summarize([f for f in frames if not f['in_absent_cohort']]))
        # Explicit counts are easier to audit than treating the first empty gate as exclusive.
        result['independent_obstacles'] = {f'{r:g}': {key: sum(f['evidence_by_radius'][f'{r:g}']['independent_pass_counts'][key] == 0 for f in cohort)
            for key in ('local_maximum', 'unmasked', 'inside_border', 'above_threshold')} for r in previous.diagnostic.RADII}
        for case in result['cases']:
            if digest(output/case['file']) != case['sha256']:
                raise ValueError('Une nouvelle trace individuelle a changé.')
        experiment.unchanged(watched); tracing.frozen()
        result.update(status='complete', input_hashes_unchanged=True, all_replays_equal=True,
            inputs_sha256={str(p): value for p, value in watched.items()})
        write_reports(output, result); experiment.save(output/'trace.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); experiment.save(output/'trace.json', result)
        raise
    print(f"Diagnostic terminé : {cohort_count} absences, {result['context_count']} situations de contexte, seuils intacts.", flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('score', 'diagnostic', 'trace', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        run(args.score, args.diagnostic, args.trace, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
