# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Predeclared four-window survey; no source/archive access during analysis."""
import argparse
import csv
from pathlib import Path
from time import perf_counter
from gar.astrometry import local_path
from gar.contracts import parse_declared_time
from gar.sessions import load_manifest, group_sessions
from gar.workset import digest
import nearby_motion_profile as paired
from prepare_seestar_series import source_path

ROOT=Path(__file__).resolve().parents[1]
PLAN_COMMIT='29665f336818ed048701ad0f0bb1c185101b8b68'
POLICY=dict(session_gap_seconds=1800,session_limit=2,starts_seconds=[0,2400],step_seconds=300,
            frame_count=8,ranking='frame_count descending, session_id; nearest time, date, frame_id')
DATA_KEYS=('raw_detections','mapped_detections','overlap_excluded_per_frame','selections','search')
slow=paired.slow


def source_hash(path):return paired.previous.diagnostic.source_hash(path)


def frozen():
    result=paired.frozen();name='examples/nearby_motion_profile.py';value=source_hash(ROOT/name)
    if value!='e6ffc37673a498074c8fb926483adac0f740f7c4c723adefbe6bcfdce8f2bbc1':
        raise ValueError('La comparaison historique a changé.')
    result[name]=value
    return result


def select(manifest):
    index={(f['path'],h['hdu_index']):(f,h) for f in manifest['files'] for h in f['hdus']}
    groups=sorted(group_sessions(manifest,1800)['sessions'],key=lambda g:(-g['frame_count'],g['session_id']))[:2]
    rows=[]
    for group in groups:
        frames=group['frames'];dates=[parse_declared_time(f['date_obs_raw']) for f in frames]
        seconds=[(d-dates[0]).total_seconds() for d in dates];used=set()
        for start in (0,2400):
            ids=[min(range(len(frames)),key=lambda i:(abs(seconds[i]-start-300*k),dates[i],frames[i]['frame_id'])) for k in range(8)]
            chosen=[frames[i] for i in ids];hashes=[index[f['path'],f['hdu_index']][0]['sha256'] for f in chosen]
            relative=[seconds[i]-seconds[ids[0]] for i in ids];reason=None
            if len(set(ids))!=8 or len(set(hashes))!=8:reason='repeated_frame_or_hash'
            elif any(f['hdu_index']!=0 or index[f['path'],0][1]['metadata'].get('STACKCNT') not in (None,1) for f in chosen):reason='not_individual_primary'
            elif set(hashes)&used:reason='overlapping_window'
            else:
                try:slow.validate_times(relative)
                except ValueError:reason='cadence_or_span'
            available=reason is None
            if available:used.update(hashes)
            rows.append(dict(series_id=f'S{len(rows)+1:02}',session_id=group['session_id'],nominal_start_seconds=start,
                selected_indices=ids,relative_declared_seconds=relative,selection_available=available,reason=reason,
                frames=[dict(**f,sha256=h) for f,h in zip(chosen,hashes)]))
    return rows


def plan(manifest_path,output,base=None):
    base=ROOT/'local' if base is None else base;mp=local_path(manifest_path,base)
    manifest,mh=load_manifest(mp);rows=select(manifest)
    # Bind source paths lexically only; do not probe the source root or support.
    for row in rows:
        for f in row['frames']:source_path(Path(manifest['input_root']),f['path'])
    output=slow._new_output(output,base)
    result=dict(survey_plan_version='1.0',status='complete',plan_commit=PLAN_COMMIT,policy=POLICY,
        inventory_path=str(mp),inventory_sha256=mh,rows=rows,source_accessed=False,
        frozen_sha256_lf=frozen(),recipe_sha256_lf=source_hash(__file__),**slow.experiment.provenance())
    if digest(mp)!=mh:raise ValueError('Le manifeste a changé pendant la sélection.')
    slow.save(output/'plan.json',result)
    return result


def checked_plan(path,base):
    pp=local_path(path,base);r=slow.read(pp);watched={pp:digest(pp)}
    mp=local_path(r['inventory_path'],base);m,mh=load_manifest(mp);watched[mp]=mh
    if (r.get('survey_plan_version')!='1.0' or r.get('status')!='complete' or r.get('plan_commit')!=PLAN_COMMIT
            or r.get('policy')!=POLICY or r.get('source_accessed') is not False or r.get('inventory_sha256')!=mh
            or r.get('rows')!=select(m) or r.get('frozen_sha256_lf')!=frozen()
            or r.get('recipe_sha256_lf')!=source_hash(__file__)):
        raise ValueError('Le plan ne reproduit pas la sélection fixée.')
    slow.unchanged(watched)
    return pp,r,watched


def worksets(index_path,plan_hash,rows,base):
    ip=local_path(index_path,base);index=slow.read(ip)
    allowed={r['series_id'] for r in rows if r['selection_available']}
    entries=index.get('entries',{})
    if (index.get('survey_worksets_version')!='1.0' or index.get('plan_sha256')!=plan_hash
            or not isinstance(entries,dict) or set(entries)-allowed):
        raise ValueError('Index local incompatible avec le plan.')
    paths=[local_path(e['path'],base) for e in entries.values()]
    if len(set(paths))!=len(paths):raise ValueError('Un workset est répété.')
    return ip,index


def summary(records):
    result={}
    for variant in paired.VARIANTS:
        counts=[r['profiles'][variant]['candidate_count'] for r in records]
        result[variant]=dict(available_series=sum(c is not None for c in counts),
            unavailable_series=sum(c is None for c in counts),
            candidate_occurrences=sum(c for c in counts if c is not None) if any(c is not None for c in counts) else None)
    return result


def run(plan_path,index_path,output,base=None):
    base=ROOT/'local' if base is None else base;pp,p,watched=checked_plan(plan_path,base)
    ip,index=worksets(index_path,watched[pp],p['rows'],base);watched[ip]=digest(ip)
    output=slow._new_output(output,base);result=dict(survey_run_version='1.0',status='running',plan_commit=PLAN_COMMIT,
        plan_path=str(pp),plan_sha256=watched[pp],index_path=str(ip),index_sha256=watched[ip],records=[],
        frozen_sha256_lf=frozen(),recipe_sha256_lf=source_hash(__file__),truth_opened=False,
        known_natural_positive_tested=False,science_fitness_passed=False,clock_qualified=False,
        **slow.experiment.provenance())
    rp=output/'survey.json';slow.save(rp,result);records=[]
    try:
        for row in p['rows']:
            started=perf_counter();sid=row['series_id'];folder=output/sid;folder.mkdir()
            record=dict(series_id=sid,source_kind=None,workset_path=None,workset_sha256=None,baseline_path=None,baseline_sha256=None,
                profiles={v:dict(search_status='blocked',candidate_count=None,data=None) for v in paired.VARIANTS},
                input_bytes=None,unconfirmed=True)
            try:
                if not row['selection_available']:raise ValueError('Sélection refusée : '+row['reason'])
                entry=index['entries'].get(sid)
                if entry is None:raise ValueError('Copies locales indisponibles dans l’index.')
                wp=local_path(entry['path'],base)
                if digest(wp)!=entry['sha256']:raise ValueError('Le workset a changé.')
                w=slow.read(wp)
                if [f['sha256_copy'] for f in w['files']]!=[f['sha256'] for f in row['frames']]:
                    raise ValueError('Les copies ne correspondent pas aux poses sélectionnées.')
                record.update(workset_path=str(wp),workset_sha256=entry['sha256'])
                watched[wp]=entry['sha256']
                baseline=slow.prepare(wp,folder/'reference',base);bp=folder/'reference/baseline.json'
                record.update(baseline_path=str(bp),baseline_sha256=digest(bp),source_kind=baseline['source_kind'],
                    input_bytes=sum(Path(c['local_copy']).stat().st_size for c in baseline['copies']))
                watched.update({Path(c['local_copy']):c['sha256'] for c in baseline['copies']})
                if baseline['search_status']=='complete':
                    record['profiles']['reference']=dict(search_status='complete',candidate_count=baseline['candidate_count'],
                        data={k:baseline[k] for k in DATA_KEYS})
                else:record['profiles']['reference']['error']=baseline['blocked_reasons']
                if baseline['registration_available']:
                    info,inputs,planes,_=slow._read_workset(wp,base,True);watched.update(inputs)
                    try:
                        data=paired.process(planes,baseline,'radius3')
                        record['profiles']['radius3']=dict(search_status='complete',candidate_count=len(data['search']['tracks']),data=data)
                    except ValueError as exc:record['profiles']['radius3']['error']=str(exc)
                else:record['profiles']['radius3']['error']='registration_unavailable'
                if all(r['search_status']=='complete' for r in record['profiles'].values()):
                    paired.compare_settings(*[record['profiles'][v]['data'] for v in paired.VARIANTS])
            except (ValueError,OSError,KeyError,TypeError) as exc:record['error']=str(exc)
            record['elapsed_seconds']=perf_counter()-started
            path=folder/'candidates.json';slow.save(path,record);records.append(record)
            result['records'].append(dict(series_id=sid,file=f'{sid}/candidates.json',sha256=digest(path)))
            slow.save(rp,result)
        result['summary']=summary(records)
        with (output/'summary.csv').open('x',encoding='utf-8-sig',newline='') as stream:
            writer=csv.writer(stream);writer.writerow(['series_id','variant','search_status','candidate_count','elapsed_seconds_pair','input_bytes'])
            for r in records:
                for v,d in r['profiles'].items():writer.writerow([r['series_id'],v,d['search_status'],d['candidate_count'],r['elapsed_seconds'],r['input_bytes']])
        for e in result['records']:watched[output/e['file']]=e['sha256']
        slow.unchanged(watched)
        if result['frozen_sha256_lf']!=frozen() or result['recipe_sha256_lf']!=source_hash(__file__):raise ValueError('Une source a changé.')
        result.update(status='complete',inputs_unchanged=True);slow.save(rp,result)
    except Exception as exc:
        result.update(status='incomplete',error=str(exc));slow.save(rp,result);raise
    return result


def checked(path,base=None):
    base=ROOT/'local' if base is None else base;rp=local_path(path,base);r=slow.read(rp)
    pp,p,watched=checked_plan(r['plan_path'],base);watched[rp]=digest(rp)
    ip,index=worksets(r['index_path'],watched[pp],p['rows'],base);watched[ip]=digest(ip)
    if (r.get('survey_run_version')!='1.0' or r.get('status')!='complete' or r.get('inputs_unchanged') is not True
            or r.get('plan_commit')!=PLAN_COMMIT or r.get('truth_opened') is not False
            or r.get('known_natural_positive_tested') is not False or r.get('science_fitness_passed') is not False
            or r.get('frozen_sha256_lf')!=frozen() or r.get('recipe_sha256_lf')!=source_hash(__file__)
            or r.get('plan_sha256')!=watched[pp] or r.get('index_sha256')!=watched[ip]
            or [e['series_id'] for e in r['records']]!=[e['series_id'] for e in p['rows']]):
        raise ValueError('Rapport de lot incomplet ou incompatible.')
    records=[]
    for entry,row in zip(r['records'],p['rows']):
        cp=local_path(rp.parent/entry['file'],base)
        if rp.parent not in cp.parents or cp in watched or digest(cp)!=entry['sha256']:raise ValueError('Rapport candidat modifié ou hors sortie.')
        rec=slow.read(cp);watched[cp]=entry['sha256']
        if rec['series_id']!=row['series_id'] or set(rec['profiles'])!=set(paired.VARIANTS):raise ValueError('Identité de série incorrecte.')
        if rec['baseline_path'] is not None:
            bp=local_path(rec['baseline_path'],base)
            if rp.parent not in bp.parents or digest(bp)!=rec['baseline_sha256']:raise ValueError('Référence modifiée ou hors sortie.')
            b=slow.read(bp);watched[bp]=rec['baseline_sha256']
            wp=local_path(rec['workset_path'],base)
            if digest(wp)!=rec['workset_sha256'] or index['entries'][row['series_id']]['sha256']!=rec['workset_sha256']:
                raise ValueError('Copies liées modifiées.')
            info,inputs,_,_=slow._read_workset(wp,base,False);watched.update(inputs)
            if (any(b[k]!=v for k,v in info.items()) or b['source_kind']!=rec['source_kind']
                    or [c['sha256'] for c in b['copies']]!=[f['sha256'] for f in row['frames']]
                    or b['frozen_sha256_lf']!=slow.frozen() or b['recipe_sha256_lf']!=slow.recipe_hash()
                    or b['profile_parameters']!=slow.PARAMETERS or b['status']!='complete' or b['inputs_unchanged'] is not True):
                raise ValueError('Contrat de référence incohérent.')
            a=rec['profiles']['reference']
            if a['search_status']=='complete' and a['data']!={k:b[k] for k in DATA_KEYS}:raise ValueError('Référence différente du bilan scellé.')
        for v,d in rec['profiles'].items():
            if d['search_status']=='complete':
                data=d['data'];search=data['search']
                if (type(d['candidate_count']) is not int or d['candidate_count']!=len(search['tracks'])
                        or search['parameters']!=slow.PARAMETERS or search['stationary_removal_applied'] is not False
                        or search['profile']!=('slow_v1' if v=='reference' else 'slow_nearby_r3_v1')):
                    raise ValueError('Profil ou compte candidat incohérent.')
                if rec['baseline_path'] is None or not b['registration_available']:raise ValueError('Modèles communs indisponibles.')
                if v=='radius3' and any(s['detector_signature']!=paired.signature(s['noise_sigma'],3) for s in data['selections']):
                    raise ValueError('Signature de détecteur incohérente.')
            elif d['search_status']!='blocked' or d['candidate_count'] is not None or d['data'] is not None:
                raise ValueError('Un refus doit garder des comptes inconnus.')
        if all(d['search_status']=='complete' for d in rec['profiles'].values()):paired.compare_settings(*[rec['profiles'][v]['data'] for v in paired.VARIANTS])
        records.append(rec)
    if r['summary']!=summary(records):raise ValueError('Synthèse différente des rapports scellés.')
    slow.unchanged(watched)
    return r,records,watched


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='command',required=True)
    for name,fields in [('plan',('manifest',)),('run',('plan','index'))]:
        p=subs.add_parser(name)
        for field in (*fields,'output'):p.add_argument(field,type=Path)
    args=parser.parse_args()
    try:
        result=plan(args.manifest,args.output) if args.command=='plan' else run(args.plan,args.index,args.output)
        blocked=(not result['rows'] or any(not r['selection_available'] for r in result['rows'])) if args.command=='plan' else (not result['records'] or any(s['unavailable_series'] for s in result['summary'].values()))
        print('Lot terminé. Zéro candidat et recherche indisponible restent distincts.')
        raise SystemExit(2 if blocked else 0)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
