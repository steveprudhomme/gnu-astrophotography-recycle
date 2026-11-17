# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Render actual report values; optional Matplotlib, no science dependency."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def plot(report, output, synthetic=False):
    document = json.loads(Path(report).read_text(encoding='utf-8'))
    fig, axes = plt.subplots(len(document['frames']), 2, figsize=(12, 3.6*len(document['frames'])), squeeze=False)
    for row, frame in enumerate(document['frames']):
        left, right = axes[row]
        if 'metrics' not in frame:
            left.text(.05, .5, frame.get('error', 'Échec'), transform=left.transAxes)
            continue
        train = [p for p in frame['pairs'] if p['split'] == 'training']
        control = [p for p in frame['pairs'] if p['split'] == 'control']
        left.scatter([p['x'] for p in train], [p['y'] for p in train], s=9, c='#bac6cf', label='Ajustement')
        left.scatter([p['x'] for p in control], [p['y'] for p in control], s=24, c='#126682', label='Contrôle réservé')
        if control:
            x = np.array([p['x'] for p in control]); y = np.array([p['y'] for p in control])
            dx = np.array([p['dx_pixels'] for p in control]); dy = np.array([p['dy_pixels'] for p in control])
            left.quiver(x, y, dx*20, dy*20, angles='xy', scale_units='xy', scale=1, color='#c4491c', width=.004)
            right.scatter(dx, dy, s=24, c='#126682', alpha=.8)
        h, w = frame['image_shape']
        left.set(xlim=(0, w), ylim=(h, 0), xlabel='x natif (pixel)', ylabel='y natif (pixel)')
        left.set_aspect('equal', adjustable='box')
        for value in [w/3, 2*w/3]: left.axvline(value, c='#d9e0e5', lw=.7, zorder=0)
        for value in [h/3, 2*h/3]: left.axhline(value, c='#d9e0e5', lw=.7, zorder=0)
        left.set_title(f'Pose {frame["file_index"]} : rotation {frame["rotation_degrees"]:.4f}° ; vecteurs ×20')
        left.legend(loc='upper left', fontsize=8)
        right.axhline(0, color='#a9b5bf', lw=.7); right.axvline(0, color='#a9b5bf', lw=.7)
        right.add_patch(plt.Circle((0, 0), .75, fill=False, ls='--', color='#72808c', label='Rayon 0,75 px (repère)'))
        right.set(xlim=(-1.6, 1.6), ylim=(-1.6, 1.6), xlabel='Écart x après recalage (pixel)', ylabel='Écart y après recalage (pixel)')
        right.set_aspect('equal', adjustable='box')
        c = frame['metrics']['control']
        med = f'{c["median_pixels"]:.3f}' if c['median_pixels'] is not None else '?'
        p95 = f'{c["p95_pixels"]:.3f}' if c['p95_pixels'] is not None else '?'
        right.set_title(f'{c["matches"]} contrôles ; médiane {med} px ; P95 {p95} px')
        right.legend(loc='lower right', fontsize=8)
        outside = sum(abs(p['dx_pixels']) > 1.6 or abs(p['dy_pixels']) > 1.6 for p in control)
        right.text(.03, .97, f'Hors cadre : {outside} ; aucun retrait du rapport', transform=right.transAxes, va='top', fontsize=8)
    origin = 'DONNÉES SYNTHÉTIQUES — réponse Bayer fictive' if synthetic else 'DONNÉES RÉELLES PRIVÉES — ne pas publier'
    fig.suptitle(origin+'\nContrôle réservé à l’ajustement ; erreur absolue et horloge non qualifiées', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(output, dpi=160, metadata={'Description': origin})
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--synthetic', action='store_true', help='Seulement pour un rapport effectivement fictif.')
    args = parser.parse_args()
    plot(args.report, args.output, args.synthetic)
