# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Replay frozen slow-study pixels before opening their answers; no new tracks."""
import argparse
from collections import Counter
import csv
from pathlib import Path
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import diagnose_slow_misses as diagnostic
import trace_peak_creation as peaks

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = '61fc2b8181cfae8f851471cce55004f1cc995ead'
CASE_ID = 'r10-a12-p1'
VARIANTS = ('control', CASE_ID)
RADII = (1.5, 3.)
PINS = {
    'examples/diagnose_slow_misses.py': 'b63f95c8943227521adb0d7767612ffab8948a18a8ae4c7af487c8a41cba7b0c',
    'examples/make_asymmetric_slow_demo.py': 'ff21075c98d2a1d2e877051a0aa9f76ae4102ad9fb6e7e955478727b88aea662',
    'examples/trace_detector_decisions.py': 'f9c69b76f504bed9b54867ef2965fee677708b517131062c0d3fc4171a668de4',
    'examples/trace_peak_creation.py': '71bff6e0b793bf693d03e444a4949e82888c883a2f1effe54dee9daa418d89c7',
}
slow = diagnostic.slow


def frozen():
    result = dict(diagnostic.historical(), **peaks.frozen())
    for name, expected in PINS.items():
        if diagnostic.source_hash(ROOT/name) != expected:
            raise ValueError('Une recette historique de trace ou du banc a changé.')
    return dict(result, **PINS)


def preflight(score_path, base):
    """Verify sealed inputs and candidates without parsing or opening truth."""
    sp = local_path(score_path, base); before = digest(sp); score = slow.read(sp)
    if (score.get('slow_motion_score_version') != '1.0' or score.get('status') != 'complete'
            or score.get('inputs_unchanged') is not True or score.get('source_kind') != 'synthetic_demo'
            or score.get('recipe_sha256_lf') != slow.recipe_hash()
            or score.get('frozen_sha256_lf') != slow.frozen()):
        raise ValueError('Un score fictif complet et gelé du profil lent est requis.')
    mp, manifest, watched = slow.load_manifest(score['manifest_path'], base)
    ap = local_path(score['analysis_path'], base)
    if digest(mp) != score['manifest_sha256'] or digest(ap) != score['analysis_sha256']:
        raise ValueError('Une entrée liée au score a changé.')
    records = slow.sealed_records(ap, watched[mp], base, watched, manifest['conditions'])
    slow.verify_derivatives(mp, manifest, base, watched)
    if manifest['source_kind'] != 'synthetic_demo' or any(records[c]['search_status'] != 'complete' for c in VARIANTS):
        raise ValueError('Les deux séries fictives choisies doivent être disponibles.')
    watched[sp] = before
    return sp, manifest, records, watched


def crop_view(plane, trace, target):
    center = (np.asarray(target)-.5)/2
    x, y = np.floor(center).astype(int)
    left, right = max(0, x-16), min(plane.shape[1], x+17)
    bottom, top = max(0, y-16), min(plane.shape[0], y+17)
    pixels = np.asarray(plane[bottom:top, left:right], dtype=float)
    # Nonfinite pixels are serialized explicitly; matplotlib later treats None as NaN.
    original = [[float(v) if np.isfinite(v) else None for v in row] for row in pixels]
    return dict(left_reduced=int(left), bottom_reduced=int(bottom), original_pixels=original,
                convolved_over_threshold=(trace['convolved'][bottom:top, left:right]/trace['threshold_effective']).tolist(),
                target_reduced=center.tolist(), display_only=True)


def pair_evidence(k, manifest, answer, traces, planes, entries):
    point = answer['positions'][k]
    target = diagnostic.pilot.from_reference(np.array([[point['x'], point['y']]]), manifest['models'][k])[0]
    result = dict(frame_index=k, focus=k < 3, declared_relative_seconds=manifest['relative_declared_seconds'][k],
                  target_source_native=target.tolist(), phase_reduced_pixels=(((target-.5)/2)%1).tolist(), variants={})
    for cid in VARIANTS:
        trace = traces[cid][k]; old = trace['old_detector_trace']
        result['variants'][cid] = dict(trace_file=entries[cid][k]['file'], trace_sha256=entries[cid][k]['sha256'],
            detector_by_radius={f'{r:g}': peaks.previous.evidence_at(old, target, r) for r in RADII},
            peaks_by_radius={f'{r:g}': peaks.evidence_at(trace, target, r) for r in RADII},
            view=crop_view(planes[cid][k], trace, target))
    return result


def summarize(pairs):
    result = {}
    for radius in ('1.5', '3'):
        result[radius] = {}
        for group, focus in (('focus', True), ('later', False)):
            chosen = [p for p in pairs if p['focus'] is focus]
            result[radius][group] = dict(images=len(chosen),
                detector_status_counts=dict(sorted(Counter(p['variants'][CASE_ID]['detector_by_radius'][radius]['status'] for p in chosen).items())),
                first_empty_stage_counts=dict(sorted(Counter(p['variants'][CASE_ID]['peaks_by_radius'][radius]['first_empty_stage'] for p in chosen).items())))
    return result


def run(score_path, output, base=None):
    base = ROOT/'local' if base is None else base
    engines = frozen(); sp, manifest, records, watched = preflight(score_path, base)
    output = slow._new_output(output, base); (output/'frames').mkdir()
    result = dict(slow_detector_trace_version='1.0', status='running', plan_commit=PLAN_COMMIT,
        source_sha256_lf=diagnostic.source_hash(__file__), frozen_sha256_lf=engines,
        score_path=str(sp), score_sha256=watched[sp], source_kind='synthetic_demo', case_id=CASE_ID,
        variants=list(VARIANTS), pairs=[], replay_records=[], pair_records=[], truth_opened_after_replay=False,
        thresholds_changed=False, association_rerun=False, registration_rerun=False,
        injections_generated=False, scientific_performance_validated=False, **slow.experiment.provenance())
    report = output/'trace.json'; slow.save(report, result)
    try:
        mp = local_path(slow.read(sp)['manifest_path'], base)
        case_map = {c['case_id']: c for c in manifest['cases']}
        pixel_watch = {}; planes, traces, entries = {}, {}, {}
        planes['control'] = slow.experiment.load_planes(mp, manifest, case_map['control'], base, pixel_watch)
        planes[CASE_ID] = slow.experiment.load_planes(mp, manifest, case_map[CASE_ID], base, pixel_watch,
                                                     [np.isnan(p) for p in planes['control']])
        watched.update(pixel_watch)
        for cid in VARIANTS:
            traces[cid], entries[cid] = [], []
            for k, plane in enumerate(planes[cid]):
                trace = peaks.trace_image(plane)
                reduced = np.asarray(trace['old_detector_trace']['selected_points_reduced']).reshape(-1, 2)
                peaks.previous.equal_points(2*reduced+.5, records[cid]['data']['raw_detections'][k],
                                            'positions natives enregistrées du profil lent')
                item = dict(variant=cid, frame_index=k, saved_raw_positions_equal=True,
                            source_plane_sha256=case_map[cid]['frames'][k]['sha256'], trace=peaks.serializable_trace(trace))
                path = output/'frames'/f'{cid}-{k:02d}.json'; slow.save(path, item)
                entry = dict(variant=cid, frame_index=k, file='frames/'+path.name, sha256=digest(path))
                watched[path] = entry['sha256']; entries[cid].append(entry); traces[cid].append(trace)
                result['replay_records'].append(entry); slow.save(report, result)
        # Every raw replay is sealed and checked before answers can be parsed.
        slow.unchanged(watched)
        checked_sp, score, _, checked_manifest, _, answers, checked_watch = slow.checked_score(sp, base)
        if checked_sp != sp or checked_manifest != manifest:
            raise ValueError('Le contexte a changé pendant le rejeu.')
        watched.update(checked_watch)
        result['truth_opened_after_replay'] = True
        result['pairs'] = [pair_evidence(k, manifest, answers[CASE_ID], traces, planes, entries) for k in range(8)]
        for pair in result['pairs']:
            p=output/'frames'/f'evidence-{pair["frame_index"]:02d}.json'
            slow.save(p,pair); watched[p]=digest(p)
            result['pair_records'].append(dict(frame_index=pair['frame_index'],file='frames/'+p.name,sha256=watched[p]))
        result.update(summary=summarize(result['pairs']), original_recovered=next(r['recovered'] for r in score['rows'] if r['case_id']==CASE_ID),
            all_saved_points_equal=True, display_background=traces['control'][0]['background'],
            display_noise=traces['control'][0]['noise_sigma'])
        with (output/'evidence.csv').open('x', encoding='utf-8-sig', newline='') as stream:
            fields = ('frame','variant','radius','detector_status','first_empty_stage','shape_reasons',
                      'noise','threshold_effective','response_ratio','higher_neighbor_ratio','phase_x','phase_y')
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for pair in result['pairs']:
                for cid in VARIANTS:
                    for r in ('1.5','3'):
                        ev=pair['variants'][cid]
                        raw=traces[cid][pair['frame_index']]
                        peak=ev['peaks_by_radius'][r]; best=peak['best_sample']; neighbour=peak['higher_neighbor']
                        writer.writerow(dict(frame=pair['frame_index']+1, variant=cid, radius=r,
                            detector_status=ev['detector_by_radius'][r]['status'],
                            first_empty_stage=peak['first_empty_stage'],
                            shape_reasons=';'.join(sorted(ev['detector_by_radius'][r]['rejection_counts'])),
                            noise=raw['noise_sigma'],threshold_effective=raw['threshold_effective'],
                            response_ratio=None if best is None else best['value_for_peaks']/raw['threshold_effective'],
                            higher_neighbor_ratio=None if neighbour is None else neighbour['value_for_peaks']/raw['threshold_effective'],
                            phase_x=pair['phase_reduced_pixels'][0],phase_y=pair['phase_reduced_pixels'][1]))
        slow.unchanged(watched)
        if frozen()!=engines or diagnostic.source_hash(__file__)!=result['source_sha256_lf']:
            raise ValueError('Une source gelée a changé.')
        result.update(status='complete', input_hashes_unchanged=True, replay_count=16)
        slow.save(report, result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); slow.save(report, result); raise
    print('Seize traces fictives vérifiées ; réponses lues après rejeu, aucun nouveau trajet.')
    return result


def checked(path, base=None):
    """Validate sealed replay, evidence and linked score without calling a detector."""
    base = ROOT/'local' if base is None else base
    path = local_path(path, base); before = digest(path); result = slow.read(path)
    if (result.get('slow_detector_trace_version')!='1.0' or result.get('status')!='complete'
            or result.get('plan_commit')!=PLAN_COMMIT or result.get('source_sha256_lf')!=diagnostic.source_hash(__file__)
            or result.get('frozen_sha256_lf')!=frozen() or result.get('case_id')!=CASE_ID
            or result.get('source_kind')!='synthetic_demo' or result.get('variants')!=list(VARIANTS)
            or result.get('truth_opened_after_replay') is not True or result.get('all_saved_points_equal') is not True
            or result.get('input_hashes_unchanged') is not True or result.get('replay_count')!=16
            or any(result.get(k) is not False for k in ('thresholds_changed','association_rerun','registration_rerun','injections_generated','scientific_performance_validated'))):
        raise ValueError('Une trace complète, gelée et sans nouvelle recherche est requise.')
    sp, score, mp, manifest, records, answers, watched = slow.checked_score(result['score_path'], base)
    if watched[sp]!=result['score_sha256'] or manifest['source_kind']!='synthetic_demo':
        raise ValueError('Le score lié a changé.')
    expected_ids=[(cid,k) for cid in VARIANTS for k in range(8)]
    if [(e['variant'],e['frame_index']) for e in result.get('replay_records',[])]!=expected_ids:
        raise ValueError('Seize traces ordonnées sont requises.')
    cached={}; cases={c['case_id']:c for c in manifest['cases']}
    for entry in result['replay_records']:
        p=local_path(path.parent/entry['file'],base)
        if path.parent not in p.parents or p in watched or digest(p)!=entry['sha256']:
            raise ValueError('Une trace brute est modifiée, répétée ou externe.')
        raw=slow.read(p); cid,k=entry['variant'],entry['frame_index']
        if (raw.get('variant')!=cid or raw.get('frame_index')!=k or raw.get('saved_raw_positions_equal') is not True
                or raw.get('source_plane_sha256')!=cases[cid]['frames'][k]['sha256']
                or raw['trace']['old_detector_trace'].get('replay_equal') is not True):
            raise ValueError('Trace brute incohérente.')
        native=2*np.asarray(raw['trace']['old_detector_trace']['selected_points_reduced']).reshape(-1,2)+.5
        peaks.previous.equal_points(native,records[cid]['data']['raw_detections'][k],'cache et candidats')
        cached[cid,k]=(raw,entry); watched[p]=entry['sha256']
    if [p['frame_index'] for p in result.get('pairs',[])]!=list(range(8)):
        raise ValueError('Huit comparaisons ordonnées sont requises.')
    if [p['frame_index'] for p in result.get('pair_records',[])]!=list(range(8)):
        raise ValueError('Huit preuves après rejeu sont requises.')
    for pair,sealed in zip(result['pairs'],result['pair_records']):
        p=local_path(path.parent/sealed['file'],base)
        if (path.parent not in p.parents or p in watched or digest(p)!=sealed['sha256']
                or slow.read(p)!=pair):
            raise ValueError('Une preuve après rejeu est modifiée, répétée ou incohérente.')
        watched[p]=sealed['sha256']
        k=pair['frame_index']; point=answers[CASE_ID]['positions'][k]
        target=diagnostic.pilot.from_reference(np.array([[point['x'],point['y']]]),manifest['models'][k])[0]
        if (pair.get('focus')!=(k<3) or pair.get('declared_relative_seconds')!=manifest['relative_declared_seconds'][k]
                or not np.array_equal(pair.get('target_source_native'),target)
                or not np.array_equal(pair.get('phase_reduced_pixels'),((target-.5)/2)%1)):
            raise ValueError('Comparaison différente des positions gelées.')
        for cid in VARIANTS:
            raw,entry=cached[cid,k]; ev=pair['variants'][cid]
            if ev['trace_file']!=entry['file'] or ev['trace_sha256']!=entry['sha256']:
                raise ValueError('Lien de trace incohérent.')
            for r in RADII:
                expected=peaks.previous.evidence_at(raw['trace']['old_detector_trace'],target,r)
                if ev['detector_by_radius'][f'{r:g}']!=expected:
                    raise ValueError('Évidence différente des maxima bruts gelés.')
    if result.get('summary')!=summarize(result['pairs']):
        raise ValueError('Bilan différent des preuves par photo.')
    original=next(r['recovered'] for r in score['rows'] if r['case_id']==CASE_ID)
    first=cached['control',0][0]['trace']
    if (result.get('original_recovered')!=original or result.get('display_background')!=first['background']
            or result.get('display_noise')!=first['noise_sigma']):
        raise ValueError('Bilan ou contraste différent du contexte conservé.')
    watched[path]=before; slow.unchanged(watched)
    return result,cached,watched


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    try: run(args.score,args.output)
    except (ValueError,OSError,KeyError,TypeError) as exc: parser.exit(1,f'Erreur : {exc}\n')
