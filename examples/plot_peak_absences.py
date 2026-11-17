# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Draw completed synthetic peak traces without convolution or peak finding."""
import argparse
from collections import Counter
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
import trace_peak_creation as tracing

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_LABELS = dict(isolated_bright='Point isolé brillant', faint='Point faible',
    brighter_neighbor='Voisin plus brillant', masked='Pixels masqués',
    library_border='Bord de la bibliothèque', plateau_tie='Fabrication plateau / égalité')
STAGE_LABELS = ('Centres examinés', 'Maximum local', 'Après masque', 'Après bord',
                'Au-dessus du seuil', 'Après plateaux', 'Graines proposées')
CONDITIONS = ('local_maximum', 'unmasked', 'inside_border', 'above_threshold')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate_evidence(trace, evidence, target, radius):
    """Check the recorded arithmetic only; do not recompute pixel decisions."""
    if evidence['target_native'] != target or evidence['radius_native'] != radius:
        raise ValueError('Voisinage différent des réponses fictives liées.')
    target = np.asarray(target, dtype=float)
    if target.shape != (2,) or not np.isfinite(target).all():
        raise ValueError('Réponse native finie à deux coordonnées requise.')
    h, w = trace['image_shape']; center = (target-.5)/2
    expected = [(x, y) for y in range(max(0, int(np.ceil(center[1]-radius/2))), min(h-1, int(np.floor(center[1]+radius/2)))+1)
                for x in range(max(0, int(np.ceil(center[0]-radius/2))), min(w-1, int(np.floor(center[0]+radius/2)))+1)
                if np.linalg.norm(2*np.array([x, y])+.5-target) <= radius]
    samples = evidence['samples']
    if [(s['x_reduced'], s['y_reduced']) for s in samples] != expected:
        raise ValueError('Centres échantillonnés différents du cercle déclaré.')
    counts = {key: 0 for key in tracing.STAGES}; obstacles = {key: 0 for key in CONDITIONS}
    seeds = {tuple(seed) for seed in trace['seeds_reduced']}
    for sample in samples:
        if not np.isfinite([sample['value_convolved'], sample['value_for_peaks']]).all():
            raise ValueError('Valeurs de réponse enregistrées finies requises.')
        passes, conditions = sample['stage_passes'], sample['conditions_passes']
        if (set(passes) != set(tracing.STAGES) or set(conditions) != set(CONDITIONS)
                or any(type(v) is not bool for v in [*passes.values(), *conditions.values()])
                or passes['samples'] is not True):
            raise ValueError('Portes booléennes et conditions prévues requises.')
        previous = True
        for key in CONDITIONS:
            if passes[key] != (previous and conditions[key]):
                raise ValueError('Portes cumulées incohérentes avec les conditions enregistrées.')
            previous = passes[key]; obstacles[key] += not conditions[key]
        if (passes['plateau'] and not passes['above_threshold']
                or passes['final'] and not passes['plateau']
                or passes['final'] != ((sample['x_reduced'], sample['y_reduced']) in seeds)
                or conditions['above_threshold'] != (sample['value_for_peaks'] > trace['threshold_effective'])):
            raise ValueError('Seuil strict ou graines incohérents avec les portes enregistrées.')
        if conditions['unmasked'] and sample['value_convolved'] != sample['value_for_peaks']:
            raise ValueError('Réponse non masquée différente de la valeur utilisée pour les pics.')
        for key in tracing.STAGES:
            counts[key] += passes[key]
    first = next((key for key in tracing.STAGES if counts[key] == 0), 'proposed')
    best = max(samples, key=lambda s: s['value_for_peaks'], default=None)
    if (evidence['stage_counts'] != counts or evidence['first_empty_stage'] != first
            or evidence['first_empty_label'] != tracing.LABELS[first]
            or evidence['simultaneous_obstacles'] != obstacles or evidence['best_sample'] != best
            or evidence['final_seed_count'] != counts['final']
            or evidence['identity_proven'] is not False or evidence['physical_cause_proven'] is not False):
        raise ValueError('Compteurs ou conclusions incohérents avec les échantillons enregistrés.')
    if 'independent_pass_counts' in evidence and evidence['independent_pass_counts'] != {key: len(samples)-value for key, value in obstacles.items()}:
        raise ValueError('Comptes indépendants des conditions incohérents.')
    neighbor = evidence['higher_neighbor']
    if neighbor is not None:
        if (best is None or not np.isfinite(neighbor['value_for_peaks'])
                or neighbor['value_for_peaks'] <= best['value_for_peaks']
                or (neighbor['x_reduced']-best['x_reduced'])**2+(neighbor['y_reduced']-best['y_reduced'])**2 > 25
                or not 0 <= neighbor['x_reduced'] < w or not 0 <= neighbor['y_reduced'] < h
                or neighbor['identity_proven'] is not False
                or abs(neighbor['distance_native']-np.linalg.norm(2*np.array([neighbor['x_reduced'], neighbor['y_reduced']])+.5-target)) > 1e-9):
            raise ValueError('Voisin plus élevé incohérent avec son échantillon et sa distance.')


def plot(trace_path, output, base=None):
    base = ROOT/'local' if base is None else base
    rp, output = [local_path(p, base) for p in (trace_path, output)]
    result = read(rp)
    if (result.get('peak_absence_trace_version') != '1.0' or result.get('status') != 'complete'
            or result.get('source_kind') != 'synthetic_demo' or result.get('input_hashes_unchanged') is not True
            or result.get('truth_opened_after_replay') is not True
            or result.get('thresholds_changed') is not False or result.get('association_rerun') is not False
            or result.get('trace_recipe_sha256_lf') != tracing.recipe_hash()):
        raise ValueError('Trace fictive complète de cette recette, sans seuil changé, requise.')
    watched = {rp: digest(rp)}
    for raw, expected in result['inputs_sha256'].items():
        path = local_path(raw, base)
        if digest(path) != expected:
            raise ValueError('Une entrée de la trace a changé avant les figures.')
        watched[path] = expected
    mp, tp = [local_path(result[key], base) for key in ('manifest_path', 'truth_path')]
    if (watched.get(mp) != result['manifest_sha256'] or watched.get(tp) != result['truth_sha256']):
        raise ValueError('Manifeste et réponses liés requis.')
    manifest, truth = read(mp), read(tp)
    specs = [(f'{scenario}-s{seed}', scenario, seed) for seed in tracing.DEMO_SEEDS for scenario in tracing.DEMO_SCENARIOS]
    if (manifest.get('peak_demo_version') != '1.0' or manifest.get('synthetic') is not True
            or manifest.get('status') != 'complete' or manifest.get('shape') != [96, 96]
            or manifest.get('seeds') != list(tracing.DEMO_SEEDS) or manifest.get('scenarios') != list(tracing.DEMO_SCENARIOS)
            or [(f['case_id'], f['scenario'], f['seed']) for f in manifest['frames']] != specs
            or [(f['case_id'], f['scenario'], f['seed']) for f in result['frames']] != specs
            or truth.get('peak_demo_truth_version') != '1.0' or truth.get('manifest_sha256') != watched[mp]
            or [a['case_id'] for a in truth.get('cases', [])] != [s[0] for s in specs]):
        raise ValueError('Banc fictif complet et réponses concordantes requis.')
    planes = {}; seen = set()
    for frame, item, answer in zip(result['frames'], manifest['frames'], truth['cases']):
        path = local_path(mp.parent/item['local_plane'], base)
        if mp.parent not in path.parents or path in seen or watched.get(path) != item['sha256']:
            raise ValueError('Image hors du banc, répétée ou empreinte incohérente.')
        seen.add(path)
        with path.open('rb') as stream:
            plane = np.load(stream, allow_pickle=False)
            if stream.read(1):
                raise ValueError('Données supplémentaires après le plan fictif.')
        trace = frame['trace']; old = trace['old_detector_trace']
        seeds = np.asarray(trace['seeds_reduced']).reshape(-1, 2)
        if (plane.shape != (96, 96) or plane.dtype != np.dtype('float32') or trace['image_shape'] != [96, 96]
                or trace.get('seeds_equal') is not True or old.get('replay_equal') is not True
                or not np.array_equal(seeds, np.asarray([r['seed_xy_reduced'] for r in old['rows']]).reshape(-1, 2))
                or trace['stage_counts_global']['final'] != len(seeds)
                or any(trace[key] != old[key] for key in ('background', 'noise_sigma', 'threshold_input', 'threshold_effective'))
                or not np.isfinite(trace['threshold_effective']) or trace['threshold_effective'] <= 0):
            raise ValueError('Plans et graines cohérents avec le rejeu complet requis.')
        for radius in (1.5, 3.):
            validate_evidence(trace, frame['evidence_by_radius'][f'{radius:g}'], answer['target_native'], radius)
        if frame['status_stable_across_radii'] != (frame['evidence_by_radius']['1.5']['first_empty_stage'] == frame['evidence_by_radius']['3']['first_empty_stage']):
            raise ValueError('Discordance de rayon incohérente avec les preuves.')
        planes[frame['case_id']] = plane
    summary = {f'{r:g}': dict(sorted(Counter(f['evidence_by_radius'][f'{r:g}']['first_empty_stage'] for f in result['frames']).items())) for r in (1.5, 3.)}
    if result['summary'] != summary:
        raise ValueError('Résumé différent des preuves individuelles.')
    output.mkdir(parents=True, exist_ok=False)
    matrix = np.array([[frame['evidence_by_radius']['1.5']['stage_counts'][stage] for frame in result['frames']] for stage in tracing.STAGES])
    fig, ax = plt.subplots(figsize=(14, 6), layout='constrained')
    ax.imshow(matrix > 0, cmap='Blues', vmin=0, vmax=1, aspect='auto')
    ax.set(xticks=range(12), xticklabels=[SCENARIO_LABELS[f['scenario']]+'\n'+str(f['seed']) for f in result['frames']],
           yticks=range(len(tracing.STAGES)), yticklabels=STAGE_LABELS)
    ax.tick_params(axis='x', labelrotation=60, labelsize=9)
    for y in range(len(tracing.STAGES)):
        for x in range(12):
            ax.text(x, y, str(matrix[y, x]), ha='center', va='center', color='white' if matrix[y, x] else 'black')
    fig.suptitle('ENTIÈREMENT FICTIF — avant les maxima proposés\nChaque colonne est une image ; chaque nombre compte les centres proches qui passent la porte', fontsize=13)
    fig.supxlabel('Rayon 1,5 pixel natif · mêmes règles et seuils · bruit apparié par graine\nLe premier groupe vide décrit une étape ; plusieurs obstacles peuvent coexister', fontsize=10)
    render(fig).save(output/'gates.png')

    first_seed = min(tracing.DEMO_SEEDS)
    chosen = [f for f in result['frames'] if f['seed'] == first_seed]
    fig, axes = plt.subplots(2, 3, figsize=(14, 10), layout='constrained')
    for ax, frame in zip(axes.ravel(), chosen):
        trace = frame['trace']; evidence = frame['evidence_by_radius']['3']
        center = (np.asarray(evidence['target_native'])-.5)/2
        plane = planes[frame['case_id']]
        display = np.arcsinh(np.maximum(np.where(np.isfinite(plane), plane, trace['background'])-trace['background']+3*trace['noise_sigma'], 0)/(1.8*trace['noise_sigma']))
        ax.imshow(display, origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10), interpolation='nearest')
        for sample in evidence['samples']:
            x, y = sample['x_reduced'], sample['y_reduced']
            above = sample['conditions_passes']['above_threshold']
            ax.plot(x, y, 's', mfc='none', mec='#45c8ff' if above else '#ffb34d', ms=12, mew=1.5)
        seeds = np.asarray(trace['seeds_reduced']).reshape(-1, 2)
        if len(seeds): ax.plot(seeds[:, 0], seeds[:, 1], '+', color='#ff5bd8', ms=11, mew=1.7)
        neighbor = evidence['higher_neighbor']
        if neighbor is not None:
            ax.plot(neighbor['x_reduced'], neighbor['y_reduced'], 'D', mfc='none', mec='yellow', ms=10, mew=1.5)
        ax.plot(*center, 'o', mfc='none', mec='lime', ms=15, mew=1.5)
        best = evidence['best_sample']
        ratio = 'inconnue' if best is None else f"{best['value_for_peaks']/trace['threshold_effective']:.2f}"
        ax.text(.03, .03, 'Meilleure réponse / seuil : '+ratio, transform=ax.transAxes, fontsize=10,
                bbox=dict(facecolor='white', edgecolor='none', alpha=.9))
        ax.set(xlim=(max(-.5, center[0]-8), min(95.5, center[0]+8)),
               ylim=(max(-.5, center[1]-8), min(95.5, center[1]+8)),
               title=SCENARIO_LABELS[frame['scenario']]+f"\nGraines proches : {evidence['final_seed_count']} ; seuil : {trace['threshold_effective']:.2f}")
        ax.set_xlabel('Coordonnée réduite x'); ax.set_ylabel('Coordonnée réduite y')
    fig.suptitle('ENTIÈREMENT FICTIF — pixels et échantillons déjà calculés\nPremière graine fixée : '+str(first_seed)+' ; aucun filtre ou détecteur rappelé pour dessiner', fontsize=13)
    fig.supxlabel('Vert : réponse inventée, pas une détection · rose : graine proposée · jaune : voisin plus haut enregistré\nCarrés = centres dans le cercle de 3 pixels natifs ; bleu : réponse > seuil, orange : réponse ≤ seuil\nNombre = meilleure valeur utilisée pour les pics / seuil effectif, sans unité photométrique\nPixels sans interpolation · données du carnet · aucune identité ou cause physique prouvée par une proximité', fontsize=10)
    render(fig).save(output/'examples.png')
    for path, expected in watched.items():
        if digest(path) != expected:
            raise ValueError('Une entrée a changé pendant le dessin ; conserver cet essai partiel.')
    journal = dict(peak_absence_figures_version='1.0', source_kind='synthetic_demo', trace_sha256=watched[rp],
        manifest_sha256=watched[mp], input_hashes_unchanged=True, detector_called=False,
        convolution_called=False, first_seed=first_seed,
        figures_sha256={p.name: digest(p) for p in sorted(output.glob('*.png'))})
    (output/'figures.json').write_text(json.dumps(journal, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Deux figures entièrement fictives dessinées depuis les preuves, sans nouvelle convolution ou détection.', flush=True)
    return journal


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('trace', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        plot(args.trace, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
