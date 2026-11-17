# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Optional Matplotlib rendering of measured reserved-star Gaia residuals."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(report, output, synthetic=False):
    document = json.loads(Path(report).read_text(encoding='utf-8'))
    fig, axes = plt.subplots(len(document['frames']), 2, figsize=(12, 3.6*len(document['frames'])), squeeze=False)
    values = [abs(p[key]) for f in document['frames'] for p in f.get('control', {}).get('pairs', []) for key in ['east_arcsec', 'north_arcsec']]
    extent = max(2.5, 1.15*max(values, default=0))
    for row, frame in enumerate(document['frames']):
        left, right = axes[row]
        if 'control' not in frame:
            left.text(.05, .5, frame.get('error', 'Échec'), transform=left.transAxes)
            continue
        pairs = frame['control']['pairs']
        secondary = frame['all_diagnostic']['pairs']
        left.scatter([p['x'] for p in secondary], [p['y'] for p in secondary], s=10, c='#c7cfd6', label='Bilan toutes détections')
        colors = ['#126682' if p['separation_arcsec'] <= 2 else '#cc741d' if p['separation_arcsec'] <= 4 else '#ae3030' for p in pairs]
        left.scatter([p['x'] for p in pairs], [p['y'] for p in pairs], s=26, c=colors, label='Contrôle réservé')
        h, w = frame['image_shape']
        left.set(xlim=(0, w), ylim=(h, 0), xlabel='x natif (pixel)', ylabel='y natif (pixel)')
        left.set_aspect('equal', adjustable='box')
        for value in [w/3, 2*w/3]: left.axvline(value, c='#d9e0e5', lw=.7, zorder=0)
        for value in [h/3, 2*h/3]: left.axhline(value, c='#d9e0e5', lw=.7, zorder=0)
        c = frame['control']['metrics']
        left.set_title(f'Pose {frame["file_index"]} : {c["matches"]} contrôles Gaia ; {c["grid_cells_occupied"]}/9 cellules')
        left.legend(loc='upper left', fontsize=8)
        right.scatter([p['east_arcsec'] for p in pairs], [p['north_arcsec'] for p in pairs], s=26, c=colors, alpha=.85)
        right.axhline(0, color='#a9b5bf', lw=.7); right.axvline(0, color='#a9b5bf', lw=.7)
        for radius in [2, 4]:
            if extent > radius:
                right.add_patch(plt.Circle((0, 0), radius, fill=False, ls='--', color='#a9b5bf'))
        right.set(xlim=(-extent, extent), ylim=(-extent, extent), xlabel='Écart vers l’Est (seconde d’arc)', ylabel='Écart vers le Nord (seconde d’arc)')
        right.set_aspect('equal', adjustable='box')
        median = f'{c["median_arcsec"]:.3f}' if c['median_arcsec'] is not None else '?'
        p95 = f'{c["p95_arcsec"]:.3f}' if c['p95_arcsec'] is not None else '?'
        right.set_title(f'Médiane {median}″ ; P95 {p95}″ — modèle gelé')
        right.text(.03, .97, 'Tous les associés ; biais conservé', transform=right.transAxes, va='top', fontsize=8)
    origin = 'DONNÉES SYNTHÉTIQUES — catalogue fictif' if synthetic else 'DONNÉES RÉELLES PRIVÉES — ne pas publier'
    bias = document.get('catalog_provenance', {}).get('injected_east_bias_arcsec')
    if synthetic and bias is not None:
        origin += ', biais injecté de '+str(bias).replace('.', ',')+'″'
    fig.suptitle(origin+'\nÉtoiles réservées avant recalage ; sélection à 8″ ; horloge et budget absolu non qualifiés', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(output, dpi=160, metadata={'Description': origin})
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--synthetic', action='store_true')
    args = parser.parse_args()
    plot(args.report, args.output, args.synthetic)
