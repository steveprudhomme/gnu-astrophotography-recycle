# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Optional scientific PNG/GIF from fictional FITS and frozen measured tracks."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np
from astropy.io import fits
from gar.astrometry import local_path
from gar.workset import digest


def plot(manifest_path, report_path, output):
    root=Path(__file__).resolve().parents[1]; base=root/'local'
    manifest_path=local_path(manifest_path,base); report_path=local_path(report_path,base)
    output=local_path(output,base)
    if output.exists(): raise ValueError('Choisir un nouveau dossier de figures dans local/.')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8')); result=json.loads(report_path.read_text(encoding='utf-8'))
    if manifest.get('synthetic') is not True or result.get('synthetic_only') is not True or digest(manifest_path)!=result['inputs_sha256_before']['manifest']:
        raise ValueError('Rapport et manifeste synthétiques correspondants requis.')
    output.mkdir(parents=True,exist_ok=False)
    scenarios=['nominal','control','missing','faint_slow','blend','jitter']
    names=['Deux mobiles faciles','Aucun mobile','Deux images manquantes','Faible et très lent','Près d’une étoile','Petit défaut de repérage']
    injected=[sum(s['evaluation']['injected'] for s in result['sequences'] if s['scenario']==name) for name in scenarios]
    recovered=[sum(s['evaluation']['recovered'] for s in result['sequences'] if s['scenario']==name) for name in scenarios]
    false=[sum(s['evaluation']['false_candidates'] for s in result['sequences'] if s['scenario']==name) for name in scenarios]
    fig,ax=plt.subplots(figsize=(11,5.5)); y=np.arange(len(names))
    ax.barh(y-.2,injected,height=.2,color='#bbc8d3',label='Objets ajoutés (vérité connue)')
    ax.barh(y,recovered,height=.2,color='#237f9b',label='Objets retrouvés')
    ax.barh(y+.2,false,height=.2,color='#d57a32',label='Faux candidats')
    for k,(a,b,c) in enumerate(zip(injected,recovered,false)): ax.text(max(a,b,c)+.15,k,f'{b}/{a} retrouvés ; {c} faux',va='center',fontsize=10)
    ax.set_yticks(y,names); ax.invert_yaxis(); ax.set_xlim(0,max(injected)+3.5)
    ax.set_xlabel('Nombre d’objets sur trois graines fictives'); ax.grid(axis='x',alpha=.15); ax.set_axisbelow(True)
    ax.legend(loc='lower right',fontsize=9)
    ax.set_title('DONNÉES SYNTHÉTIQUES — résultats réellement calculés\nLes échecs des cas difficiles restent visibles',pad=18)
    fig.tight_layout(); fig.savefig(output/'moving-benchmark.png',dpi=160); plt.close(fig)
    seq=next(s for s in manifest['sequences'] if s['sequence_id']=='nominal-17')
    measured=next(s for s in result['sequences'] if s['sequence_id']=='nominal-17')
    images=[]; image_paths=[]
    for frame in seq['frames']:
        path=local_path(manifest_path.parent/frame['local_copy'],base)
        if digest(path)!=frame['sha256']: raise ValueError('Image modifiée.')
        with fits.open(path,mode='readonly',memmap=False) as hdus:
            if hdus[0].header.get('GARSYNTH') is not True: raise ValueError('Marqueur synthétique requis.')
            images.append(hdus[0].data.astype(float))
        image_paths.append((path,frame['sha256']))
    fig,ax=plt.subplots(figsize=(6,6)); display=ax.imshow(np.arcsinh(np.maximum(images[0]-96,0)/10),cmap='gray',vmin=0,vmax=4.5,origin='lower')
    ax.set_xlabel('x (pixel)'); ax.set_ylabel('y (pixel)')
    artists=[]
    for i,t in enumerate(measured['tracks']):
        line,=ax.plot([],[],color=['#42dcad','#ffb858'][i%2],marker='o',ms=5,lw=1,label=f'Candidat {t["candidate_id"]}')
        artists.append(line)
    ax.legend(loc='upper right',fontsize=8)
    def update(k):
        display.set_data(np.arcsinh(np.maximum(images[k]-96,0)/10))
        ax.set_title(f'IMAGES FICTIVES — image {k+1}/8\nTemps relatif inventé : {seq["frames"][k]["relative_time_seconds"]:.0f} s')
        for artist,track in zip(artists,measured['tracks']):
            points=[p for p in track['points'] if p['frame_index']<=k]
            artist.set_data([p['x'] for p in points],[p['y'] for p in points])
        return [display,*artists]
    update(0); fig.tight_layout(); update(7); fig.savefig(output/'moving-frame.png',dpi=160)
    animation=FuncAnimation(fig,update,frames=8,interval=400,blit=False)
    animation.save(output/'moving-demo.gif',writer=PillowWriter(fps=2)); plt.close(fig)
    if any(digest(path)!=value for path,value in image_paths): raise ValueError('Une image a changé.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path); parser.add_argument('report',type=Path); parser.add_argument('output',type=Path)
    args=parser.parse_args(); plot(args.manifest,args.report,args.output)
