# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: synthetic regression tests for source preservation.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from astropy.io import fits
import numpy as np
import pytest

from gar.cli import main
from gar.contracts import json_value
from gar.inventory import check_paths, discover, inspect_file, inventory


def image(path, **metadata):
    hdu = fits.PrimaryHDU(np.arange(48, dtype=np.uint16).reshape(8, 6))
    hdu.header['DATE-OBS'] = ('2025-01-02T03:04:05.123456', 'Image created time')
    hdu.header['EXPTIME'] = 10.0
    hdu.header['BAYERPAT'] = 'GRBG'
    for key, value in metadata.items():
        hdu.header[key] = value
    hdu.writeto(path)
    return path


@pytest.fixture
def archive(tmp_path):
    root = tmp_path / 'archives avec accents é'
    root.mkdir()
    return root


def test_readonly_raw_values_and_no_pixels(archive, monkeypatch):
    path = image(archive / 'pose.fit')
    before = path.read_bytes()
    def forbidden(self):
        raise AssertionError('Pixel array must not be loaded')
    monkeypatch.setattr(fits.PrimaryHDU, 'data', property(forbidden))
    record = inspect_file(path, archive)
    assert record['status'] == 'ok'
    assert path.read_bytes() == before
    assert record['sha256'] == hashlib.sha256(before).hexdigest()
    hdu = record['hdus'][0]
    assert hdu['dimensions_fits_order'] == [6, 8]
    assert hdu['metadata']['BZERO'] == 32768
    assert hdu['metadata']['DATE-OBS'] == '2025-01-02T03:04:05.123456'
    assert hdu['metadata']['TIMESYS'] is None
    assert not hdu['time_validated'] and not hdu['wcs_validated']
    assert any(card['comment'] == 'Image created time' for card in hdu['raw_cards'])


def test_empty_primary_and_image_extension_are_both_kept(archive):
    path = archive / 'multi.fits'
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(np.zeros((3, 4))) ]).writeto(path)
    file = inspect_file(path, archive)
    assert file['status'] == 'ok'
    assert [h['kind'] for h in file['hdus']] == ['empty_primary', 'image_2d_candidate']
    assert file['hdus'][0]['frame_id'] != file['hdus'][1]['frame_id']


def test_no_inheritance_from_primary(archive):
    primary = fits.PrimaryHDU()
    primary.header['DATE-OBS'] = '2025-01-01'
    path = archive / 'extension.fit'
    fits.HDUList([primary, fits.ImageHDU(np.zeros((3, 4)))]).writeto(path)
    file = inspect_file(path, archive)
    assert file['hdus'][1]['metadata']['DATE-OBS'] is None


def test_duplicate_bytes_and_reproducible_content(archive):
    a = image(archive / 'a.fit')
    shutil.copyfile(a, archive / 'b.FITS')
    first, incidents = inventory(archive)
    second, _ = inventory(archive)
    assert not incidents
    assert first == second
    assert first[0]['duplicate_of'] is None
    assert first[1]['duplicate_of'] == 'a.fit'
    assert first[0]['hdus'][0]['frame_id'] == first[1]['hdus'][0]['frame_id']


@pytest.mark.parametrize('name', ['pose.FIT', 'pose.fits.gz', 'pose.fts'])
def test_supported_names_and_gzip(archive, name):
    path = image(archive / name)
    file = inspect_file(path, archive)
    assert file['status'] == 'ok'
    assert len(discover(archive)[0]) == 1


def test_tile_compression(archive):
    path = archive / 'compressed.fits.fz'
    fits.HDUList([fits.PrimaryHDU(), fits.CompImageHDU(np.zeros((8, 8), dtype=np.int16))]).writeto(path)
    file = inspect_file(path, archive)
    assert file['status'] == 'ok'
    assert file['hdus'][1]['dimensions_fits_order'] == [8, 8]


def test_corrupt_and_truncated_do_not_stop_inventory(archive):
    image(archive / 'valid.fit')
    (archive / 'invalid.fit').write_bytes(b'not a FITS file')
    broken = image(archive / 'truncated.fit')
    broken.write_bytes(broken.read_bytes()[:2880])
    files, _ = inventory(archive)
    assert len(files) == 3
    status = {f['path']: f['status'] for f in files}
    assert status == {'invalid.fit': 'error', 'truncated.fit': 'error', 'valid.fit': 'ok'}


def test_rgb_bayer_keyword_not_treated_as_mosaic(archive):
    path = archive / 'Stacked_test.fit'
    hdu = fits.PrimaryHDU(np.zeros((3, 8, 6), dtype=np.uint16))
    hdu.header['BAYERPAT'] = 'GRBG'
    hdu.header['STACKCNT'] = 3
    hdu.writeto(path)
    record = inspect_file(path, archive)['hdus'][0]
    assert record['kind'] == 'stacked_candidate'
    assert 'bayer_keyword_on_non_2d_image' in record['flags']


@pytest.mark.parametrize('mode', ['same', 'child', 'ancestor', 'existing'])
def test_unsafe_outputs_rejected(archive, tmp_path, mode):
    output = {'same': archive, 'child': archive / 'reports', 'ancestor': tmp_path,
              'existing': tmp_path / 'existing'}[mode]
    if mode == 'existing':
        output.mkdir()
    with pytest.raises(ValueError):
        check_paths(archive, output)


def test_missing_source_does_not_create_output(tmp_path):
    output = tmp_path / 'output'
    assert main(['inventory', str(tmp_path/'missing'), '--output', str(output)]) == 1
    assert not output.exists()


def test_empty_archive_is_explicit(archive, tmp_path):
    output = tmp_path / 'output'
    assert main(['inventory', str(archive), '--output', str(output)]) == 2
    manifest = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['summary']['files'] == 0


def test_access_errors_are_reported(archive, monkeypatch):
    path = image(archive / 'denied.fit')
    original = Path.open
    def deny(self, *args, **kwargs):
        if self == path:
            raise PermissionError('synthetic denied file')
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', deny)
    file = inspect_file(path, archive)
    assert file['status'] == 'error' and 'PermissionError' in file['error']


def test_directory_access_errors_are_reported(archive, monkeypatch):
    def deny(path):
        raise PermissionError('synthetic denied folder')
    monkeypatch.setattr(os, 'scandir', deny)
    files, incidents = discover(archive)
    assert files == [] and incidents[0]['status'] == 'traversal_error'


def test_changed_source_is_flagged(archive, monkeypatch):
    import gar.inventory as module
    path = image(archive / 'changed.fit')
    original = module.sha256_stream
    def change(stream):
        value = original(stream)
        stamp = path.stat().st_mtime_ns + 10_000_000
        os.utime(path, ns=(stamp, stamp))
        return value
    monkeypatch.setattr(module, 'sha256_stream', change)
    assert inspect_file(path, archive)['status'] == 'changed'


def test_links_are_not_followed(archive, tmp_path):
    target = tmp_path / 'outside'
    target.mkdir()
    image(target / 'private.fit')
    link = archive / 'linked'
    if os.name == 'nt':
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True)
        assert result.returncode == 0
    else:
        link.symlink_to(target, target_is_directory=True)
    files, incidents = discover(archive)
    assert files == [] and incidents[0]['status'] == 'skipped_link'
    with pytest.raises(ValueError):
        check_paths(link, tmp_path/'output')


def test_csv_json_reports_preserve_values(archive, tmp_path):
    image(archive / '=formula.fit', OBJECT='=1+1', CTYPE1='RA---TAN', CTYPE2='DEC--TAN')
    output = tmp_path / 'output'
    assert main(['inventory', str(archive), '--output', str(output)]) == 0
    doc = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    assert doc['files'][0]['path'] == '=formula.fit'
    assert doc['files'][0]['hdus'][0]['metadata']['OBJECT'] == '=1+1'
    assert doc['files'][0]['hdus'][0]['wcs_axes_present']
    assert not doc['files'][0]['hdus'][0]['wcs_validated']
    with (output/'inventory.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1 and rows[0]['path'] == "'=formula.fit"
    assert (output/'summary.svg').exists() and (output/'report.md').exists()
    assert main(['inventory', str(archive), '--output', str(output)]) == 1


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_values_are_json_null(value):
    assert json_value(value) is None


def test_cli_module_and_windows_launcher(tmp_path, archive):
    image(archive / 'pose.fit')
    project = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(project/'src'))
    result = subprocess.run([sys.executable, '-m', 'gar', 'inventory', str(archive),
                             '--output', str(tmp_path/'cli')], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    if os.name == 'nt':
        invocation = (f'cmd /d /s /c ""{project / "scripts" / "gar-inventory.bat"}" '
                      f'"{archive}" --output "{tmp_path / "batch output é"}""')
        result = subprocess.run(invocation,
                                env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
