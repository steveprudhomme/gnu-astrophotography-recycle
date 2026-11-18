# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Explicit date-only JPL request; cache and parse once, then work offline."""
import argparse
import csv
from datetime import datetime,timezone
from io import StringIO
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request,build_opener,HTTPRedirectHandler
import numpy as np
from astropy.time import Time
from gar.astrometry import local_path
from gar.workset import digest
import prepare_positive_control as control

ROOT=Path(__file__).resolve().parents[1]
ENDPOINT='https://ssd.jpl.nasa.gov/api/horizons.api'


def dates(plan):
    if plan['selected'] is None:raise ValueError('Huit poses sélectionnées sont requises.')
    times=[r['DATE-OBS'] for r in plan['selected']['frames']]
    if len(times)!=8 or len(set(times))!=8:raise ValueError('Huit dates distinctes requises.')
    return [float(Time(t,format='isot',scale='utc').jd) for t in times]


def parameters(plan):
    if plan['selected']['target']!=control.TARGET:raise ValueError('Désignation non autorisée pour cette requête.')
    return dict(format='json',COMMAND="'DES=C/2023 A3;NOFRAG;CAP'",MAKE_EPHEM="'YES'",OBJ_DATA="'YES'",
        EPHEM_TYPE="'OBSERVER'",CENTER="'500@399'",TLIST=' '.join(f"'{v:.12f}'" for v in dates(plan)),
        TLIST_TYPE="'JD'",TIME_TYPE="'UT'",TIME_DIGITS="'FRACSEC'",CSV_FORMAT="'YES'",ANG_FORMAT="'DEG'",
        REF_SYSTEM="'ICRF'",RANGE_UNITS="'AU'",QUANTITIES="'1,3,20'")


def parse(payload,plan,synthetic=False):
    if not isinstance(payload,dict) or payload.get('error'):raise ValueError('Réponse JPL en erreur.')
    expected_source='LOCAL SYNTHETIC' if synthetic else 'NASA/JPL Horizons API'
    if payload.get('signature',{}).get('source')!=expected_source:raise ValueError('Provenance de référence incorrecte.')
    text=payload.get('result','')
    if (not isinstance(text,str) or text.count('$$SOE')!=1 or text.count('$$EOE')!=1
            or not re.search(r'Target body name:.*C/2023 A3',text)
            or 'Center-site name: GEOCENTRIC' not in text):raise ValueError('Désignation, observateur ou table non reconnus.')
    before,data=text.split('$$SOE');body,after=data.split('$$EOE')
    headers=[line for line in before.splitlines() if ',' in line and 'R.A._(ICRF)' in line and ('JDUT' in line or 'Date__(UT)' in line)]
    if not headers:raise ValueError('En-tête de dates UT manquant.')
    names=[s.strip() for s in next(csv.reader([headers[-1]]))]
    time_column=next((n for n in names if 'JDUT' in n),None)
    if time_column is None:time_column=next((n for n in names if n.startswith('Date__(UT)__HR:MN:SC')),None)
    required={'ra':'R.A._(ICRF)','dec':'DEC_(ICRF)','east':'dRA*cosD','north':'d(DEC)/dt','distance':'delta'}
    if time_column is None:raise ValueError('Colonne UT précise requise.')
    if any(n not in names for n in required.values()):raise ValueError('Colonnes ou unités JPL non reconnues.')
    rows=[]
    for cells in csv.reader(StringIO(body.strip())):
        if not cells or not any(s.strip() for s in cells):continue
        if len(cells)!=len(names):raise ValueError('Ligne de référence incomplète.')
        record=dict(zip(names,[c.strip() for c in cells]))
        try:
            v={k:float(record[n]) for k,n in required.items()}
            if 'JDUT' in time_column:v['jd']=float(record[time_column])
            else:
                date=record[time_column];match=re.fullmatch(r'(\d{4})-([A-Z][a-z]{2})-(\d{2}) (\d{2}:\d{2}:\d{2}(?:\.\d+)?)',date)
                if match is None:raise ValueError('Date calendaire UT non reconnue.')
                year,month,day,hour=match.groups();months='Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
                isot=f'{year}-{months.index(month)+1:02}-{day}T{hour}'
                v['jd']=float(Time(isot,format='isot',scale='utc').jd)
        except (ValueError,TypeError):raise ValueError('Valeur de référence ou date UT non reconnue.') from None
        if (not all(np.isfinite(x) for x in v.values()) or not 0<=v['ra']<360 or not -90<=v['dec']<=90 or v['distance']<=0):
            raise ValueError('Valeur de référence hors domaine.')
        rows.append(dict(jd_utc_assumed=v['jd'],ra_astrometric_icrf_degrees=v['ra'],dec_astrometric_icrf_degrees=v['dec'],
            east_rate_arcsec_hour=v['east'],north_rate_arcsec_hour=v['north'],geocentric_distance_au=v['distance']))
    if len(rows)!=8 or any(abs(r['jd_utc_assumed']-d)>5e-8 for r,d in zip(rows,dates(plan))):
        raise ValueError('Les huit dates de référence ne correspondent pas au plan.')
    return rows


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Redirection refusée pour la requête privée.')


def fetch(plan_path,output,allow_date_query=False,base=None):
    base=ROOT/'local' if base is None else base;pp,p,watched=control.checked_plan(plan_path,base)
    if not allow_date_query:raise ValueError('Autorisation explicite de transmettre les huit dates requise.')
    if p['synthetic']:raise ValueError('Aucune requête externe pour un exercice fictif.')
    params=parameters(p);output=control.slow._new_output(output,base)
    receipt=dict(control_reference_version='1.0',status='running',plan_path=str(pp),plan_sha256=watched[pp],
        parameters=params,endpoint=ENDPOINT,synthetic=False,geocentric=True,
        downloaded_at_utc=datetime.now(timezone.utc).isoformat(),frozen_sha256_lf=control.frozen())
    rp=output/'reference.json';control.slow.save(rp,receipt)
    try:
        request=Request(ENDPOINT+'?'+urlencode(params),headers={'User-Agent':'GNU-Astrophotography-Recycle/0.16.0a1'})
        with build_opener(NoRedirect()).open(request,timeout=90) as response:
            raw=response.read(4*1024*1024+1)
        if len(raw)>4*1024*1024:raise ValueError('Réponse trop volumineuse.')
        path=output/'response.json';path.write_bytes(raw)
        receipt.update(response_file='response.json',response_sha256=digest(path));control.slow.save(rp,receipt)
        payload=control.slow.read(path);rows=parse(payload,p)
        control.slow.unchanged(watched)
        receipt.update(status='complete',response_file='response.json',response_sha256=digest(path),rows=rows,
            input_dates_assumed_utc=True,inputs_unchanged=True);control.slow.save(rp,receipt)
    except Exception as exc:
        receipt.update(status='incomplete',error=str(exc));control.slow.save(rp,receipt);raise
    return receipt


def checked_reference(path,pp,plan,base):
    rp=local_path(path,base);r=control.slow.read(rp);raw=local_path(rp.parent/r['response_file'],base)
    if (r.get('control_reference_version')!='1.0' or r.get('status')!='complete' or r.get('plan_path')!=str(pp)
            or r.get('plan_sha256')!=digest(pp) or r.get('parameters')!=parameters(plan)
            or r.get('synthetic')!=plan['synthetic'] or r.get('geocentric') is not True
            or r.get('frozen_sha256_lf')!=control.frozen() or r.get('endpoint')!=ENDPOINT
            or r.get('input_dates_assumed_utc') is not True or r.get('inputs_unchanged') is not True
            or rp.parent not in raw.parents or digest(raw)!=r['response_sha256']):
        raise ValueError('Référence incomplète, modifiée ou étrangère au plan.')
    rows=parse(control.slow.read(raw),plan,plan['synthetic'])
    if rows!=r.get('rows'):raise ValueError('Valeurs normalisées différentes de la réponse brute.')
    return rows,{rp:digest(rp),raw:digest(raw)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--allow-date-query',action='store_true');args=parser.parse_args()
    try:fetch(args.plan,args.output,args.allow_date_query);print('Référence géocentrique conservée localement.')
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
