# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Figures, complete rankings and explicit post-search comparison with the study."""
from html import escape
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.wcs import WCS
from .pipeline import read, write, frames, DATA, height
from .orbit import Satrec, Time, u, SkyCoord, AltAz, altaz


def report(run):
    rows = frames(run)
    traces = read(run / 'measurements.json')['traces']
    orbital = read(run / 'orbital-results.json')
    # Answers enter only AFTER the full search has been saved.
    expected = read(DATA / 'expected-results.json')
    checks = []
    by_id = {r['frame_id']: r for r in orbital['results']}
    if any(not by_id[a['frame_id']]['ranked_hypotheses'] for a in expected['expected']):
        raise ValueError('Une trace n’a aucune hypothèse classée. Conserver le résultat négatif ; ne pas forcer une figure attendue.')
    for answer in expected['expected']:
        ranking = by_id[answer['frame_id']]['ranked_hypotheses']
        best = ranking[0] if ranking else None
        passed = bool(best and best['norad_id'] == answer['norad_id']
                and abs(best['median_cross_track_arcsec'] - answer['median_cross_track_arcsec']) <= expected['cross_track_tolerance_arcsec']
                and abs(best['orientation_difference_degrees'] - answer['orientation_difference_degrees']) <= expected['orientation_tolerance_degrees'])
        checks.append(dict(frame_id=answer['frame_id'], historical_result_reproduced=passed))
    if not all(c['historical_result_reproduced'] for c in checks):
        write(run / 'verification-refused.json', dict(checks=checks, identity_confirmed=False,
              reason='Historical results differ; keep complete search, do not label a replacement as plausible.'))
        raise ValueError('Le classement diffère de l’étude. Voir verification-refused.json ; aucune association de remplacement déclarée plausible.')
    figure_dir = run / 'figures'
    figure_dir.mkdir(exist_ok=True)
    for series in ['S03', 'S04']:
        fig, axes = plt.subplots(2, 4, figsize=(12, 10), layout='constrained')
        for ax, row in zip(axes.flat, [r for r in rows if r['series'] == series]):
            pixels = fits.getdata(run / 'fits' / row['file']).astype(float)
            lo, hi = np.percentile(pixels, [5, 99.5])
            ax.imshow(pixels, cmap='gray', vmin=lo, vmax=hi)
            ax.set_title(row['frame_id'] + '\n' + row['date_obs'][11:19], fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle('Images réelles autorisées — ' + series + ' — poses natives de 10 s')
        fig.savefig(figure_dir / (series + '-overview.png'), dpi=145)
        plt.close(fig)
    registration = read(run / 'registration.json')
    calibration = read(DATA / 'calibration.json')
    wcs = WCS(fits.Header.fromstring(calibration['reference_wcs_header'], sep='\n'), naxis=2)
    catalogue = read(run / 'references/catalogue.json')['rows']
    site = height(run)
    cards = []
    for trace in traces:
        key = trace['frame_id']
        row = next(r for r in rows if r['frame_id'] == key)
        strong = trace['visual_status'] != 'weak_doubtful'
        best = by_id[key]['ranked_hypotheses'][0] if by_id[key]['ranked_hypotheses'] else None
        pixels = fits.getdata(run / 'fits' / row['file']).astype(float)
        endpoints = np.array(trace['measurement']['native_endpoints'])
        y0 = max(0, int(endpoints[:, 1].min()) - 45)
        y1 = min(pixels.shape[0], int(endpoints[:, 1].max()) + 46)
        crop = pixels[y0:y1]
        lo, hi = np.percentile(crop, [5, 99.7])
        fig, axes = plt.subplots(2, 1, figsize=(11, 5), layout='constrained', sharex=True)
        label = best['name'] + ' — association plausible' if strong and best else 'Trace faible — non identifiée'
        for ax in axes:
            ax.imshow(crop, cmap='gray', vmin=lo, vmax=hi,
                      extent=[0, pixels.shape[1], y1, y0], aspect='auto')
            ax.set_ylim(y1, y0)
            ax.set_xlim(0, pixels.shape[1])
            ax.set_ylabel('y natif (pixels)')
        axes[0].set_title('Image réelle — ' + key + ' — pixels affichés sans ligne ajoutée')
        axes[1].plot(endpoints[:, 0], endpoints[:, 1], color='#e67300', lw=1.1,
                     label='Ligne ajustée aux pixels', linestyle='--')
        if strong and best:
            match = next(r for r in catalogue if r['satellite_id'] == best['norad_id']
                         and r['data_source'] == best['source']
                         and __import__('hashlib').sha256((r['tle_line1']+'\n'+r['tle_line2']).encode()).hexdigest() == best['tle_sha256'])
            satellite = Satrec.twoline2rv(match['tle_line1'], match['tle_line2'])
            times = Time(trace['date_obs'], scale='utc') + np.linspace(-10, 20, 301) * u.s
            aa, errors = altaz([satellite], times, site)
            sky = SkyCoord(az=aa.az[0], alt=aa.alt[0], frame=AltAz(obstime=times, location=site, pressure=0*u.hPa)).icrs
            x, y = wcs.world_to_pixel(sky)
            native = np.column_stack([x, y])
            chain = [registration['bridge']]
            if row['series'] == 'S04':
                chain.append(registration['cross'])
            chain.append(registration['models'][key])
            for model in chain:
                native = (native - model['translation_pixels']) @ np.array(model['rotation_matrix'])
            keep = (native[:, 0] >= 0) & (native[:, 0] <= pixels.shape[1]) & (errors[0] == 0)
            axes[1].plot(native[keep, 0], native[keep, 1], color='#00bfff', lw=1.2, label='Prévision orbitale')
        axes[1].set_title(label + ' ; identité non confirmée', fontsize=11)
        axes[1].set_xlabel('x natif (pixels)')
        axes[1].legend(fontsize=8)
        fig.savefig(figure_dir / (key + '-comparison.png'), dpi=145)
        plt.close(fig)
        cards.append(dict(frame_id=key, label=label, strong_visual_feature=strong,
                     identity_confirmed=False, figure='figures/' + key + '-comparison.png'))
    strongest = [by_id[a['frame_id']]['ranked_hypotheses'][0] for a in expected['expected']]
    labels = [a['frame_id'] for a in expected['expected']]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout='constrained')
    axes[0].bar(labels, [r['median_cross_track_arcsec'] for r in strongest], color='#245b78')
    axes[0].set_ylabel('Écart médian transversal (secondes d’arc)')
    axes[1].bar(labels, [r['orientation_difference_degrees'] for r in strongest], color='#6a477d')
    axes[1].set_ylabel('Différence d’orientation (degrés)')
    fig.suptitle('Mesures calculées — trois associations plausibles, sans probabilité d’identité')
    fig.savefig(figure_dir / 'residuals.png', dpi=145)
    plt.close(fig)
    intervals = [r['time_compatibility']['beginning_timestamp_offset_interval'] for r in strongest]
    common = [max(i[0] for i in intervals), min(i[1] for i in intervals)]
    fig, ax = plt.subplots(figsize=(10, 4), layout='constrained')
    for i, (label, interval) in enumerate(zip(labels, intervals)):
        ax.plot(interval, [i, i], 'o-', lw=4, label=label)
    ax.axvline(0, color='black', linestyle='--', label='Aucun décalage')
    if common[0] <= common[1]:
        ax.axvspan(*common, alpha=.15, color='green', label='Intersection conditionnelle')
    ax.set_yticks(range(3), labels)
    ax.set_xlabel('Début réel supposé moins DATE-OBS (secondes)')
    ax.set_title('Calcul conditionnel : UTC et début de pose supposés ; aucune horloge qualifiée')
    ax.legend(fontsize=8, loc='best')
    fig.savefig(figure_dir / 'timing.png', dpi=145)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 3.2), layout='constrained')
    ax.axis('off')
    blocks = ['16 FITS\nvérifiés', 'Étoiles\n+ étalonnage fourni', '4 lignes\nrevues à l’œil', 'Catalogue historique\n+ SGP4 local', '3 associations plausibles\n+ 1 trace douteuse']
    for i, label in enumerate(blocks):
        x = .08 + i * .21
        ax.text(x, .5, label, ha='center', va='center', fontsize=10,
                bbox=dict(boxstyle='round,pad=.7', facecolor='#e4eff4', edgecolor='#245b78'), transform=ax.transAxes)
        if i < 4:
            ax.annotate('', xy=(x+.135, .5), xytext=(x+.085, .5), xycoords='axes fraction',
                        arrowprops=dict(arrowstyle='->', color='black'))
    ax.set_title('Schéma explicatif — analyse ciblée, sans reprise de toute l’archive')
    fig.savefig(figure_dir / 'workflow.png', dpi=145, bbox_inches='tight')
    plt.close(fig)
    summary = dict(examined_frames=16, visually_selected_traces=4, historical_associations=3,
                   all_historical_results_reproduced=all(c['historical_result_reproduced'] for c in checks),
                   checks=checks, weak_unidentified_traces=1,
                   proposals=sum(r['count'] for r in read(run / 'proposals.json')['rows']),
                   common_start_offset_interval_seconds=common,
                   identity_confirmed=False, clock_qualified=False, large_archive_started=False,
                   all_source_hashes_unchanged=True, guided_reproduction_not_blind_test=True)
    write(run / 'summary.json', summary)
    html = ['<!doctype html><html lang="fr"><meta charset="utf-8"><title>Reproduction des séries 3 et 4</title>',
            '<style>body{font:18px Arial;max-width:1150px;margin:2em auto;padding:1em;color:#123;background:white}img{max-width:100%;height:auto}a{color:#075399}</style>',
            '<h1>Reproduction ciblée des séries 3 et 4</h1><p>Images réelles autorisées. Trois associations historiques plausibles, aucune identité confirmée. Une trace faible reste non identifiée.</p>',
            '<p>Les lignes colorées sont des calculs. Les FITS restent intacts. Étalonnage WCS fourni ; horloge non qualifiée. La fouille générale reste en pause.</p>']
    for card in cards:
        html += ['<h2>'+escape(card['frame_id']+' — '+card['label'])+'</h2>',
                 '<img src="'+card['figure']+'" alt="Même extrait réel sans annotation en haut, puis ligne mesurée et éventuelle prévision en bas.">',
                 '<p>Trait discontinu : mesure guidée. Trait continu : orbite calculée. La proximité est une hypothèse, pas une preuve définitive.</p>']
    html += ['<h2>Résultats et fichiers de travail</h2><p><a href="summary.json">Bilan JSON</a> · <a href="orbital-results.json">Tous les classements orbitaux</a> · <a href="proposals.json">Toutes les propositions de lignes</a></p>', '</html>']
    (run / 'index.html').write_text('\n'.join(html), encoding='utf-8')
    frames(run)
    return summary
