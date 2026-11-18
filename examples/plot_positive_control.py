# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Draw a verified preparation; no detection, fitting, association, or download."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
import prepare_positive_control as control
from plot_seestar_pilot import render
from run_seestar_pilot import intensity_plane
from gar.workset import digest

ROOT=Path(__file__).resolve().parents[1]


def plot(path,output,base=None):
    base=ROOT/'local' if base is None else base;r,info,watched=control.checked_preparation(path,base)
    output=control.slow._new_output(output,base)
    title='ENTIÈREMENT FICTIF' if r['source_kind']=='synthetic_demo' else 'COPIES RÉELLES — PRIVÉ'
    conditions=[('Cadence compatible','cadence_admissible'),('Copies vérifiées','copies_verified'),('Contrat de configuration compatible','profile_copy_contract_compatible'),
        ('Vitesse nominale compatible','nominal_rate_compatible'),('Horloge qualifiée','clock_qualified'),
        ('Astrométrie qualifiée','astrometry_qualified'),('Noyau vérifié','nucleus_visibility_verified'),
        ('Contrôle positif validé','positive_control_validated')]
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained');ax.axis('off')
    table=ax.table(cellText=[[label,'inconnu' if r[key] is None else 'oui' if r[key] else 'non'] for label,key in conditions],
        colLabels=['Condition','État conservé'],cellLoc='center',bbox=[0,.18,1,.65])
    table.auto_set_font_size(False);table.set_fontsize(12)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#152b40');cell.set_text_props(color='#152b40');cell.set_facecolor('#e8f2fa' if row==0 else 'white')
    ax.set_title(title+' — préparer ne veut pas dire réussir le contrôle',fontsize=13)
    ax.text(.02,.06,'Les inconnues restent visibles. Aucun mobile recherché ou identité confirmée dans ce lot.',transform=ax.transAxes,fontsize=10)
    render(fig).save(output/'conditions.png')
    fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained')
    lo,hi=[r['profile_parameters'][k] for k in ('angular_min_arcsec_hour','angular_max_arcsec_hour')]
    ax.axhspan(lo,hi,color='#dcebd9',label='Domaine du profil conservé : 5 à 120')
    ax.axhline(lo,color='#152b40',ls='--');ax.axhline(hi,color='#152b40',ls='--')
    if r['ephemeris'] is None:
        ax.text(.5,.6,'RÉFÉRENCE ABSENTE\nVitesse inconnue',ha='center',transform=ax.transAxes);ax.set_ylim(0,160)
    else:
        rates=[np.hypot(v['east_rate_arcsec_hour'],v['north_rate_arcsec_hour']) for v in r['ephemeris']]
        ax.plot(range(1,9),rates,'o-',color='#152b40',label='Référence géocentrique, UTC supposé');ax.set_ylim(0,max(160,max(rates)*1.15))
    ax.set(xlabel='Pose choisie',ylabel='Vitesse nominale, secondes d’arc par heure',xticks=range(1,9),title=title+' — comparaison au domaine actuel')
    ax.legend(loc='best',fontsize=9);render(fig).save(output/'rates.png')
    planes=[]
    for item in info['copies']:
        with fits.open(Path(item['local_copy']),mode='readonly',memmap=False) as hdus:planes.append(intensity_plane(hdus[0].data))
    low,high=np.nanpercentile(planes[0],[5,99.7]);contrast=max((high-low)/10,1)
    fig,axes=plt.subplots(2,4,figsize=(12,7),layout='constrained')
    for k,(ax,image) in enumerate(zip(axes.flat,planes)):
        ax.imshow(np.arcsinh(np.maximum(image-low,0)/contrast),origin='lower',cmap='gray',vmin=0,vmax=np.arcsinh(10))
        ax.axis('off');ax.set_title(f'Pose {k+1}')
    fig.suptitle(title+' — huit vues brutes, sans alignement ou détection',fontsize=12)
    fig.supxlabel('Contraste commun pour affichage. Une forme visible ne prouve pas son identité ou sa détection.',fontsize=10)
    render(fig).save(output/'views.png')
    control.slow.unchanged(watched)
    result=dict(control_figures_version='1.0',source_kind=r['source_kind'],preparation_sha256=digest(Path(path)),
        detector_called=False,registration_called=False,association_called=False,network_used=False,
        figures_sha256={p.name:digest(p) for p in sorted(output.glob('*.png'))})
    control.slow.save(output/'figures.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('preparation',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    try:plot(args.preparation,args.output);print('Décisions, vitesses et vues dessinées sans recherche.')
    except (ValueError,OSError,KeyError,TypeError) as exc:parser.exit(1,f'Erreur : {exc}\n')
