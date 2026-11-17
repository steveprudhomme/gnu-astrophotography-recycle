# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Every image in these tests is invented, including unmarked input cases."""
import builtins
from copy import deepcopy
import json
from pathlib import Path
import socket
import sys
from unittest.mock import patch

import numpy as np
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import make_seestar_pilot_demo as demo
    import run_seestar_pilot as pilot
    import plot_seestar_pilot as drawing
finally:
    sys.path.pop(0)


@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    base = tmp_path_factory.mktemp('pilot')/'local'; base.mkdir()
    records = {}
    for name in ('mobile', 'control', 'insufficient'):
        folder = base/name
        demo.make(folder, base, name)
        report = pilot.run(folder/'plan/plan.json', folder/'workset/workset.json',
                           folder/'audit/series.json', base/(name+'-analysis'), base)
        records[name] = (folder, report)
    return base, records


def test_known_mobile_recovered_without_truth_used_during_analysis(cases):
    _, records = cases
    folder, result = records['mobile']
    assert result['status'] == 'complete' and result['motion_searched']
    assert result['candidate_count'] == 1 and result['registration_available']
    truth = json.loads((folder/'truth.json').read_text(encoding='utf-8'))
    track = result['search']['tracks'][0]
    true = {p['frame_index']: np.array([p['x'], p['y']]) for p in truth['reference_positions']}
    for p in track['points']:
        assert np.linalg.norm(np.array([p['x'], p['y']])-true[p['frame_index']]) < .6
    assert np.linalg.norm(np.array(track['velocity_native_pixels_per_declared_second'])-[.5, .2]) < .01
    assert len(track['points']) >= 5


def test_no_mobile_control_has_zero_candidates(cases):
    result = cases[1]['control'][1]
    assert result['motion_searched'] and result['candidate_count'] == 0
    assert result['search_status'] == 'complete'


def test_insufficient_controls_block_whole_series_without_fake_zero(cases):
    result = cases[1]['insufficient'][1]
    assert result['status'] == 'complete' and result['search_status'] == 'blocked'
    assert result['candidate_count'] is None and result['search'] is None
    assert not result['registration_available'] and not result['motion_searched']
    assert len(result['models']) == 8 and result['blocked_reasons']


def test_reports_keep_time_provenance_and_no_science_claim(cases):
    for _, result in cases[1].values():
        assert result['relative_declared_seconds'] == [13.*k for k in range(8)]
        assert result['input_kind'] == 'synthetic_demo'
        for flag in ('clock_qualified', 'scientific_submission_certified',
                     'real_data_performance_validated', 'pixels_rewritten', 'source_files_opened'):
            assert result[flag] is False
        assert result['inputs_sha256_before'] == result['inputs_sha256_after']
        assert result['input_hashes_unchanged']
        for track in (result['search'] or {}).get('tracks', []):
            assert not any('fictitious' in key or key == 'velocity_pixels_per_second' for key in track)
            assert track['review_status'] == 'unreviewed_not_a_discovery'


def test_native_conversion_and_inverse_round_trip():
    reduced = np.array([[0., 0.], [10.2, 30.7]])
    native = 2*reduced+.5
    assert np.allclose((native-.5)/2, reduced)
    angle = .12
    r = [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    model = dict(rotation_matrix=r, translation_pixels=[12., -5.])
    assert np.allclose(pilot.from_reference(pilot.to_reference(native, model), model), native)


def test_common_overlap_uses_all_inverse_fields():
    a = dict(rotation_matrix=np.eye(2), translation_pixels=[0, 0])
    b = dict(rotation_matrix=np.eye(2), translation_pixels=[20, 0])
    points = [np.array([[20., 40.], [40., 40.], [90., 40.]]), np.array([[20., 40.]])]
    mapped, excluded = pilot.common_points(points, [a, b], (100, 100))
    assert np.allclose(mapped[0], [[40, 40]])
    assert np.allclose(mapped[1], [[40, 40]]) and excluded == [2, 0]


def test_display_interpolation_coordinates_do_not_shift_identity():
    image = np.arange(32*32, dtype=float).reshape(32, 32)
    model = dict(rotation_matrix=np.eye(2), translation_pixels=[0, 0])
    assert np.array_equal(drawing.align_for_display(image, model), image)
    image[:] = 0; image[10, 7] = 10
    model['translation_pixels'] = [2, 0]
    shown = drawing.align_for_display(image, model)
    assert np.unravel_index(np.nanargmax(shown), shown.shape) == (10, 8)
    assert image[10, 7] == 10


@pytest.mark.parametrize('bad', [(63, 64), (65, 64), (64, 65), (64, 64, 3)])
def test_invalid_pixel_shapes_refused(bad):
    with pytest.raises(ValueError):
        pilot.intensity_plane(np.ones(bad))


def test_saturated_native_pixel_masks_whole_block():
    image = np.full((64, 64), 100.); image[1, 0] = 65000
    plane = pilot.intensity_plane(image)
    assert np.isnan(plane[0, 0]) and np.isfinite(plane[1:, :]).all()
    assert image[1, 0] == 65000


def test_no_source_or_truth_or_network_reads_and_copies_read_only(cases, monkeypatch):
    base, records = cases
    folder, _ = records['control']
    original_open, original_path_open, original_stat = builtins.open, Path.open, Path.stat
    def guard(path, args):
        if isinstance(path, (str, Path)):
            p = Path(path)
            assert 'invented-source' not in p.parts and p.name != 'truth.json'
            if p.suffix.lower() in ('.fit', '.fits'):
                assert not args or args[0] in ('rb', 'r')
    def open_file(path, *a, **kw):
        guard(path, a); return original_open(path, *a, **kw)
    def open_path(path, *a, **kw):
        guard(path, a); return original_path_open(path, *a, **kw)
    def stat_path(path, *a, **kw):
        guard(path, ()); return original_stat(path, *a, **kw)
    def no_network(*a, **kw):
        raise AssertionError('No network in pilot')
    monkeypatch.setattr(builtins, 'open', open_file)
    monkeypatch.setattr(Path, 'open', open_path); monkeypatch.setattr(Path, 'stat', stat_path)
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    result = pilot.run(folder/'plan/plan.json', folder/'workset/workset.json',
                       folder/'audit/series.json', base/'guarded-analysis', base)
    drawing.plot(base/'guarded-analysis/pilot.json', base/'guarded-figures', base)
    assert result['candidate_count'] == 0
    with Image.open(base/'guarded-figures/blink.gif') as image:
        assert image.n_frames == 8 and image.info['duration'] == 600


@pytest.mark.parametrize('field,value', [('date_obs_raw', '2025-01-01T03:00:00'),
                                         ('local_copy', 'Z:/forbidden/image.fit')])
def test_tampered_audit_not_trusted_and_partial_result_kept(cases, field, value):
    base, records = cases; folder, _ = records['mobile']
    altered = json.loads((folder/'audit/series.json').read_text(encoding='utf-8'))
    altered['files'][0][field] = value
    name = base/('altered-'+field+'.json'); pilot.save(name, altered)
    output = base/('failed-'+field)
    with pytest.raises(ValueError):
        pilot.run(folder/'plan/plan.json', folder/'workset/workset.json', name, output, base)
    result = json.loads((output/'pilot.json').read_text(encoding='utf-8'))
    assert result['status'] == 'incomplete' and result['candidate_count'] is None
    assert not result['motion_searched']


def test_bad_hash_refused_before_detection(cases):
    base, records = cases; folder, _ = records['control']
    altered = json.loads((folder/'workset/workset.json').read_text(encoding='utf-8'))
    altered['files'][0]['sha256_before'] = '0'*64
    path = folder/'workset/tampered.json'; pilot.save(path, altered)
    with pytest.raises(ValueError):
        pilot.run(folder/'plan/plan.json', path, folder/'audit/series.json', base/'bad-hash', base)


def test_bayer_requires_explicit_compatible_mode(cases):
    base, records = cases; folder, _ = records['control']
    with pytest.raises(ValueError, match='Bayer'):
        pilot.run(folder/'plan/plan.json', folder/'workset/workset.json', folder/'audit/series.json',
                  base/'incorrect-mono-mode', base, pixel_mode='mono')


def test_external_input_rejected_before_probe(cases, monkeypatch):
    base, _ = cases
    external = base.parent/'external.json'
    original = Path.stat
    def stated(path, *a, **kw):
        assert path != external
        return original(path, *a, **kw)
    monkeypatch.setattr(Path, 'stat', stated)
    with pytest.raises(ValueError, match='local'):
        pilot.run(external, external, external, base/'not-created', base)


def test_existing_outputs_preserved(cases):
    base, records = cases; folder, _ = records['mobile']
    output = base/'mobile-analysis'
    before = (output/'pilot.json').read_bytes()
    with pytest.raises(ValueError):
        pilot.run(folder/'plan/plan.json', folder/'workset/workset.json', folder/'audit/series.json', output, base)
    assert (output/'pilot.json').read_bytes() == before
