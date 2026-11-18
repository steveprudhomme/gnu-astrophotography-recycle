# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Describe frozen slow-motion measurements; never search or replace candidates."""
import argparse
import csv
from hashlib import sha256
from pathlib import Path

import numpy as np
from gar.astrometry import local_path
from gar.slow_moving import PARAMETERS, fit_track
from gar.workset import digest
import slow_motion_profile as slow
import run_seestar_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]
PLAN_COMMIT = '13ded75ad3f0020316a230647e2c12dfeb655ff8'
FROZEN = {
    'examples/make_slow_motion_demo.py': '6146793c792554b9fd01f5fa763b61d9c22464c60b067193fa6f4d62756ee3cd',
    'examples/slow_motion_profile.py': 'fd642779d51eb3f37fa4160b2a68b98d45673571803a2b2d731077449404591d',
    'src/gar/slow_moving.py': '3882a2ded3a4faaa02f553520779c48a6301c3bef8e620ed49d2a01a15944846',
}
RADII = (1.5, 3.)
ROTATION_LIMIT = .05
SPATIAL_RMS_LIMIT = .75
SPATIAL_MAX_LIMIT = 1.5


def source_hash(path):
    return sha256(Path(path).read_text(encoding='utf-8').encode()).hexdigest()


def historical():
    for name, expected in FROZEN.items():
        if source_hash(ROOT/name) != expected:
            raise ValueError('Une source gelée du lot 23 a changé.')
    return dict(slow.frozen(), **FROZEN)


def rotation_audit(baseline):
    """Independent known-fabrication check; never supplies a replacement model."""
    if baseline.get('source_kind') != 'synthetic_demo':
        return dict(applicable=False, reason='No known fabrication for real copies', passed=None, frames=[])
    if (baseline.get('image_shape') != [512, 512]
            or baseline.get('relative_declared_seconds') != [float(k*300) for k in range(8)]
            or len(baseline.get('models', [])) != 8):
        raise ValueError('La fabrication fictive 512², huit poses de 300 s, est requise.')
    controls = np.array([(x, y) for y in (64., 256., 448.) for x in (64., 256., 448.)])
    center = np.array([255.5, 255.5]); rows = []
    for k, model in enumerate(baseline['models']):
        row = dict(frame_index=k, registration_accepted=model.get('model_usable') is True,
                   geometry_control_passed=False, rotation_error_degrees=None,
                   spatial_rms_native_pixels=None, spatial_max_native_pixels=None)
        if row['registration_accepted']:
            angle = np.deg2rad(.5*k/7)
            forward = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
            translation = center-forward@center+[3.5*k/7, 0.]
            expected = (controls-translation)@forward
            observed = pilot.to_reference(controls, model)
            errors = np.linalg.norm(observed-expected, axis=1)
            rotation = np.asarray(model['rotation_matrix'], dtype=float)
            if not np.isfinite(observed).all() or rotation.shape != (2, 2):
                raise ValueError('Un modèle fini à deux dimensions est requis.')
            measured = float(np.rad2deg(np.arctan2(rotation[1, 0], rotation[0, 0])))
            angle_error = float((measured+.5*k/7+180)%360-180)
            rms, maximum = float(np.sqrt(np.mean(errors**2))), float(errors.max())
            row.update(measured_rotation_degrees=measured, expected_inverse_rotation_degrees=-.5*k/7,
                       rotation_error_degrees=angle_error, control_errors_native_pixels=errors.tolist(),
                       spatial_rms_native_pixels=rms, spatial_max_native_pixels=maximum,
                       geometry_control_passed=bool(abs(angle_error) <= ROTATION_LIMIT
                           and rms <= SPATIAL_RMS_LIMIT and maximum <= SPATIAL_MAX_LIMIT))
        rows.append(row)
    return dict(applicable=True, known_fabrication_only=True, models_replaced=False,
                passed=all(r['geometry_control_passed'] for r in rows), frames=rows,
                control_source_positions_native=controls.tolist(), rotation_limit_degrees=ROTATION_LIMIT,
                spatial_rms_limit_native_pixels=SPATIAL_RMS_LIMIT, spatial_max_limit_native_pixels=SPATIAL_MAX_LIMIT)


def nearby(points, expected, radius):
    points = np.asarray(points, dtype=float).reshape(-1, 2)
    if not np.isfinite(points).all() or not np.isfinite(expected).all():
        raise ValueError('Des coordonnées finies sont requises.')
    if not len(points):
        return dict(distance=None, index=None, within_radius=False, neighbours_in_radius=0)
    distances = np.linalg.norm(points-expected, axis=1)
    index = int(np.argmin(distances))
    return dict(distance=float(distances[index]), index=index, within_radius=bool(distances[index] <= radius),
                neighbours_in_radius=int((distances <= radius).sum()))


def support(frames, times, key):
    ids = [r['frame_index'] for r in frames if r[key]['within_radius']]
    span = float(times[ids[-1]]-times[ids[0]]) if len(ids) > 1 else 0.
    return dict(frame_indices=ids, frames=len(ids), span_declared_seconds=span,
                sufficient=bool(len(ids) >= 6 and span >= 1800))


def descriptive_fit(points, times, scale):
    if len(points) < 6:
        return None
    epoch, coefficients, residual = fit_track(points, times)
    linear_sse = float(np.sum(residual**2))
    fixed_sse = float(np.sum((points-np.mean(points, axis=0))**2))
    variance = max(.25**2, linear_sse/(2*len(points)-4))
    span = float(times[-1]-times[0]); speed = float(np.linalg.norm(coefficients[1]))
    rms = float(np.sqrt(np.mean(residual**2))); p95 = float(np.percentile(residual, 95))
    improvement = (fixed_sse-linear_sse)/variance
    gates = dict(minimum_frames=len(points) >= 6, minimum_span=span >= 1800,
                 nominal_speed=bool(5 <= speed*scale*3600 <= 120), displacement=span*speed >= 1.5,
                 rms=rms <= .75, p95=p95 <= 1.5, fixed_linear_improvement=improvement >= 25)
    return dict(epoch_relative_seconds=epoch, velocity_native_per_declared_second=coefficients[1].tolist(),
                rms_native_pixels=rms, p95_native_pixels=p95, displacement_native_pixels=span*speed,
                angular_rate_nominal_arcsec_hour=speed*scale*3600, fixed_linear_improvement=improvement,
                gates=gates, failed_gates=[name for name, passed in gates.items() if not passed],
                truth_guided_after_search=True, candidate=False)


def build(score_path, base):
    engines = historical()
    sp, score, mp, manifest, records, answers, watched = slow.checked_score(score_path, base)
    baseline = slow.read(local_path(manifest['baseline_report'], base))
    audit = rotation_audit(baseline)
    rows = []; times = np.asarray(manifest['relative_declared_seconds'])
    for scored in score['rows'][1:]:
        if scored['peak_sigma'] != 12:
            continue
        cid = scored['case_id']; record = records[cid]
        row = dict(case_id=cid, originally_recovered=scored['recovered'], available=scored['available'],
                   status='unavailable', radii=[])
        if not scored['available']:
            rows.append(row); continue
        raw = [np.asarray(p, dtype=float).reshape(-1, 2) for p in record['data']['raw_detections']]
        mapped = [np.asarray(p, dtype=float).reshape(-1, 2) for p in record['data']['mapped_detections']]
        actual, excluded = pilot.common_points(raw, manifest['models'], manifest['image_shape'])
        if (len(raw) != 8 or len(mapped) != 8
                or excluded != record['data']['overlap_excluded_per_frame']
                or any(a.shape != b.shape or not np.allclose(a, b, atol=1e-10, rtol=0) for a, b in zip(actual, mapped))):
            raise ValueError('Les positions recalées diffèrent des mesures et modèles gelés.')
        for radius in RADII:
            frames = []
            for k, point in enumerate(answers[cid]['positions']):
                reference = np.array([point['x'], point['y']])
                native = pilot.from_reference(reference[None, :], manifest['models'][k])[0]
                frames.append(dict(frame_index=k, raw=nearby(raw[k], native, radius),
                                   mapped=nearby(mapped[k], reference, radius)))
            raw_support, mapped_support = [support(frames, times, key) for key in ('raw', 'mapped')]
            ids = mapped_support['frame_indices']
            points = np.array([mapped[k][frames[k]['mapped']['index']] for k in ids]).reshape(-1, 2)
            fit = descriptive_fit(points, times[ids], manifest['scale_arcsec_per_native_pixel'])
            if scored['recovered'] == 1:
                verdict = 'recovered_context'
            elif not raw_support['sufficient']:
                verdict = 'raw_support_insufficient'
            elif not mapped_support['sufficient']:
                verdict = 'common_field_support_insufficient'
            elif fit and fit['failed_gates']:
                verdict = 'descriptive_fit_rejected'
            else:
                verdict = 'association_unexplained'
            row['radii'].append(dict(radius_native_pixels=radius, frames=frames,
                raw_support=raw_support, mapped_support=mapped_support, descriptive_fit=fit, verdict=verdict,
                possible_confusion=any(r['mapped']['neighbours_in_radius'] > 1 for r in frames)))
        row.update(status='complete', verdict=row['radii'][0]['verdict'],
                   radius_sensitive=row['radii'][0]['verdict'] != row['radii'][1]['verdict'])
        rows.append(row)
    slow.unchanged(watched)
    if historical() != engines:
        raise ValueError('Une source gelée a changé pendant le diagnostic.')
    values = dict(source_kind=score['source_kind'], score_path=str(sp), score_sha256=watched[sp],
                  frozen_sha256_lf=engines, profile_parameters=PARAMETERS, rows=rows,
                  bright_misses=[r['case_id'] for r in rows if r['originally_recovered'] == 0],
                  registration_audit=audit, search_called=False, candidates_changed=False,
                  real_data_performance_validated=False, clock_qualified=False)
    return values, watched


def diagnose(score_path, output, base=None):
    base = ROOT/'local' if base is None else base
    values, watched = build(score_path, base)
    output = slow._new_output(output, base)
    result = dict(slow_miss_diagnostic_version='1.0', status='complete', plan_commit=PLAN_COMMIT,
                  diagnostic_source_sha256_lf=source_hash(__file__), inputs_unchanged=True,
                  **values, **slow.experiment.provenance())
    slow.save(output/'diagnostic.json', result)
    with (output/'support.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        fields = ('case_id', 'originally_recovered', 'verdict', 'radius', 'frames', 'span')
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for row in result['rows']:
            for local in row['radii']:
                writer.writerow(dict(case_id=row['case_id'], originally_recovered=row['originally_recovered'],
                    verdict=local['verdict'], radius=local['radius_native_pixels'],
                    frames=local['mapped_support']['frames'], span=local['mapped_support']['span_declared_seconds']))
    slow.unchanged(watched)
    return result


def checked_diagnostic(path, base=None):
    base = ROOT/'local' if base is None else base
    path = local_path(path, base); before = digest(path); result = slow.read(path)
    if (result.get('slow_miss_diagnostic_version') != '1.0' or result.get('status') != 'complete'
            or result.get('plan_commit') != PLAN_COMMIT or result.get('inputs_unchanged') is not True
            or result.get('diagnostic_source_sha256_lf') != source_hash(__file__)):
        raise ValueError('Un diagnostic complet et gelé de ce lot est requis.')
    values, watched = build(result['score_path'], base)
    if any(result.get(k) != v for k, v in values.items()):
        raise ValueError('Le diagnostic diffère de ses preuves gelées.')
    watched[path] = before; slow.unchanged(watched)
    return result, watched


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('score', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        result = diagnose(args.score, args.output)
        print(f"Diagnostic terminé : {len(result['bright_misses'])} manque(s) brillant(s), anciens candidats conservés.")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
