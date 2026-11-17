# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Teaching figures from the measured frozen experiment; no invented screenshots."""
import argparse
import json
from pathlib import Path

from astropy.io import fits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import numpy as np

from gar.astrometry import local_path
from gar.workset import digest
from moving_limits import ROOT, validate_suite


def plot(suite_path, report_path, output, base=None):
    base = ROOT/'local' if base is None else base
    suite_path, report_path, output = [local_path(p, base) for p in (suite_path, report_path, output)]
    suite = json.loads(suite_path.read_text(encoding='utf-8'))
    result = json.loads(report_path.read_text(encoding='utf-8'))
    validate_suite(suite)
    if (result.get('synthetic_only') is not True or result.get('suite_complete') is not True
            or result.get('descriptive_only') is not True or result.get('suite_sha256') != digest(suite_path)):
        raise ValueError('Bilan complet et protocole fictif correspondant requis.')
    watched = {suite_path: digest(suite_path), report_path: digest(report_path)}
    raw = {}
    manifests, truths = {}, {}
    for batch in suite['batches']:
        group = batch['group']
        for role, dest in [('manifest', manifests), ('truth', truths)]:
            path = local_path(suite_path.parent/batch[role], base)
            if digest(path) != batch[f'{role}_sha256']:
                raise ValueError('Une entrée du protocole a changé.')
            watched[path] = digest(path)
            dest[group] = json.loads(path.read_text(encoding='utf-8'))
        path = local_path(report_path.parent/group/'moving.json', base)
        if digest(path) != result['native_report_sha256'][group]:
            raise ValueError('Le rapport de candidats a changé.')
        watched[path] = digest(path)
        raw[group] = json.loads(path.read_text(encoding='utf-8'))
    output.mkdir(parents=True, exist_ok=False)
    grid = [c for c in result['conditions'] if c['group'] == 'grid']
    counts = np.array([c['recovered'] for c in grid]).reshape(3, 4)
    false = np.array([c['false_candidates'] for c in grid]).reshape(3, 4)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), layout='constrained')
    for ax, data, title, color in zip(axes, [counts, false],
                                     ['Objets retrouvés sur 5 ajoutés', 'Faux candidats sur les 5 séquences'],
                                     ['Blues', 'Oranges']):
        ax.imshow(data, cmap=color, vmin=0, vmax=max(5, data.max()))
        ax.set_xticks(range(4), ['0,03', '0,15', '0,5', '1,2'])
        ax.set_yticks(range(3), ['12', '30', '120'])
        ax.set_xlabel('Vitesse ajoutée (pixel / seconde fictive)')
        ax.set_ylabel('Pic au-dessus du fond (ADU)')
        ax.set_title(title, fontsize=11)
        for y in range(3):
            for x in range(4):
                label = f'{data[y, x]}/5' if ax is axes[0] else str(data[y, x])
                ax.text(x, y, label, ha='center', va='center',
                        color='white' if data[y, x] >= max(5, data.max())*.6 else '#173b50', fontsize=13)
    fig.suptitle('IMAGES FICTIVES — détecteur inchangé\nCinq répétitions par case ; ce tableau ne donne pas une magnitude limite', fontsize=13)
    fig.savefig(output/'limits-grid.png', dpi=150)
    plt.close(fig)

    noise = [c for c in result['conditions'] if c['group'] == 'noise']
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(4)
    ax.bar(x-.17, [c['recovered'] for c in noise], width=.34, color='#237f9b', label='Objets retrouvés / 5')
    ax.bar(x+.17, [c['false_candidates'] for c in noise], width=.34, color='#d57a32', label='Faux candidats')
    for k, c in enumerate(noise):
        ax.text(k-.17, c['recovered']+.12, f'{c["recovered"]}/5', ha='center')
        ax.text(k+.17, c['false_candidates']+.12, str(c['false_candidates']), ha='center')
    ax.set_xticks(x, [str(int(c['noise_sigma_adu'])) for c in noise])
    ax.set_xlabel('Bruit ajouté : écart-type (ADU) — plus grand = image plus bruitée')
    ax.set_ylabel('Nombre d’objets ou candidats')
    ax.set_ylim(0, max(5, max(c['false_candidates'] for c in noise))+1.5)
    ax.set_title('IMAGES FICTIVES — faire grandir le bruit\nMême pic de 30 ADU, même vitesse de 0,5 pixel/s fictive')
    ax.legend()
    fig.tight_layout()
    fig.savefig(output/'limits-noise.png', dpi=150)
    plt.close(fig)

    geometry = [c for c in result['conditions'] if c['group'] == 'geometry']
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    labels = ['Alignées (référence)', 'Dérive 0,05 pixel/s', 'Dérive 0,15 pixel/s',
              'Rotation 0,5 degré', 'Rotation 2 degrés', 'Dérive + rotation']
    for ax, key, color, title in zip(axes, ['recovered', 'false_candidates'], ['#237f9b', '#d57a32'],
                                      ['Objets retrouvés / 5', 'Faux candidats (étoiles entraînées incluses)']):
        values = [c[key] for c in geometry]
        ax.barh(np.arange(6), values, color=color)
        for k, value in enumerate(values):
            ax.text(value+max(1, max(values))*.025, k, f'{value}/5' if key == 'recovered' else str(value), va='center')
        ax.set_xlim(0, max(5, max(values))*1.25)
        ax.set_yticks(np.arange(6), labels)
        ax.set_title(title, fontsize=10)
    axes[0].invert_yaxis()
    fig.suptitle('IMAGES FICTIVES — que se passe-t-il si le champ bouge ?\nLes cinq derniers cas sortent de l’hypothèse « images alignées » ; aucun recalage ici', fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .9))
    fig.savefig(output/'limits-geometry.png', dpi=150)
    plt.close(fig)

    # Fixed comparison chosen by the plan, not by success/failure on a favourable seed.
    selected = ['aligned-s101', 'drift-large-s101']
    panels = []
    for name in selected:
        sequence = next(s for s in manifests['geometry']['sequences'] if s['sequence_id'] == name)
        measured = next(s for s in raw['geometry']['sequences'] if s['sequence_id'] == name)
        truth = next(s for s in truths['geometry']['sequences'] if s['sequence_id'] == name)
        images = []
        for frame in sequence['frames']:
            path = local_path(suite_path.parent/'geometry'/frame['local_copy'], base)
            if digest(path) != frame['sha256']:
                raise ValueError('Image illustrée modifiée.')
            watched[path] = digest(path)
            with fits.open(path, mode='readonly', memmap=False) as hdus:
                if hdus[0].header.get('GARSYNTH') is not True:
                    raise ValueError('Marqueur synthétique requis.')
                images.append(hdus[0].data.astype(float))
        matched = {m['candidate_id'] for m in measured['evaluation']['matches']}
        panels.append((images, measured, truth, matched))
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.6), layout='constrained')
    artists = []
    for ax, (images, measured, _, _) in zip(axes, panels):
        display = ax.imshow(np.arcsinh(np.maximum(images[0]-96, 0)/10), origin='lower', cmap='gray', vmin=0, vmax=4.5)
        true, = ax.plot([], [], 'o', color='#6ae3ac', mfc='none', ms=15, label='Mobile ajouté (réponse connue)')
        good, = ax.plot([], [], '+', color='#5bd0fa', ms=8, linestyle='none', label='Candidat apparié au mobile')
        bad, = ax.plot([], [], 'x', color='#ffb455', ms=6, linestyle='none', label='Faux candidat de cet exercice')
        ax.legend(loc='lower right', fontsize=7)
        ax.set_xlabel('x (pixel)')
        ax.set_ylabel('y (pixel)')
        artists.append((display, true, good, bad))

    def update(k):
        for ax, (images, measured, truth, matched), (display, true, good, bad), label in zip(
                axes, panels, artists, ['Images alignées', 'Dérive du champ : 0,15 pixel/s fictive']):
            display.set_data(np.arcsinh(np.maximum(images[k]-96, 0)/10))
            point = truth['injections'][0]['positions'][k]
            true.set_data([point['x']], [point['y']])
            for artist, keep in [(good, True), (bad, False)]:
                points = [p for t in measured['tracks'] if (t['candidate_id'] in matched) == keep
                          for p in t['points'] if p['frame_index'] == k]
                artist.set_data([p['x'] for p in points], [p['y'] for p in points])
            ax.set_title(f'{label}\n{measured["evaluation"]["false_candidates"]} faux candidats sur la séquence', fontsize=11)
        fig.suptitle(f'IMAGES FICTIVES — image {k+1}/8, temps inventé {k*10} s\nLes réponses connues servent au bilan et au dessin, jamais à la détection', fontsize=12)
        return [a for group in artists for a in group]

    update(0)
    update(7)
    fig.savefig(output/'limits-comparison.png', dpi=130)
    animation = FuncAnimation(fig, update, frames=8, interval=500, blit=False)
    animation.save(output/'limits-comparison.gif', writer=PillowWriter(fps=2))
    plt.close(fig)
    if any(digest(path) != value for path, value in watched.items()):
        raise ValueError('Une entrée a changé pendant le tracé.')
    print('Quatre PNG et un GIF produits depuis les pixels et mesures fictifs.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    plot(args.suite, args.report, args.output)
