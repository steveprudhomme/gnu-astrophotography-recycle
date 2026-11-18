# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Draw a checked paired score; no detector or trajectory search is run."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import nearby_motion_profile as comparison
from plot_seestar_pilot import align_for_display,render

ROOT=Path(__file__).resolve().parents[1]
CASE_ID='r10-a12-p1'


def plot(score_path,output,base=None):
    base=ROOT/'local' if base is None else base
    sp=local_path(score_path,base)
    score,mp,manifest,records,answers,watched=comparison.checked_score(sp,base)
    output=local_path(output,base);output.mkdir(parents=True,exist_ok=False)
    synthetic=manifest['source_kind']=='synthetic_demo'
    label='ENTIÈREMENT FICTIF' if synthetic else 'FOND RÉEL + AJOUTS ARTIFICIELS — PRIVÉ'
    fig,ax=plt.subplots(figsize=(12,6),layout='constrained');ax.axis('off')
    cells=[]
    for variant in comparison.VARIANTS:
        data=score['variants'][variant]
        for peak in (6,12):
            groups={g['angular_rate_arcsec_hour']:g for g in data['groups'] if g['peak_sigma']==peak}
            cells.append([('Référence 5' if variant=='reference' else 'Variante 3'),f'{peak} × bruit',
                *['non mesuré' if groups[r]['recovered'] is None else
                  f"{groups[r]['recovered']}/2 retrouvés\n{groups[r]['unavailable']} indisponible(s)" for r in (10.,30.,60.)]])
    table=ax.table(cellText=cells,colLabels=['Voisinage réduit','Pic ajouté','10 secondes d’arc/h','30 secondes d’arc/h','60 secondes d’arc/h'],
                   cellLoc='center',bbox=[0,.30,1,.48])
    table.auto_set_font_size(False);table.set_fontsize(10)
    for (r,c),cell in table.get_celld().items():
        cell.set_edgecolor('#152b40');cell.set_text_props(color='#152b40')
        cell.set_facecolor('#e8f2fa' if r==0 or c<2 else '#ffffff')
    lines=[]
    for variant in comparison.VARIANTS:
        d=score['variants'][variant];bright=d['bright']['recovered'];control=d['control_candidates']
        lines.append(f"{'Référence 5' if variant=='reference' else 'Variante 3'} : brillants {bright if bright is not None else '?'} / 6 ; "
                     f"témoin {control if control is not None else '?'} ; non associés {d['unassociated_candidates'] if d['unassociated_candidates'] is not None else '?' }.")
    ax.text(.02,.19,'\n'.join(lines),transform=ax.transAxes,va='top',fontsize=11,color='#152b40')
    criterion=score['synthetic_criteria_passed']
    verdict='satisfait' if criterion is True else 'NON satisfait' if criterion is False else 'sans objet sur fond réel'
    ax.text(.02,.06,'Critère réservé de la variante : '+verdict+'.',transform=ax.transAxes,fontsize=11,color='#152b40')
    ax.set_title(label+' — mêmes pixels, seul le voisinage de détection change\n'
        'Seuil de luminosité : 5 × bruit ; filtres de forme et trajectoires identiques.',fontsize=13)
    render(fig).save(output/'recovery.png')
    case=next(c for c in manifest['cases'] if c['case_id']==CASE_ID)
    pixel_watch={};planes=comparison.slow.experiment.load_planes(mp,manifest,case,base,pixel_watch)
    baseline=comparison.slow.read(local_path(manifest['baseline_report'],base))
    background=baseline['selections'][0]['background'];noise=manifest['noise_sigma_first_reduced']
    known=np.array([[p['x'],p['y']] for p in answers[CASE_ID]['positions']])
    low=(known.min(axis=0)-.5)/2-16;high=(known.max(axis=0)-.5)/2+16
    def panel(ax,variant,k):
        ax.axis('off')
        if planes is None:
            ax.text(.5,.5,'INDISPONIBLE',transform=ax.transAxes,ha='center');return
        shown=align_for_display(planes[k],manifest['models'][k])
        ax.imshow(np.arcsinh(np.maximum(shown-background,0)/noise),origin='lower',cmap='gray',vmin=0,vmax=np.arcsinh(20))
        ax.set(xlim=(low[0],high[0]),ylim=(low[1],high[1]))
        target=(known[k]-.5)/2;ax.plot(*target,'o',mfc='none',mec='#ffce45',ms=14,mew=1.5)
        record=records[variant][CASE_ID]
        if record['search_status']=='complete':
            for point in record['data']['mapped_detections'][k]:
                xy=(np.asarray(point)-.5)/2
                if np.linalg.norm(xy-target)<=6:ax.plot(*xy,'+',color='#59eaff',ms=11,mew=1.5)
        else:ax.text(.02,.02,'RECHERCHE INDISPONIBLE',transform=ax.transAxes,color='#ffffff',fontsize=9)
    frames=[]
    for k in range(8):
        fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
        for ax,variant,title in zip(axes,comparison.VARIANTS,('Référence : 5 cases réduites','Variante : 3 cases réduites')):
            panel(ax,variant,k);ax.set_title(title,fontsize=12)
        fig.suptitle(label+f' — photo {k+1}/8, cas fixé 10 secondes d’arc/h, pic 12',fontsize=12)
        fig.supxlabel('Pixels identiques ; contraste commun. Cercle : ajout connu après recherche. Croix + : mesure conservée près du cercle.\n'
            'Une mesure proche ne garantit pas un trajet récupéré. Lecture artificielle : 600 ms par vue.',fontsize=9)
        frames.append(render(fig))
    frames[0].save(output/'comparison-first.png')
    frames[0].save(output/'comparison.gif',save_all=True,append_images=frames[1:],duration=600,loop=0,optimize=False)
    fig,axes=plt.subplots(2,2,figsize=(10,8),layout='constrained')
    for row,k in enumerate((0,3)):
        for col,variant in enumerate(comparison.VARIANTS):
            panel(axes[row,col],variant,k)
            axes[row,col].set_title(f"Photo {k+1} · {'référence 5' if variant=='reference' else 'variante 3'}",fontsize=11)
    fig.suptitle(label+' — photos 1 et 4 choisies avant les essais',fontsize=12)
    fig.supxlabel('Mêmes pixels et modèles ; seuls les centres proposés peuvent changer.\n'
        'Cercle connu après recherche ; croix limitée aux mesures à moins de 6 cases réduites.',fontsize=10)
    render(fig).save(output/'comparison-static.png')
    comparison.slow.unchanged(watched);comparison.slow.unchanged(pixel_watch)
    journal=dict(nearby_figures_version='1.0',source_kind=manifest['source_kind'],score_sha256=watched[sp],
        detector_called=False,association_called=False,case_fixed=CASE_ID,static_frames_fixed=[0,3],
        playback_ms=600,figures_sha256={p.name:digest(p) for p in sorted(output.iterdir()) if p.suffix in ('.png','.gif')})
    comparison.slow.save(output/'figures.json',journal)
    print('Bilan comparatif, vues fixes et animation dessinés sans nouvelle recherche.')
    return journal


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('score',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    try:plot(args.score,args.output)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
