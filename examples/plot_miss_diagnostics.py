# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Post-score stage matrix and deterministic representative cutouts."""
import argparse
from collections import Counter
from pathlib import Path
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import diagnose_injection_misses as diagnostic
import injection_recovery as experiment
from plot_seestar_pilot import align_for_display, render

ROOT = Path(__file__).resolve().parents[1]


def plot(diagnostic_path, output, base=None):
    base = ROOT/'local' if base is None else base
    dp, output = [local_path(p, base) for p in (diagnostic_path, output)]
    result = experiment.read(dp)
    if (result.get('miss_diagnostic_version') != '1.0' or result.get('status') != 'complete'
            or not result.get('input_hashes_unchanged') or result.get('search_rerun') is not False
            or result.get('thresholds_changed') is not False
            or result.get('diagnostic_recipe_sha256_lf') != diagnostic.recipe_hash()):
        raise ValueError('Diagnostic complet de cette version sans nouvelle recherche requis.')
    sp, score, mp, manifest, records, answers, watched = diagnostic.load_scored(result['score_path'], base)
    if digest(sp) != result['score_sha256'] or result['source_kind'] != manifest['source_kind']:
        raise ValueError('Score ou fond différents du diagnostic.')
    watched[dp] = digest(dp)
    if [r['case_id'] for r in result['cases']] != [c['case_id'] for c in experiment.conditions()]:
        raise ValueError('Diagnostic individuel incomplet.')
    missed = [r for r in result['cases'] if r['missed'] == 1]
    categories = dict(sorted(Counter(r['primary'] for r in missed).items()))
    representatives = {name: min(r['case_id'] for r in missed if r['primary'] == name) for name in categories}
    if categories != result['missed_categories'] or representatives != result['representatives'] or len(missed) != score['missed']:
        raise ValueError('Résumé ou exemples différents des diagnostics individuels.')
    output.mkdir(parents=True, exist_ok=False)
    title = 'ENTIÈREMENT FICTIF — DIAGNOSTIC APRÈS SCORE' if manifest['source_kind'] == 'synthetic_demo' else 'FOND RÉEL + AJOUTS ARTIFICIELS — PRIVÉ'
    fig, ax = plt.subplots(figsize=(10, max(3.8, 1.5+.8*len(categories))), layout='constrained')
    labels = [textwrap.fill(diagnostic.LABELS[k], 36) for k in categories]
    ax.barh(labels, list(categories.values()), color=['gray' if k.startswith('outside') else 'teal' for k in categories])
    ax.set(xlabel='Nombre de manques (catégories descriptives)', xlim=(0, max(categories.values(), default=1)+1))
    for i, count in enumerate(categories.values()):
        ax.text(count+.1, i, str(count), va='center')
    if not categories:
        ax.text(.5, .5, 'Aucun manque disponible à illustrer', transform=ax.transAxes, ha='center')
    fig.suptitle(title+f"\n{result['missed']} manques ; {result['recovered']} récupérations inchangées", fontsize=11)
    fig.supxlabel('Proximité mesurée dans des tableaux gelés · aucune cause physique démontrée · aucun seuil modifié', fontsize=9)
    render(fig).save(output/'overview.png')
    baseline = experiment.read(local_path(manifest['baseline_report'], base))
    noise = manifest['noise_sigma_first_reduced']; background = baseline['motion_selection'][0]['background']
    low, high = background-3*noise, background+15*noise
    def stretch(image):
        return np.arcsinh(np.maximum(image-low, 0)/max((high-low)/10, 1))
    cases = {c['case_id']: c for c in manifest['cases']}
    selected_watched = {}
    for category, case_id in representatives.items():
        row = next(r for r in result['cases'] if r['case_id'] == case_id)
        planes = experiment.load_planes(mp, manifest, cases[case_id], base, selected_watched)
        if planes is None or len(row['frames']) != 8:
            raise ValueError('Exemple de manque disponible à huit images requis.')
        xy = np.array([[f['truth_x'], f['truth_y']] for f in row['frames']])
        lo, hi = (xy.min(axis=0)-.5)/2-16, (xy.max(axis=0)-.5)/2+16
        fig = plt.figure(figsize=(12, 8), layout='constrained')
        grid = fig.add_gridspec(3, 4, height_ratios=[.7, 1, 1])
        ax = fig.add_subplot(grid[0, :])
        evidence = row['radii_evidence']['1.5']
        presence = np.array([[k in evidence[stage]['frame_indices'] for k in range(8)] for stage in ('raw', 'common', 'kept')], dtype=int)
        ax.imshow(presence, vmin=0, vmax=1, cmap='Blues', aspect='auto')
        ax.set(xticks=range(8), xticklabels=range(1, 9), yticks=range(3),
               yticklabels=[f"{label} ({evidence[key]['count']}/8)" for key, label in
                            [('raw', 'Détection proche'), ('common', 'Champ commun'), ('kept', 'Après filtre')]])
        for a in range(3):
            for b in range(8):
                ax.text(b, a, 'oui' if presence[a, b] else 'non', color='white' if presence[a, b] else 'black', ha='center', va='center', fontsize=9)
        ax.set_title('Proximité ≤1,5 pixel natif ; il faut au moins cinq images et 40 secondes déclarées', fontsize=10)
        for k in range(8):
            ax = fig.add_subplot(grid[1+k//4, k%4])
            ax.imshow(stretch(align_for_display(planes[k], manifest['models'][k])), origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10))
            ax.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]), title=f'Pose {k+1}'); ax.axis('off')
            frame = row['frames'][k]
            ax.plot((frame['truth_x']-.5)/2, (frame['truth_y']-.5)/2, 'o', mfc='none', mec='lime', ms=12)
            for key, marker, color in [('control', 'D', 'silver'), ('kept', '+', 'cyan')]:
                point = frame[key]
                if point is not None and point['distance_native_pixels'] <= 1.5:
                    ax.plot((point['x']-.5)/2, (point['y']-.5)/2, marker, color=color, mfc='none', ms=8)
            point = frame['common']
            if frame['closest_common_was_removed'] and point['distance_native_pixels'] <= 1.5:
                ax.plot((point['x']-.5)/2, (point['y']-.5)/2, 'x', color='orange', ms=8)
        fig.suptitle(title+f'\n{case_id} — {diagnostic.LABELS[category]}\nPremier identifiant de la catégorie ; contexte à 3 pixels conservé dans le rapport', fontsize=11)
        fig.supxlabel('Vert : ajout connu, pas une détection · cyan : conservé · orange : retiré · gris : source témoin proche\nInterpolation pour affichage uniquement ; aucune recherche relancée', fontsize=9)
        render(fig).save(output/f'example-{category}.png')
    experiment.unchanged(watched); diagnostic.frozen()
    experiment.save(output/'figures.json', dict(diagnostic_sha256=watched[dp], representatives=representatives,
        source_kind=manifest['source_kind'], search_rerun=False, thresholds_changed=False,
        input_hashes_unchanged=True, interpolation_display_only=True,
        figures_sha256={p.name: digest(p) for p in sorted(output.iterdir()) if p.suffix == '.png'}))
    print('Diagramme et vignettes du diagnostic produits ; positions gelées et seuils intacts.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('diagnostic', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); plot(args.diagnostic, args.output)
