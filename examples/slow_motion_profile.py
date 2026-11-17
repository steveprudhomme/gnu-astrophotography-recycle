# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Prepare a separate long-baseline profile, inject, search blind, then score."""
import argparse
import csv
from hashlib import sha256
from pathlib import Path

from astropy.io import fits
import numpy as np
from gar.astrometry import local_path
from gar.contracts import parse_declared_time
from gar.moving import detect_sources
from gar.registration import detect
from gar.sessions import CONFIG_KEYS
from gar.slow_moving import PARAMETERS, validate_times, find_tracks, score_track
from gar.workset import digest
import injection_recovery as experiment
import realistic_motions as representative
import run_seestar_pilot as pilot
from spatial_controls import register_spatial

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = '0f063684ec85495f4497348d18cbac566d41a2ea'
RATES, PEAKS = (10., 30., 60.), (6, 12)
save, read, unchanged = experiment.save, experiment.read, experiment.unchanged
trajectory = representative.trajectory


def recipe_hash():
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def frozen():
    hashes = representative.frozen()
    relative = 'examples/realistic_motions.py'
    value = sha256((ROOT/relative).read_text(encoding='utf-8').encode()).hexdigest()
    if value != '78d62a2887f36c0c4b39e7a079981ebfbf30659653eaec4ab4d118eda61928e0':
        raise ValueError('La recette historique de traînée a changé.')
    hashes[relative] = value
    relative = 'src/gar/slow_moving.py'
    hashes[relative] = sha256((ROOT/relative).read_text(encoding='utf-8').encode()).hexdigest()
    return hashes


def conditions(scale):
    if type(scale) not in (int, float) or not np.isfinite(scale) or scale <= 0:
        raise ValueError('Une échelle nominale positive est requise.')
    return [dict(case_id=f'r{rate:g}-a{peak}-p{position+1}', family='angular',
        angular_rate_arcsec_hour=rate, peak_sigma=peak, position_index=position,
        speed_native_per_declared_second=rate/(3600*scale), in_speed_domain=True,
        smear_samples=7) for rate in RATES for peak in PEAKS for position in range(2)]


def _new_output(path, base):
    path = local_path(path, base)
    path.mkdir(parents=True, exist_ok=False)
    return path


def _stable_code(record):
    if record['frozen_sha256_lf'] != frozen() or record['recipe_sha256_lf'] != recipe_hash():
        raise ValueError('Une source de calcul a changé pendant cette étape.')


def _read_workset(path, base, pixels=False):
    wp = local_path(path, base); watched = {wp: digest(wp)}; report = read(wp)
    if (report.get('workset_schema_version') != '1.0' or report.get('success') is not True
            or len(report.get('files', [])) != 8):
        raise ValueError('Un lot local vérifié de huit copies est requis.')
    copies, headers, planes, stars = [], [], [], []
    seen_paths, seen_hashes = set(), set()
    for item in report['files']:
        copy = local_path(wp.parent/item['local_copy'], base)
        expected = item['sha256_copy']
        if (wp.parent not in copy.parents or copy in seen_paths or expected in seen_hashes
                or item['sha256_before'] != expected or item['sha256_after'] != expected
                or digest(copy) != expected):
            raise ValueError('Une copie est répétée, modifiée ou hors du lot.')
        seen_paths.add(copy); seen_hashes.add(expected); watched[copy] = expected
        with fits.open(copy, mode='readonly', memmap=False) as hdus:
            header = hdus[0].header.copy()
            shape = (header.get('NAXIS2'), header.get('NAXIS1'))
            if (header.get('NAXIS') != 2 or any(type(v) is not int or v < 512 or v % 2 for v in shape)
                    or header.get('BAYERPAT') not in pilot.BAYER):
                raise ValueError('Huit poses Bayer 2D paires d’au moins 512 pixels sont requises.')
            if pixels:
                image = np.asarray(hdus[0].data, dtype=float)
                planes.append(pilot.intensity_plane(image).astype('float32'))
                try:
                    points, selection = detect(image)
                    stars.append((points, selection))
                except ValueError as exc:
                    stars.append((None, dict(error=str(exc))))
        headers.append(header)
        copies.append(dict(local_copy=str(copy), sha256=expected))
    shapes = [(h['NAXIS2'], h['NAXIS1']) for h in headers]
    configs = [{k: h.get(k) for k in CONFIG_KEYS} for h in headers]
    markers = [h.get('GARSYNTH') is True for h in headers]
    if any(s != shapes[0] for s in shapes) or any(c != configs[0] for c in configs) or any(markers) != all(markers):
        raise ValueError('Dimensions, configuration ou nature des huit copies différentes.')
    dates = [parse_declared_time(h.get('DATE-OBS')) for h in headers]
    times = validate_times([(d-dates[0]).total_seconds() for d in dates])
    exposures = [h.get('EXPTIME') for h in headers]
    if any(type(v) not in (int, float) or not np.isfinite(v) or not 0 < v <= 120 for v in exposures):
        raise ValueError('Les huit durées de pose doivent être positives et au plus 120 s.')
    scale = representative.scale_from_headers(headers)
    summary = dict(workset_path=str(wp), workset_sha256=watched[wp], copies=copies,
        image_shape=list(shapes[0]), reduced_shape=[v//2 for v in shapes[0]],
        configuration=configs[0], relative_declared_seconds=times.tolist(),
        declared_optics={k: headers[0].get(k) for k in ('XPIXSZ', 'YPIXSZ', 'FOCALLEN')},
        exposure_seconds_declared=exposures, scale_arcsec_per_native_pixel=scale,
        source_kind='synthetic_demo' if all(markers) else 'real_local_copies')
    unchanged(watched)
    return summary, watched, planes, stars


def process(planes, models, shape, times, scale):
    detections, selections = [], []
    for plane in planes:
        points, selection = detect_sources(plane)
        detections.append(2*points+.5); selections.append(selection)
    mapped, excluded = pilot.common_points(detections, models, shape)
    tracks, hypotheses = find_tracks(mapped, times, scale)
    return dict(raw_detections=[p.tolist() for p in detections],
        mapped_detections=[p.tolist() for p in mapped], overlap_excluded_per_frame=excluded,
        selections=selections, search=dict(tracks=tracks, hypotheses_scored=hypotheses,
            profile='slow_v1', parameters=PARAMETERS.copy(), stationary_removal_applied=False))


def prepare(workset_path, output, base=None):
    base = ROOT/'local' if base is None else base
    engines = frozen(); summary, watched, planes, stars = _read_workset(workset_path, base, True)
    output = _new_output(output, base)
    result = dict(slow_motion_baseline_version='1.0', status='running', plan_commit=PLAN_COMMIT,
        recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=engines, profile_parameters=PARAMETERS.copy(),
        **summary, models=[], registration_available=False, candidate_count=None,
        search_status='blocked', search=None, blocked_reasons=[], clock_qualified=False,
        science_fitness_passed=False, **experiment.provenance())
    bp = output/'baseline.json'; save(bp, result)
    try:
        reference = stars[0][0]
        result['star_selection'] = [s for _, s in stars]
        result['models'].append(dict(kind='measured_reference_identity', model_usable=reference is not None,
            rotation_matrix=np.eye(2).tolist(), translation_pixels=[0., 0.], independent_control=False))
        if reference is None:
            result['blocked_reasons'].append(dict(frame_index=0, stage='registration', reason='reference_stars_unavailable'))
        for k, (points, _) in enumerate(stars[1:], 1):
            try:
                if points is None or reference is None:
                    raise ValueError('Les étoiles de recalage ne sont pas disponibles.')
                model = register_spatial(points, reference, summary['image_shape'])
            except ValueError as exc:
                model = dict(model_usable=False, error=str(exc))
            result['models'].append(model)
            if not model['model_usable']:
                result['blocked_reasons'].append(dict(frame_index=k, stage='registration', reason=model.get('error', 'criteria_failed')))
        result['registration_available'] = all(m['model_usable'] for m in result['models'])
        if result['registration_available']:
            try:
                data = process(planes, result['models'], summary['image_shape'],
                    summary['relative_declared_seconds'], summary['scale_arcsec_per_native_pixel'])
                result.update(data, search_status='complete', candidate_count=len(data['search']['tracks']))
                result['noise_sigma_first_reduced'] = data['selections'][0]['noise_sigma']
            except ValueError as exc:
                result['blocked_reasons'].append(dict(stage='search', reason=str(exc)))
        unchanged(watched)
        _stable_code(result)
        result.update(status='complete', inputs_unchanged=True,
            inputs_sha256_before={str(p): h for p, h in watched.items()},
            inputs_sha256_after={str(p): h for p, h in watched.items()})
        save(bp, result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); save(bp, result); raise
    return result


def checked_baseline(path, base, pixels=False):
    bp = local_path(path, base); r = read(bp); watched = {bp: digest(bp)}
    if (r.get('slow_motion_baseline_version') != '1.0' or r.get('status') != 'complete'
            or r.get('plan_commit') != PLAN_COMMIT or r.get('recipe_sha256_lf') != recipe_hash()
            or r.get('frozen_sha256_lf') != frozen() or r.get('profile_parameters') != PARAMETERS
            or r.get('inputs_unchanged') is not True or r.get('registration_available') is not True
            or r.get('search_status') != 'complete' or len(r.get('models', [])) != 8
            or r.get('inputs_sha256_before') != r.get('inputs_sha256_after')):
        raise ValueError('Un bilan long complet, recalé et gelé de ce profil est requis.')
    summary, inputs, planes, _ = _read_workset(r['workset_path'], base, pixels)
    if (any(r.get(k) != v for k, v in summary.items())
            or {str(p): h for p, h in inputs.items()} != r['inputs_sha256_before']):
        raise ValueError('Les copies ou leur contrat diffèrent du bilan.')
    for model in r['models']:
        rotation, translation = np.asarray(model['rotation_matrix']), np.asarray(model['translation_pixels'])
        if (model.get('model_usable') is not True or rotation.shape != (2, 2) or translation.shape != (2,)
                or not np.isfinite(rotation).all() or not np.isfinite(translation).all()
                or not np.allclose(rotation.T@rotation, np.eye(2), atol=1e-10, rtol=0)
                or not np.isclose(np.linalg.det(rotation), 1, atol=1e-10, rtol=0)):
            raise ValueError('Un modèle rigide accepté est requis pour chaque pose.')
    if (not np.array_equal(r['models'][0]['rotation_matrix'], np.eye(2))
            or r['models'][0]['translation_pixels'] != [0., 0.]):
        raise ValueError('La première pose doit garder le modèle identité.')
    noise = r.get('noise_sigma_first_reduced')
    if type(noise) not in (int, float) or not np.isfinite(noise) or noise <= 0:
        raise ValueError('Le bruit initial positif doit être enregistré.')
    if r.get('candidate_count') != len(r['search']['tracks']):
        raise ValueError('Le nombre de candidats du bilan est incohérent.')
    if (r['search'].get('parameters') != PARAMETERS
            or r['search'].get('stationary_removal_applied') is not False
            or len(r.get('selections', [])) != 8 or r['selections'][0].get('noise_sigma') != noise):
        raise ValueError('Le profil ou le bruit enregistré est incohérent.')
    watched.update(inputs)
    return r, watched, planes


def generate(baseline_path, output, base=None):
    base = ROOT/'local' if base is None else base
    bp = local_path(baseline_path, base)
    baseline, watched, planes = checked_baseline(bp, base, True)
    output = _new_output(output, base); (output/'planes').mkdir()
    keys = ('source_kind', 'image_shape', 'reduced_shape', 'models', 'relative_declared_seconds',
        'noise_sigma_first_reduced', 'scale_arcsec_per_native_pixel', 'declared_optics', 'exposure_seconds_declared')
    manifest = dict(slow_motion_manifest_version='1.0', status='running', plan_commit=PLAN_COMMIT,
        recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=frozen(), profile_parameters=PARAMETERS.copy(),
        baseline_report=str(bp), baseline_sha256=watched[bp], **{k: baseline[k] for k in keys},
        scale_kind='nominal_declared_optics_not_calibrated', sigma_native=2.2, exposure_samples=7,
        photon_noise_added=False, physical_time_qualified=False,
        conditions=conditions(baseline['scale_arcsec_per_native_pixel']), cases=[], **experiment.provenance())
    mp = output/'manifest.json'; save(mp, manifest); answers = []
    try:
        for spec in [dict(case_id='control'), *manifest['conditions']]:
            control = spec['case_id'] == 'control'
            positions, velocity = (None, None) if control else trajectory(manifest['image_shape'], manifest['relative_declared_seconds'], spec)
            available = control or experiment.covered(positions, manifest['models'], manifest['image_shape'])
            entry = dict(spec, available=bool(available), frames=[], error=None if available else 'outside_common_field_margin_32')
            if available:
                for k, plane in enumerate(planes):
                    if control:
                        derivative = plane.copy()
                    else:
                        model = manifest['models'][k]
                        center = pilot.from_reference(positions[k:k+1], model)[0]
                        source_velocity = velocity@np.asarray(model['rotation_matrix'])
                        derivative = representative.inject(plane, center, source_velocity,
                            manifest['exposure_seconds_declared'][k],
                            spec['peak_sigma']*manifest['noise_sigma_first_reduced'], True)
                    p = output/'planes'/f'{spec["case_id"]}-{k:02d}.npy'
                    item = experiment.write_plane(p, derivative)
                    item['local_plane'] = 'planes/'+item['local_plane']; entry['frames'].append(item)
            manifest['cases'].append(entry); save(mp, manifest)
            if not control:
                answers.append(dict(case_id=spec['case_id'], available=bool(available),
                    positions=[dict(frame_index=k, x=float(p[0]), y=float(p[1])) for k, p in enumerate(positions)],
                    velocity_native_per_declared_second=velocity.tolist()))
        unchanged(watched); _stable_code(manifest)
        manifest.update(status='complete', inputs_unchanged=True); save(mp, manifest)
        save(output/'truth.json', dict(slow_motion_truth_version='1.0', manifest_sha256=digest(mp), cases=answers))
    except Exception as exc:
        manifest.update(status='incomplete', error=str(exc)); save(mp, manifest); raise
    return manifest


def load_manifest(path, base):
    mp = local_path(path, base); manifest = read(mp)
    if (manifest.get('slow_motion_manifest_version') != '1.0' or manifest.get('status') != 'complete'
            or manifest.get('plan_commit') != PLAN_COMMIT or manifest.get('recipe_sha256_lf') != recipe_hash()
            or manifest.get('frozen_sha256_lf') != frozen() or manifest.get('profile_parameters') != PARAMETERS
            or manifest.get('inputs_unchanged') is not True):
        raise ValueError('Un manifeste complet et gelé du profil lent est requis.')
    bp = local_path(manifest['baseline_report'], base)
    if digest(bp) != manifest['baseline_sha256']:
        raise ValueError('Le bilan de départ a changé.')
    baseline, watched, _ = checked_baseline(bp, base)
    expected = {k: baseline[k] for k in ('source_kind', 'image_shape', 'reduced_shape', 'models',
        'relative_declared_seconds', 'noise_sigma_first_reduced', 'scale_arcsec_per_native_pixel',
        'declared_optics', 'exposure_seconds_declared')}
    expected.update(conditions=conditions(baseline['scale_arcsec_per_native_pixel']), sigma_native=2.2,
        exposure_samples=7, photon_noise_added=False, physical_time_qualified=False,
        scale_kind='nominal_declared_optics_not_calibrated')
    if any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError('Les paramètres diffèrent du protocole ou du bilan de départ.')
    specs = [dict(case_id='control'), *manifest['conditions']]
    if [c['case_id'] for c in manifest.get('cases', [])] != [s['case_id'] for s in specs]:
        raise ValueError('Les treize séries ordonnées sont requises.')
    for entry, spec in zip(manifest['cases'], specs):
        positions = None if spec['case_id'] == 'control' else trajectory(manifest['image_shape'], manifest['relative_declared_seconds'], spec)[0]
        available = positions is None or experiment.covered(positions, manifest['models'], manifest['image_shape'])
        if (type(entry.get('available')) is not bool or entry['available'] != available
                or any(entry.get(k) != v for k, v in spec.items())
                or len(entry.get('frames', [])) != (8 if available else 0)
                or entry.get('error') != (None if available else 'outside_common_field_margin_32')):
            raise ValueError('Un cas ou sa disponibilité diffère du protocole.')
    watched[mp] = digest(mp)
    return mp, manifest, watched


def analyze(manifest_path, output, base=None):
    """The search takes no truth file and never refits the registration."""
    base = ROOT/'local' if base is None else base
    mp, manifest, watched = load_manifest(manifest_path, base)
    output = _new_output(output, base); (output/'cases').mkdir()
    result = dict(slow_motion_analysis_version='1.0', status='running', manifest_sha256=watched[mp],
        source_kind=manifest['source_kind'], profile_parameters=PARAMETERS.copy(),
        frozen_sha256_lf=frozen(), recipe_sha256_lf=recipe_hash(), truth_opened=False,
        models_refitted=False, records=[], **experiment.provenance())
    ap = output/'analysis.json'; save(ap, result); masks = None
    try:
        for case in manifest['cases']:
            planes = experiment.load_planes(mp, manifest, case, base, watched, masks)
            if case['case_id'] == 'control':
                masks = [np.isnan(p) for p in planes]
            record = dict(case_id=case['case_id'], search_status='blocked', candidate_count=None, data=None)
            if planes is not None:
                try:
                    record['data'] = process(planes, manifest['models'], manifest['image_shape'],
                        manifest['relative_declared_seconds'], manifest['scale_arcsec_per_native_pixel'])
                    record.update(search_status='complete', candidate_count=len(record['data']['search']['tracks']))
                except ValueError as exc:
                    record['error'] = str(exc)
            else:
                record['error'] = case['error']
            p = output/'cases'/f'{case["case_id"]}.json'; save(p, record)
            result['records'].append(dict(case_id=case['case_id'], file='cases/'+p.name, sha256=digest(p)))
            save(ap, result)
        for item in result['records']:
            if digest(output/item['file']) != item['sha256']:
                raise ValueError('Un candidat gelé a changé pendant la recherche.')
        unchanged(watched); _stable_code(result)
        result.update(status='complete', inputs_unchanged=True,
            all_available=all(read(output/r['file'])['search_status'] == 'complete' for r in result['records']))
        save(ap, result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); save(ap, result); raise
    return result


def sealed_records(path, manifest_hash, base, watched, specs):
    ap = local_path(path, base); result = read(ap)
    if (result.get('slow_motion_analysis_version') != '1.0' or result.get('status') != 'complete'
            or result.get('manifest_sha256') != manifest_hash or result.get('truth_opened') is not False
            or result.get('models_refitted') is not False or result.get('inputs_unchanged') is not True
            or result.get('profile_parameters') != PARAMETERS or result.get('frozen_sha256_lf') != frozen()
            or result.get('recipe_sha256_lf') != recipe_hash()
            or [r['case_id'] for r in result.get('records', [])] != ['control', *[s['case_id'] for s in specs]]):
        raise ValueError('Les treize analyses doivent être gelées avant les réponses.')
    watched[ap] = digest(ap); records = {}
    for item in result['records']:
        p = local_path(ap.parent/item['file'], base)
        if ap.parent not in p.parents or p in watched or digest(p) != item['sha256']:
            raise ValueError('Un candidat est modifié, répété ou hors du lot.')
        record = read(p)
        if record.get('case_id') != item['case_id'] or record.get('search_status') not in ('complete', 'blocked'):
            raise ValueError('Le bilan candidat est incohérent.')
        if record['search_status'] == 'complete':
            if (type(record.get('candidate_count')) is not int
                    or record['candidate_count'] != len(record['data']['search']['tracks'])
                    or record['data']['search']['parameters'] != PARAMETERS
                    or record['data']['search']['stationary_removal_applied'] is not False):
                raise ValueError('Le nombre ou le profil des candidats est incohérent.')
        elif record.get('candidate_count') is not None or record.get('data') is not None:
            raise ValueError('Un refus ne doit pas devenir un nombre nul.')
        watched[p] = digest(p); records[item['case_id']] = record
    if result.get('all_available') != all(r['search_status'] == 'complete' for r in records.values()):
        raise ValueError('Le bilan des séries disponibles est incohérent.')
    return records


def verify_derivatives(mp, manifest, base, watched):
    # Validate serialized bytes AND NaN masks, not just filenames recorded by a report.
    masks = None
    for case in manifest['cases']:
        planes = experiment.load_planes(mp, manifest, case, base, watched, masks)
        if case['case_id'] == 'control':
            masks = [np.isnan(p) for p in planes]


def _answers(tp, manifest, manifest_hash):
    truth = read(tp)
    if (truth.get('slow_motion_truth_version') != '1.0' or truth.get('manifest_sha256') != manifest_hash
            or [r['case_id'] for r in truth.get('cases', [])] != [s['case_id'] for s in manifest['conditions']]):
        raise ValueError('Les douze réponses de cette expérience sont requises.')
    for answer, spec, entry in zip(truth['cases'], manifest['conditions'], manifest['cases'][1:]):
        positions, velocity = trajectory(manifest['image_shape'], manifest['relative_declared_seconds'], spec)
        if (answer.get('available') != entry['available']
                or [p['frame_index'] for p in answer['positions']] != list(range(8))
                or not np.allclose([[p['x'], p['y']] for p in answer['positions']], positions, atol=1e-10, rtol=0)
                or not np.allclose(answer['velocity_native_per_declared_second'], velocity, atol=1e-10, rtol=0)):
            raise ValueError('Une réponse diffère du trajet annoncé avant la recherche.')
    return {r['case_id']: r for r in truth['cases']}


def score_one(record, truth):
    if record['search_status'] != 'complete':
        return dict(available=False, recovered=None, missed=None, unassociated_candidates=None, match=None)
    tracks = record['data']['search']['tracks']
    matches = [m for track in tracks if (m := score_track(track, truth)) is not None] if truth is not None else []
    chosen = min(matches, key=lambda m: (m['rms_native_pixels'], m['candidate_id'])) if matches else None
    recovered = int(chosen is not None) if truth is not None else None
    return dict(available=True, recovered=recovered, missed=1-recovered if recovered is not None else None,
        unassociated_candidates=len(tracks)-int(chosen is not None), match=chosen)


def _score_values(manifest, baseline, records, answers):
    rows = [dict(spec, **score_one(records[spec['case_id']], answers.get(spec['case_id'])))
        for spec in [dict(case_id='control'), *manifest['conditions']]]
    groups = []
    for rate in RATES:
        for peak in PEAKS:
            selected = [r for r in rows[1:] if r['angular_rate_arcsec_hour'] == rate and r['peak_sigma'] == peak]
            groups.append(dict(family='angular', angular_rate_arcsec_hour=rate, peak_sigma=peak, planned=2,
                available=sum(r['available'] for r in selected), recovered=sum(r['recovered'] or 0 for r in selected),
                missed=sum(r['missed'] or 0 for r in selected), unavailable=sum(not r['available'] for r in selected),
                unassociated_candidates=sum(r['unassociated_candidates'] or 0 for r in selected) if any(r['available'] for r in selected) else None))
    control = records['control']
    identical = control['search_status'] == 'complete' and all(control['data'][key] == baseline[key]
        for key in ('raw_detections', 'mapped_detections', 'overlap_excluded_per_frame', 'search'))
    bright = [r for r in rows[1:] if r['peak_sigma'] == 12]
    synthetic = manifest['source_kind'] == 'synthetic_demo'
    fixture = bool(identical and control['candidate_count'] == 0
        and all(r['available'] and r['recovered'] == 1 for r in bright)) if synthetic else None
    available = sum(r['available'] for r in rows[1:])
    recovered = sum(r['recovered'] or 0 for r in rows[1:])
    unassociated = sum(r['unassociated_candidates'] or 0 for r in rows[1:]) if available else None
    return dict(rows=rows, groups=groups, planned_injections=12, available_injections=available,
        recovered=recovered, missed=sum(r['missed'] or 0 for r in rows[1:]), unavailable=12-available,
        unassociated_candidates=unassociated, control_candidates=control['candidate_count'],
        control_identical_to_baseline=identical, bright_recovered=sum(r['recovered'] or 0 for r in bright),
        bright_available=sum(r['available'] for r in bright), slow_recovered=recovered, slow_available=available,
        slow_domain_covered=True, science_fitness_passed=False, synthetic_fixture_criteria_passed=fixture,
        false_candidates=(unassociated+(control['candidate_count'] or 0)) if synthetic and all(r['available'] for r in rows) else None,
        nominal_angular_domain_arcsec_hour=[5., 120.],
        scale_arcsec_per_native_pixel=manifest['scale_arcsec_per_native_pixel'],
        source_kind=manifest['source_kind'], descriptive_only=True, clock_qualified=False,
        real_data_performance_validated=False, known_natural_positive_tested=False,
        conditional_on_frozen_registration=True)


def _score_inputs(manifest_path, truth_path, analysis_path, base):
    mp, manifest, watched = load_manifest(manifest_path, base)
    tp, ap = [local_path(p, base) for p in (truth_path, analysis_path)]
    # Validate every candidate and derivative before opening the truth file.
    records = sealed_records(ap, watched[mp], base, watched, manifest['conditions'])
    verify_derivatives(mp, manifest, base, watched)
    watched[tp] = digest(tp); answers = _answers(tp, manifest, watched[mp])
    baseline = read(local_path(manifest['baseline_report'], base))
    values = _score_values(manifest, baseline, records, answers)
    return mp, tp, ap, manifest, watched, values, records, answers


def score(manifest_path, truth_path, analysis_path, output, base=None):
    base = ROOT/'local' if base is None else base
    mp, tp, ap, manifest, watched, values, _, _ = _score_inputs(manifest_path, truth_path, analysis_path, base)
    output = _new_output(output, base)
    result = dict(slow_motion_score_version='1.0', status='running', plan_commit=PLAN_COMMIT,
        recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=frozen(), profile_parameters=PARAMETERS.copy(),
        manifest_path=str(mp), manifest_sha256=watched[mp], truth_path=str(tp), truth_sha256=watched[tp],
        analysis_path=str(ap), analysis_sha256=watched[ap], **values, **experiment.provenance())
    sp = output/'score.json'; save(sp, result)
    try:
        with (output/'recovery.csv').open('x', encoding='utf-8-sig', newline='') as stream:
            fields = ['case_id', 'angular_rate_arcsec_hour', 'peak_sigma', 'available', 'recovered', 'missed', 'unassociated_candidates']
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            writer.writerows({k: r.get(k) for k in fields} for r in result['rows'])
        text = '# Mobiles lents : bilan local\n\n'
        text += f"Ajouts retrouvés : {result['recovered']}/12. Indisponibles : {result['unavailable']}.\n\n"
        text += 'Une réponse ajoutée est connue. Un candidat naturel reste inconnu. Les heures et l’échelle ne sont pas qualifiées.\n\n'
        text += '| Vitesse déclarée (secondes d’arc/heure) | Pic/bruit initial | Retrouvés | Disponibles |\n|---|---|---|---|\n'
        for group in result['groups']:
            text += f"| {group['angular_rate_arcsec_hour']:g} | {group['peak_sigma']} | {group['recovered']} | {group['available']} |\n"
        (output/'README.md').write_text(text, encoding='utf-8')
        unchanged(watched); _stable_code(result)
        result.update(status='complete', inputs_unchanged=True); save(sp, result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); save(sp, result); raise
    return result


def checked_score(path, base=None):
    """Check an existing score for figures; no detection or association is run."""
    base = ROOT/'local' if base is None else base
    sp = local_path(path, base); result = read(sp); score_hash = digest(sp)
    if (result.get('slow_motion_score_version') != '1.0' or result.get('status') != 'complete'
            or result.get('plan_commit') != PLAN_COMMIT or result.get('recipe_sha256_lf') != recipe_hash()
            or result.get('frozen_sha256_lf') != frozen() or result.get('profile_parameters') != PARAMETERS
            or result.get('inputs_unchanged') is not True):
        raise ValueError('Un score complet et gelé du profil lent est requis.')
    mp, tp, ap, manifest, watched, values, records, answers = _score_inputs(result['manifest_path'], result['truth_path'], result['analysis_path'], base)
    if (any(result.get(k) != v for k, v in values.items())
            or any(result[key] != watched[p] for key, p in
                [('manifest_sha256', mp), ('truth_sha256', tp), ('analysis_sha256', ap)])):
        raise ValueError('Le score diffère de ses preuves gelées.')
    watched[sp] = score_hash; unchanged(watched)
    return sp, result, mp, manifest, records, answers, watched


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    for name, fields in [('prepare', ('workset',)), ('generate', ('baseline',)),
                         ('analyze', ('manifest',)), ('score', ('manifest', 'truth', 'analysis'))]:
        subparser = subparsers.add_parser(name)
        for field in (*fields, 'output'):
            subparser.add_argument(field, type=Path)
    args = parser.parse_args()
    try:
        fields = {'prepare': ('workset',), 'generate': ('baseline',), 'analyze': ('manifest',), 'score': ('manifest', 'truth', 'analysis')}[args.command]
        result = globals()[args.command](*[getattr(args, f) for f in fields], args.output)
        unavailable = (args.command == 'prepare' and result['search_status'] != 'complete'
            or args.command == 'analyze' and not result['all_available']
            or args.command == 'score' and (result['unavailable'] > 0 or result['synthetic_fixture_criteria_passed'] is False))
        print(f"Profil lent : {args.command} terminé. Les résultats restent expérimentaux.", flush=True)
        raise SystemExit(2 if unavailable else 0)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
