# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Draw checked slow-profile results; no detection or association is run."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from gar.astrometry import local_path
from gar.workset import digest
import injection_recovery as previous
import slow_motion_profile as experiment
from plot_seestar_pilot import align_for_display, render

ROOT = Path(__file__).resolve().parents[1]
SELECTED = ('control', 'r10-a12-p1', 'r30-a12-p1', 'r60-a12-p1')


def plot(score_path, output, base=None):
    """Keep numerical counts and all eight views readable without animation."""
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    sp, score, mp, manifest, records, answers, watched = experiment.checked_score(score_path, base)
    output.mkdir(parents=True, exist_ok=False)
    synthetic = manifest['source_kind'] == 'synthetic_demo'
    label = 'ENTIÈREMENT FICTIF' if synthetic else 'FOND RÉEL + AJOUTS ARTIFICIELS — PRIVÉ'
    rows = {row['case_id']: row for row in score['rows']}
    groups = {(g['angular_rate_arcsec_hour'], g['peak_sigma']): g for g in score['groups']}

    fig, ax = plt.subplots(figsize=(10.5, 5.6), layout='constrained')
    ax.axis('off')
    cells = []
    for peak in (6, 12):
        cells.append([f'{peak} × bruit initial', *[
            (f"{groups[rate, peak]['recovered']}/2 retrouvés" if groups[rate, peak]['available'] else 'NON MESURÉ')
            +f"\n{groups[rate, peak]['unavailable']} indisponible(s)"
            for rate in (10, 30, 60)]])
    table = ax.table(cellText=cells,
        colLabels=['Pic du point ajouté', '10 secondes d’arc/h', '30 secondes d’arc/h', '60 secondes d’arc/h'],
        cellLoc='center', bbox=[0, .34, 1, .40])
    table.auto_set_font_size(False); table.set_fontsize(11)
    for (i, j), cell in table.get_celld().items():
        cell.set_edgecolor('#152b40')
        cell.set_facecolor('#e8f2fa' if i == 0 or j == 0 else '#ffffff')
        cell.set_text_props(color='#152b40')
    control = 'indisponible' if score['control_candidates'] is None else str(score['control_candidates'])
    extra = 'indisponibles' if score['unassociated_candidates'] is None else str(score['unassociated_candidates'])
    criterion = score['synthetic_fixture_criteria_passed']
    verdict = 'satisfait' if criterion is True else 'NON satisfait' if criterion is False else 'sans objet sur fond réel'
    bright = f"{score['bright_recovered']}/6 retrouvés" if score['bright_available'] else 'non mesurés'
    ax.text(.02, .22, f"Cas brillants : {bright} ; {score['bright_available']}/6 testables.\n"
        f'Témoin sans ajout : {control} candidat(s). Non associés dans les ajouts : {extra}.\n'
        f'Critère du banc fictif : {verdict}.', transform=ax.transAxes, fontsize=12, color='#152b40', va='top')
    ax.set_title(label+' — bilan du profil lent\nChaque case conserve les deux trajets fixés avant les essais.', fontsize=13, color='#152b40')
    fig.supxlabel('Nominal : 5–120 secondes d’arc/h ; déplacement minimal et autres contrôles aussi requis.\n'
        'Heures et échelle non qualifiées. Une récupération artificielle n’est pas une découverte.', fontsize=10)
    render(fig).save(output/'recovery.png')

    by_id = {case['case_id']: case for case in manifest['cases']}
    pixel_watched = {}
    planes = {cid: previous.load_planes(mp, manifest, by_id[cid], base, pixel_watched) for cid in SELECTED}
    baseline = experiment.read(local_path(manifest['baseline_report'], base))
    low = baseline['selections'][0]['background']-3*manifest['noise_sigma_first_reduced']
    high = baseline['selections'][0]['background']+15*manifest['noise_sigma_first_reduced']
    known = np.concatenate([np.array([[p['x'], p['y']] for p in answers[cid]['positions']]) for cid in SELECTED[1:]])
    lo, hi = (known.min(axis=0)-.5)/2-18, (known.max(axis=0)-.5)/2+18

    def draw_panel(ax, cid, k):
        ax.axis('off')
        if planes[cid] is None:
            ax.text(.5, .5, 'INDISPONIBLE', transform=ax.transAxes, ha='center', color='#152b40')
            return
        shown = align_for_display(planes[cid][k], manifest['models'][k])
        contrast = np.arcsinh(np.maximum(shown-low, 0)/max((high-low)/10, 1))
        ax.imshow(contrast, origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10))
        ax.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]))
        if cid == 'control':
            return
        pos = answers[cid]['positions'][k]
        ax.plot((pos['x']-.5)/2, (pos['y']-.5)/2, 'o', mfc='none', mec='#ffce45', ms=15, mew=1.8)
        if rows[cid]['match'] is not None:
            track = next(t for t in records[cid]['data']['search']['tracks']
                if t['candidate_id'] == rows[cid]['match']['candidate_id'])
            for measured in track['points']:
                if measured['frame_index'] == k:
                    ax.plot((measured['x']-.5)/2, (measured['y']-.5)/2, '+', color='#59eaff', ms=12, mew=1.8)

    legend = 'Cercle : position ajoutée connue après recherche. Croix + : mesure du candidat associé.\n'
    legend += 'Contraste commun au témoin ; interpolation réservée au dessin. Aucun nouveau candidat calculé.'
    frames = []
    times = manifest['relative_declared_seconds']
    for k in range(8):
        fig, axes = plt.subplots(1, 4, figsize=(14, 4.8), layout='constrained')
        for ax, cid, title in zip(axes, SELECTED, ('Témoin sans ajout', '10 secondes d’arc/h', '30 secondes d’arc/h', '60 secondes d’arc/h')):
            draw_panel(ax, cid, k); ax.set_title(title, fontsize=11)
        fig.suptitle(f'{label} — photo {k+1}/8, temps relatif déclaré {times[k]:.1f} s\n'
            'Trois exemples fixés : pic 12 × bruit initial, premier trajet.', fontsize=12)
        fig.supxlabel(legend+'\nLecture artificielle : 0,6 seconde par vue ; durée des données différente.', fontsize=10)
        frames.append(render(fig))
    frames[0].save(output/'comparison-first.png')
    frames[0].save(output/'comparison.gif', save_all=True, append_images=frames[1:], duration=600, loop=0, optimize=False)

    fig, axes = plt.subplots(2, 4, figsize=(14, 8), layout='constrained')
    for k, ax in enumerate(axes.flat):
        draw_panel(ax, 'r30-a12-p1', k)
        ax.set_title(f'Photo {k+1} · {times[k]:.1f} s', fontsize=11)
    fig.suptitle(label+' — les huit photos, sans animation\nExemple fixé : 30 secondes d’arc/h, pic 12 × bruit initial, premier trajet.', fontsize=12)
    fig.supxlabel(legend, fontsize=10)
    render(fig).save(output/'comparison-static.png')

    experiment.unchanged(watched); experiment.unchanged(pixel_watched)
    journal = dict(slow_motion_figures_version='1.0', source_kind=manifest['source_kind'],
        synthetic_background=synthetic, score_sha256=watched[sp], example_cases_fixed=list(SELECTED),
        input_hashes_unchanged=True, detector_called=False, association_called=False,
        display_limits_from_first_control=[float(low), float(high)], interpolation_display_only=True,
        playback_milliseconds_per_frame=600, static_eight_frame_case='r30-a12-p1',
        figures_sha256={p.name: digest(p) for p in sorted(output.iterdir()) if p.suffix in ('.png', '.gif')})
    experiment.save(output/'figures.json', journal)
    print('Bilan, vues fixes et animation du profil lent dessinés depuis les résultats conservés.', flush=True)
    return journal


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        plot(args.score, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
