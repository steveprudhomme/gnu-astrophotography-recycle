# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Prepare a known-comet control offline; never detect, register, or associate."""
import argparse
from collections import defaultdict
import csv
from pathlib import Path,PurePosixPath
import numpy as np
from astropy.io import fits
from gar.astrometry import local_path
from gar.contracts import parse_declared_time
from gar.workset import digest,prepare_workset
import seestar_survey as historical

ROOT=Path(__file__).resolve().parents[1]
PLAN_COMMIT='3799e33efbe9eca366099ad35312bf837b5c672c'
ALIASES={'C-2023 A3':'C/2023 A3','C/2023 A3':'C/2023 A3',
         'C-2021 S3':'C/2021 S3','C/2021 S3':'C/2021 S3','C2021 S3 (PANSTARRS)':'C/2021 S3'}
TARGET='C/2023 A3'
CONFIG=('INSTRUME','FILTER','BAYERPAT','EXPTIME','NAXIS1','NAXIS2','BITPIX','EQMODE')
slow=historical.slow


def frozen():
    values=historical.frozen();name='examples/seestar_survey.py';value=historical.source_hash(ROOT/name)
    if value!='0e2754f1d5616ff9a94f2737405606ce20d27fe1f46fccef45f5dd7331dfaca4':raise ValueError('Le pilote historique a changé.')
    values[name]=value
    for name in ('prepare_positive_control.py','fetch_control_ephemeris.py','make_positive_control_demo.py','plot_positive_control.py'):
        values['examples/'+name]=historical.source_hash(ROOT/'examples'/name)
    return values


def relative_path(raw):
    if not isinstance(raw,str):raise ValueError('Chemin relatif de texte requis.')
    raw=raw.replace('\\','/');p=PurePosixPath(raw)
    if not raw or raw!=p.as_posix() or p.is_absolute() or '..' in p.parts or ':' in raw:
        raise ValueError('Chemin relatif de source dangereux.')
    return raw


def choose(times):
    """First admissible start, then minimum absolute schedule error, then indices."""
    times=np.asarray(times,dtype=float)
    if times.ndim!=1 or not np.isfinite(times).all() or np.any(np.diff(times)<0):raise ValueError('Temps finis triés requis.')
    for start in range(max(0,len(times)-7)):
        states={start:(0.,(start,))}
        for step in range(1,8):
            new={}
            for j in range(start+step,len(times)):
                if times[j]-times[start]>2700:break
                candidates=[(cost+abs(times[j]-times[start]-300*step),path+(j,))
                    for i,(cost,path) in states.items() if 240<=times[j]-times[i]<=360]
                if candidates:new[j]=min(candidates)
            states=new
        valid=[v for j,v in states.items() if 1800<=times[j]-times[start]<=2700]
        if valid:return list(min(valid)[1])
    return None


def groups(rows):
    if not isinstance(rows,list):raise ValueError('Inventaire exploratoire en liste requis.')
    buckets=defaultdict(list);seen=set();excluded=defaultdict(int)
    for row in rows:
        path=relative_path(row['path'])
        if path in seen:raise ValueError('Chemin source répété dans l’inventaire.')
        seen.add(path);target=ALIASES.get(row.get('OBJECT'))
        if target is None:continue
        if (row.get('kind')!='individual_candidate' or row.get('hdu')!=0 or row.get('status')!='header_read'
                or row.get('NAXIS')!=2 or row.get('STACKCNT') not in (None,1)):
            excluded['not_individual_primary']+=1;continue
        try:date=parse_declared_time(row['DATE-OBS'])
        except (ValueError,KeyError):excluded['invalid_time']+=1;continue
        values=tuple(row.get(k) for k in CONFIG)
        if any(isinstance(v,(dict,list)) for v in values):raise ValueError('Configuration scalaire requise.')
        key=(target,str(PurePosixPath(path).parent),date.date().isoformat(),*values)
        buckets[key].append(dict(row,path=path))
    result=[]
    for key,items in sorted(buckets.items(),key=lambda p:str(p[0])):
        items.sort(key=lambda r:(parse_declared_time(r['DATE-OBS']),r['path']));chunks=[[]]
        for row in items:
            if chunks[-1] and (parse_declared_time(row['DATE-OBS'])-parse_declared_time(chunks[-1][-1]['DATE-OBS'])).total_seconds()>1800:
                chunks.append([])
            chunks[-1].append(row)
        for chunk in chunks:
            first=parse_declared_time(chunk[0]['DATE-OBS'])
            times=[(parse_declared_time(r['DATE-OBS'])-first).total_seconds() for r in chunk]
            ids=choose(times)
            result.append(dict(target=key[0],first_time=chunk[0]['DATE-OBS'],directory=key[1],count=len(chunk),
                span_seconds=times[-1],cadence_admissible=ids is not None,indices=ids,frames=[chunk[i] for i in ids] if ids else []))
    result.sort(key=lambda g:(-g['count'],g['first_time'],g['directory'],g['target']))
    return result,dict(excluded)


def plan(inventory_path,summary_path,output,base=None):
    base=ROOT/'local' if base is None else base
    ip,sp=[local_path(p,base) for p in (inventory_path,summary_path)];watched={p:digest(p) for p in (ip,sp)}
    s=slow.read(sp);source=s.get('input_root')
    if s.get('schema_version')!='exploratory-1' or not isinstance(source,str) or not Path(source).is_absolute():raise ValueError('Racine et schéma exploratoires requis.')
    candidates,excluded=groups(slow.read(ip))
    selected=next((g for g in candidates if g['target']==TARGET and g['cadence_admissible']),None)
    output=slow._new_output(output,base)
    result=dict(control_plan_version='1.0',status='complete',plan_commit=PLAN_COMMIT,inventory_path=str(ip),summary_path=str(sp),
        inventory_sha256=watched[ip],summary_sha256=watched[sp],source_root=source,source_accessed=False,
        selected=selected,candidates=candidates,excluded=excluded,historical_pixel_hashes_available=False,
        synthetic=s.get('synthetic') is True,frozen_sha256_lf=frozen(),**slow.experiment.provenance())
    slow.unchanged(watched);slow.save(output/'plan.json',result)
    return result


def checked_plan(path,base):
    pp=local_path(path,base);r=slow.read(pp);watched={pp:digest(pp)}
    ip,sp=[local_path(r[k],base) for k in ('inventory_path','summary_path')];watched.update({p:digest(p) for p in (ip,sp)})
    candidates,excluded=groups(slow.read(ip));s=slow.read(sp)
    selected=next((g for g in candidates if g['target']==TARGET and g['cadence_admissible']),None)
    if (r.get('control_plan_version')!='1.0' or r.get('status')!='complete' or r.get('plan_commit')!=PLAN_COMMIT
            or r.get('inventory_sha256')!=watched[ip] or r.get('summary_sha256')!=watched[sp]
            or r.get('selected')!=selected or r.get('candidates')!=candidates or r.get('excluded')!=excluded
            or r.get('source_root')!=s.get('input_root') or r.get('source_accessed') is not False
            or r.get('synthetic')!=(s.get('synthetic') is True) or r.get('frozen_sha256_lf')!=frozen()
            or r.get('historical_pixel_hashes_available') is not False):raise ValueError('Plan modifié ou sélection différente.')
    slow.unchanged(watched)
    return pp,r,watched


def check_copies(workset_path,p,base):
    wp=local_path(workset_path,base);w=slow.read(wp);watched={wp:digest(wp)}
    rows=p['selected']['frames'];copies=[];headers=[];hashes=set()
    if w.get('workset_schema_version')!='1.0' or w.get('success') is not True:
        raise ValueError('Huit copies vérifiées requises.')
    if len(rows)!=8 or len(w.get('files',[]))!=8:raise ValueError('Huit copies vérifiées requises.')
    for item,frame in zip(w['files'],rows):
        cp=local_path(wp.parent/item['local_copy'],base)
        hsh=item['sha256_copy']
        if (wp.parent not in cp.parents or cp in watched or hsh in hashes or digest(cp)!=hsh
                or item['sha256_before']!=hsh or item['sha256_after']!=hsh):raise ValueError('Copie répétée ou modifiée.')
        watched[cp]=hsh;hashes.add(hsh);copies.append(dict(local_copy=str(cp),sha256=hsh))
        if cp.stat().st_size!=frame['size_bytes']:raise ValueError('Taille différente de l’inventaire exploratoire.')
        with fits.open(cp,mode='readonly',memmap=False) as hdus:
            h=hdus[0].header.copy();headers.append(h)
            if (ALIASES.get(h.get('OBJECT'))!=p['selected']['target']
                    or h.get('DATE-OBS')!=frame['DATE-OBS'] or any(h.get(k)!=frame.get(k) for k in CONFIG)):
                raise ValueError('En-tête différent de la sélection locale.')
    synthetic=[h.get('GARSYNTH') is True for h in headers]
    if any(v!=p['synthetic'] for v in synthetic):raise ValueError('Nature des copies incohérente.')
    first=parse_declared_time(rows[0]['DATE-OBS'])
    times=slow.validate_times([(parse_declared_time(f['DATE-OBS'])-first).total_seconds() for f in rows])
    summary=dict(source_kind='synthetic_demo' if p['synthetic'] else 'real_local_copies',copies=copies,
        image_shape=[headers[0].get('NAXIS2'),headers[0].get('NAXIS1')],relative_declared_seconds=times.tolist(),
        profile_copy_contract_compatible=True,profile_copy_contract_error=None)
    try:slow._read_workset(wp,base,False)
    except ValueError as exc:
        summary.update(profile_copy_contract_compatible=False,profile_copy_contract_error=str(exc))
    slow.unchanged(watched)
    return summary,watched


def copy(plan_path,output,base=None,local_workset=None):
    base=ROOT/'local' if base is None else base;pp,p,watched=checked_plan(plan_path,base)
    if p['selected'] is None:raise ValueError('Aucune suite admissible sélectionnée.')
    output=slow._new_output(output,base)
    receipt=dict(control_copies_version='1.0',status='running',plan_path=str(pp),plan_sha256=watched[pp],
        historical_pixel_hashes_available=False,frozen_sha256_lf=frozen(),**slow.experiment.provenance())
    rp=output/'copies.json';slow.save(rp,receipt)
    try:
        if local_workset is None:
            selection=dict(selection_schema_version='1.0',files=[dict(source=str(historical.source_path(Path(p['source_root']),r['path']))) for r in p['selected']['frames']])
            prepare_workset(selection,output/'workset',base);wp=output/'workset/workset.json'
        else:wp=local_path(local_workset,base)
        info,inputs=check_copies(wp,p,base);watched.update(inputs)
        slow.unchanged(watched)
        receipt.update(status='complete',workset_path=str(wp),workset_sha256=digest(wp),legacy_metadata_checked=True,
            inputs_unchanged=True,existing_local_workset_reused=local_workset is not None);slow.save(rp,receipt)
    except Exception as exc:
        receipt.update(status='incomplete',error=str(exc));slow.save(rp,receipt);raise
    return receipt


def checked_copies(path,pp,p,base):
    cp=local_path(path,base);r=slow.read(cp);wp=local_path(r['workset_path'],base)
    if (r.get('control_copies_version')!='1.0' or r.get('status')!='complete' or r.get('plan_path')!=str(pp)
            or r.get('plan_sha256')!=digest(pp) or r.get('workset_sha256')!=digest(wp)
            or r.get('legacy_metadata_checked') is not True or r.get('inputs_unchanged') is not True
            or r.get('frozen_sha256_lf')!=frozen()):raise ValueError('Copies incomplètes ou modifiées.')
    info,watched=check_copies(wp,p,base);watched[cp]=digest(cp)
    return info,watched


def decisions(info,ephemeris):
    rates=None if ephemeris is None else [float(np.hypot(r['east_rate_arcsec_hour'],r['north_rate_arcsec_hour'])) for r in ephemeris]
    compatible=None if rates is None else all(slow.PARAMETERS['angular_min_arcsec_hour']<=v<=slow.PARAMETERS['angular_max_arcsec_hour'] for v in rates)
    issues=['clock_not_qualified','absolute_astrometry_not_qualified','nucleus_visibility_not_verified','geocentric_reference_only']
    if rates is None:issues.insert(0,'reference_missing')
    elif not compatible:issues.insert(0,'nominal_speed_outside_profile')
    if not info['profile_copy_contract_compatible']:issues.insert(0,'profile_copy_contract_refused')
    return dict(cadence_admissible=True,copies_verified=True,profile_copy_contract_compatible=info['profile_copy_contract_compatible'],
        profile_copy_contract_error=info['profile_copy_contract_error'],nominal_rate_compatible=compatible,
        rate_range_arcsec_hour=None if rates is None else [min(rates),max(rates)],profile_parameters=slow.PARAMETERS.copy(),
        blockers=issues,positive_control_validated=False,ready_for_blind_test=False,
        decision='blocked_copy_metadata' if not info['profile_copy_contract_compatible'] else 'needs_reference' if rates is None else 'blocked_outside_rate' if not compatible else 'needs_qualification',
        clock_qualified=False,astrometry_qualified=False,nucleus_visibility_verified=False,
        date_assumption='DATE-OBS interpreted conditionally as UTC; no midpoint or timezone correction',
        source_kind=info['source_kind'],relative_declared_seconds=info['relative_declared_seconds'])


def assess(plan_path,copies_path,output,reference_path=None,base=None):
    from fetch_control_ephemeris import checked_reference
    base=ROOT/'local' if base is None else base;pp,p,watched=checked_plan(plan_path,base)
    info,inputs=checked_copies(copies_path,pp,p,base);watched.update(inputs)
    ephemeris=None;reference=None
    if reference_path is not None:
        ref=local_path(reference_path,base);ephemeris,inputs=checked_reference(ref,pp,p,base);watched.update(inputs);reference=str(ref)
    output=slow._new_output(output,base)
    result=dict(control_preparation_version='1.0',status='complete',plan_path=str(pp),plan_sha256=watched[pp],
        copies_path=str(local_path(copies_path,base)),reference_path=reference,ephemeris=ephemeris,
        **decisions(info,ephemeris),frozen_sha256_lf=frozen(),detector_called=False,registration_called=False,association_called=False,
        input_hashes={str(k):v for k,v in watched.items()},**slow.experiment.provenance())
    with (output/'conditions.csv').open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['condition','state'])
        for k in ('cadence_admissible','copies_verified','profile_copy_contract_compatible','nominal_rate_compatible','positive_control_validated','ready_for_blind_test'):writer.writerow([k,result[k]])
        for reason in result['blockers']:writer.writerow([reason,'unresolved'])
    slow.unchanged(watched);slow.save(output/'preparation.json',result)
    return result


def checked_preparation(path,base=None):
    from fetch_control_ephemeris import checked_reference
    base=ROOT/'local' if base is None else base;rp=local_path(path,base);r=slow.read(rp)
    pp,p,watched=checked_plan(r['plan_path'],base);info,inputs=checked_copies(r['copies_path'],pp,p,base);watched.update(inputs)
    ephemeris=None
    if r['reference_path'] is not None:ephemeris,inputs=checked_reference(r['reference_path'],pp,p,base);watched.update(inputs)
    expected=decisions(info,ephemeris)
    if (r.get('control_preparation_version')!='1.0' or r.get('status')!='complete' or r.get('plan_sha256')!=watched[pp]
            or r.get('frozen_sha256_lf')!=frozen() or r.get('ephemeris')!=ephemeris or r.get('input_hashes')!={str(k):v for k,v in watched.items()}
            or any(r.get(k)!=v for k,v in expected.items())
            or any(r.get(k) is not False for k in ('detector_called','registration_called','association_called'))):
        raise ValueError('Préparation différente des preuves conservées.')
    watched[rp]=digest(rp);slow.unchanged(watched)
    return r,info,watched


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='command',required=True)
    for name,fields in [('plan',('inventory','summary')),('copy',('plan',)),('assess',('plan','copies'))]:
        sub=subs.add_parser(name)
        for field in (*fields,'output'):sub.add_argument(field,type=Path)
        if name=='assess':sub.add_argument('--reference',type=Path)
        if name=='copy':sub.add_argument('--local-workset',type=Path)
    args=parser.parse_args()
    try:
        if args.command=='plan':r=plan(args.inventory,args.summary,args.output);code=0 if r['selected'] else 2
        elif args.command=='copy':r=copy(args.plan,args.output,local_workset=args.local_workset);code=0
        else:r=assess(args.plan,args.copies,args.output,args.reference);code=2
        print('Préparation conservée ; aucun contrôle positif naturel validé.');raise SystemExit(code)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
