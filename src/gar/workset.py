# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: verified local copies and complete header capture.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
import hashlib
import json
import os
from pathlib import Path
import re
import warnings

from astropy.io import fits
from astropy.wcs import WCS

from .contracts import json_value


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def no_links(path):
    return not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)()
                   for p in (*reversed(path.parents),path))


def validate_selection(selection, output, local_root):
    if not isinstance(selection,dict) or selection.get('selection_schema_version')!='1.0':
        raise ValueError('Sélection 1.0 attendue.')
    items=selection.get('files')
    if not isinstance(items,list) or not items:
        raise ValueError('La sélection doit contenir des fichiers explicites.')
    if not no_links(local_root) or not no_links(output):
        raise ValueError('Liens et jonctions refusés dans la destination.')
    base=local_root.resolve();output=output.resolve()
    if base not in output.parents or output.exists():
        raise ValueError('Choisir une nouvelle sortie dans le dossier local/ du projet.')
    paths=[]
    for item in items:
        if not isinstance(item,dict) or not isinstance(item.get('source'),str):
            raise ValueError('Chemin source incorrect.')
        path=Path(item['source'])
        if not path.is_absolute() or not no_links(path) or not path.is_file():
            raise ValueError('Source absolue, régulière et sans lien requise.')
        path=path.resolve()
        if output==path or output in path.parents:
            raise ValueError('La sortie ne peut pas contenir une source.')
        expected=item.get('expected_sha256')
        if expected is not None and (not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected)):
            raise ValueError('Empreinte historique incorrecte.')
        paths.append(path)
    if len(set(paths))!=len(paths):
        raise ValueError('Fichier source répété dans la sélection.')
    return paths,output


def capture_headers(copy, index, output):
    rows=[]
    with fits.open(copy,mode='readonly',memmap=False,do_not_scale_image_data=True,
                   lazy_load_hdus=False) as hdus:
        for number,hdu in enumerate(hdus):
            header=hdu.header
            text_path=f'headers/file-{index:03d}-hdu-{number:03d}.hdr'
            (output/text_path).write_text(header.tostring(sep='\n',endcard=True,padding=False),encoding='utf-8')
            cards=[{'keyword':c.keyword,'value':json_value(c.value),'comment':c.comment,
                    'value_type':type(c.value).__name__,'image':c.image} for c in header.cards]
            model={'status':'no_primary_celestial_axes_observed','celestial_model_constructed':False,
                   'scientifically_validated':False,'sky_coordinates_computed':False,'warnings':[]}
            if header.get('CTYPE1') and header.get('CTYPE2'):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    try:
                        wcs=WCS(header,fobj=hdus,naxis=2,relax=True,fix=False)
                        model['celestial_model_constructed']=bool(wcs.has_celestial)
                        model['status']='celestial_model_constructed_not_validated' if wcs.has_celestial else 'no_celestial_model'
                        model['sip_in_model']=wcs.sip is not None
                        model['normalized_cunit']=[str(u) for u in wcs.wcs.cunit]
                    except Exception as exc:
                        model['status']='model_construction_error';model['error']=f'{type(exc).__name__}: {exc}'
                    model['warnings']=[str(w.message) for w in caught]
            rows.append({'hdu_index':number,'type':type(hdu).__name__,'cards':cards,
                         'header_text':text_path,'wcs_model':model})
    return rows


def prepare_workset(selection,output,local_root):
    paths,output=validate_selection(selection,output,local_root)
    output.mkdir(parents=True,exist_ok=False)
    (output/'copies').mkdir();(output/'headers').mkdir()
    report={'workset_schema_version':'1.0','success':False,'files':[],
            'selection':selection,'sources_open_mode':'rb','science_validated':False}
    try:
        for index,(path,item) in enumerate(zip(paths,selection['files']),1):
            before=digest(path)
            if item.get('expected_sha256') is not None and before!=item['expected_sha256']:
                raise ValueError('Une source ne correspond plus à son empreinte historique.')
            target=output/'copies'/f'{index:03d}-{path.name}'
            stat_before=path.stat()
            with path.open('rb') as source,target.open('xb') as dest:
                while block:=source.read(1024*1024):dest.write(block)
            copied=digest(target);after=digest(path);stat_after=path.stat()
            if before!=copied or before!=after or (stat_before.st_size,stat_before.st_mtime_ns)!=(stat_after.st_size,stat_after.st_mtime_ns):
                raise ValueError('La source a changé ou la copie est différente ; lot non validé.')
            entry={'source':str(path),'local_copy':str(target.relative_to(output)),
                   'sha256_before':before,'sha256_copy':copied,'sha256_after':after,
                   'historical_hash_checked':item.get('expected_sha256') is not None,
                   'hdus':capture_headers(target,index,output)}
            if digest(target)!=copied:raise ValueError('La copie a changé pendant la collecte.')
            report['files'].append(entry)
        report['success']=True
    except Exception as exc:
        report['error']=f'{type(exc).__name__}: {exc}'
        raise ValueError(report['error']) from exc
    finally:
        (output/'workset.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    return report
