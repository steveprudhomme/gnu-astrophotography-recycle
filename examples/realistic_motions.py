# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Conditional representative-motion experiment; generation, blind search, score."""
import argparse
import csv
from hashlib import sha256
from pathlib import Path

from astropy.io import fits
import numpy as np
from gar.astrometry import local_path
from gar.workset import digest
import injection_recovery as experiment
import run_seestar_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = '082e1623b6881eebb4c6903dd24f9964643c80ff'
INJECTION_HASH = '7f0ed216d7822180f88e2f761ffe95968805946f9771cc8b03effa8c8d842b94'
RATES = (10., 30., 60., 900.)
PEAKS = (6, 12)
STARTS = ((.35, .35, 30.), (.65, .65, 150.))
SIGMA_NATIVE = 2.2
EXPOSURE_SAMPLES = 7
save, read, unchanged = experiment.save, experiment.read, experiment.unchanged
load_planes = experiment.load_planes


def recipe_hash():
    return sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()


def frozen():
    if experiment.recipe_hash() != INJECTION_HASH:
        raise ValueError('Recette historique modifiée : nouveau protocole requis.')
    return dict(experiment.frozen(), **{'examples/injection_recovery.py': INJECTION_HASH})


def scale_from_headers(headers):
    """Nominal geometry only, not a measured plate-scale or qualified clock."""
    if len(headers) != 8:
        raise ValueError('Huit en-têtes d’optique déclarée requis.')
    values = []
    for header in headers:
        row = [header.get(k) for k in ('XPIXSZ', 'YPIXSZ', 'FOCALLEN')]
        if any(type(v) not in (int, float) or not np.isfinite(v) or v <= 0 for v in row):
            raise ValueError('Tailles de pixel et focale déclarées positives requises.')
        if not np.isclose(row[0], row[1], rtol=1e-6, atol=0):
            raise ValueError('Pixels déclarés carrés requis.')
        values.append(row)
    if not np.allclose(values, values[0], rtol=1e-6, atol=0):
        raise ValueError('Optique déclarée différente entre copies.')
    return float(206264.806247*(values[0][0]/1000)/values[0][2])


def conditions(scale):
    if type(scale) not in (int, float) or not np.isfinite(scale) or scale <= 0:
        raise ValueError('Échelle nominale positive requise.')
    rows = []
    for rate in RATES:
        for peak in PEAKS:
            for position in range(2):
                speed = rate/(3600*scale)
                rows.append(dict(case_id=f'r{rate:g}-a{peak}-p{position+1}', family='angular',
                    angular_rate_arcsec_hour=rate, peak_sigma=peak, position_index=position,
                    speed_native_per_declared_second=speed, in_speed_domain=bool(.1 <= speed <= 1.5),
                    smear_samples=EXPOSURE_SAMPLES))
    for position in range(2):
        rows.append(dict(case_id=f'technical-p{position+1}', family='technical_positive',
            angular_rate_arcsec_hour=None, peak_sigma=12, position_index=position,
            speed_native_per_declared_second=.5, in_speed_domain=True, smear_samples=1))
    return rows


def trajectory(shape, times, spec):
    h, w = shape; fx, fy, angle = STARTS[spec['position_index']]
    velocity = spec['speed_native_per_declared_second']*np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
    return np.array([fx*w, fy*h])+np.asarray(times)[:, None]*velocity, velocity


def inject(plane, source_center, velocity_source, exptime, peak, smear=True):
    """Seven equal-flux samples; native motion and reduced sampling stay distinct.

    The sampled truncated kernel is normalized to its nominal continuous flux
    before averaging. Masked pixels retain their original mask, so flux landing
    there is not usable. No photon noise, Bayer response, or calibrated flux.
    """
    if (type(exptime) not in (int, float) or not np.isfinite(exptime) or exptime <= 0
            or type(peak) not in (int, float) or not np.isfinite(peak) or peak <= 0):
        raise ValueError('Exposition et amplitude de modèle positives requises.')
    source_center = np.asarray(source_center, dtype=float); velocity_source = np.asarray(velocity_source, dtype=float)
    if source_center.shape != (2,) or velocity_source.shape != (2,) or not np.isfinite([source_center, velocity_source]).all():
        raise ValueError('Centre et vitesse natifs finis requis.')
    result = np.array(plane, dtype='float32', copy=True)
    if result.ndim != 2:
        raise ValueError('Plan réduit 2D requis.')
    offsets = np.linspace(-exptime/2, exptime/2, EXPOSURE_SAMPLES) if smear else np.array([0.])
    centers = (source_center+offsets[:, None]*velocity_source-.5)/2
    radius = 5*SIGMA_NATIVE/2
    lo = np.floor(centers.min(axis=0)-radius).astype(int)
    hi = np.ceil(centers.max(axis=0)+radius).astype(int)+1
    if np.any(lo < 0) or np.any(hi > [result.shape[1], result.shape[0]]):
        raise ValueError('Support complet de la traînée hors du plan.')
    yy, xx = np.mgrid[lo[1]:hi[1], lo[0]:hi[0]]
    addition = np.zeros(xx.shape, dtype=float)
    target_flux = peak*2*np.pi*(SIGMA_NATIVE/2)**2*(1-np.exp(-12.5))
    for center in centers:
        radius2 = (xx-center[0])**2+(yy-center[1])**2
        kernel = np.where(radius2 <= radius**2, np.exp(-radius2/(2*(SIGMA_NATIVE/2)**2)), 0.)
        addition += kernel*(target_flux/kernel.sum())/len(centers)
    result[lo[1]:hi[1], lo[0]:hi[0]] += addition.astype('float32')
    return result


def checked_baseline(path, base, pixels=False):
    report, watched, planes = experiment.checked_pilot(path, base, load_planes=pixels)
    headers, exposures = [], []
    for copy in report['copies']:
        p = local_path(copy['local_copy'], base)
        with fits.open(p, mode='readonly', memmap=False) as hdus:
            header = hdus[0].header
            headers.append({key: header.get(key) for key in ('XPIXSZ', 'YPIXSZ', 'FOCALLEN')})
            exposure = header.get('EXPTIME')
            if type(exposure) not in (int, float) or not np.isfinite(exposure) or exposure <= 0 or exposure > 120:
                raise ValueError('Exposition déclarée positive et ≤120 secondes requise.')
            exposures.append(float(exposure))
    scale = scale_from_headers(headers)
    unchanged(watched)
    return report, watched, planes, scale, exposures, headers


def generate(pilot_path, output, base=None):
    base = ROOT/'local' if base is None else base
    rp, output = [local_path(p, base) for p in (pilot_path, output)]
    frozen(); report, watched, planes, scale, exposures, optics = checked_baseline(rp, base, True)
    output.mkdir(parents=True, exist_ok=False); (output/'planes').mkdir()
    manifest = dict(realistic_motion_manifest_version='1.0', status='running', plan_commit=PLAN_COMMIT,
        recipe_sha256_lf=recipe_hash(), frozen_sha256_lf=frozen(), baseline_report=str(rp), baseline_sha256=watched[rp],
        source_kind=report['input_kind'], image_shape=report['image_shape'], reduced_shape=list(planes[0].shape),
        models=report['models'], relative_declared_seconds=report['relative_declared_seconds'],
        noise_sigma_first_reduced=report['motion_selection'][0]['noise_sigma'],
        scale_arcsec_per_native_pixel=scale, scale_kind='nominal_declared_optics_not_calibrated',
        declared_optics=optics, exposure_seconds_declared=exposures, sigma_native=SIGMA_NATIVE,
        exposure_samples=EXPOSURE_SAMPLES, conditions=conditions(scale), cases=[],
        photon_noise_added=False, physical_time_qualified=False, **experiment.provenance())
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
                        center = pilot.from_reference(positions[k:k+1], manifest['models'][k])[0]
                        rotation = np.asarray(manifest['models'][k]['rotation_matrix'])
                        source_velocity = velocity@rotation
                        derivative = inject(plane, center, source_velocity, exposures[k],
                            spec['peak_sigma']*manifest['noise_sigma_first_reduced'], spec['smear_samples'] == 7)
                    p = output/'planes'/f'{spec["case_id"]}-{k:02d}.npy'
                    item = experiment.write_plane(p, derivative); item['local_plane'] = 'planes/'+item['local_plane']; entry['frames'].append(item)
            manifest['cases'].append(entry); save(mp, manifest)
            if not control:
                answers.append(dict(case_id=spec['case_id'], available=bool(available),
                    positions=[dict(frame_index=k, x=float(p[0]), y=float(p[1])) for k, p in enumerate(positions)],
                    velocity_native_per_declared_second=velocity.tolist()))
        unchanged(watched); frozen(); manifest.update(status='complete', inputs_unchanged=True); save(mp, manifest)
        save(output/'truth.json', dict(realistic_motion_truth_version='1.0', manifest_sha256=digest(mp), cases=answers))
    except Exception as exc:
        manifest.update(status='incomplete', error=str(exc)); save(mp, manifest); raise
    print('19 séries préparées : témoin, 16 mouvements angulaires et deux contrôles techniques.', flush=True)
    return manifest


def load_manifest(path, base):
    mp = local_path(path, base); manifest = read(mp); frozen()
    if (manifest.get('realistic_motion_manifest_version') != '1.0' or manifest.get('status') != 'complete'
            or manifest.get('plan_commit') != PLAN_COMMIT or manifest.get('recipe_sha256_lf') != recipe_hash()
            or manifest.get('frozen_sha256_lf') != frozen() or manifest.get('inputs_unchanged') is not True):
        raise ValueError('Manifeste réaliste complet de ce protocole requis.')
    rp = local_path(manifest['baseline_report'], base)
    if digest(rp) != manifest['baseline_sha256']:
        raise ValueError('Pilote lié modifié.')
    report, watched, _, scale, exposures, optics = checked_baseline(rp, base)
    specs = conditions(scale)
    expected = dict(image_shape=report['image_shape'], models=report['models'], source_kind=report['input_kind'],
        relative_declared_seconds=report['relative_declared_seconds'], scale_arcsec_per_native_pixel=scale,
        exposure_seconds_declared=exposures, declared_optics=optics, reduced_shape=[v//2 for v in report['image_shape']],
        noise_sigma_first_reduced=report['motion_selection'][0]['noise_sigma'], sigma_native=SIGMA_NATIVE,
        exposure_samples=EXPOSURE_SAMPLES, conditions=specs, photon_noise_added=False, physical_time_qualified=False,
        scale_kind='nominal_declared_optics_not_calibrated')
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError('Paramètres différents du pilote ou du protocole.')
    all_specs = [dict(case_id='control'), *specs]
    if [c['case_id'] for c in manifest['cases']] != [s['case_id'] for s in all_specs]:
        raise ValueError('Dix-neuf cas distincts et ordonnés requis.')
    for entry, spec in zip(manifest['cases'], all_specs):
        positions = None if spec['case_id'] == 'control' else trajectory(manifest['image_shape'], manifest['relative_declared_seconds'], spec)[0]
        available = positions is None or experiment.covered(positions, manifest['models'], manifest['image_shape'])
        if (type(entry.get('available')) is not bool or entry['available'] != available
                or any(entry.get(k) != v for k, v in spec.items())
                or len(entry.get('frames', [])) != (8 if available else 0)):
            raise ValueError('Cas ou disponibilité différents du protocole.')
    watched[mp] = digest(mp)
    return mp, manifest, watched


def analyze(manifest_path, output, base=None):
    base = ROOT/'local' if base is None else base
    mp, manifest, watched = load_manifest(manifest_path, base); output = local_path(output, base)
    output.mkdir(parents=True, exist_ok=False); (output/'cases').mkdir()
    result = dict(realistic_motion_analysis_version='1.0', status='running', manifest_sha256=watched[mp],
        source_kind=manifest['source_kind'], truth_opened=False, models_refitted=False, records=[], **experiment.provenance())
    ap = output/'analysis.json'; save(ap, result); masks = None
    try:
        for index, case in enumerate(manifest['cases']):
            planes = experiment.load_planes(mp, manifest, case, base, watched, masks)
            if index == 0:
                if planes is None: raise ValueError('Témoin disponible requis.')
                masks = [np.isnan(p) for p in planes]
            record = dict(case_id=case['case_id'], search_status='blocked', candidate_count=None, data=None)
            if planes is not None:
                try:
                    record['data'] = experiment.process(planes, manifest['models'], manifest['image_shape'], manifest['relative_declared_seconds'])
                    record.update(search_status='complete', candidate_count=len(record['data']['search']['tracks']))
                except ValueError as exc:
                    record['error'] = str(exc)
            else:
                record['error'] = case['error']
            p = output/'cases'/f'{case["case_id"]}.json'; save(p, record)
            result['records'].append(dict(case_id=case['case_id'], file='cases/'+p.name, sha256=digest(p))); save(ap, result)
            print(f'Analyse gelée {index+1}/19 : {record["search_status"]}.', flush=True)
        if any(digest(output/item['file']) != item['sha256'] for item in result['records']):
            raise ValueError('Un candidat gelé a changé pendant l’analyse.')
        unchanged(watched); frozen(); result.update(status='complete', inputs_unchanged=True,
            all_available=all(read(output/r['file'])['search_status'] == 'complete' for r in result['records']))
        save(ap, result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); save(ap, result); raise
    return result


def sealed_records(path, manifest_hash, base, watched, specs):
    ap = local_path(path, base); result = read(ap)
    if (result.get('realistic_motion_analysis_version') != '1.0' or result.get('status') != 'complete'
            or result.get('manifest_sha256') != manifest_hash or result.get('truth_opened') is not False
            or result.get('models_refitted') is not False or result.get('inputs_unchanged') is not True
            or [r['case_id'] for r in result.get('records', [])] != ['control', *[s['case_id'] for s in specs]]):
        raise ValueError('Dix-neuf analyses complètes gelées avant réponses requises.')
    watched[ap] = digest(ap); records = {}
    for item in result['records']:
        p = local_path(ap.parent/item['file'], base)
        if ap.parent not in p.parents or p in watched or digest(p) != item['sha256']:
            raise ValueError('Candidat modifié, répété ou hors du lot.')
        record = read(p)
        if record.get('case_id') != item['case_id'] or record.get('search_status') not in ('complete', 'blocked'):
            raise ValueError('Résultat candidat incohérent.')
        if record['search_status'] == 'complete':
            if record['candidate_count'] != len(record['data']['search']['tracks']): raise ValueError('Effectif candidat incohérent.')
        elif record['candidate_count'] is not None or record['data'] is not None:
            raise ValueError('Un refus ne doit pas devenir zéro.')
        watched[p] = digest(p); records[item['case_id']] = record
    return records


def verify_derivatives(mp, manifest, base, watched):
    experiment.verify_derivatives(mp, manifest, base, watched)


def score(manifest_path, truth_path, analysis_path, output, base=None):
    base = ROOT/'local' if base is None else base
    mp, manifest, watched = load_manifest(manifest_path, base)
    tp, ap, output = [local_path(p, base) for p in (truth_path, analysis_path, output)]
    records = sealed_records(ap, watched[mp], base, watched, manifest['conditions'])
    verify_derivatives(mp, manifest, base, watched)
    watched[tp] = digest(tp); truth = read(tp)
    if (truth.get('realistic_motion_truth_version') != '1.0' or truth.get('manifest_sha256') != watched[mp]
            or [r['case_id'] for r in truth.get('cases', [])] != [s['case_id'] for s in manifest['conditions']]):
        raise ValueError('Réponses complètes du même protocole requises.')
    answers = {r['case_id']: r for r in truth['cases']}
    for spec, entry in zip(manifest['conditions'], manifest['cases'][1:]):
        answer = answers[spec['case_id']]; positions, velocity = trajectory(manifest['image_shape'], manifest['relative_declared_seconds'], spec)
        if (answer.get('available') != entry['available'] or [p['frame_index'] for p in answer['positions']] != list(range(8))
                or not np.allclose([[p['x'], p['y']] for p in answer['positions']], positions, atol=1e-10, rtol=0)
                or not np.allclose(answer['velocity_native_per_declared_second'], velocity, atol=1e-10, rtol=0)):
            raise ValueError('Réponses différentes des trajets préenregistrés.')
    output.mkdir(parents=True, exist_ok=False)
    rows = [dict(spec, **experiment.score_one(records[spec['case_id']], answers.get(spec['case_id'])))
        for spec in [dict(case_id='control'), *manifest['conditions']]]
    groups = []
    for rate, peak in [(r, a) for r in RATES for a in PEAKS]+[(None, 12)]:
        selected = [r for r in rows[1:] if r['angular_rate_arcsec_hour'] == rate and r['peak_sigma'] == peak]
        groups.append(dict(family='angular' if rate is not None else 'technical_positive', angular_rate_arcsec_hour=rate,
            peak_sigma=peak, planned=2, available=sum(r['available'] for r in selected), recovered=sum(r['recovered'] or 0 for r in selected),
            missed=sum(r['missed'] or 0 for r in selected), unavailable=sum(not r['available'] for r in selected),
            unassociated_candidates=sum(r['unassociated_candidates'] or 0 for r in selected) if any(r['available'] for r in selected) else None))
    baseline = read(local_path(manifest['baseline_report'], base)); control = records['control']
    identical = control['search_status'] == 'complete' and all(control['data'][key] == baseline[key]
        for key in ('raw_detections', 'mapped_detections', 'overlap_excluded_per_frame', 'search'))
    tech = [r for r in rows[1:] if r['family'] == 'technical_positive']
    slow = [r for r in rows[1:] if r['family'] == 'angular' and r['angular_rate_arcsec_hour'] in (10, 30, 60)]
    synthetic = manifest['source_kind'] == 'synthetic_demo'
    fixture = bool(identical and control['candidate_count'] == 0 and all(r['available'] and r['recovered'] == 1 for r in tech)
        and all(r['available'] and r['recovered'] == 0 for r in slow)) if synthetic else None
    result = dict(realistic_motion_score_version='1.0', status='running', plan_commit=PLAN_COMMIT,
        manifest_path=str(mp), manifest_sha256=watched[mp], truth_path=str(tp), truth_sha256=watched[tp],
        analysis_path=str(ap), analysis_sha256=watched[ap], source_kind=manifest['source_kind'], rows=rows, groups=groups,
        scale_arcsec_per_native_pixel=manifest['scale_arcsec_per_native_pixel'],
        engine_angular_domain_arcsec_hour=[v*manifest['scale_arcsec_per_native_pixel']*3600 for v in (.1, 1.5)],
        planned_injections=18, recovered=sum(g['recovered'] for g in groups), missed=sum(g['missed'] for g in groups),
        unavailable=sum(g['unavailable'] for g in groups), available_injections=sum(g['available'] for g in groups),
        unassociated_candidates=sum(g['unassociated_candidates'] or 0 for g in groups) if any(r['available'] for r in rows[1:]) else None,
        control_candidates=control['candidate_count'], control_identical_to_baseline=identical,
        technical_recovered=sum(r['recovered'] or 0 for r in tech), technical_available=sum(r['available'] for r in tech),
        slow_recovered=sum(r['recovered'] or 0 for r in slow), slow_available=sum(r['available'] for r in slow),
        slow_domain_covered=all(r['in_speed_domain'] for r in slow), science_fitness_passed=False,
        synthetic_fixture_criteria_passed=fixture,
        false_candidates=sum(g['unassociated_candidates'] or 0 for g in groups)+(control['candidate_count'] or 0) if synthetic and all(r['available'] for r in rows) else None,
        descriptive_only=True, clock_qualified=False, real_data_performance_validated=False,
        known_natural_positive_tested=False, conditional_on_frozen_registration=True, **experiment.provenance())
    save(output/'score.json', result)
    try:
        with (output/'recovery.csv').open('w', encoding='utf-8-sig', newline='') as stream:
            fields = ['case_id', 'family', 'angular_rate_arcsec_hour', 'peak_sigma', 'in_speed_domain', 'available', 'recovered', 'missed', 'unassociated_candidates']
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows({k: r.get(k) for k in fields} for r in rows)
        text = '# Récupération représentative — rapport local\n\n'
        text += f"Ajouts retrouvés : {result['recovered']}/18 ; manqués : {result['missed']} ; indisponibles : {result['unavailable']}.\n\n"
        text += 'Les mouvements lents visés ne sont pas couverts par les bornes du moteur. Aptitude scientifique non validée ; les contrôles techniques ne sont pas des objets naturels.\n\n'
        text += '| Type | Mouvement angulaire déclaré | Pic/sigma initial | Retrouvés | Disponibles |\n|---|---|---|---|---|\n'
        for g in groups: text += f"| {g['family']} | {g['angular_rate_arcsec_hour']} | {g['peak_sigma']} | {g['recovered']} | {g['available']}/2 |\n"
        text += '\nÉchelle nominale et temps déclarés non qualifiés, modèle de traînée sans bruit de photons ou Bayer calibré. Sur fond réel, les candidats non associés ne sont pas des faux positifs établis. Aucun objet naturel connu utilisé comme contrôle positif.\n'
        (output/'report.md').write_text(text, encoding='utf-8')
        unchanged(watched); frozen(); result.update(status='complete', inputs_unchanged=True); save(output/'score.json', result)
    except Exception as exc:
        result.update(status='incomplete', error=str(exc)); save(output/'score.json', result); raise
    print(f"Bilan : {result['recovered']}/18 ajouts retrouvés ; domaine lent couvert : {result['slow_domain_covered']}. Aptitude scientifique non validée.", flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    generate_parser = sub.add_parser('generate'); generate_parser.add_argument('pilot', type=Path); generate_parser.add_argument('output', type=Path)
    analyze_parser = sub.add_parser('analyze'); analyze_parser.add_argument('manifest', type=Path); analyze_parser.add_argument('output', type=Path)
    score_parser = sub.add_parser('score')
    for name in ('manifest', 'truth', 'analysis', 'output'): score_parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'generate': generate(args.pilot, args.output); code = 0
        elif args.command == 'analyze': code = 0 if analyze(args.manifest, args.output)['all_available'] else 2
        else:
            result = score(args.manifest, args.truth, args.analysis, args.output)
            code = 2 if result['unavailable'] or result['synthetic_fixture_criteria_passed'] is False else 0
        raise SystemExit(code)
    except (ValueError, OSError, KeyError, TypeError, EOFError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
