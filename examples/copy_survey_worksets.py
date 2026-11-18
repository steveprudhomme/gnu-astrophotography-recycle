# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Explicit manifest-selected copies only; local cache first, never scan archives."""
import argparse
from pathlib import Path
from gar.astrometry import local_path
from gar.workset import digest,prepare_workset
import seestar_survey as survey

ROOT=Path(__file__).resolve().parents[1]


def copy(plan_path,output,cache_path=None,base=None):
    base=ROOT/'local' if base is None else base;pp,p,watched=survey.checked_plan(plan_path,base)
    manifest=survey.slow.read(p['inventory_path']);known={}
    if cache_path is not None:
        cp=local_path(cache_path,base);cache=survey.slow.read(cp);watched[cp]=digest(cp)
        if cache.get('survey_copy_cache_version')!='1.0' or not isinstance(cache.get('worksets'),list):
            raise ValueError('Liste locale de worksets version 1.0 requise.')
        for name in cache['worksets']:
            wp=local_path(name,base);w=survey.slow.read(wp);watched[wp]=digest(wp)
            if w.get('workset_schema_version')!='1.0' or w.get('success') is not True:raise ValueError('Workset local incomplet.')
            for item in w['files']:
                h=item['sha256_copy']
                if item['sha256_before']!=h or item['sha256_after']!=h:raise ValueError('Ancienne copie non vérifiée.')
                source=local_path(wp.parent/item['local_copy'],base)
                if wp.parent not in source.parents:raise ValueError('Ancienne copie hors de son workset.')
                known.setdefault(h,source)
    output=survey.slow._new_output(output,base)
    index=dict(survey_worksets_version='1.0',plan_sha256=watched[pp],status='running',entries={},errors={},copy_origins={})
    path=output/'worksets.json';survey.slow.save(path,index)
    try:
        for row in p['rows']:
            sid=row['series_id']
            if not row['selection_available']:
                index['errors'][sid]=row['reason'];survey.slow.save(path,index);continue
            try:
                files=[];origins=[]
                for frame in row['frames']:
                    h=frame['sha256'];source=known.get(h)
                    if source is not None:
                        if digest(source)!=h:raise ValueError('Copie locale modifiée ; aucun remplacement par l’archive.')
                        watched[source]=h;origins.append('local_verified_copy')
                    else:
                        source=survey.source_path(Path(manifest['input_root']),frame['path']);origins.append('manifest_source_readonly')
                    files.append(dict(source=str(source),expected_sha256=h))
                folder=output/sid;folder.mkdir()
                prepare_workset(dict(selection_schema_version='1.0',files=files),folder/'workset',base)
                wp=folder/'workset/workset.json';index['entries'][sid]=dict(path=str(wp),sha256=digest(wp))
                index['copy_origins'][sid]=origins
            except (ValueError,OSError,KeyError,TypeError) as exc:index['errors'][sid]=str(exc)
            survey.slow.save(path,index)
        survey.slow.unchanged(watched)
        index.update(status='complete',inputs_unchanged=True);survey.slow.save(path,index)
    except Exception as exc:
        index.update(status='incomplete',error=str(exc));survey.slow.save(path,index);raise
    return index


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--cache',type=Path);args=parser.parse_args()
    try:
        result=copy(args.plan,args.output,args.cache);print('Copies locales préparées ; sources seulement lues.')
        raise SystemExit(2 if result['errors'] or not result['entries'] else 0)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
