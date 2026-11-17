# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Conditional injection experiment: separate generation, blind analysis and scoring."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from astropy.io import fits
import numpy as np

from gar.astrometry import local_path
from gar.contracts import json_value
from gar.moving import detect_sources
from gar.workset import digest
from prepare_seestar_series import CONFIG_KEYS
import run_seestar_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = '9344495d49d8051e74663ab41e49de6ce05286eb'
PILOT_HASH = '605504751a6bbc25ffd1134b4c55efcebf47baf31ce044b70c229f47c9553e08'
PEAKS = (3, 6, 12)
SPEEDS = (.03, .15, .5, 1.2)
STARTS = ((.3, .3, 30.), (.5, .5, 150.), (.7, .7, 270.))
SIGMA_NATIVE = 2.2
save = pilot.save


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def frozen():
    result = pilot.frozen()
    value = sha256((ROOT/'examples/run_seestar_pilot.py').read_text(encoding='utf-8').encode()).hexdigest()
    if value != PILOT_HASH:
        raise ValueError('Recette pilote modifiée : nouveau protocole requis.')
    result['examples/run_seestar_pilot.py'] = value
    return result


def recipe_hash():
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def conditions():
    return [dict(case_id=f'a{a}-v{v:g}-p{p+1}'.replace('.', 'p'), peak_sigma=a,
                 speed_native_per_declared_second=v, position_index=p)
            for a in PEAKS for v in SPEEDS for p in range(3)]


def trajectory(shape, times, condition):
    h, w = shape
    fx, fy, angle = STARTS[condition['position_index']]
    velocity = condition['speed_native_per_declared_second']*np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
    return np.array([fx*w, fy*h])+np.asarray(times)[:, None]*velocity, velocity


def covered(positions, models, shape):
    h, w = shape
    return all(np.all(pilot.from_reference(positions, model) >= 32) and
               np.all(pilot.from_reference(positions, model) < [w-32, h-32]) for model in models)


def add_injection(plane, source_center, peak):
    """New float32 array; circular Gaussian on reduced sample centers, 5-sigma disk."""
    result = np.array(plane, dtype='float32', copy=True)
    center = (np.asarray(source_center)-.5)/2
    radius = 5*SIGMA_NATIVE/2
    lo = np.maximum(np.floor(center-radius).astype(int), 0)
    hi = np.minimum(np.ceil(center+radius).astype(int)+1, [plane.shape[1], plane.shape[0]])
    yy, xx = np.mgrid[lo[1]:hi[1], lo[0]:hi[0]]
    r2 = (2*xx+.5-source_center[0])**2+(2*yy+.5-source_center[1])**2
    signal = np.where(r2 <= (5*SIGMA_NATIVE)**2, peak*np.exp(-r2/(2*SIGMA_NATIVE**2)), 0)
    result[lo[1]:hi[1], lo[0]:hi[0]] += signal.astype('float32')
    return result


def checked_pilot(path, base, load_planes=False):
    path = local_path(path, base)
    watched = {path: digest(path)}; r = read(path)
    if (r.get('seestar_pilot_schema_version') != '1.0' or r.get('status') != 'complete'
            or not r.get('input_hashes_unchanged') or not r.get('registration_available')
            or not r.get('motion_searched') or len(r.get('copies', [])) != 8
            or len(r.get('models', [])) != 8 or r.get('frozen_sha256_lf') != pilot.frozen()
            or r.get('input_kind') not in ('synthetic_demo', 'real_local_copies')
            or r.get('inputs_sha256_before') != r.get('inputs_sha256_after')):
        raise ValueError('Pilote complet à huit copies, recalage accepté et empreintes gelées requis.')
    times = np.asarray(r['relative_declared_seconds'], dtype=float)
    shape = r['image_shape']
    if (times.shape != (8,) or not np.isfinite(times).all() or times[0] != 0 or times[-1] > 120
            or np.any(np.diff(times) <= 0) or np.any(np.diff(times) > 30)
            or len(shape) != 2 or any(type(n) is not int or n < 512 or n % 2 for n in shape)):
        raise ValueError('Huit temps croissants sur au plus 120 s déclarées et dimensions paires ≥512 requis.')
    for model in r['models']:
        rotation, translation = np.asarray(model['rotation_matrix']), np.asarray(model['translation_pixels'])
        if (not model.get('model_usable') or rotation.shape != (2, 2) or translation.shape != (2,)
                or not np.isfinite(rotation).all() or not np.isfinite(translation).all()
                or not np.allclose(rotation.T@rotation, np.eye(2), atol=1e-10, rtol=0)
                or not np.isclose(np.linalg.det(rotation), 1., atol=1e-10, rtol=0)):
            raise ValueError('Modèle rigide accepté requis pour chaque pose.')
    if not np.allclose(r['models'][0]['rotation_matrix'], np.eye(2)) or not np.allclose(r['models'][0]['translation_pixels'], [0, 0]):
        raise ValueError('La première pose doit être la référence identité mesurée.')
    audits = []
    for raw, expected in r['inputs_sha256_before'].items():
        p = local_path(raw, base)
        if digest(p) != expected:
            raise ValueError('Entrée du pilote modifiée.')
        watched[p] = expected
        if p.suffix == '.json':
            value = read(p)
            if value.get('series_audit_schema_version') == '1.0':
                audits.append(value)
    if len(audits) != 1 or not audits[0].get('copies_prepared') or len(audits[0]['files']) != 8:
        raise ValueError('Audit de préparation gelé requis.')
    planes, seen = [], set()
    for item, audit in zip(r['copies'], audits[0]['files']):
        p = local_path(item['local_copy'], base)
        if (p in seen or item['sha256'] in seen or item['sha256'] != audit['sha256']
                or p != local_path(audit['local_copy'], base) or digest(p) != item['sha256']):
            raise ValueError('Copie différente, modifiée ou répétée.')
        seen.update((p, item['sha256'])); watched[p] = item['sha256']
        if load_planes:
            with fits.open(p, mode='readonly', memmap=False) as hdus:
                h, data = hdus[0].header, hdus[0].data
                if (data is None or list(data.shape) != shape or not np.isfinite(data).all()
                        or {k: json_value(h.get(k)) for k in CONFIG_KEYS} != audit['metadata']
                        or h.get('DATE-OBS') != audit['date_obs_raw'] or h.get('EXPTIME') != audit['exptime_seconds_declared']
                        or (h.get('GARSYNTH') is True) != (r['input_kind'] == 'synthetic_demo')):
                    raise ValueError('Pixels, nature ou en-tête différents de la préparation.')
                planes.append(pilot.intensity_plane(data).astype('float32'))
    noise = r['motion_selection'][0]['noise_sigma']
    if not isinstance(noise, (float, int)) or not np.isfinite(noise) or noise <= 0:
        raise ValueError('Bruit de première pose positif requis, sans estimation adaptée aux résultats.')
    return r, watched, planes


def provenance():
    return dict(code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                tracked_tree_clean=not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip())


def unchanged(watched):
    if any(digest(p) != h for p, h in watched.items()):
        raise ValueError('Une entrée locale a changé.')


def write_plane(path, plane):
    with path.open('xb') as stream:
        np.save(stream, plane, allow_pickle=False)
    return dict(local_plane=path.name, sha256=digest(path))


def generate(pilot_path, output, base=None):
    base = ROOT/'local' if base is None else base
    rp, output = [local_path(p, base) for p in (pilot_path, output)]
    engines = frozen(); r, watched, planes = checked_pilot(rp, base, load_planes=True)
    output.mkdir(parents=True, exist_ok=False); (output/'planes').mkdir()
    manifest = dict(injection_manifest_version='1.0', status='running', plan_commit=PLAN_COMMIT,
                    frozen_sha256_lf=engines, recipe_sha256_lf=recipe_hash(), baseline_report=str(rp),
                    baseline_sha256=watched[rp], source_kind=r['input_kind'], image_shape=r['image_shape'],
                    reduced_shape=list(planes[0].shape), models=r['models'],
                    relative_declared_seconds=r['relative_declared_seconds'],
                    noise_sigma_first_reduced=r['motion_selection'][0]['noise_sigma'],
                    sigma_native=SIGMA_NATIVE, conditions=conditions(), cases=[], **provenance())
    answers = []
    save(output/'manifest.json', manifest)
    try:
        for spec in [dict(case_id='control'), *conditions()]:
            control = spec['case_id'] == 'control'
            positions, velocity = (None, None) if control else trajectory(r['image_shape'], r['relative_declared_seconds'], spec)
            available = control or covered(positions, r['models'], r['image_shape'])
            entry = dict(spec, available=available, frames=[], error=None if available else 'outside_common_field_margin_32')
            if available:
                for k, plane in enumerate(planes):
                    if control:
                        derivative = plane.copy()
                    else:
                        source = pilot.from_reference(positions[k:k+1], r['models'][k])[0]
                        derivative = add_injection(plane, source, spec['peak_sigma']*manifest['noise_sigma_first_reduced'])
                    path = output/'planes'/f'{spec["case_id"]}-{k:02d}.npy'
                    item = write_plane(path, derivative); item['local_plane'] = 'planes/'+item['local_plane']
                    entry['frames'].append(item)
            if not control:
                answers.append(dict(case_id=spec['case_id'], available=bool(available),
                    velocity_native_per_declared_second=velocity.tolist(),
                    positions=[dict(frame_index=k, x=float(p[0]), y=float(p[1])) for k, p in enumerate(positions)]))
            manifest['cases'].append(entry); save(output/'manifest.json', manifest)
        unchanged(watched)
        manifest.update(status='complete', inputs_unchanged=True); save(output/'manifest.json', manifest)
        save(output/'truth.json', dict(injection_truth_version='1.0', manifest_sha256=digest(output/'manifest.json'), cases=answers))
    except Exception as exc:
        manifest.update(status='incomplete', error=str(exc)); save(output/'manifest.json', manifest)
        raise
    print('37 séquences préparées : témoin et 36 injections ; vérité séparée, FITS intacts.', flush=True)
    return manifest


def load_manifest(path, base):
    path = local_path(path, base); manifest = read(path)
    if (manifest.get('injection_manifest_version') != '1.0' or manifest.get('status') != 'complete'
            or manifest.get('plan_commit') != PLAN_COMMIT or manifest.get('conditions') != conditions()
            or manifest.get('frozen_sha256_lf') != frozen() or manifest.get('recipe_sha256_lf') != recipe_hash()
            or [c['case_id'] for c in manifest.get('cases', [])] != ['control', *[c['case_id'] for c in conditions()]]):
        raise ValueError('Manifeste complet et protocole gelé requis.')
    rp = local_path(manifest['baseline_report'], base)
    if digest(rp) != manifest['baseline_sha256']:
        raise ValueError('Rapport pilote modifié.')
    r, watched, _ = checked_pilot(rp, base)
    for key in ('models', 'image_shape', 'relative_declared_seconds'):
        if manifest[key] != r[key]:
            raise ValueError('Paramètres du pilote gelé différents.')
    if manifest['source_kind'] != r['input_kind'] or manifest['noise_sigma_first_reduced'] != r['motion_selection'][0]['noise_sigma']:
        raise ValueError('Nature du fond ou bruit différent.')
    expected_shape = [n//2 for n in r['image_shape']]
    if manifest['reduced_shape'] != expected_shape or manifest['sigma_native'] != SIGMA_NATIVE:
        raise ValueError('Plan réduit ou largeur d’injection différent du protocole.')
    for case, spec in zip(manifest['cases'], [dict(case_id='control'), *conditions()]):
        if type(case.get('available')) is not bool or any(case.get(k) != v for k, v in spec.items()):
            raise ValueError('Description individuelle différente du protocole.')
    watched[path] = digest(path)
    return path, manifest, watched


def load_planes(mp, manifest, case, base, watched, masks=None):
    if not case['available']:
        if case['frames']:
            raise ValueError('Un cas indisponible ne doit pas contenir de plans.')
        return None
    if len(case['frames']) != 8:
        raise ValueError('Huit plans requis par cas disponible.')
    planes = []
    for k, item in enumerate(case['frames']):
        path = local_path(mp.parent/item['local_plane'], base)
        if (mp.parent not in path.parents or path.suffix != '.npy' or path in watched
                or digest(path) != item['sha256']):
            raise ValueError('Plan hors du lot, répété ou modifié.')
        with path.open('rb') as stream:
            plane = np.load(stream, allow_pickle=False)
            if stream.read(1):
                raise ValueError('Données après le plan NumPy refusées.')
        if (not isinstance(plane, np.ndarray) or plane.dtype != np.dtype('float32')
                or list(plane.shape) != manifest['reduced_shape'] or np.isinf(plane).any()
                or (masks is not None and not np.array_equal(np.isnan(plane), masks[k]))):
            raise ValueError('Type, forme ou masque du plan différent.')
        watched[path] = item['sha256']; planes.append(plane)
    return planes


def process(planes, models, shape, times):
    detections, selections = [], []
    for plane in planes:
        points, selection = detect_sources(plane)
        detections.append(2*points+.5); selections.append(selection)
    mapped, excluded = pilot.common_points(detections, models, shape)
    return dict(search=pilot.declared_tracks(mapped, times), raw_detections=[p.tolist() for p in detections],
                mapped_detections=[p.tolist() for p in mapped], selections=selections,
                overlap_excluded_per_frame=excluded)


def analyze(manifest_path, output, base=None):
    """No truth path or injection coordinate argument is accepted here."""
    base = ROOT/'local' if base is None else base
    output = local_path(output, base); mp, manifest, watched = load_manifest(manifest_path, base)
    output.mkdir(parents=True, exist_ok=False); (output/'cases').mkdir()
    result = dict(injection_analysis_version='1.0', status='running', manifest_sha256=watched[mp],
                  expected_case_count=37, records=[], truth_opened=False, models_refitted=False,
                  source_kind=manifest['source_kind'], **provenance())
    save(output/'analysis.json', result)
    masks = None
    try:
        for index, case in enumerate(manifest['cases']):
            planes = load_planes(mp, manifest, case, base, watched, masks)
            if index == 0:
                if planes is None:
                    raise ValueError('Le témoin sans ajout doit être disponible.')
                masks = [np.isnan(p) for p in planes]
            record = dict(case_id=case['case_id'], search_status='blocked', candidate_count=None, data=None)
            if planes is not None:
                try:
                    record['data'] = process(planes, manifest['models'], manifest['image_shape'], manifest['relative_declared_seconds'])
                    record.update(search_status='complete', candidate_count=len(record['data']['search']['tracks']))
                except ValueError as exc:
                    record['error'] = str(exc)
            else:
                record['error'] = case['error']
            path = output/'cases'/f'{case["case_id"]}.json'; save(path, record)
            result['records'].append(dict(case_id=case['case_id'], file='cases/'+path.name, sha256=digest(path)))
            save(output/'analysis.json', result)
            print(f'Analyse gelée {index+1}/37 : {record["search_status"]}.', flush=True)
        unchanged(watched)
        if any(digest(output/item['file']) != item['sha256'] for item in result['records']):
            raise ValueError('Un candidat gelé a changé pendant l’analyse.')
        result.update(status='complete', inputs_unchanged=True,
                      all_available=all(read(output/r['file'])['search_status'] == 'complete' for r in result['records']))
        save(output/'analysis.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); save(output/'analysis.json', result)
        raise
    return result


def sealed_records(path, manifest_hash, base, watched):
    path = local_path(path, base); document = read(path)
    if (document.get('injection_analysis_version') != '1.0' or document.get('status') != 'complete'
            or document.get('manifest_sha256') != manifest_hash or document.get('truth_opened') is not False
            or not document.get('inputs_unchanged') or document.get('models_refitted') is not False
            or [r['case_id'] for r in document.get('records', [])] != ['control', *[c['case_id'] for c in conditions()]]):
        raise ValueError('Analyse complète gelée avant lecture de la vérité requise.')
    watched[path] = digest(path); result = {}
    for item in document['records']:
        p = local_path(path.parent/item['file'], base)
        if path.parent not in p.parents or p in watched or digest(p) != item['sha256']:
            raise ValueError('Résultat individuel modifié, répété ou hors du lot.')
        record = read(p)
        if record.get('case_id') != item['case_id'] or record.get('search_status') not in ('complete', 'blocked'):
            raise ValueError('Résultat individuel incohérent.')
        if record['search_status'] == 'complete':
            if record['candidate_count'] != len(record['data']['search']['tracks']):
                raise ValueError('Nombre de candidats incohérent.')
        elif record['candidate_count'] is not None or record['data'] is not None:
            raise ValueError('Un refus ne doit pas devenir un nombre de candidats.')
        result[item['case_id']] = record; watched[p] = item['sha256']
    return result


def verify_derivatives(mp, manifest, base, watched):
    seen = set()
    for case in manifest['cases']:
        for frame in case['frames']:
            path = local_path(mp.parent/frame['local_plane'], base)
            if (mp.parent not in path.parents or path in seen or path.suffix != '.npy'
                    or digest(path) != frame['sha256']):
                raise ValueError('Dérivé modifié, répété ou hors du lot.')
            seen.add(path); watched[path] = frame['sha256']


def score_one(record, truth):
    """Post-search one-injection matching; candidates are never altered."""
    if record['search_status'] != 'complete':
        return dict(available=False, recovered=None, missed=None, unassociated_candidates=None, match=None)
    tracks = record['data']['search']['tracks']
    matches = []
    if truth is not None:
        true = {p['frame_index']: np.array([p['x'], p['y']]) for p in truth['positions']}
        for track in tracks:
            measured = {p['frame_index']: np.array([p['x'], p['y']]) for p in track['points']}
            common = sorted(set(measured) & set(true))
            if len(common) < 5:
                continue
            errors = [float(np.linalg.norm(measured[k]-true[k])) for k in common]
            rms = float(np.sqrt(np.mean(np.square(errors))))
            velocity_error = float(np.linalg.norm(np.asarray(track['velocity_native_pixels_per_declared_second'])-truth['velocity_native_per_declared_second']))
            if rms <= 1 and velocity_error <= .05:
                matches.append(dict(candidate_id=track['candidate_id'], rms_native_pixels=rms,
                                    position_errors_native_pixels=errors, velocity_error_native_per_declared_second=velocity_error))
    chosen = min(matches, key=lambda m: (m['rms_native_pixels'], m['candidate_id'])) if matches else None
    recovered = int(chosen is not None) if truth is not None else None
    return dict(available=True, recovered=recovered, missed=1-recovered if recovered is not None else None,
                unassociated_candidates=len(tracks)-int(chosen is not None), match=chosen)


def score(manifest_path, truth_path, analysis_path, output, base=None):
    base = ROOT/'local' if base is None else base
    mp, manifest, watched = load_manifest(manifest_path, base)
    tp, ap, output = [local_path(p, base) for p in (truth_path, analysis_path, output)]
    records = sealed_records(ap, watched[mp], base, watched)
    verify_derivatives(mp, manifest, base, watched)
    # No truth file is opened until every candidate result has passed its frozen hash.
    watched[tp] = digest(tp); truth = read(tp)
    if (truth.get('injection_truth_version') != '1.0' or truth.get('manifest_sha256') != watched[mp]
            or [c['case_id'] for c in truth.get('cases', [])] != [c['case_id'] for c in conditions()]):
        raise ValueError('Vérité complète liée au même manifeste requise.')
    answers = {c['case_id']: c for c in truth['cases']}
    for spec in conditions():
        answer = answers[spec['case_id']]
        positions, velocity = trajectory(manifest['image_shape'], manifest['relative_declared_seconds'], spec)
        if ([p['frame_index'] for p in answer['positions']] != list(range(8))
                or not np.allclose([[p['x'], p['y']] for p in answer['positions']], positions, atol=1e-10, rtol=0)
                or not np.allclose(answer['velocity_native_per_declared_second'], velocity, atol=1e-10, rtol=0)
                or answer['available'] != next(c['available'] for c in manifest['cases'] if c['case_id'] == spec['case_id'])):
            raise ValueError('Vérité différente des trajets préenregistrés.')
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for spec in [dict(case_id='control'), *conditions()]:
        item = score_one(records[spec['case_id']], answers.get(spec['case_id']))
        rows.append(dict(spec, **item))
    groups = []
    for a in PEAKS:
        for v in SPEEDS:
            local = [r for r in rows if r.get('peak_sigma') == a and r.get('speed_native_per_declared_second') == v]
            groups.append(dict(peak_sigma=a, speed_native_per_declared_second=v, planned=3,
                               available=sum(r['available'] for r in local),
                               recovered=sum(r['recovered'] or 0 for r in local),
                               missed=sum(r['missed'] or 0 for r in local),
                               unavailable=sum(not r['available'] for r in local),
                               unassociated_candidates=sum(r['unassociated_candidates'] or 0 for r in local)))
    baseline = read(local_path(manifest['baseline_report'], base))
    control = records['control']
    control_identical = control['search_status'] == 'complete' and all(
        control['data'][k] == baseline[k] for k in ('raw_detections', 'mapped_detections', 'overlap_excluded_per_frame', 'search'))
    synthetic = manifest['source_kind'] == 'synthetic_demo'
    bright = next(g for g in groups if g['peak_sigma'] == 12 and g['speed_native_per_declared_second'] == .5)
    fixture_pass = (control['candidate_count'] == 0 and bright['recovered'] == bright['available'] == 3
                    and all(g['recovered'] == 0 for g in groups if g['speed_native_per_declared_second'] == .03)) if synthetic else None
    result = dict(injection_score_version='1.0', status='running', manifest_path=str(mp), analysis_path=str(ap),
                  truth_path=str(tp), manifest_sha256=watched[mp], analysis_sha256=watched[ap], truth_sha256=watched[tp],
                  source_kind=manifest['source_kind'], descriptive_only=True, conditional_on_frozen_registration=True,
                  clock_qualified=False, real_data_performance_validated=False, scientific_submission_certified=False,
                  rows=rows, groups=groups, control_candidates=control['candidate_count'],
                  control_identical_to_baseline=control_identical, planned_injections=36,
                  available_injections=sum(g['available'] for g in groups), recovered=sum(g['recovered'] for g in groups),
                  missed=sum(g['missed'] for g in groups), unavailable=sum(g['unavailable'] for g in groups),
                  unassociated_candidates=sum(g['unassociated_candidates'] for g in groups) if any(g['available'] for g in groups) else None,
                  false_candidates=sum(g['unassociated_candidates'] for g in groups)+control['candidate_count'] if synthetic and all(r['available'] for r in rows) else None,
                  synthetic_fixture_criteria_passed=fixture_pass, **provenance())
    save(output/'score.json', result)
    try:
        write_score_outputs(output, result)
        unchanged(watched)
        result.update(status='complete', inputs_unchanged=True)
        save(output/'score.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); save(output/'score.json', result)
        raise
    print(f"Score descriptif : {result['recovered']}/36 retrouvées, {result['missed']} manquées, {result['unavailable']} indisponibles. Aucun seuil ajusté.", flush=True)
    return result


def write_score_outputs(output, result):
    with (output/'recovery.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['case_id', 'available', 'recovered', 'missed', 'unassociated_candidates']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({k: row.get(k) for k in fields} for row in result['rows'])
    text = '# Récupération descriptive — rapport local\n\n'
    text += f"Injections prévues : 36 ; retrouvées : {result['recovered']}, manquées parmi les disponibles : {result['missed']}, indisponibles : {result['unavailable']}.\n\n"
    text += '| Pic / sigma initial | Vitesse native / seconde déclarée | Retrouvées | Disponibles / prévues | Manquées | Non associés |\n|---|---|---|---|---|---|\n'
    for g in result['groups']:
        text += f"| {g['peak_sigma']} | {g['speed_native_per_declared_second']} | {g['recovered']} | {g['available']}/3 | {g['missed']} | {g['unassociated_candidates']} |\n"
    text += ('\nTrois positions fixées, pas une probabilité universelle. Recalage gelé, ajout gaussien sans bruit de photons supplémentaire, spectre ou traînée. '
             'Le pic/sigma initial n’est pas un rapport signal/bruit étalonné. Temps déclarés non qualifiés. '
             'Sur fond réel, les candidats non associés ne sont pas des faux positifs établis. '
             'Les manques et cas bloqués sont conservés ; aucune découverte ou performance scientifique validée.\n')
    (output/'report.md').write_text(text, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    gen = sub.add_parser('generate'); gen.add_argument('pilot', type=Path); gen.add_argument('output', type=Path)
    ana = sub.add_parser('analyze'); ana.add_argument('manifest', type=Path); ana.add_argument('output', type=Path)
    sco = sub.add_parser('score')
    for field in ('manifest', 'truth', 'analysis', 'output'):
        sco.add_argument(field, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'generate':
            generate(args.pilot, args.output); code = 0
        elif args.command == 'analyze':
            r = analyze(args.manifest, args.output); code = 0 if r['all_available'] else 2
        else:
            r = score(args.manifest, args.truth, args.analysis, args.output)
            code = 2 if r['unavailable'] or r['synthetic_fixture_criteria_passed'] is False else 0
        raise SystemExit(code)
    except (ValueError, OSError, KeyError, TypeError, EOFError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
