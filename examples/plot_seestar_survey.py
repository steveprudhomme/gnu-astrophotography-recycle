# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Render a sealed survey, without detection, registration, or association."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seestar_survey as survey
from plot_seestar_pilot import plot as draw_series,render
from gar.astrometry import local_path
from gar.workset import digest

ROOT=Path(__file__).resolve().parents[1]


def plot(path,output,base=None):
    base=ROOT/'local' if base is None else base;r,records,watched=survey.checked(path,base)
    output=survey.slow._new_output(output,base)
    synthetic=bool(records) and all(rec['source_kind']=='synthetic_demo' for rec in records)
    label='ENTIÈREMENT FICTIF' if synthetic else 'SÉRIES RÉELLES — PRIVÉ'
    cells=[];files=[]
    for rec in records:
        cells.append([rec['series_id'],*['indisponible' if rec['profiles'][v]['candidate_count'] is None else str(rec['profiles'][v]['candidate_count']) for v in survey.paired.VARIANTS]])
        if rec['baseline_path'] is None:continue
        b=survey.slow.read(local_path(rec['baseline_path'],base))
        for variant,d in rec['profiles'].items():
            view=dict(status='complete',input_hashes_unchanged=True,input_kind=rec['source_kind'],copies=b['copies'],models=b['models'],
                registration_available=b['registration_available'],motion_searched=d['search_status']=='complete',
                candidate_count=d['candidate_count'],search=d['data']['search'] if d['data'] is not None else None)
            adapter=output/f'{rec["series_id"]}-{variant}.json';survey.slow.save(adapter,view)
            folder=output/f'{rec["series_id"]}-{variant}';draw_series(adapter,folder,base)
            files.extend(p for p in folder.iterdir() if p.suffix in ('.png','.gif'))
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained');ax.axis('off')
    table=ax.table(cellText=cells or [['Aucune série','indisponible','indisponible']],
        colLabels=['Série prévue','Référence : 5 cases','Variante : 3 cases'],cellLoc='center',bbox=[0,.25,1,.55])
    table.auto_set_font_size(False);table.set_fontsize(12)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#152b40');cell.set_facecolor('#e8f2fa' if row==0 else 'white');cell.set_text_props(color='#152b40')
    ax.set_title(label+' — occurrences de candidats, sans identité confirmée',fontsize=13)
    ax.text(.02,.12,'0 = recherche terminée sans candidat. Indisponible = aucun compte mesuré.\n'
        'Les deux colonnes peuvent contenir le même objet. Aucun total d’objets distincts déduit.',transform=ax.transAxes,fontsize=10)
    p=output/'overview.png';render(fig).save(p);files.append(p)
    survey.slow.unchanged(watched)
    result=dict(survey_figures_version='1.0',source_kind='synthetic_demo' if synthetic else 'real_or_unavailable_private',
        survey_sha256=digest(local_path(path,base)),detector_called=False,registration_called=False,association_called=False,
        figures_sha256={str(p.relative_to(output)):digest(p) for p in sorted(files)})
    survey.slow.save(output/'figures.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('survey',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    try:plot(args.survey,args.output);print('Bilan, vues fixes et GIF dessinés sans nouvelle recherche.')
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
