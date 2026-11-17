# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Development catalogues, distinct from the two reserved image backgrounds."""
from hashlib import sha256
from pathlib import Path

import numpy as np
import pytest

from gar import slow_moving as slow

TIMES = np.arange(8, dtype=float)*300
SCALE = 206264.806247*.0029/250


def moving_catalogues(rate=30., angle=30., present=range(8), jitter=0.):
    rng = np.random.default_rng(314159)
    direction = np.array([np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))])
    velocity = rate/(3600*SCALE)*direction
    stars = np.array([[40., 40.], [80., 60.], [120., 120.], [60., 130.]])
    result = []
    for frame, time in enumerate(TIMES):
        points = stars.copy()
        if frame in present:
            point = [200., 200.]+time*velocity+rng.normal(0., jitter, 2)
            points = np.vstack([points, point])
        result.append(points)
    return result


@pytest.mark.parametrize('rate', [10., 30., 60.])
@pytest.mark.parametrize('angle', [30., 150.])
def test_recovers_slow_trajectory_among_fixed_stars(rate, angle):
    tracks, hypotheses = slow.find_tracks(moving_catalogues(rate, angle, jitter=.03), TIMES, SCALE)
    assert len(tracks) == 1 and 0 < hypotheses <= 100000


def test_empty_catalogues_are_a_complete_zero_not_an_error():
    tracks, hypotheses = slow.find_tracks([np.empty((0, 2)) for _ in range(8)], TIMES, SCALE)
    assert tracks == [] and hypotheses == 0


def test_fixed_star_control_has_no_mobile():
    stars = np.array([[20., 25.], [60., 60.], [100., 150.]])
    tracks, _ = slow.find_tracks([stars.copy() for _ in range(8)], TIMES, SCALE)
    assert tracks == []


def test_alternating_centroid_jitter_is_not_a_mobile():
    stars = np.array([[20., 25.], [60., 60.], [100., 150.]])
    catalogues = [stars+np.array([(-1)**k*.3, (-1)**(k+1)*.2]) for k in range(8)]
    tracks, _ = slow.find_tracks(catalogues, TIMES, SCALE)
    assert tracks == []


def test_incoherent_positions_do_not_make_a_regular_track():
    offsets = np.array([[0., 0.], [2., 1.], [-1., 3.], [3., -2.],
                        [1., 4.], [-2., 1.], [4., 3.], [1., -3.]])
    tracks, _ = slow.find_tracks([(point+[120., 120.])[None, :] for point in offsets], TIMES, SCALE)
    assert tracks == []


@pytest.mark.parametrize('rate', [0., 5., 900., 4306.80915443])
def test_static_too_short_displacement_or_fast_controls_are_not_recovered(rate):
    tracks, _ = slow.find_tracks(moving_catalogues(rate), TIMES, SCALE)
    assert tracks == []


def test_five_points_fail_required_support():
    tracks, _ = slow.find_tracks(moving_catalogues(present=[0, 1, 3, 5, 7]), TIMES, SCALE)
    assert tracks == []


def test_six_well_spaced_points_are_accepted():
    tracks, _ = slow.find_tracks(moving_catalogues(present=[0, 1, 2, 5, 6, 7]), TIMES, SCALE)
    assert len(tracks) == 1


def test_six_points_in_fifteen_hundred_seconds_fail_duration():
    tracks, _ = slow.find_tracks(moving_catalogues(present=[0, 1, 2, 3, 4, 5]), TIMES, SCALE)
    assert tracks == []


def test_shared_point_duplicates_are_collapsed_deterministically():
    catalogues = moving_catalogues()
    first = slow.find_tracks(catalogues, TIMES, SCALE)
    assert first == slow.find_tracks(catalogues, TIMES, SCALE)
    assert len(first[0]) == 1


def test_two_disjoint_slow_objects_remain_two_candidates():
    catalogues = moving_catalogues(30., 30.)
    velocity = 60./(3600*SCALE)*np.array([np.cos(np.deg2rad(150.)), np.sin(np.deg2rad(150.))])
    catalogues = [np.vstack([points, [320., 320.]+time*velocity])
        for points, time in zip(catalogues, TIMES)]
    tracks, _ = slow.find_tracks(catalogues, TIMES, SCALE)
    assert len(tracks) == 2
    speeds = sorted(np.linalg.norm(t['velocity_native_pixels_per_declared_second'])*SCALE*3600 for t in tracks)
    assert speeds == pytest.approx([30., 60.])


@pytest.mark.parametrize('times', [np.arange(8)*10., np.arange(7)*300.,
    [0., 300., 600., 900., 1200., 1500., 1800., 1800.],
    [0., 300., 600., 900., 1200., 1500., 1800., float('nan')],
    np.arange(8)*400., np.arange(8)[::-1]*300.,
    [0., 200., 600., 900., 1200., 1500., 1800., 2100.]])
def test_invalid_long_cadence_contract_is_refused(times):
    with pytest.raises((ValueError, TypeError)):
        slow.validate_times(times)


@pytest.mark.parametrize('scale', [0., -1., float('inf'), float('nan')])
def test_invalid_nominal_angular_scale_is_refused(scale):
    with pytest.raises((ValueError, TypeError)):
        slow.find_tracks(moving_catalogues(), TIMES, scale)


@pytest.mark.parametrize('problem', ['seven', 'nonfinite', 'shape', 'many'])
def test_invalid_catalogues_are_refused(problem):
    catalogues = moving_catalogues()
    if problem == 'seven':
        catalogues.pop()
    elif problem == 'nonfinite':
        catalogues[0][0, 0] = float('nan')
    elif problem == 'shape':
        catalogues[0] = np.ones((4, 3))
    else:
        catalogues[0] = np.zeros((501, 2))
    with pytest.raises((ValueError, TypeError)):
        slow.find_tracks(catalogues, TIMES, SCALE)


def test_catalogues_and_timestamps_are_not_mutated():
    catalogues = moving_catalogues()
    copies = [points.copy() for points in catalogues]
    times = TIMES.copy()
    slow.find_tracks(catalogues, times, SCALE)
    assert all(np.array_equal(a, b) for a, b in zip(catalogues, copies))
    assert np.array_equal(times, TIMES)


def test_hypothesis_limit_refuses_instead_of_returning_a_truncated_search():
    # Two crowded endpoint catalogues exceed the ceiling before six-frame fits.
    catalogues = [np.empty((0, 2)) for _ in range(8)]
    catalogues[0] = np.tile([100., 100.], (500, 1))
    catalogues[7] = np.tile([108., 100.], (500, 1))
    with pytest.raises(ValueError, match='100000'):
        slow.find_tracks(catalogues, TIMES, SCALE)


def test_historical_sources_remain_frozen():
    root = Path(__file__).resolve().parents[1]
    for name, expected in {
        'src/gar/moving.py': 'f492032e0188310484faaf372db4c96597fd7910ecd3821629edb8365f27be67',
        'examples/injection_recovery.py': '7f0ed216d7822180f88e2f761ffe95968805946f9771cc8b03effa8c8d842b94',
        'examples/run_seestar_pilot.py': '605504751a6bbc25ffd1134b4c55efcebf47baf31ce044b70c229f47c9553e08',
    }.items():
        assert sha256((root/name).read_text(encoding='utf-8').encode()).hexdigest() == expected


def test_fitted_motion_and_fixed_linear_statistic_use_native_units():
    tracks, _ = slow.find_tracks(moving_catalogues(30., 30.), TIMES, SCALE)
    track = tracks[0]
    speed = np.linalg.norm(track['velocity_native_pixels_per_declared_second'])
    assert speed*SCALE*3600 == pytest.approx(30.)
    assert track['span_declared_seconds'] == 2100.
    assert track['displacement_native_pixels'] == pytest.approx(speed*2100.)
    assert track['variance_used_native_pixels_squared'] == .25**2
    assert track['fixed_linear_improvement'] == pytest.approx(
        (track['fixed_sse_native_pixels_squared']-track['linear_sse_native_pixels_squared'])/(.25**2))
    assert track['fixed_linear_improvement'] >= 25.


def truth_for(track):
    return dict(positions=[dict(frame_index=p['frame_index'], x=p['x'], y=p['y'])
        for p in track['points']], velocity_native_per_declared_second=
        track['velocity_native_pixels_per_declared_second'].copy())


def test_scoring_accepts_exact_positions_but_refuses_wrong_velocity():
    tracks, _ = slow.find_tracks(moving_catalogues(), TIMES, SCALE)
    track = tracks[0]
    truth = truth_for(track)
    match = slow.score_track(track, truth)
    assert match['rms_native_pixels'] == 0.
    assert match['velocity_error_native_per_declared_second'] == 0.
    truth['velocity_native_per_declared_second'][0] += .00051
    assert slow.score_track(track, truth) is None


def test_scoring_refuses_spatial_offset_and_fewer_than_six_shared_positions():
    tracks, _ = slow.find_tracks(moving_catalogues(), TIMES, SCALE)
    track = tracks[0]
    truth = truth_for(track)
    for point in truth['positions']:
        point['x'] += 1.01
    assert slow.score_track(track, truth) is None
    truth = truth_for(track)
    truth['positions'] = truth['positions'][2:]
    track = dict(track, points=track['points'][:6])
    assert slow.score_track(track, truth) is None


@pytest.mark.parametrize('problem', ['nan_position', 'nan_velocity', 'infinite_velocity',
    'repeated_index', 'external_index', 'noninteger_index', 'short_velocity', 'few_positions'])
def test_score_rejects_malformed_truth_instead_of_accepting_unknown_numbers(problem):
    tracks, _ = slow.find_tracks(moving_catalogues(), TIMES, SCALE)
    truth = truth_for(tracks[0])
    if problem == 'nan_position':
        truth['positions'][0]['x'] = float('nan')
    elif problem == 'nan_velocity':
        truth['velocity_native_per_declared_second'][0] = float('nan')
    elif problem == 'infinite_velocity':
        truth['velocity_native_per_declared_second'][0] = float('inf')
    elif problem == 'repeated_index':
        truth['positions'][1]['frame_index'] = truth['positions'][0]['frame_index']
    elif problem == 'external_index':
        truth['positions'][0]['frame_index'] = 8
    elif problem == 'noninteger_index':
        truth['positions'][0]['frame_index'] = .5
    elif problem == 'short_velocity':
        truth['velocity_native_per_declared_second'] = [0.]
    else:
        truth['positions'] = truth['positions'][:5]
    with pytest.raises(ValueError):
        slow.score_track(tracks[0], truth)
