# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Private replay of frozen detector decisions for the in-domain missed additions."""
import argparse
from collections import Counter
import csv
from hashlib import sha256
from pathlib import Path

import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import diagnose_injection_misses as diagnostic
import injection_recovery as experiment
import run_seestar_pilot as pilot
import trace_detector_decisions as tracing

ROOT = Path(__file__).resolve().parents[1]


def recipe_hash():
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def load_diagnosed(score_path, diagnostic_path, base):
    tracing.frozen()
    sp, score, mp, manifest, records, answers, watched = diagnostic.load_scored(score_path, base)
    dp = local_path(diagnostic_path, base); report = experiment.read(dp)
    if (report.get('miss_diagnostic_version') != '1.0' or report.get('status') != 'complete'
            or report.get('diagnostic_recipe_sha256_lf') != diagnostic.recipe_hash()
            or report.get('score_sha256') != watched[sp] or local_path(report['score_path'], base) != sp
            or report.get('source_kind') != manifest['source_kind'] or not report.get('input_hashes_unchanged')
            or report.get('search_rerun') is not False or report.get('thresholds_changed') is not False
            or report.get('frozen_sha256_lf') != diagnostic.frozen()
            or report.get('diagnostic_radii_native_pixels') != list(diagnostic.RADII)
            or report.get('subset_tolerance_native_pixels') != diagnostic.SUBSET_TOLERANCE):
        raise ValueError('Diagnostic complet du lot 19 lié au même score requis.')
    expected = [diagnostic.inspect_case(records[row['case_id']], records['control'], answers[row['case_id']], row, manifest) for row in score['rows'][1:]]
    if report.get('cases') != expected:
        raise ValueError('Preuves individuelles du diagnostic différentes des positions gelées.')
    for key in ('recovered', 'missed', 'unavailable'):
        if report.get(key) != score[key]:
            raise ValueError('Bilan du diagnostic différent du score.')
    watched[dp] = digest(dp)
    selected = [r for r in expected if r['missed'] == 1 and not r.get('outside_speed_domain') and not r.get('outside_time_span')]
    if manifest['source_kind'] == 'real_local_copies' and len(selected) != 17:
        raise ValueError('Le lot réel attendu comporte exactement 17 manques dans le domaine.')
    return sp, dp, score, mp, manifest, records, answers, watched, selected


def write_reports(output, result):
    fields = ['case_id', 'frame_index', 'status_1p5', 'status_3', 'selected_1p5', 'selected_3', 'rejections_1p5', 'rejections_3']
    with (output/'trace.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for case in result['cases']:
            for frame in case['frames']:
                a, b = [frame['evidence_by_radius'][r] for r in ('1.5', '3')]
                writer.writerow(dict(case_id=case['case_id'], frame_index=frame['frame_index'], status_1p5=a['status'], status_3=b['status'],
                    selected_1p5=a['selected_count'], selected_3=b['selected_count'], rejections_1p5=str(a['rejection_counts']), rejections_3=str(b['rejection_counts'])))
    text = '# Trace privée des manques dans le domaine\n\n'
    text += f"Cas examinés : {len(result['cases'])}. Les scores et candidats restent inchangés.\n\n"
    text += f"Contexte conservé : {result['recovered']} ajouts retrouvés, {result['missed']} manqués, dont {result['outside_speed_misses']} hors vitesse.\n\n"
    text += '| Constat par image | Rayon 1,5 pixel natif | Rayon 3 pixels natifs |\n|---|---|---|\n'
    for name in tracing.STATUSES:
        text += f"| {tracing.LABELS[name]} | {result['summary']['1.5'].get(name, 0)} | {result['summary']['3'].get(name, 0)} |\n"
    text += '\n'
    text += '| Injection | Images retenues, rayon 1,5 | Images retenues, rayon 3 |\n|---|---|---|\n'
    for case in result['cases']:
        text += f"| {case['case_id']} | {case['retained_frames_by_radius']['1.5']} | {case['retained_frames_by_radius']['3']} |\n"
    text += '\nLes états par image ne sont pas des essais indépendants. Une absence de maximum brut proche regroupe des possibilités non séparées (seuil, voisinage, séparation, masque, bord). Une proximité de maximum ou de centroïde ne démontre pas son identité. Aucun réglage ni nouvelle trajectoire.\n'
    (output/'report.md').write_text(text, encoding='utf-8')


def run(score_path, diagnostic_path, output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    sp, dp, score, mp, manifest, records, answers, watched, selected = load_diagnosed(score_path, diagnostic_path, base)
    output.mkdir(parents=True, exist_ok=False); (output/'cases').mkdir()
    result = dict(scored_detector_trace_version='1.0', status='running', plan_commit=tracing.PLAN_COMMIT,
        trace_recipe_sha256_lf=tracing.recipe_hash(), scored_recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=tracing.frozen(),
        source_kind=manifest['source_kind'], score_path=str(sp), score_sha256=watched[sp],
        diagnostic_path=str(dp), diagnostic_sha256=watched[dp], manifest_path=str(mp), manifest_sha256=watched[mp],
        thresholds_changed=False, association_rerun=False, new_injections=False, pixel_replay=True,
        recovered=score['recovered'], missed=score['missed'], outside_speed_misses=sum(r['primary'] == 'outside_speed_domain' for r in experiment.read(dp)['cases']),
        expected_cases=len(selected), cases=[], **experiment.provenance())
    experiment.save(output/'trace.json', result)
    try:
        specs = {case['case_id']: case for case in manifest['cases']}
        for old in selected:
            cid = old['case_id']; loaded = {}
            planes = experiment.load_planes(mp, manifest, specs[cid], base, loaded)
            case = dict(case_id=cid, frames=[], retained_frames_by_radius={})
            for k, plane in enumerate(planes):
                saved = diagnostic.points(records[cid]['data']['raw_detections'][k])
                trace = tracing.trace_image(plane, expected_points=(saved-.5)/2)
                answer = answers[cid]['positions'][k]
                target = pilot.from_reference([[answer['x'], answer['y']]], manifest['models'][k])[0]
                evidence = {f'{r:g}': tracing.evidence_at(trace, target, r) for r in diagnostic.RADII}
                case['frames'].append(dict(frame_index=k, trace=trace, evidence_by_radius=evidence,
                    status_stable_across_radii=evidence['1.5']['status'] == evidence['3']['status']))
            for radius in diagnostic.RADII:
                key = f'{radius:g}'
                count = sum(frame['evidence_by_radius'][key]['selected_count'] > 0 for frame in case['frames'])
                if count != old['radii_evidence'][key]['raw']['count']:
                    raise ValueError('Support du rejeu différent du diagnostic gelé.')
                case['retained_frames_by_radius'][key] = count
            experiment.unchanged(loaded)
            case_path = output/'cases'/f'{cid}.json'; experiment.save(case_path, case)
            result['cases'].append(dict(case_id=cid, frames=[dict(frame_index=f['frame_index'], evidence_by_radius=f['evidence_by_radius'], status_stable_across_radii=f['status_stable_across_radii']) for f in case['frames']],
                retained_frames_by_radius=case['retained_frames_by_radius'], file='cases/'+case_path.name, sha256=digest(case_path)))
            experiment.save(output/'trace.json', result)
            print(f"Trace gelée {len(result['cases'])}/{len(selected)} : {cid}.", flush=True)
        all_frames = [f for case in result['cases'] for f in case['frames']]
        result['summary'] = tracing.summarize(all_frames)
        result['rejection_counts_by_radius'] = {f'{r:g}': dict(sorted(sum((Counter(f['evidence_by_radius'][f'{r:g}']['rejection_counts']) for f in all_frames), Counter()).items())) for r in diagnostic.RADII}
        for case in result['cases']:
            if digest(output/case['file']) != case['sha256']:
                raise ValueError('Une trace individuelle a changé pendant le rejeu.')
        experiment.unchanged(watched); tracing.frozen()
        result.update(status='complete', input_hashes_unchanged=True, all_replays_equal=True,
                      inputs_sha256={str(p): h for p, h in watched.items()})
        write_reports(output, result); experiment.save(output/'trace.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); experiment.save(output/'trace.json', result)
        raise
    print(f"Trace terminée : {len(result['cases'])} manques, anciens scores et seuils inchangés.", flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path); parser.add_argument('diagnostic', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        run(args.score, args.diagnostic, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
