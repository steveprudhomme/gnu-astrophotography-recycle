# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Draw only completed synthetic detector traces; never calls a detector."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
from plot_seestar_pilot import render
from trace_detector_decisions import evidence_at

ROOT = Path(__file__).resolve().parents[1]
LABELS = dict(bright='Point brillant', faint='Point faible', hot_pixel='Défaut ponctuel',
              elongated='Source étirée', border='Près du bord', masked='Pixels masqués')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def plot(trace_path, output, base=None):
    base = ROOT/'local' if base is None else base
    rp, output = [local_path(p, base) for p in (trace_path, output)]
    result = read(rp)
    if (result.get('detector_trace_version') != '1.0' or result.get('status') != 'complete'
            or result.get('source_kind') != 'synthetic_demo'
            or result.get('input_hashes_unchanged') is not True
            or result.get('thresholds_changed') is not False or result.get('association_rerun') is not False
            or result.get('trace_recipe_sha256_lf') != sha256((ROOT/'examples/trace_detector_decisions.py').read_text(encoding='utf-8').encode()).hexdigest()):
        raise ValueError('Trace fictive complète et entrées intactes requises pour ces figures publiques.')
    mp = local_path(result['manifest_path'], base)
    if digest(mp) != result['manifest_sha256']:
        raise ValueError('Manifeste modifié depuis la trace.')
    manifest = read(mp)
    if (manifest.get('detector_demo_version') != '1.0' or manifest.get('synthetic') is not True
            or manifest.get('status') != 'complete' or len(manifest.get('frames', [])) != 12
            or [f['case_id'] for f in result.get('frames', [])] != [f['case_id'] for f in manifest['frames']]):
        raise ValueError('Douze images fictives liées au même manifeste requises.')
    watched = {rp: digest(rp), mp: digest(mp)}
    for raw_path, expected in result['inputs_sha256'].items():
        path = local_path(raw_path, base)
        if digest(path) != expected:
            raise ValueError('Une entrée liée à la trace a changé avant le dessin.')
        watched[path] = expected
    tp = local_path(result['truth_path'], base)
    if tp not in watched or digest(tp) != watched[tp]:
        raise ValueError('Réponses fictives liées et intactes requises.')
    truth = read(tp)
    if (truth.get('detector_demo_truth_version') != '1.0' or truth.get('manifest_sha256') != watched[mp]
            or [r['case_id'] for r in truth.get('cases', [])] != [f['case_id'] for f in manifest['frames']]):
        raise ValueError('Réponses fictives incohérentes avec les douze cas.')
    planes = {}
    seen_paths = set()
    for frame, item, answer in zip(result['frames'], manifest['frames'], truth['cases']):
        path = local_path(mp.parent/item['local_plane'], base)
        if (mp.parent not in path.parents or path in seen_paths or frame['case_id'] in planes or digest(path) != item['sha256']
                or any(frame.get(key) != item[key] for key in ('scenario', 'seed'))
                or any(frame['evidence_by_radius'][radius]['target_native'] != answer['target_native'] for radius in ('1.5', '3'))):
            raise ValueError('Image fictive modifiée, répétée ou hors du dossier attendu.')
        seen_paths.add(path)
        trace = frame['trace']
        if (trace.get('selected_points_reduced') != [r['centroid_xy_reduced'] for r in trace['rows'] if r['project_kept']]
                or trace.get('selected_count') != sum(r['project_kept'] for r in trace['rows'])
                or trace.get('library_count') != sum(r['library_kept'] for r in trace['rows'])
                or trace.get('raw_count') != len(trace['rows'])
                or any(frame['evidence_by_radius'][f'{radius:g}'] != evidence_at(trace, answer['target_native'], radius) for radius in (1.5, 3.))):
            raise ValueError('Positions et preuves de proximité incohérentes avec les traces enregistrées.')
        watched[path] = item['sha256']
        plane = np.load(path, allow_pickle=False)
        if (plane.shape != (96, 96) or plane.dtype != np.dtype('float32')
                or frame['trace'].get('replay_equal') is not True
                or frame['trace'].get('image_shape') != [96, 96]):
            raise ValueError('Trace fidèle et image fictive 96×96 float32 requises.')
        planes[frame['case_id']] = plane
    output.mkdir(parents=True, exist_ok=False)
    stages = ('raw_seed_count', 'raw_centroid_count', 'library_count', 'selected_count')
    matrix = np.array([[frame['evidence_by_radius']['1.5'][stage] for frame in result['frames']] for stage in stages])
    if np.any(matrix < 0):
        raise ValueError('Effectifs de proximité non négatifs requis.')
    fig, ax = plt.subplots(figsize=(13, 5.5), layout='constrained')
    ax.imshow(matrix > 0, cmap='Blues', vmin=0, vmax=1, aspect='auto')
    ax.set(xticks=range(12), xticklabels=[LABELS[f['scenario']]+'\n'+str(f['seed']) for f in manifest['frames']],
           yticks=range(4), yticklabels=['Maximum brut proche', 'Centre brut proche', 'Après critères internes', 'Après marge du projet'])
    ax.tick_params(axis='x', labelrotation=65, labelsize=9)
    for i in range(4):
        for j in range(12):
            ax.text(j, i, str(matrix[i, j]), ha='center', va='center', color='white' if matrix[i, j] else 'black')
    fig.suptitle('ENTIÈREMENT FICTIF — les portes du détecteur inchangé\nChaque colonne est une image ; le nombre compte les points proches', fontsize=13)
    fig.supxlabel('Proximité ≤1,5 pixel natif · le sommet initial et son centre sont deux positions distinctes\nUne absence ne prouve pas sa cause ; même bruit entre situations d’une même graine', fontsize=10)
    render(fig).save(output/'gates.png')

    first_seed = min(f['seed'] for f in manifest['frames'])
    chosen = [f for f in result['frames'] if f['seed'] == first_seed]
    fig, axes = plt.subplots(2, 3, figsize=(13, 9), layout='constrained')
    for ax, frame in zip(axes.ravel(), chosen):
        trace = frame['trace']; evidence = frame['evidence_by_radius']['1.5']
        target = (np.asarray(evidence['target_native'], dtype=float)-.5)/2
        plane = planes[frame['case_id']]
        display = np.arcsinh(np.maximum(np.where(np.isfinite(plane), plane, trace['background'])-trace['background']+3*trace['noise_sigma'], 0)/(1.8*trace['noise_sigma']))
        ax.imshow(display, origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10), interpolation='nearest')
        ax.plot(*target, 'o', mfc='none', mec='lime', ms=15, mew=1.5)
        for row in trace['rows']:
            seed = np.asarray(row['seed_xy_reduced'], dtype=float)
            ax.plot(*seed, '.', color='#ffa126', ms=7)
            center = np.asarray([np.nan, np.nan] if row['centroid_xy_reduced'] is None else row['centroid_xy_reduced'], dtype=float)
            if np.isfinite(center).all():
                ax.plot(*center, '+' if row['project_kept'] else 'x', color='cyan' if row['project_kept'] else '#ff6273', ms=9)
        ax.set(xlim=(max(-.5, target[0]-14), min(95.5, target[0]+14)),
               ylim=(max(-.5, target[1]-14), min(95.5, target[1]+14)),
               title=LABELS[frame['scenario']]+f"\nSommets proches : {evidence['raw_seed_count']} ; retenus : {evidence['selected_count']}")
        ax.set_xlabel('Coordonnée réduite x'); ax.set_ylabel('Coordonnée réduite y')
    fig.suptitle('ENTIÈREMENT FICTIF — six situations fabriquées avant le résultat\nPremière graine fixée : '+str(first_seed)+' ; pixels affichés sans interpolation', fontsize=13)
    fig.supxlabel('Vert : position inventée connue, pas une détection · orange : sommet proposé\nCyan : centre conservé · rose : centre retiré · contraste commun −3 à +15 fois le bruit de chaque image\nLes noms décrivent la fabrication ; une proximité ne démontre ni identité ni cause physique', fontsize=10)
    render(fig).save(output/'examples.png')
    for path, expected in watched.items():
        if digest(path) != expected:
            raise ValueError('Une entrée a changé pendant le dessin ; conserver cet essai partiel.')
    journal = dict(detector_trace_figures_version='1.0', source_kind='synthetic_demo',
                   trace_sha256=watched[rp], manifest_sha256=watched[mp], input_hashes_unchanged=True,
                   detector_called=False, first_seed=first_seed,
                   figures_sha256={p.name: digest(p) for p in sorted(output.glob('*.png'))})
    (output/'figures.json').write_text(json.dumps(journal, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Deux figures entièrement fictives dessinées depuis les traces terminées ; aucun détecteur rappelé.', flush=True)
    return journal


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        plot(args.trace, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
