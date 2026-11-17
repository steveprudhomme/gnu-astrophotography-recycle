# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Experimental spatial holdout; the production registration module is unchanged."""
import numpy as np
from gar.registration import solve, mutual, metrics, CRITERIA, PARAMETERS


def select_controls(points, shape):
    points = np.asarray(points, dtype=float)
    h, w = shape
    if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 4 or min(shape) <= 0
            or not np.isfinite(points).all() or np.any(points < 0) or np.any(points >= [w, h])):
        raise ValueError('Centres finis dans une image valide requis.')
    cells = np.floor(points*[3/w, 3/h]).astype(int)
    quadrants = (points >= [w/2, h/2]).astype(int)
    buckets = {}
    for i, ((cx, cy), (qx, qy)) in enumerate(zip(cells, quadrants)):
        buckets.setdefault((int(qy), int(qx), int(cy), int(cx)), []).append(i)
    rng = np.random.default_rng(20261116)
    buckets = {key: list(rng.permutation(buckets[key])) for key in sorted(buckets)}
    keys = {q: [key for key in buckets if key[:2] == q] for q in [(0, 0), (0, 1), (1, 0), (1, 1)]}
    cursor = {q: 0 for q in keys}
    chosen, target = [], max(1, len(points)//4)
    while len(chosen) < target:
        progressed = False
        for q, local in keys.items():
            for step in range(len(local)):
                j = (cursor[q]+step) % len(local)
                if buckets[local[j]]:
                    chosen.append(int(buckets[local[j]].pop(0)))
                    cursor[q] = (j+1) % len(local)
                    progressed = True
                    break
            if len(chosen) == target:
                break
        if not progressed:
            raise ValueError('Pas assez de points distincts pour la partition.')
    return np.sort(chosen)


def fit_partition(points, reference, shape, control_ids):
    """Use a fixed holdout: controls never enter hypothesis scoring or fitting."""
    points, reference = np.asarray(points, dtype=float), np.asarray(reference, dtype=float)
    control_ids = np.asarray(control_ids)
    if (control_ids.ndim != 1 or control_ids.dtype.kind not in 'iu' or not len(control_ids)
            or len(set(control_ids)) != len(control_ids) or np.any(control_ids < 0) or np.any(control_ids >= len(points))):
        raise ValueError('Indices de contrôle distincts requis.')
    train_ids = np.setdiff1d(np.arange(len(points)), control_ids)
    rotation, translation, hypotheses = solve(points[train_ids], reference)
    rows, statistics = [], {}
    for label, ids in [('training', train_ids), ('control', control_ids)]:
        i, j = mutual(points[ids], reference, rotation, translation)
        chosen = ids[i]
        residual = points[chosen]@rotation.T+translation-reference[j]
        statistics[label] = metrics(points[chosen], residual, shape)
        for k, p in enumerate(chosen):
            rows.append(dict(split=label, detection_index=int(p), reference_index=int(j[k]),
                             x=float(points[p, 0]), y=float(points[p, 1]), reference_x=float(reference[j[k], 0]),
                             reference_y=float(reference[j[k], 1]), dx_pixels=float(residual[k, 0]), dy_pixels=float(residual[k, 1])))
    t, c = statistics['training'], statistics['control']
    passed = (t['matches'] >= CRITERIA['min_training'] and c['matches'] >= CRITERIA['min_control']
              and c['median_pixels'] <= CRITERIA['median_max_pixels'] and c['p95_pixels'] <= CRITERIA['p95_max_pixels']
              and c['grid_cells_occupied'] >= CRITERIA['min_grid_cells'] and c['quadrants_occupied'] == CRITERIA['required_quadrants'])
    return dict(rotation_matrix=rotation.tolist(), translation_pixels=translation.tolist(),
                rotation_degrees=float(np.rad2deg(np.arctan2(rotation[1, 0], rotation[0, 0]))),
                metrics=statistics, criteria_passed=bool(passed), model_usable=bool(passed), pairs=rows,
                control_detection_indices=control_ids.tolist(), training_detection_indices=train_ids.tolist(),
                selection_counts=dict(training_detections=len(train_ids), control_detections=len(control_ids),
                                      unmatched_training=len(train_ids)-t['matches'], unmatched_control=len(control_ids)-c['matches']),
                selected_control_coverage=dict(selected=len(control_ids),
                    grid_cells_occupied=len(set(map(tuple, np.floor(points[control_ids]*[3/shape[1], 3/shape[0]]).astype(int)))),
                    quadrants_occupied=len(set(map(tuple, points[control_ids] >= [shape[1]/2, shape[0]/2])))),
                hypotheses_scored=hypotheses, criteria=CRITERIA, parameters=PARAMETERS,
                selection_method='quadrant_cell_round_robin_v1', image_shape=list(shape),
                clock_qualified=False, scientific_submission_certified=False)


def register_spatial(points, reference, shape):
    return fit_partition(points, reference, shape, select_controls(points, shape))
