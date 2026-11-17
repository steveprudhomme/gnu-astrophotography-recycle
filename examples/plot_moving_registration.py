# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Measured before/after coordinate overlays, with refused sequences kept visible."""
import argparse
import json
from pathlib import Path

from astropy.io import fits
import matplotlib
matplotlib.use('Agg')
from matplotlib import patches
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

from gar.astrometry import local_path
from gar.workset import digest
from moving_registration import ROOT, validate_manifest


def plot(manifest_path, truth_path, report_path, output, base=None):
    base = ROOT/'local' if base is None else base
    mp, tp, rp, output = [local_path(p, base) for p in (manifest_path, truth_path, report_path, output)]
    manifest, truth, result = [json.loads(p.read_text(encoding='utf-8')) for p in (mp, tp, rp)]
    validate_manifest(manifest)
    if (result.get('synthetic_only') is not True or result.get('suite_complete') is not True
            or result['manifest_sha256'] != digest(mp) or result['truth_sha256'] != digest(tp)):
        raise ValueError('Rapport et réponses fictives correspondant au manifeste requis.')
    watched = {p: digest(p) for p in (mp, tp, rp)}
    for name, value in result['frozen_candidate_report_sha256'].items():
        path = local_path(rp.parent/f'{name}.json', base)
        if digest(path) != value:
            raise ValueError('Un rapport gelé de candidats a changé.')
        watched[path] = value
    output.mkdir(parents=True, exist_ok=False)
    rows = result['summary']['conditions']
    labels = ['Alignées', 'Dérive', 'Rotation 2°', 'Dérive + rotation 2°', 'Rotation 8° (descriptif)',
              'Sans mobile : dérive', 'Sans mobile : combinaison', '12 étoiles (refus attendu)']
    y = np.arange(8)
    fig, ax = plt.subplots(figsize=(11, 6), layout='constrained')
    accepted = [c['after_available'] for c in rows]
    blocked = [c['after_blocked'] for c in rows]
    ax.barh(y, accepted, color='#237f9b', label='Branche après disponible')
    ax.barh(y, blocked, left=accepted, color='#d7816c', label='Branche après bloquée')
    for k, (a, b) in enumerate(zip(accepted, blocked)):
        ax.text(5.1, k, f'{a}/5 disponibles ; {b} bloquée(s)', va='center', fontsize=9)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 8.6)
    ax.set_xticks(range(6))
    ax.set_xlabel('Nombre de séquences sur cinq prévues')
    fig.legend(loc='outside lower center', ncol=2, fontsize=9)
    ax.set_title('IMAGES FICTIVES — conserver les refus\nCritères globaux non tous satisfaits : 15/20 séquences principales exploitables après recalage')
    fig.savefig(output/'registered-availability.png', dpi=150)
    plt.close(fig)

    # Paired comparisons use exactly the same available sequences in BOTH branches.
    paired = []
    for c in rows:
        seq = [s for s in result['sequences'] if s['condition_id'] == c['condition_id'] and s['after_available']]
        paired.append(dict(n=len(seq), before_false=sum(s['before']['evaluation']['false_candidates'] for s in seq),
                           after_false=sum(s['after']['evaluation']['false_candidates'] for s in seq),
                           before_recovered=sum(s['before']['evaluation']['recovered'] for s in seq),
                           after_recovered=sum(s['after']['evaluation']['recovered'] for s in seq), mobile=c['mobile']))
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5), sharey=True, layout='constrained')
    for ax, before_key, after_key, title in zip(axes, ['before_false', 'before_recovered'],
                                               ['after_false', 'after_recovered'], ['Faux candidats', 'Mobiles retrouvés']):
        for k, p in enumerate(paired):
            if not p['n']:
                ax.text(.1, k, 'Indisponible : aucune comparaison', va='center', fontsize=8)
                continue
            a, b = p[before_key], p[after_key]
            ax.barh(k-.16, a, height=.3, color='#d57a32', label='Avant (mêmes séquences)' if k == 0 else None)
            ax.barh(k+.16, b, height=.3, color='#237f9b', label='Après' if k == 0 else None)
            label = f'{a} → {b}' if before_key == 'before_false' else (f'{a}/{p["n"]} → {b}/{p["n"]}' if p['mobile'] else 'Aucun mobile injecté')
            ax.text(max(a, b)+(.12 if before_key != 'before_false' else 4), k, label, va='center', fontsize=8)
        ax.set_title(title)
        ax.set_yticks(y, [f'{label} [{p["n"]}/5]' for label, p in zip(labels, paired)])
        ax.set_xlim(0, 490 if before_key == 'before_false' else 8.8)
        ax.set_xlabel('Comparaison sur les seules séquences disponibles des deux côtés')
    axes[0].set_ylim(7.65, -.65)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc='outside lower center', ncol=2, fontsize=8)
    fig.suptitle('DONNÉES SYNTHÉTIQUES — comparaisons appariées\nLes séquences bloquées restent dans le bilan précédent ; aucun taux global de réduction déduit ici', fontsize=12)
    fig.savefig(output/'registered-paired.png', dpi=150)
    plt.close(fig)

    # First refused primary frame in manifest order: an observed failure, never hidden.
    refusal = next((s for s in result['sequences'] if s['condition_id'] in ('aligned', 'drift', 'rotation', 'combined')
                    and not s['after_available']), None)
    if refusal:
        k = next(i for i in refusal['blocked_frame_indices'] if i > 0)
        model = refusal['registration'][k]
        frame = next(s for s in manifest['sequences'] if s['sequence_id'] == refusal['sequence_id'])['frames'][k]
        image_path = local_path(mp.parent/frame['local_copy'], base)
        if digest(image_path) != frame['sha256']:
            raise ValueError('Image de contrôle modifiée.')
        watched[image_path] = frame['sha256']
        with fits.open(image_path, mode='readonly', memmap=False) as hdus:
            image = hdus[0].data.astype(float)
        fig, ax = plt.subplots(figsize=(7.4, 7.7), layout='constrained')
        ax.imshow(np.arcsinh(np.maximum(image-96, 0)/10), origin='lower', cmap='gray', vmin=0, vmax=4.5)
        control = [p for p in model['pairs'] if p['split'] == 'control']
        used = {(int(p['x'] >= 128), int(p['y'] >= 128)) for p in control}
        for x in range(2):
            for yq in range(2):
                if (x, yq) not in used:
                    ax.add_patch(patches.Rectangle((128*x, 128*yq), 128, 128, facecolor='#ef9e64', alpha=.22))
        ax.axvline(128, color='white', lw=.8)
        ax.axhline(128, color='white', lw=.8)
        for split, color, label in [('training', '#67c7f5', 'Étoiles utilisées pour ajuster'),
                                     ('control', '#ffb357', 'Étoiles réservées au contrôle')]:
            p = [p for p in model['pairs'] if p['split'] == split]
            ax.scatter([q['x'] for q in p], [q['y'] for q in p], s=60, facecolors='none', edgecolors=color, label=label)
        ax.legend(loc='lower right', fontsize=8)
        ax.set_xlabel('x (pixel natif)')
        ax.set_ylabel('y (pixel natif)')
        ax.set_title('IMAGE FICTIVE — un refus utile\n'+refusal['sequence_id']+f', image {k+1}/8\nContrôles dans {model["metrics"]["control"]["quadrants_occupied"]}/4 quadrants : recalage refusé', fontsize=11)
        fig.savefig(output/'registered-refusal.png', dpi=145)
        plt.close(fig)

    name = 'combined-s607'  # Comparison fixed by the published plan.
    sequence = next(s for s in manifest['sequences'] if s['sequence_id'] == name)
    measured = next(s for s in result['sequences'] if s['sequence_id'] == name)
    answers = next(s for s in truth['sequences'] if s['sequence_id'] == name)
    frame = sequence['frames'][0]
    image_path = local_path(mp.parent/frame['local_copy'], base)
    if digest(image_path) != frame['sha256']:
        raise ValueError('Image de référence modifiée.')
    watched[image_path] = frame['sha256']
    with fits.open(image_path, mode='readonly', memmap=False) as hdus:
        background = hdus[0].data.astype(float)
    fig, axes = plt.subplots(1, 2, figsize=(12, 7.2), layout='constrained')
    artists = []
    for ax in axes:
        ax.imshow(np.arcsinh(np.maximum(background-96, 0)/10), origin='lower', cmap='gray', vmin=0, vmax=4.5)
        detected, = ax.plot([], [], '.', color='#b0b8bf', ms=2, linestyle='none', label='Positions mesurées des sources')
        known, = ax.plot([], [], 'o', color='#6ae3ac', ms=15, mfc='none', linestyle='none', label='Mobile ajouté (réponse après recherche)')
        good, = ax.plot([], [], '+', color='#5bd0fa', ms=9, linestyle='none', label='Candidat apparié')
        false, = ax.plot([], [], 'x', color='#ffb455', ms=6, linestyle='none', label='Faux candidat')
        ax.legend(loc='lower right', fontsize=6.5)
        ax.set_xlabel('x dans le repère affiché (pixel)')
        ax.set_ylabel('y (pixel)')
        artists.append((detected, known, good, false))

    def update(k):
        for ax, branch, group in zip(axes, ['before', 'after'], artists):
            detected, known, good, false = group
            point = answers[branch][0]['positions'][k]
            known.set_data([point['x']], [point['y']])
            data = measured[branch]
            if data is None:
                ax.set_title('APRÈS : branche indisponible')
                for artist in [detected, good, false]: artist.set_data([], [])
                continue
            p = np.asarray(measured['raw_detections' if branch == 'before' else 'mapped_detections'][k]).reshape(-1, 2)
            detected.set_data(p[:, 0], p[:, 1])
            matched = {m['candidate_id'] for m in data['evaluation']['matches']}
            for artist, keep in [(good, True), (false, False)]:
                points = [p for track in data['tracks'] if (track['candidate_id'] in matched) == keep
                          for p in track['points'] if p['frame_index'] == k]
                artist.set_data([p['x'] for p in points], [p['y'] for p in points])
            label = 'AVANT : positions brutes' if branch == 'before' else 'APRÈS : positions recalées'
            ax.set_title(label+f'\n{data["evaluation"]["false_candidates"]} faux candidats sur cette séquence', fontsize=10)
        fig.suptitle(f'IMAGES FICTIVES — superposition de coordonnées, image {k+1}/8\nFond fixe : pixels de la première image, jamais rééchantillonnés\nExemple fixé à la graine 607 ; le bilan complet conserve les autres séquences refusées', fontsize=10)
        return [artist for group in artists for artist in group]

    update(7)
    fig.savefig(output/'registered-overlay.png', dpi=130)
    animation = FuncAnimation(fig, update, frames=8, interval=500, blit=False)
    animation.save(output/'registered-overlay.gif', writer=PillowWriter(fps=2))
    plt.close(fig)
    if any(digest(path) != value for path, value in watched.items()):
        raise ValueError('Une entrée a changé pendant le dessin.')
    print('Figures et GIF issus des mesures fictives, refus conservés.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('manifest', 'truth', 'report', 'output'):
        parser.add_argument(field, type=Path)
    args = parser.parse_args()
    plot(args.manifest, args.truth, args.report, args.output)
