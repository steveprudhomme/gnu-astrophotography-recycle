# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Paired radius-five/radius-three experiment on identical frozen planes/models."""
import argparse
import csv
from pathlib import Path
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
from gar.nearby_moving import detect_sources,signature
import slow_motion_profile as slow
import make_asymmetric_slow_demo as demo
import trace_slow_detector as previous

ROOT=Path(__file__).resolve().parents[1]
PLAN_COMMIT='785b9dec6c36098bf4982d12d8b0127494374a07'
VARIANTS=('reference','radius3')
SEEDS=(2026112601,2026112602)


def frozen():
    hashes=previous.frozen()
    name='examples/trace_slow_detector.py';value=previous.diagnostic.source_hash(ROOT/name)
    if value!='7166bb3f0c78aeb2b9247ec52d0e69269ea5f029732884a21c61d43bccb5244c':
        raise ValueError('La recette historique de trace a changé.')
    hashes[name]=value
    hashes['src/gar/nearby_moving.py']=previous.diagnostic.source_hash(ROOT/'src/gar/nearby_moving.py')
    return hashes


def recipe_hash():return previous.diagnostic.source_hash(__file__)


def stable(result):
    if result['frozen_sha256_lf']!=frozen() or result['recipe_sha256_lf']!=recipe_hash():
        raise ValueError('Une source de comparaison a changé.')


def make(output,base=None):
    base=ROOT/'local' if base is None else base;engines=frozen();output=slow._new_output(output,base)
    result=dict(nearby_demo_version='1.0',status='running',seeds=list(SEEDS),contexts=[],
                frozen_sha256_lf=engines,recipe_sha256_lf=recipe_hash(),synthetic=True,**slow.experiment.provenance())
    path=output/'contexts.json';slow.save(path,result)
    try:
        for seed in SEEDS:
            result['contexts'].append(demo.make_context(output/f'context-s{seed}',seed,base));slow.save(path,result)
        stable(result)
        result.update(status='complete',all_contexts_admissible=all(c['experiment_admissible'] for c in result['contexts']))
        slow.save(path,result)
    except Exception as exc:
        result.update(status='incomplete',error=str(exc));slow.save(path,result);raise
    return result


def process(planes,manifest,variant):
    if variant=='reference':
        return slow.process(planes,manifest['models'],manifest['image_shape'],
                            manifest['relative_declared_seconds'],manifest['scale_arcsec_per_native_pixel'])
    if variant!='radius3':raise ValueError('Profil inconnu.')
    detections=[];selections=[]
    for plane in planes:
        xy,selection=detect_sources(plane);detections.append(2*xy+.5);selections.append(selection)
    mapped,excluded=slow.pilot.common_points(detections,manifest['models'],manifest['image_shape'])
    tracks,hypotheses=slow.find_tracks(mapped,manifest['relative_declared_seconds'],manifest['scale_arcsec_per_native_pixel'])
    return dict(raw_detections=[p.tolist() for p in detections],mapped_detections=[p.tolist() for p in mapped],
        overlap_excluded_per_frame=excluded,selections=selections,
        search=dict(tracks=tracks,hypotheses_scored=hypotheses,profile='slow_nearby_r3_v1',
                    parameters=slow.PARAMETERS.copy(),stationary_removal_applied=False))


def compare_settings(reference,reduced):
    for first,second in zip(reference['selections'],reduced['selections']):
        if any(first[k]!=second[k] for k in ('background','noise_sigma')):
            raise ValueError('Bruit ou fond différent entre les deux profils.')
        expected=signature(first['noise_sigma'],5);actual=second['detector_signature']
        if (expected['minimum_separation_reduced']!=5 or actual['minimum_separation_reduced']!=3
                or any(expected[k]!=v for k,v in actual.items() if k!='minimum_separation_reduced')):
            raise ValueError('Un paramètre autre que le voisinage a changé.')


def analyze(manifest_path,output,base=None):
    base=ROOT/'local' if base is None else base
    mp,manifest,watched=slow.load_manifest(manifest_path,base)
    output=slow._new_output(output,base);(output/'cases').mkdir()
    result=dict(nearby_analysis_version='1.0',status='running',plan_commit=PLAN_COMMIT,
        manifest_sha256=watched[mp],variants=list(VARIANTS),source_kind=manifest['source_kind'],
        frozen_sha256_lf=frozen(),recipe_sha256_lf=recipe_hash(),truth_opened=False,models_refitted=False,
        records=[],**slow.experiment.provenance())
    path=output/'analysis.json';slow.save(path,result);masks=None
    try:
        # Each plane is shared by both detectors; no answer reaches either search.
        for case in manifest['cases']:
            planes=slow.experiment.load_planes(mp,manifest,case,base,watched,masks)
            if case['case_id']=='control':masks=[np.isnan(p) for p in planes]
            pair={}
            for variant in VARIANTS:
                record=dict(variant=variant,case_id=case['case_id'],search_status='blocked',candidate_count=None,data=None)
                if planes is not None:
                    try:
                        data=process(planes,manifest,variant)
                        record.update(search_status='complete',candidate_count=len(data['search']['tracks']),data=data)
                    except ValueError as exc:record['error']=str(exc)
                else:record['error']=case['error']
                pair[variant]=record
            if all(r['search_status']=='complete' for r in pair.values()):
                compare_settings(pair['reference']['data'],pair['radius3']['data'])
            for variant,record in pair.items():
                p=output/'cases'/f'{variant}-{case["case_id"]}.json';slow.save(p,record)
                result['records'].append(dict(variant=variant,case_id=case['case_id'],file='cases/'+p.name,sha256=digest(p)))
            slow.save(path,result)
        for entry in result['records']:
            if digest(output/entry['file'])!=entry['sha256']:raise ValueError('Un candidat scellé a changé.')
        slow.unchanged(watched);stable(result)
        result.update(status='complete',inputs_unchanged=True,
            all_available=all(slow.read(output/e['file'])['search_status']=='complete' for e in result['records']))
        slow.save(path,result)
    except Exception as exc:
        result.update(status='incomplete',error=str(exc));slow.save(path,result);raise
    return result


def sealed(path,manifest,manifest_hash,base,watched):
    ap=local_path(path,base);result=slow.read(ap);watched[ap]=digest(ap)
    expected=[(variant,case['case_id']) for case in manifest['cases'] for variant in VARIANTS]
    if (result.get('nearby_analysis_version')!='1.0' or result.get('status')!='complete'
            or result.get('plan_commit')!=PLAN_COMMIT or result.get('manifest_sha256')!=manifest_hash
            or result.get('variants')!=list(VARIANTS) or result.get('inputs_unchanged') is not True
            or result.get('source_kind')!=manifest['source_kind']
            or result.get('truth_opened') is not False or result.get('models_refitted') is not False
            or result.get('frozen_sha256_lf')!=frozen() or result.get('recipe_sha256_lf')!=recipe_hash()
            or [(e['variant'],e['case_id']) for e in result.get('records',[])]!=expected):
        raise ValueError('Vingt-six rapports ordonnés et scellés sont requis avant les réponses.')
    records={v:{} for v in VARIANTS}
    for entry in result['records']:
        p=local_path(ap.parent/entry['file'],base)
        if ap.parent not in p.parents or p in watched or digest(p)!=entry['sha256']:
            raise ValueError('Un candidat est modifié, répété ou hors du dossier.')
        record=slow.read(p);variant,cid=entry['variant'],entry['case_id']
        if record.get('variant')!=variant or record.get('case_id')!=cid or record.get('search_status') not in ('complete','blocked'):
            raise ValueError('Identité du candidat incohérente.')
        if record['search_status']=='complete':
            data=record['data'];search=data['search']
            profile='slow_v1' if variant=='reference' else 'slow_nearby_r3_v1'
            if (type(record.get('candidate_count')) is not int or record['candidate_count']!=len(search['tracks'])
                    or search.get('parameters')!=slow.PARAMETERS or search.get('profile')!=profile
                    or search.get('stationary_removal_applied') is not False or len(data['selections'])!=8):
                raise ValueError('Profil ou compte candidat incohérent.')
            if variant=='radius3' and any(s.get('detector_signature')!=signature(s['noise_sigma'],3) for s in data['selections']):
                raise ValueError('Signature du détecteur réduit incohérente.')
        elif record.get('candidate_count') is not None or record.get('data') is not None:
            raise ValueError('Un refus doit garder des comptes inconnus.')
        watched[p]=entry['sha256'];records[variant][cid]=record
    for case in manifest['cases']:
        a,b=[records[v][case['case_id']] for v in VARIANTS]
        if a['search_status']==b['search_status']=='complete':compare_settings(a['data'],b['data'])
    if result.get('all_available')!=all(r['search_status']=='complete' for d in records.values() for r in d.values()):
        raise ValueError('Disponibilité incohérente.')
    return records


def totals(rows):
    available=sum(r['available'] for r in rows)
    return dict(planned=len(rows),available=available,unavailable=len(rows)-available,
                recovered=sum(r['recovered'] or 0 for r in rows) if available else None,
                missed=sum(r['missed'] or 0 for r in rows) if available else None,
                unassociated_candidates=sum(r['unassociated_candidates'] or 0 for r in rows) if available else None)


def values(manifest,records,answers,baseline):
    result={};synthetic=manifest['source_kind']=='synthetic_demo'
    for variant in VARIANTS:
        rows=[dict(spec,**slow.score_one(records[variant][spec['case_id']],answers.get(spec['case_id'])))
              for spec in [dict(case_id='control'),*manifest['conditions']]]
        groups=[dict(angular_rate_arcsec_hour=rate,peak_sigma=peak,
            **totals([r for r in rows[1:] if r['angular_rate_arcsec_hour']==rate and r['peak_sigma']==peak]))
            for rate in (10.,30.,60.) for peak in (6,12)]
        bright=totals([r for r in rows[1:] if r['peak_sigma']==12]);counts=totals(rows[1:])
        control=records[variant]['control']['candidate_count']
        all_available=all(r['available'] for r in rows)
        false=control+counts['unassociated_candidates'] if synthetic and all_available else None
        result[variant]=dict(rows=rows,groups=groups,bright=bright,**counts,control_candidates=control,
            false_candidates=false,all_available=all_available)
    a,b=[{r['case_id']:r for r in result[v]['rows'][1:]} for v in VARIANTS]
    lost=[cid for cid in a if a[cid]['available'] and b[cid]['available'] and a[cid]['recovered']==1 and b[cid]['recovered']==0]
    unavailable=[cid for cid in a if not (a[cid]['available'] and b[cid]['available'])]
    passed=(all(result[v]['all_available'] for v in VARIANTS) and result['radius3']['bright']['recovered']==6
            and result['radius3']['false_candidates']==0 and not lost) if synthetic else None
    reference=records['reference']['control']
    identical=(all(reference['data'][k]==baseline[k]
        for k in ('raw_detections','mapped_detections','overlap_excluded_per_frame','search'))
        if reference['search_status']=='complete' else None)
    if identical is False:raise ValueError('La référence ne reproduit pas le témoin historique.')
    return dict(variants=result,lost_reference_cases=lost,unavailable_comparisons=unavailable,
        synthetic_criteria_passed=passed,reference_control_identical_to_baseline=identical,
        source_kind=manifest['source_kind'],science_fitness_passed=False,clock_qualified=False,
        known_natural_positive_tested=False,new_radius_reduced_pixels=3,reference_radius_reduced_pixels=5,
        luminosity_threshold_sigma=5.,association_parameters=slow.PARAMETERS.copy())


def inputs(manifest_path,truth_path,analysis_path,base):
    mp,manifest,watched=slow.load_manifest(manifest_path,base)
    ap,tp=[local_path(p,base) for p in (analysis_path,truth_path)]
    records=sealed(ap,manifest,watched[mp],base,watched)
    slow.verify_derivatives(mp,manifest,base,watched)
    # Parse answers only after closing every candidate and derivative.
    watched[tp]=digest(tp);answers=slow._answers(tp,manifest,watched[mp])
    baseline=slow.read(local_path(manifest['baseline_report'],base))
    return mp,tp,ap,manifest,records,answers,watched,values(manifest,records,answers,baseline)


def score(manifest_path,truth_path,analysis_path,output,base=None):
    base=ROOT/'local' if base is None else base
    mp,tp,ap,manifest,records,answers,watched,computed=inputs(manifest_path,truth_path,analysis_path,base)
    output=slow._new_output(output,base)
    result=dict(nearby_score_version='1.0',status='running',plan_commit=PLAN_COMMIT,
        manifest_path=str(mp),manifest_sha256=watched[mp],truth_path=str(tp),truth_sha256=watched[tp],
        analysis_path=str(ap),analysis_sha256=watched[ap],frozen_sha256_lf=frozen(),recipe_sha256_lf=recipe_hash(),
        **computed,**slow.experiment.provenance())
    path=output/'score.json';slow.save(path,result)
    try:
        with (output/'comparison.csv').open('x',encoding='utf-8-sig',newline='') as stream:
            fields=('variant','case_id','available','recovered','missed','unassociated_candidates')
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            for variant,data in result['variants'].items():
                for row in data['rows']:writer.writerow(dict(variant=variant,**{k:row.get(k) for k in fields if k!='variant'}))
        slow.unchanged(watched);stable(result)
        result.update(status='complete',inputs_unchanged=True);slow.save(path,result)
    except Exception as exc:
        result.update(status='incomplete',error=str(exc));slow.save(path,result);raise
    return result


def checked_score(path,base=None):
    base=ROOT/'local' if base is None else base
    path=local_path(path,base);before=digest(path);result=slow.read(path)
    if (result.get('nearby_score_version')!='1.0' or result.get('status')!='complete'
            or result.get('plan_commit')!=PLAN_COMMIT or result.get('inputs_unchanged') is not True):
        raise ValueError('Un score comparatif complet est requis.')
    stable(result)
    mp,tp,ap,manifest,records,answers,watched,computed=inputs(result['manifest_path'],result['truth_path'],result['analysis_path'],base)
    if (any(result.get(k)!=v for k,v in computed.items())
            or any(result[key]!=watched[p] for key,p in [('manifest_sha256',mp),('truth_sha256',tp),('analysis_sha256',ap)])):
        raise ValueError('Le score diffère des preuves scellées.')
    watched[path]=before;slow.unchanged(watched)
    return result,mp,manifest,records,answers,watched


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='command',required=True)
    for name,fields in [('make',()),('analyze',('manifest',)),('score',('manifest','truth','analysis'))]:
        p=subs.add_parser(name)
        for field in (*fields,'output'):p.add_argument(field,type=Path)
    args=parser.parse_args()
    try:
        fields={'make':(),'analyze':('manifest',),'score':('manifest','truth','analysis')}[args.command]
        result=globals()[args.command](*[getattr(args,f) for f in fields],args.output)
        refused=(args.command=='make' and not result['all_contexts_admissible']
            or args.command=='analyze' and not result['all_available']
            or args.command=='score' and (result['synthetic_criteria_passed'] is False
                or any(not v['all_available'] for v in result['variants'].values())))
        print('Comparaison de voisinage terminée ; les résultats restent expérimentaux.')
        raise SystemExit(2 if refused else 0)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
