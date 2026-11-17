# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Separate experimental slow-track association in native registered pixels.

The historical detector/association are untouched. This profile uses declared
relative times and nominal optics; its statistic is not a calibrated p-value.
"""
import numpy as np
from scipy.spatial import cKDTree

PARAMETERS = dict(frame_count=8, span_min_seconds=1800., span_max_seconds=2700.,
    gap_min_seconds=240., gap_max_seconds=360., angular_min_arcsec_hour=5.,
    angular_max_arcsec_hour=120., association_radius_pixels=1.5, minimum_frames=6,
    minimum_support_seconds=1800., minimum_displacement_pixels=1.5,
    rms_max_pixels=.75, p95_max_pixels=1.5, variance_floor_pixels_squared=.25**2,
    fixed_linear_improvement_min=25., max_hypotheses=100000,
    seed_min_span_fraction=.5, refit_iterations=2, maximum_detections=500,
    deduplicate_shared_points=3)


def validate_times(times):
    times = np.asarray(times, dtype=float)
    if (times.shape != (8,) or not np.isfinite(times).all() or times[0] != 0
            or not 1800 <= times[-1] <= 2700 or np.any(np.diff(times) < 240)
            or np.any(np.diff(times) > 360)):
        raise ValueError('Huit poses sur 1800 à 2700 s, espacées de 240 à 360 s, sont requises.')
    return times


def fit_track(points, times):
    points, times = np.asarray(points, dtype=float), np.asarray(times, dtype=float)
    if (times.ndim != 1 or len(times) < 2 or points.shape != (len(times), 2)
            or not np.isfinite(points).all() or not np.isfinite(times).all()
            or np.any(np.diff(times) <= 0)):
        raise ValueError('Des positions finies et des temps croissants sont requis.')
    epoch = float(times[0])
    design = np.column_stack((np.ones(len(times)), times-epoch))
    coefficients = np.linalg.lstsq(design, points, rcond=None)[0]
    residual = np.linalg.norm(points-design@coefficients, axis=1)
    return epoch, coefficients, residual


def find_tracks(detections, times, scale):
    """Search without truth, static removal, or edits to the old engine."""
    times = validate_times(times)
    if type(scale) not in (int, float) or not np.isfinite(scale) or scale <= 0:
        raise ValueError('Une échelle nominale positive est requise.')
    if len(detections) != 8:
        raise ValueError('Huit catalogues sont requis.')
    detections = [np.asarray(p, dtype=float) for p in detections]
    if any(p.ndim != 2 or p.shape[1] != 2 or len(p) > 500 or not np.isfinite(p).all()
           for p in detections):
        raise ValueError('Chaque catalogue doit contenir au plus 500 positions finies à deux coordonnées.')
    trees = [cKDTree(p) if len(p) else None for p in detections]
    speed_min, speed_max = np.array([5., 120.])/(3600*scale)
    hypotheses, candidates = 0, {}

    def associate(epoch, offset, velocity):
        rows = []
        for k, tree in enumerate(trees):
            if tree is not None:
                distance, j = tree.query(offset+(times[k]-epoch)*velocity)
                if distance <= 1.5:
                    rows.append((k, int(j)))
        return rows

    for a in range(7):
        for b in range(a+1, 8):
            delta = times[b]-times[a]
            if delta < .5*times[-1] or trees[b] is None:
                continue
            for p in detections[a]:
                # A bounded annulus avoids the full Cartesian product in a rich field.
                for j in sorted(trees[b].query_ball_point(p, speed_max*delta)):
                    velocity = (detections[b][j]-p)/delta
                    if not speed_min <= np.linalg.norm(velocity) <= speed_max:
                        continue
                    hypotheses += 1
                    if hypotheses > 100000:
                        raise ValueError('Plus de 100000 hypothèses : recherche arrêtée sans troncature.')
                    rows = associate(times[a], p, velocity)
                    for _ in range(2):
                        if len(rows) < 6:
                            break
                        xy = np.array([detections[k][m] for k, m in rows])
                        t = np.array([times[k] for k, _ in rows])
                        epoch, coefficients, _ = fit_track(xy, t)
                        rows = associate(epoch, coefficients[0], coefficients[1])
                    if len(rows) < 6:
                        continue
                    xy = np.array([detections[k][m] for k, m in rows])
                    t = np.array([times[k] for k, _ in rows])
                    epoch, coefficients, residual = fit_track(xy, t)
                    span = float(t[-1]-t[0])
                    speed = float(np.linalg.norm(coefficients[1]))
                    rms = float(np.sqrt(np.mean(residual**2)))
                    p95 = float(np.percentile(residual, 95))
                    linear_sse = float(np.sum(residual**2))
                    fixed_sse = float(np.sum((xy-xy.mean(axis=0))**2))
                    denominator = max(.25**2, linear_sse/(2*len(rows)-4))
                    improvement = (fixed_sse-linear_sse)/denominator
                    if (span < 1800 or not speed_min <= speed <= speed_max
                            or span*speed < 1.5 or rms > .75 or p95 > 1.5
                            or improvement < 25):
                        continue
                    key = tuple(rows)
                    candidates[key] = dict(epoch_relative_seconds=epoch,
                        position_at_epoch_native_pixels=coefficients[0].tolist(),
                        velocity_native_pixels_per_declared_second=coefficients[1].tolist(),
                        angular_rate_nominal_arcsec_hour=speed*scale*3600,
                        rms_native_pixels=rms, p95_native_pixels=p95,
                        span_declared_seconds=span, displacement_native_pixels=span*speed,
                        linear_sse_native_pixels_squared=linear_sse,
                        fixed_sse_native_pixels_squared=fixed_sse,
                        variance_used_native_pixels_squared=denominator,
                        fixed_linear_improvement=improvement,
                        points=[dict(frame_index=k, detection_index=m,
                            x=float(detections[k][m, 0]), y=float(detections[k][m, 1])) for k, m in rows])
    chosen, used = [], []
    for key, track in sorted(candidates.items(), key=lambda item:
            (-len(item[0]), item[1]['rms_native_pixels'], item[0])):
        identities = set(key)
        if any(len(identities & previous) >= 3 for previous in used):
            continue
        track['candidate_id'] = len(chosen)+1
        chosen.append(track); used.append(identities)
    return chosen, hypotheses


def score_track(track, truth):
    """Score one frozen candidate against a known addition, after search."""
    for collection in (track['points'], truth['positions']):
        indices = [p['frame_index'] for p in collection]
        coordinates = np.asarray([[p['x'], p['y']] for p in collection], dtype=float)
        if (len(collection) < 6 or len(set(indices)) != len(indices)
                or any(type(k) is not int or not 0 <= k < 8 for k in indices)
                or coordinates.shape != (len(collection), 2) or not np.isfinite(coordinates).all()):
            raise ValueError('Six positions finies et distinctes par pose sont requises pour le score.')
    for velocity in (track['velocity_native_pixels_per_declared_second'], truth['velocity_native_per_declared_second']):
        vector = np.asarray(velocity, dtype=float)
        if vector.shape != (2,) or not np.isfinite(vector).all():
            raise ValueError('Une vitesse finie à deux coordonnées est requise pour le score.')
    true = {p['frame_index']: np.array([p['x'], p['y']]) for p in truth['positions']}
    measured = {p['frame_index']: np.array([p['x'], p['y']]) for p in track['points']}
    common = sorted(set(true) & set(measured))
    if len(common) < 6:
        return None
    errors = [float(np.linalg.norm(measured[k]-true[k])) for k in common]
    rms = float(np.sqrt(np.mean(np.square(errors))))
    velocity_error = float(np.linalg.norm(np.asarray(track['velocity_native_pixels_per_declared_second'])
                                         -truth['velocity_native_per_declared_second']))
    if rms > 1 or velocity_error > .0005:
        return None
    return dict(candidate_id=track['candidate_id'], rms_native_pixels=rms,
        position_errors_native_pixels=errors, velocity_error_native_per_declared_second=velocity_error)
