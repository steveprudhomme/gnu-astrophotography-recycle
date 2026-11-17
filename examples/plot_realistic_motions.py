# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Draw frozen representative-motion scores without running any image search."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import injection_recovery as previous
import realistic_motions as experiment
from plot_seestar_pilot import align_for_display, render

ROOT = Path(__file__).resolve().parents[1]


def load_score(score_path, base):
    sp = local_path(score_path, base); score = experiment.read(sp)
    if (score.get('realistic_motion_score_version') != '1.0' or score.get('status') != 'complete'
            or score.get('inputs_unchanged') is not True or score.get('science_fitness_passed') is not False
            or score.get('descriptive_only') is not True or score.get('clock_qualified') is not False):
        raise ValueError('Score représentatif complet, descriptif et entrées intactes requis.')
    mp, manifest, watched = experiment.load_manifest(score['manifest_path'], base)
    ap, tp = [local_path(score[key], base) for key in ('analysis_path', 'truth_path')]
    for path, key in ((mp, 'manifest_sha256'), (ap, 'analysis_sha256'), (tp, 'truth_sha256')):
        if digest(path) != score[key]:
            raise ValueError('Une entrée liée au score a changé.')
    records = experiment.sealed_records(ap, watched[mp], base, watched, manifest['conditions'])
    experiment.verify_derivatives(mp, manifest, base, watched)
    watched[tp] = digest(tp); watched[sp] = digest(sp)
    truth = experiment.read(tp)
    if (truth.get('realistic_motion_truth_version') != '1.0' or truth.get('manifest_sha256') != watched[mp]
            or [r['case_id'] for r in truth.get('cases', [])] != [r['case_id'] for r in manifest['conditions']]):
        raise ValueError('Réponses complètes liées au même manifeste requises.')
    answers = {r['case_id']: r for r in truth['cases']}
    for spec, case in zip(manifest['conditions'], manifest['cases'][1:]):
        answer = answers[spec['case_id']]
        positions, velocity = experiment.trajectory(manifest['image_shape'], manifest['relative_declared_seconds'], spec)
        if (answer.get('available') != case['available'] or [p['frame_index'] for p in answer['positions']] != list(range(8))
                or not np.allclose([[p['x'], p['y']] for p in answer['positions']], positions, atol=1e-10, rtol=0)
                or not np.allclose(answer['velocity_native_per_declared_second'], velocity, atol=1e-10, rtol=0)):
            raise ValueError('Réponses différentes des trajets fixés.')
    rows = [dict(spec, **previous.score_one(records[spec['case_id']], answers.get(spec['case_id'])))
            for spec in [dict(case_id='control'), *manifest['conditions']]]
    if score.get('rows') != rows or score.get('source_kind') != manifest['source_kind']:
        raise ValueError('Score différent des candidats gelés et des réponses.')
    groups = []
    for rate, peak in [(r, a) for r in (10, 30, 60, 900) for a in (6, 12)]+[(None, 12)]:
        selected = [r for r in rows[1:] if r['angular_rate_arcsec_hour'] == rate and r['peak_sigma'] == peak]
        groups.append(dict(family='angular' if rate is not None else 'technical_positive', angular_rate_arcsec_hour=rate,
            peak_sigma=peak, planned=2, available=sum(r['available'] for r in selected), recovered=sum(r['recovered'] or 0 for r in selected),
            missed=sum(r['missed'] or 0 for r in selected), unavailable=sum(not r['available'] for r in selected),
            unassociated_candidates=sum(r['unassociated_candidates'] or 0 for r in selected) if any(r['available'] for r in selected) else None))
    if score.get('groups') != groups:
        raise ValueError('Groupes du bilan différents des résultats individuels gelés.')
    expected = dict(planned_injections=18, recovered=sum(r['recovered'] or 0 for r in rows[1:]),
        missed=sum(r['missed'] or 0 for r in rows[1:]), unavailable=sum(not r['available'] for r in rows[1:]),
        available_injections=sum(r['available'] for r in rows[1:]),
        scale_arcsec_per_native_pixel=manifest['scale_arcsec_per_native_pixel'])
    technical = [r for r in rows[1:] if r['family'] == 'technical_positive']
    slow = [r for r in rows[1:] if r['family'] == 'angular' and r['angular_rate_arcsec_hour'] in (10, 30, 60)]
    expected.update(technical_recovered=sum(r['recovered'] or 0 for r in technical),
        technical_available=sum(r['available'] for r in technical),
        slow_recovered=sum(r['recovered'] or 0 for r in slow), slow_available=sum(r['available'] for r in slow),
        slow_domain_covered=all(r['in_speed_domain'] for r in slow), control_candidates=records['control']['candidate_count'],
        engine_angular_domain_arcsec_hour=[v*manifest['scale_arcsec_per_native_pixel']*3600 for v in (.1, 1.5)])
    baseline = experiment.read(local_path(manifest['baseline_report'], base)); control = records['control']
    identical = control['search_status'] == 'complete' and all(control['data'][key] == baseline[key]
        for key in ('raw_detections', 'mapped_detections', 'overlap_excluded_per_frame', 'search'))
    synthetic = manifest['source_kind'] == 'synthetic_demo'
    fixture = bool(identical and control['candidate_count'] == 0
        and all(r['available'] and r['recovered'] == 1 for r in technical)
        and all(r['available'] and r['recovered'] == 0 for r in slow)) if synthetic else None
    expected.update(control_identical_to_baseline=identical, synthetic_fixture_criteria_passed=fixture,
        unassociated_candidates=sum(r['unassociated_candidates'] or 0 for r in rows[1:]) if any(r['available'] for r in rows[1:]) else None,
        false_candidates=sum(r['unassociated_candidates'] or 0 for r in rows[1:])+(control['candidate_count'] or 0)
            if synthetic and all(r['available'] for r in rows) else None,
        known_natural_positive_tested=False, real_data_performance_validated=False,
        conditional_on_frozen_registration=True)
    if any(score.get(key) != value for key, value in expected.items()):
        raise ValueError('Bilan différent des résultats individuels gelés.')
    return sp, score, mp, manifest, records, answers, watched


def plot(score_path, output, base=None):
    base = ROOT/'local' if base is None else base
    output = local_path(output, base)
    sp, score, mp, manifest, records, answers, watched = load_score(score_path, base)
    output.mkdir(parents=True, exist_ok=False)
    synthetic = manifest['source_kind'] == 'synthetic_demo'
    title = 'ENTIÈREMENT FICTIF' if synthetic else 'FOND RÉEL + AJOUTS ARTIFICIELS — PRIVÉ'
    specs = manifest['conditions']; rows = {r['case_id']: r for r in score['rows']}
    scale = manifest['scale_arcsec_per_native_pixel']
    rates = (10, 30, 60, 900); peaks = (6, 12)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.8), layout='constrained', gridspec_kw=dict(height_ratios=(1.1, 1.4)))
    ax = axes[0]; ax.axis('off')
    speed_rows = [[str(rate), f'{rate/(3600*scale):.5f}', 'Dans la plage' if .1 <= rate/(3600*scale) <= 1.5 else 'Hors plage'] for rate in rates]
    table = ax.table(cellText=speed_rows, colLabels=['Secondes d’arc / heure', 'Pixels natifs / seconde déclarée', 'Domaine du moteur inchangé'],
                     cellLoc='center', loc='center', bbox=[0, .08, 1, .82])
    table.auto_set_font_size(False); table.set_fontsize(11)
    for i in range(1, 5):
        for j in range(3): table[i, j].set_facecolor('#fff0cd' if i < 4 else '#deeeff')
    ax.set_title(f'Échelle nominale : {scale:.4f}″ / pixel · borne basse : {score["engine_angular_domain_arcsec_hour"][0]:.1f}″ / h', fontsize=12)
    grid = np.full((2, 4), np.nan); labels = {}
    for i, peak in enumerate(peaks):
        for j, rate in enumerate(rates):
            selected = [rows[s['case_id']] for s in specs if s['family'] == 'angular' and s['peak_sigma'] == peak and s['angular_rate_arcsec_hour'] == rate]
            count = sum(r['recovered'] or 0 for r in selected); unavailable = sum(not r['available'] for r in selected)
            grid[i, j] = count/2 if unavailable < 2 else np.nan
            labels[i, j] = f'{count}/2' + (f'\n{unavailable} indisponible(s)' if unavailable else '')
    cmap = plt.get_cmap('Blues').copy(); cmap.set_bad('#dddddd')
    ax = axes[1]; ax.imshow(grid, origin='lower', vmin=0, vmax=1, cmap=cmap, aspect='auto')
    for (i, j), label in labels.items(): ax.text(j, i, label, ha='center', va='center', fontsize=13, color='white' if grid[i, j] > .6 else 'black')
    ax.set(xticks=range(4), xticklabels=rates, yticks=range(2), yticklabels=['6 × sigma initial', '12 × sigma initial'],
        xlabel='Scénarios angulaires (secondes d’arc par heure déclarée)', ylabel='Pic du modèle ajouté')
    ax.set_title('Ajouts retrouvés parmi deux trajets fixés · indisponibles conservés', fontsize=12)
    fig.suptitle(title+' — couverture et récupération\nLes exemples lents ne sont pas dans le domaine du moteur', fontsize=13)
    fig.supxlabel(f'Contrôles techniques sans traînée : {score["technical_recovered"]}/2 prévus retrouvés, {score["technical_available"]}/2 testables · témoin : {score["control_candidates"]} candidat(s)\n'
        'Un contrôle technique réussi ne valide pas les mouvements lents · temps/échelle déclarés, pas une magnitude ou probabilité universelle', fontsize=10)
    render(fig).save(output/'coverage-recovery.png')

    selected_ids = ['control', 'r30-a12-p1', 'r900-a12-p1', 'technical-p1']
    cases = {c['case_id']: c for c in manifest['cases']}; chosen_watched = {}
    planes = {cid: previous.load_planes(mp, manifest, cases[cid], base, chosen_watched) for cid in selected_ids}
    baseline = experiment.read(local_path(manifest['baseline_report'], base))
    background = baseline['motion_selection'][0]['background']; noise = manifest['noise_sigma_first_reduced']
    low, high = background-3*noise, background+15*noise
    positions = np.concatenate([np.array([[p['x'], p['y']] for p in answers[cid]['positions']]) for cid in selected_ids[1:]])
    lo, hi = (positions.min(axis=0)-.5)/2-14, (positions.max(axis=0)-.5)/2+14
    frames = []
    panel_labels = ['Témoin sans ajout', '30″ / h · traînée modélisée', '900″ / h · traînée modélisée', 'Contrôle technique · 0,5 pixel/s\nsans traînée']
    for k in range(8):
        fig, axes = plt.subplots(1, 4, figsize=(14, 4.8), layout='constrained')
        for ax, cid, label in zip(axes, selected_ids, panel_labels):
            ax.axis('off'); ax.set_title(label, fontsize=10)
            if planes[cid] is None:
                ax.text(.5, .5, 'INDISPONIBLE', transform=ax.transAxes, ha='center'); continue
            shown = align_for_display(planes[cid][k], manifest['models'][k])
            display = np.arcsinh(np.maximum(shown-low, 0)/max((high-low)/10, 1))
            ax.imshow(display, origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10))
            ax.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]))
            if cid != 'control':
                p = answers[cid]['positions'][k]
                ax.plot((p['x']-.5)/2, (p['y']-.5)/2, 'o', mfc='none', mec='lime', ms=14, mew=1.4)
                row = rows[cid]
                if row['match'] is not None:
                    track = next(t for t in records[cid]['data']['search']['tracks'] if t['candidate_id'] == row['match']['candidate_id'])
                    for measured in track['points']:
                        if measured['frame_index'] == k:
                            ax.plot((measured['x']-.5)/2, (measured['y']-.5)/2, '+', color='cyan', ms=11, mew=1.5)
        fig.suptitle(title+f' — pose {k+1}/8\nExemples préchoisis, pic 12 × sigma initial · réponses révélées après score', fontsize=12)
        fig.supxlabel('Vert : position ajoutée connue, pas une détection · cyan : candidat associé\nInterpolation uniquement pour l’affichage · contraste commun au témoin · cadence de lecture artificielle 0,6 s / pose', fontsize=10)
        frames.append(render(fig))
    frames[0].save(output/'comparison-first.png')
    frames[0].save(output/'comparison.gif', save_all=True, append_images=frames[1:], duration=600, loop=0, optimize=False)
    experiment.unchanged(watched); experiment.unchanged(chosen_watched)
    journal = dict(realistic_motion_figures_version='1.0', source_kind=manifest['source_kind'],
        synthetic_background=synthetic, score_sha256=watched[sp], example_cases_fixed=selected_ids,
        input_hashes_unchanged=True, detector_called=False, association_called=False,
        display_limits_from_first_control=[float(low), float(high)], interpolation_display_only=True,
        playback_milliseconds_per_frame=600,
        figures_sha256={p.name: digest(p) for p in sorted(output.iterdir()) if p.suffix in ('.png', '.gif')})
    experiment.save(output/'figures.json', journal)
    print('Carte et animation des mouvements représentatifs dessinées depuis les résultats gelés.', flush=True)
    return journal


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('score', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        plot(args.score, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
