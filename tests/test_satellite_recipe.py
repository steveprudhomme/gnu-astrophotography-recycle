# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Synthetic controls and boundary guards; no real FITS read by these tests."""
from pathlib import Path
import sys
import numpy as np
import pytest

pytest.importorskip('sgp4', reason='Installer requirements/satellite-tutorial.txt pour la recette facultative.')

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
from satellite_recipe import pipeline as p
from satellite_recipe.imaging import line_fit, detect_lines
from satellite_recipe.orbit import compatible_intervals, checks


def test_native_line_recovery_and_pixels_preserved():
    rng = np.random.default_rng(539115)
    yy, xx = np.indices((200, 320))
    image = 100 + rng.normal(0, 2, xx.shape) + 4*np.exp(-.5*((yy-(82+.075*xx))/1.1)**2)
    before = image.copy()
    result = line_fit(image, [[0, 80], [319, 105]])
    assert np.max(np.abs(np.array(result['native_endpoints']) - [[0, 82], [319, 105.925]])) < 1
    assert np.array_equal(image, before)
    assert result['mean_clipped_native_signal'] > max(result['parallel_control_signals'])


def test_frozen_integral_development_control():
    rng = np.random.default_rng(3804103)
    noise = rng.normal(0, 1, (160, 240))
    bright = noise.copy()
    bright[40, 15:225] += 8
    assert any(abs(r['normal_degrees']-90) < 1 for r in detect_lines(bright))
    assert detect_lines(noise) == []


def test_field_clipping_interval_not_full_duration_speed():
    result = compatible_intervals(np.arange(4.), np.array([-.5, 0, 1, 1.5]), 10)
    assert result['beginning_timestamp_offset_interval'] == [-8., 1.]
    assert result['midpoint_timestamp_offset_interval'] == [-3., 6.]
    assert result['ending_timestamp_offset_interval'] == [2., 11.]


@pytest.mark.parametrize('along', [np.array([.1, .2, .7, .9]), np.array([1.1, 1.2, 1.3, 1.4])])
def test_no_claim_when_field_crossing_not_bracketed(along):
    assert compatible_intervals(np.arange(4.), along, 10) is None


def test_propagator_reference_and_angular_round_trip():
    result = checks()
    assert result['sgp4_reference_vector_passed']
    assert result['angular_roundtrip_arcsec'] < .001


def test_checked_copy_rejects_wrong_hash_without_writing(tmp_path):
    source, target = tmp_path / 'source.bin', tmp_path / 'target.bin'
    source.write_bytes(b'unchanged input')
    before = source.read_bytes()
    with pytest.raises(ValueError, match='Empreinte'):
        p.checked_copy(source, target, '0'*64)
    assert source.read_bytes() == before
    assert not target.exists()
    assert p.checked_copy(source, target, p.digest(source)) == p.digest(source)
    with pytest.raises(FileExistsError):
        p.checked_copy(source, target)


def test_prepare_rejects_changed_input_before_creating_run(tmp_path, monkeypatch):
    data, source = tmp_path / 'data', tmp_path / 'source'
    data.mkdir()
    source.mkdir()
    (source / 'first.fit').write_bytes(b'not the authorized FITS')
    p.write(data / 'manifest.json', dict(frames=[dict(file='first.fit', original_name='old.fit', frame_id='S03-01', sha256='0'*64)]))
    monkeypatch.setattr(p, 'DATA', data)
    run = tmp_path / 'new-run'
    with pytest.raises(ValueError, match='diffère'):
        p.prepare(run, source)
    assert not run.exists()


def test_references_require_explicit_download_option(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'frames', lambda _: [])
    monkeypatch.setattr(p, 'download', lambda *args: pytest.fail('Unexpected network request'))
    with pytest.raises(ValueError, match='download-references'):
        p.references(tmp_path)


def test_report_does_not_call_changed_top_rank_plausible(tmp_path, monkeypatch):
    from satellite_recipe import report as reports
    data = tmp_path / 'data'
    data.mkdir()
    p.write(data / 'expected-results.json', dict(expected=[dict(frame_id='FAKE', norad_id=2,
        median_cross_track_arcsec=1, orientation_difference_degrees=.1)],
        cross_track_tolerance_arcsec=2, orientation_tolerance_degrees=.05))
    p.write(tmp_path / 'measurements.json', dict(traces=[]))
    p.write(tmp_path / 'orbital-results.json', dict(results=[dict(frame_id='FAKE', ranked_hypotheses=[
        dict(norad_id=999, median_cross_track_arcsec=1, orientation_difference_degrees=.1)])]))
    monkeypatch.setattr(reports, 'DATA', data)
    monkeypatch.setattr(reports, 'frames', lambda _: [])
    with pytest.raises(ValueError, match='diffère'):
        reports.report(tmp_path)
    refusal = p.read(tmp_path / 'verification-refused.json')
    assert not refusal['identity_confirmed']
    assert not refusal['checks'][0]['historical_result_reproduced']
    assert not (tmp_path / 'figures').exists()
