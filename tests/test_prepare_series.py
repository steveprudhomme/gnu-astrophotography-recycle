# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
from copy import deepcopy
import json
from pathlib import Path
import sys

from astropy.io import fits
from PIL import Image
import pytest

from gar.inventory import inventory
from gar.workset import prepare_workset, digest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'examples'))
try:
    import make_series_demo as demo
    import prepare_seestar_series as recipe
    import plot_series_preview as preview
finally:
    sys.path.pop(0)


@pytest.fixture
def case(tmp_path):
    base = tmp_path/'local'; source = base/'source'
    demo.make_demo(source, base)
    files, incidents = inventory(source)
    manifest = dict(schema_version='1.0', input_root=str(source), files=files, traversal_incidents=incidents)
    mp = base/'manifest.json'; recipe.save(mp, manifest)
    return base, source, mp, manifest


def test_offline_plan_never_probes_or_opens_archive(case, monkeypatch):
    base, source, mp, _ = case
    bound = base/'missing-source'
    original_open, original_stat = Path.open, Path.stat
    def opened(self, *a, **kw):
        assert not self.is_relative_to(source) and not self.is_relative_to(bound)
        return original_open(self, *a, **kw)
    def stated(self, *a, **kw):
        assert not self.is_relative_to(source) and not self.is_relative_to(bound)
        return original_stat(self, *a, **kw)
    monkeypatch.setattr(Path, 'open', opened); monkeypatch.setattr(Path, 'stat', stated)
    p = recipe.plan_series(mp, bound, base/'plan', base=base)
    assert p['selection_available'] and not p['sources_accessed_during_planning']
    assert len(p['frames']) == 8 and p['frames'][0]['path'] == 'pose-01.fit'


def test_manifest_order_does_not_change_chronological_selection(case):
    base, source, mp, manifest = case
    first = recipe.plan_series(mp, source, base/'plan1', base=base)
    manifest['files'].reverse(); recipe.save(mp, manifest)
    second = recipe.plan_series(mp, source, base/'plan2', base=base)
    assert first['frames'] == second['frames']
    assert [f['path'] for f in first['frames']] == [f'pose-{i:02d}.fit' for i in range(1, 9)]


@pytest.mark.parametrize('problem', ['short', 'incompatible', 'large_gaps', 'invalid_dates', 'duplicate_hashes'])
def test_no_eight_pose_selection_is_reported_honestly(case, problem):
    base, source, mp, manifest = case
    if problem == 'short': manifest['files'] = manifest['files'][:7]
    elif problem == 'incompatible':
        for f in manifest['files'][:6]: f['hdus'][0]['metadata']['GAIN'] = 999
    elif problem == 'large_gaps':
        from datetime import datetime, timedelta
        for k, f in enumerate(manifest['files']):
            f['hdus'][0]['metadata']['DATE-OBS'] = (datetime(2025, 1, 1)+timedelta(seconds=45*k)).isoformat()
    elif problem == 'invalid_dates':
        for f in manifest['files']: f['hdus'][0]['metadata']['DATE-OBS'] = 'unknown'
    else:
        for f in manifest['files']:
            f['sha256'] = 'a'*64; f['hdus'][0]['frame_id'] = 'a'*64+':0'
    recipe.save(mp, manifest)
    p = recipe.plan_series(mp, source, base/'plan', base=base)
    assert not p['selection_available'] and not (base/'plan/selection.json').exists()
    assert (base/'plan/report.md').exists()


@pytest.mark.parametrize('path', ['../outside.fit', '/absolute.fit', 'C:\\outside.fit', 'one\\..\\outside.fit'])
def test_dangerous_manifest_paths_rejected_without_source_access(case, path):
    base, source, mp, m = case
    m['files'][0]['path'] = path; recipe.save(mp, m)
    with pytest.raises(ValueError): recipe.plan_series(mp, source, base/'plan', base=base)
    assert not (base/'plan').exists()


@pytest.mark.parametrize('count', [7, 65])
def test_count_limits(case, count):
    base, source, mp, _ = case
    with pytest.raises(ValueError): recipe.plan_series(mp, source, base/'plan', count, base)


def copied_case(case):
    base, source, mp, _ = case
    plan = recipe.plan_series(mp, source, base/'plan', base=base)
    prepare_workset(plan['selection'], base/'copies', base)
    return base, source, plan


def test_audit_and_preview_use_only_unchanged_local_copies(case, monkeypatch):
    base, source, plan = copied_case(case)
    original_open = Path.open; original_fits = fits.open
    def opened(self, *args, **kwargs):
        assert not self.is_relative_to(source), 'Audit must not reopen originals'
        return original_open(self, *args, **kwargs)
    def fits_open(path, *args, **kwargs):
        assert Path(path).is_relative_to(base/'copies/copies') and kwargs['mode'] == 'readonly'
        return original_fits(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', opened); monkeypatch.setattr(fits, 'open', fits_open)
    r = recipe.audit_series(base/'plan/plan.json', base/'copies/workset.json', base/'audit', base)
    assert r['copies_prepared'] and r['prepared_count'] == 8 and r['input_hashes_unchanged']
    assert not any(r[k] for k in ['clock_qualified', 'motion_searched', 'science_validated', 'source_files_opened_during_audit'])
    preview.plot(base/'audit/series.json', base/'figures', base)
    assert (base/'figures/series-preview.png').exists()
    with pytest.raises(ValueError): preview.plot(base/'audit/series.json', base/'fake-cc0', base, public_cc0=True)


def test_changed_source_fails_copy_and_keeps_incomplete_workset(case):
    base, source, mp, _ = case
    p = recipe.plan_series(mp, source, base/'plan', base=base)
    with Path(p['selection']['files'][0]['source']).open('ab') as stream: stream.write(b'changed')
    with pytest.raises(ValueError): prepare_workset(p['selection'], base/'copies', base)
    r = json.loads((base/'copies/workset.json').read_text(encoding='utf-8'))
    assert not r['success']


@pytest.mark.parametrize('problem', ['copy_hash', 'wrong_header_plan', 'interrupted'])
def test_audit_does_not_turn_failures_into_preparation(case, monkeypatch, problem):
    base, source, _ = copied_case(case)
    wp = base/'copies/workset.json'
    if problem == 'copy_hash':
        r = json.loads(wp.read_text(encoding='utf-8')); r['files'][0]['sha256_copy'] = '0'*64; recipe.save(wp, r)
        with pytest.raises(ValueError): recipe.audit_series(base/'plan/plan.json', wp, base/'audit', base)
    elif problem == 'wrong_header_plan':
        pp = base/'plan/plan.json'; p = json.loads(pp.read_text(encoding='utf-8'))
        p['frames'][0]['metadata']['GAIN'] = 999; recipe.save(pp, p)
        r = recipe.audit_series(pp, wp, base/'audit', base)
        assert not r['copies_prepared'] and r['status'] == 'complete' and r['issues']
    else:
        original = fits.open; calls = []
        def opened(*args, **kwargs):
            calls.append(1)
            if len(calls) == 3: raise OSError('Synthetic interruption')
            return original(*args, **kwargs)
        monkeypatch.setattr(fits, 'open', opened)
        with pytest.raises(OSError): recipe.audit_series(base/'plan/plan.json', wp, base/'audit', base)
        r = json.loads((base/'audit/series.json').read_text(encoding='utf-8'))
        assert r['status'] == 'incomplete' and len(r['files']) == 2 and not r['copies_prepared']


def test_explicit_cc0_preview_removes_metadata_and_preserves_fits(case):
    # All test pixels are invented, even when simulating an unmarked real-input branch.
    base, source, mp, m = case
    for p in source.glob('*.fit'):
        with fits.open(p, mode='update', memmap=False) as hdus: del hdus[0].header['GARSYNTH']
    files, incidents = inventory(source)
    recipe.save(mp, dict(schema_version='1.0', input_root=str(source), files=files, traversal_incidents=incidents))
    base, source, _ = copied_case(case)
    r = recipe.audit_series(base/'plan/plan.json', base/'copies/workset.json', base/'audit', base)
    before = {Path(f['local_copy']): f['sha256'] for f in r['files']}
    preview.plot(base/'audit/series.json', base/'cc0', base, public_cc0=True)
    for name in ['series-preview.png', 'first-pose.png']:
        with Image.open(base/'cc0'/name) as image: assert not image.info and image.mode == 'RGB'
    assert all(digest(p) == value for p, value in before.items())
