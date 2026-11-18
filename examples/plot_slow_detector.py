# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Draw sealed slow-detector replay; no detector, convolution or search is called."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import trace_slow_detector as tracing
from plot_seestar_pilot import render

ROOT=Path(__file__).resolve().parents[1]
LABELS=dict(retained='retenu',project_margin='marge',raw_rejected='rejet interne',
            centroid_displaced='centre déplacé',no_near_raw_maximum='pas de maximum')


def plot(path,output,base=None):
    base=ROOT/'local' if base is None else base
    path=local_path(path,base)
    result,cached,watched=tracing.checked(path,base)
    output=local_path(output,base);output.mkdir(parents=True,exist_ok=False)
    pairs=result['pairs']
    fig,ax=plt.subplots(figsize=(14,6),layout='constrained');ax.axis('off')
    cells=[]
    for cid in tracing.VARIANTS:
        for radius in ('1.5','3'):
            cells.append([('Témoin' if cid=='control' else 'Ajout')+f' · rayon {radius}',
                          *[LABELS[p['variants'][cid]['detector_by_radius'][radius]['status']] for p in pairs]])
    table=ax.table(cellText=cells,colLabels=['Série · pixels natifs',*[f'Photo {i+1}' for i in range(8)]],
                   cellLoc='center',bbox=[0,.25,1,.53],colWidths=[.20]+[.10]*8)
    table.auto_set_font_size(False);table.set_fontsize(10)
    for (r,c),cell in table.get_celld().items():
        cell.set_text_props(color='#152b40');cell.set_edgecolor('#152b40')
        cell.set_facecolor('#e8f2fa' if r==0 or c==0 else '#ffffff')
    ax.set_title('ENTIÈREMENT FICTIF — décisions près des positions connues après rejeu\n'
                 'Les photos 1 à 3 sont la cible du contrôle ; les photos 4 à 8 servent de comparaison.',fontsize=13)
    fig.supxlabel('« pas de maximum » : aucun maximum brut proche proposé, avant les filtres de forme.\n'
        '« retenu » : centre conservé dans le voisinage ; sa seule proximité ne prouve pas une identité.\n'
        'Seuils et positions enregistrées inchangés. Aucun nouveau trajet calculé.',fontsize=10)
    render(fig).save(output/'timeline.png')
    fig,ax=plt.subplots(figsize=(12,5.5),layout='constrained')
    values={};neighbours=[]
    for cid in tracing.VARIANTS:
        values[cid]=[]
        for pair in pairs:
            k=pair['frame_index'];ev=pair['variants'][cid]['peaks_by_radius']['1.5']
            threshold=cached[cid,k][0]['trace']['threshold_effective'];sample=ev['best_sample']
            values[cid].append(np.nan if sample is None else sample['value_for_peaks']/threshold)
            if cid==tracing.CASE_ID:
                other=ev['higher_neighbor'];neighbours.append(np.nan if other is None else other['value_for_peaks']/threshold)
    x=np.arange(1,9)
    ax.plot(x,values['control'],'s--',color='#555555',label='Témoin : meilleure réponse du cercle')
    ax.plot(x,values[tracing.CASE_ID],'o-',color='#143f70',label='Ajout : meilleure réponse du cercle')
    ax.plot(x,neighbours,'^:',color='#8b3308',label='Échantillon voisin plus haut, si présent')
    ax.axhline(1,color='#111111',linestyle='-.',label='Seuil effectif : rapport égal à 1')
    ax.set(xlabel='Numéro de la photo fictive',ylabel='Valeur utilisée pour les maxima / seuil effectif',xticks=x)
    ax.grid(alpha=.2);ax.legend(fontsize=9,loc='best')
    ax.set_title('ENTIÈREMENT FICTIF — dépasser le seuil ne garantit pas un maximum local',fontsize=12)
    fig.supxlabel('Cercle principal : 1,5 pixel natif. Échantillon voisin mesuré dans le voisinage de la trace.\n'
        'Ces valeurs filtrées ne sont pas des magnitudes. Un voisin plus haut ne reçoit aucune identité.',fontsize=10)
    render(fig).save(output/'response.png')
    fig,axes=plt.subplots(2,4,figsize=(13,8),layout='constrained')
    for row,k in enumerate((0,3)):
        pair=pairs[k]
        for col,(cid,kind) in enumerate((('control','original'),(tracing.CASE_ID,'original'),
                                       ('control','convolved'),(tracing.CASE_ID,'convolved'))):
            ax=axes[row,col];view=pair['variants'][cid]['view']
            if kind=='original':
                pixels=np.asarray(view['original_pixels'],dtype=float)
                image=np.arcsinh((pixels-result['display_background'])/result['display_noise'])
                limits=(-1,float(np.arcsinh(20)))
            else:
                image=np.asarray(view['convolved_over_threshold'],dtype=float);limits=(0,3)
            left,bottom=view['left_reduced'],view['bottom_reduced']
            ax.imshow(image,origin='lower',cmap='gray',vmin=limits[0],vmax=limits[1],
                      extent=(left-.5,left+image.shape[1]-.5,bottom-.5,bottom+image.shape[0]-.5))
            target=view['target_reduced'];ax.plot(*target,'o',mfc='none',mec='#ffce45',ms=12,mew=1.5)
            raw=cached[cid,k][0]['trace']['old_detector_trace']
            for point in raw['selected_points_reduced']:
                if np.linalg.norm(np.asarray(point)-target)<=6:
                    ax.plot(*point,'+',color='#59eaff',ms=10,mew=1.5)
            ax.set_title(f"Photo {k+1} · {'Témoin' if cid=='control' else 'Ajout'}\n"
                         +('Intensité, contraste commun' if kind=='original' else 'Carte filtrée / seuil, de 0 à 3'),fontsize=10)
            ax.set_xlabel('Case réduite horizontale',fontsize=8);ax.set_ylabel('Case réduite verticale',fontsize=8)
    fig.suptitle('ENTIÈREMENT FICTIF — comparaison fixée des photos 1 et 4, avec et sans ajout',fontsize=13)
    fig.supxlabel('Cercle : position ajoutée connue après rejeu, aussi reportée sur le témoin. Croix + : centre retenu.\n'
        'Images et cartes conservées ; aucun nouveau calcul de détection ou convolution pendant le dessin.',fontsize=10)
    render(fig).save(output/'comparison.png')
    tracing.slow.unchanged(watched)
    journal=dict(slow_detector_figures_version='1.0',trace_sha256=watched[path],source_kind='synthetic_demo',
                  detector_called=False,convolution_called=False,association_called=False,
                  comparison_frames_fixed=[0,3],figures_sha256={p.name:digest(p) for p in sorted(output.glob('*.png'))})
    tracing.slow.save(output/'figures.json',journal)
    print('Trois figures dessinées depuis les traces scellées, sans nouvelle détection.')
    return journal


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    try:plot(args.trace,args.output)
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
