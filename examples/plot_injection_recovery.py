# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Recovery grid and prechosen cutout animation; truth used only after scoring."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import injection_recovery as experiment
from plot_seestar_pilot import align_for_display, render

ROOT = Path(__file__).resolve().parents[1]


def plot(score_path, output, base=None):
    base = ROOT/'local' if base is None else base
    sp, output = [local_path(p, base) for p in (score_path, output)]
    score = experiment.read(sp)
    if score.get('injection_score_version') != '1.0' or score.get('status') != 'complete' or not score.get('inputs_unchanged'):
        raise ValueError('Score complet sur des entrées intactes requis.')
    mp, manifest, watched = experiment.load_manifest(score['manifest_path'], base)
    watched[sp] = digest(sp)
    ap, tp = [local_path(score[k], base) for k in ('analysis_path', 'truth_path')]
    if any(digest(p) != score[k] for p, k in [(mp, 'manifest_sha256'), (ap, 'analysis_sha256'), (tp, 'truth_sha256')]):
        raise ValueError('Une entrée de score a changé.')
    records = experiment.sealed_records(ap, watched[mp], base, watched)
    watched[tp] = digest(tp); truth = experiment.read(tp)
    answers = {c['case_id']: c for c in truth['cases']}
    synthetic = manifest['source_kind'] == 'synthetic_demo'
    title = 'ENTIÈREMENT FICTIF — AJOUTS ARTIFICIELS' if synthetic else 'FOND RÉEL + AJOUTS ARTIFICIELS — PRIVÉ'
    output.mkdir(parents=True, exist_ok=False)
    fig, ax = plt.subplots(figsize=(9, 4.8), layout='constrained')
    grid = np.array([[next(g for g in score['groups'] if g['peak_sigma'] == a and g['speed_native_per_declared_second'] == v)['recovered']/3
                      for v in experiment.SPEEDS] for a in experiment.PEAKS])
    ax.imshow(grid, origin='lower', vmin=0, vmax=1, cmap='Blues', aspect='auto')
    for i, a in enumerate(experiment.PEAKS):
        for j, v in enumerate(experiment.SPEEDS):
            g = next(g for g in score['groups'] if g['peak_sigma'] == a and g['speed_native_per_declared_second'] == v)
            label = f"{g['recovered']}/3"
            if g['unavailable']:
                label += f"\n{g['unavailable']} bloqué(s)"
            ax.text(j, i, label, ha='center', va='center', color='white' if grid[i, j] > .6 else 'black', fontsize=13)
    ax.set(xticks=range(4), xticklabels=experiment.SPEEDS, yticks=range(3), yticklabels=[f'{a} × sigma initial' for a in experiment.PEAKS],
           xlabel='Vitesse native, pixels par seconde déclarée', ylabel='Pic artificiel dans le plan réduit')
    fig.suptitle(title+'\nRetrouvées parmi trois positions prévues — recalage gelé', fontsize=11)
    fig.supxlabel('Trois trajets fixés, pas une probabilité universelle · bruit/photon/couleur non étalonnés', fontsize=9)
    render(fig).save(output/'recovery-grid.png')

    selected = ['control', 'a3-v0p5-p1', 'a12-v0p5-p1']
    cases = {c['case_id']: c for c in manifest['cases']}
    control = experiment.load_planes(mp, manifest, cases['control'], base, watched)
    masks = [np.isnan(p) for p in control]
    planes = {'control': control}
    for name in selected[1:]:
        planes[name] = experiment.load_planes(mp, manifest, cases[name], base, watched, masks)
    baseline = experiment.read(local_path(manifest['baseline_report'], base))
    background = baseline['motion_selection'][0]['background']
    noise = manifest['noise_sigma_first_reduced']
    low, high = background-3*noise, background+15*noise
    def stretch(a):
        return np.arcsinh(np.maximum(a-low, 0)/max((high-low)/10, 1))
    position = np.array([[p['x'], p['y']] for p in answers[selected[1]]['positions']])
    lo, hi = (position.min(axis=0)-.5)/2-16, (position.max(axis=0)-.5)/2+16
    frames = []
    for k in range(8):
        fig, axes = plt.subplots(1, 3, figsize=(12, 4.8), layout='constrained')
        for ax, name, label in zip(axes, selected, ['Témoin sans ajout', 'Ajout faible : 3 × sigma', 'Ajout plus brillant : 12 × sigma']):
            ax.axis('off'); ax.set_title(label, fontsize=10)
            if planes[name] is None:
                ax.text(.5, .5, 'CAS INDISPONIBLE', transform=ax.transAxes, ha='center')
                continue
            shown = align_for_display(planes[name][k], manifest['models'][k])
            ax.imshow(stretch(shown), origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10))
            ax.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]))
            if name != 'control':
                p = answers[name]['positions'][k]
                ax.plot((p['x']-.5)/2, (p['y']-.5)/2, 'o', mfc='none', mec='lime', ms=14)
                row = next(r for r in score['rows'] if r['case_id'] == name)
                if row['match']:
                    track = next(t for t in records[name]['data']['search']['tracks'] if t['candidate_id'] == row['match']['candidate_id'])
                    for measured in track['points']:
                        if measured['frame_index'] == k:
                            ax.plot((measured['x']-.5)/2, (measured['y']-.5)/2, '+', color='cyan', ms=10)
        fig.suptitle(title+f' — pose {k+1}/8\nVitesse fixée 0,5 ; cercles de réponse ajoutés APRÈS recherche et score', fontsize=11)
        fig.supxlabel('Vert : ajout connu · cyan : candidat associé · interpolation pour affichage · lecture artificielle 0,6 s/pose', fontsize=9)
        frames.append(render(fig))
    frames[0].save(output/'injection-comparison.gif', save_all=True, append_images=frames[1:], duration=600, loop=0, optimize=False)
    frames[0].save(output/'injection-comparison-first.png')
    experiment.unchanged(watched)
    experiment.save(output/'figures.json', dict(synthetic_background=synthetic, mixed_real_artificial=not synthetic,
        score_sha256=watched[sp], example_cases_fixed=selected, truth_used_after_score_only=True,
        display_limits_from_first_control=[float(low), float(high)],
        interpolation_display_only=True, input_hashes_unchanged=True,
        figures_sha256={p.name: digest(p) for p in sorted(output.iterdir()) if p.suffix in ('.png', '.gif')}))
    print('Carte et animation des exemples préchoisis produites ; ajouts artificiels explicitement signalés.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('score', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); plot(args.score, args.output)
