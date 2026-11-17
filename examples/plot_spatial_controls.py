# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Actual synthetic control selections, availability and the path to a real pilot."""
import argparse
import json
from pathlib import Path

from astropy.io import fits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

from gar.astrometry import local_path
from gar.workset import digest
from compare_spatial_controls import ROOT, validate_manifest


def plot(manifest_path, report_path, output, base=None):
    base = ROOT/'local' if base is None else base
    mp, rp, output = [local_path(p, base) for p in (manifest_path, report_path, output)]
    manifest, result = [json.loads(p.read_text(encoding='utf-8')) for p in (mp, rp)]
    validate_manifest(manifest)
    if result.get('synthetic_only') is not True or result.get('suite_complete') is not True or result['manifest_sha256'] != digest(mp):
        raise ValueError('Manifeste et rapport synthétiques complets correspondants requis.')
    watched = {mp: digest(mp), rp: digest(rp)}
    for name, value in result['frozen_report_sha256'].items():
        p = local_path(rp.parent/f'{name}.json', base)
        if digest(p) != value: raise ValueError('Rapport gelé modifié.')
        watched[p] = value
    output.mkdir(parents=True, exist_ok=False)

    def load_image(sequence, k):
        frame = sequence['frames'][k]
        p = local_path(mp.parent/frame['local_copy'], base)
        if digest(p) != frame['sha256']: raise ValueError('Image modifiée.')
        watched[p] = frame['sha256']
        with fits.open(p, mode='readonly', memmap=False) as hdus:
            if hdus[0].header.get('GARSYNTH') is not True: raise ValueError('Image fictive requise.')
            return hdus[0].data.astype(float)

    rows = result['summary']['conditions']
    labels = [c['label'] for c in rows]
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), sharey=True, layout='constrained')
    for ax, method, color, title in zip(axes, ['historical', 'spatial'], ['#a4b4c2', '#237f9b'], ['Partition historique', 'Partition spatiale']):
        counts = [c['methods'][method]['available'] for c in rows]
        ax.barh(np.arange(10), counts, color=color)
        for k, n in enumerate(counts): ax.text(n+.08, k, f'{n}/5', va='center')
        ax.set_xlim(0, 5.9); ax.set_xticks(range(6)); ax.set_yticks(np.arange(10), labels)
        ax.set_xlabel('Séquences avec branche après disponible'); ax.set_title(title)
    axes[0].set_ylim(9.6, -.6)
    fig.suptitle('IMAGES FICTIVES — mêmes images, deux façons de réserver les contrôles\nLes trois dernières lignes doivent rester refusées ; les critères de qualité sont inchangés', fontsize=12)
    fig.savefig(output/'spatial-availability.png', dpi=145); plt.close(fig)

    sequence = next(s for s in manifest['sequences'] if s['sequence_id'] == 'combined-s1103')
    measured = next(s for s in result['sequences'] if s['sequence_id'] == 'combined-s1103')
    images = [load_image(sequence, k) for k in range(8)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 7), layout='constrained')
    artists = []
    for ax in axes:
        display = ax.imshow(np.arcsinh(np.maximum(images[0]-96, 0)/10), origin='lower', cmap='gray', vmin=0, vmax=4.5)
        training, = ax.plot([], [], 'o', color='#60c7f0', mfc='none', ms=6, linestyle='none', label='Ajustement')
        control, = ax.plot([], [], 'o', color='#ffb357', mfc='none', ms=9, linestyle='none', label='Réservées au contrôle')
        for boundary in [256/3, 128, 512/3]:
            ax.axvline(boundary, color='white', lw=1 if boundary == 128 else .4, alpha=.7)
            ax.axhline(boundary, color='white', lw=1 if boundary == 128 else .4, alpha=.7)
        ax.set_xlabel('x (pixel natif)'); ax.set_ylabel('y (pixel natif)')
        ax.legend(loc='lower right', fontsize=8)
        artists.append((display, training, control))

    def update(k):
        stars = np.asarray(measured['star_detections'][k]).reshape(-1, 2)
        for ax, method, (display, training, control), label in zip(axes, ['historical', 'spatial'], artists, ['Ancienne partition', 'Partition spatiale']):
            display.set_data(np.arcsinh(np.maximum(images[k]-96, 0)/10))
            model = measured['methods'][method]['registration'][k]
            for artist, key in [(training, 'training_detection_indices'), (control, 'control_detection_indices')]:
                ids = model.get(key, [])
                artist.set_data(stars[ids, 0], stars[ids, 1])
            c = model.get('metrics', {}).get('control')
            detail = f'{c["matches"]} associés ; {c["quadrants_occupied"]}/4 quadrants ; {c["grid_cells_occupied"]}/9 cellules' if c else 'Référence commune, pas de partition ajustée'
            ax.set_title(label+'\n'+detail, fontsize=10)
        fig.suptitle(f'IMAGES FICTIVES — sélection réservée avant ajustement, image {k+1}/8\nMêmes étoiles mesurées ; aucun résidu ou réponse connue pour choisir les contrôles', fontsize=11)
        return [a for group in artists for a in group]

    update(1); fig.savefig(output/'spatial-selection.png', dpi=140)
    animation = FuncAnimation(fig, update, frames=8, interval=500, blit=False)
    animation.save(output/'spatial-controls.gif', writer=PillowWriter(fps=2)); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.3), layout='constrained')
    for ax, name, label in zip(axes, ['insufficient', 'missing-quadrant', 'narrow-field'],
                               ['12 étoiles : trop peu de contrôles', 'Quadrant réellement vide', 'Bande étroite : couverture insuffisante']):
        s = next(s for s in manifest['sequences'] if s['sequence_id'] == f'{name}-s1103')
        m = next(r for r in result['sequences'] if r['sequence_id'] == s['sequence_id'])
        image = load_image(s, 1)
        ax.imshow(np.arcsinh(np.maximum(image-96, 0)/10), origin='lower', cmap='gray', vmin=0, vmax=4.5)
        p = np.asarray(m['star_detections'][1])
        model = m['methods']['spatial']['registration'][1]
        ids = model.get('control_detection_indices', [])
        ax.scatter(p[ids, 0], p[ids, 1], s=55, facecolors='none', edgecolors='#ffb357')
        for boundary in [256/3, 128, 512/3]:
            ax.axvline(boundary, color='white', lw=.5); ax.axhline(boundary, color='white', lw=.5)
        ax.set_title(label+'\nBranche refusée conservée', fontsize=9)
        ax.set_xlabel('x (pixel)'); ax.set_ylabel('y (pixel)')
    fig.suptitle('IMAGES FICTIVES — mieux répartir ne crée pas les étoiles manquantes\nContrôles sélectionnés en orange ; les quinze séquences négatives restent bloquées', fontsize=12)
    fig.savefig(output/'spatial-negatives.png', dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 4.8), layout='constrained')
    ax.set_xlim(0, 12); ax.set_ylim(0, 5); ax.axis('off')
    for x, title, lines, color in [(0.1, '1. Préparer la série', 'Manifestes locaux\nCopies de poses compatibles\nTraitement des pixels à établir', '#e6f0f7'),
                                  (4.15, '2. Essai exploratoire réel', 'Recalage et candidats\nRésultats privés et revus\nAucune découverte garantie', '#d9eef2'),
                                  (8.2, '3. Mesures scientifiques', 'Heures et erreurs qualifiées\nCalibrations et traçabilité\nTravail supplémentaire', '#f6e6d8')]:
        ax.add_patch(patches.FancyBboxPatch((x, 1.25), 3.6, 2.65, boxstyle='round,pad=.08', facecolor=color, edgecolor='#5b8498'))
        ax.text(x+1.8, 3.45, title, ha='center', fontsize=11, weight='bold')
        ax.text(x+1.8, 2.35, lines, ha='center', va='center', fontsize=10, linespacing=1.8)
    for x in [3.75, 7.8]: ax.annotate('', xy=(x+.35, 2.6), xytext=(x, 2.6), arrowprops=dict(arrowstyle='->', color='#325d73'))
    ax.text(6, 4.65, 'Vers les vraies images Seestar : le prochain jalon à préparer', ha='center', fontsize=15, weight='bold', color='#173b50')
    ax.text(6, .55, 'SCHÉMA CONCEPTUEL — ni mesure ni capture d’écran ; aucune date de disponibilité promise', ha='center', fontsize=10, color='#526c7a')
    fig.savefig(output/'seestar-next-pilot.png', dpi=150); plt.close(fig)
    if any(digest(p) != value for p, value in watched.items()): raise ValueError('Une entrée a changé pendant le dessin.')
    print('Quatre PNG (dont un schéma conceptuel) et un GIF synthétique produits.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('manifest', 'report', 'output'): parser.add_argument(field, type=Path)
    args = parser.parse_args(); plot(args.manifest, args.report, args.output)
