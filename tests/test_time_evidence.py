# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
import importlib.util
import json
from pathlib import Path
import socket
import numpy as np
import pytest
from astropy.io import fits
from gar.time_evidence import inspect_header, run_time_evidence, evidence_template
from gar.workset import digest

spec = importlib.util.spec_from_file_location('time_demo', Path(__file__).resolve().parents[1]/'examples/make_time_evidence_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


def rich_header():
    return fits.Header({'NAXIS': 2, 'DATE-OBS': '2025-01-01T00:00:00.123456',
                        'DATE-BEG': '2025-01-01T00:00:00', 'DATE-END': '2025-01-01T00:00:10',
                        'DATE-AVG': '2025-01-01T00:00:05', 'TIMESYS': 'UTC', 'TIMEUNIT': 's',
                        'EXPTIME': 10., 'TELAPSE': 10., 'TIMSYER': .001, 'TIMRDER': .0001,
                        'FIRMWARE': 'FICTITIOUS-1.0'})


def test_rich_declarations_never_qualify_clock_or_compute_midpoint():
    row = inspect_header(rich_header(), 1, 0)
    assert row['naive_calendar_span_seconds'] == 10
    assert row['naive_span_minus_telapse_if_explicit_seconds'] == 0
    assert row['dates']['DATE-OBS']['written_quantum_seconds'] == 1e-6
    assert row['explicit_firmware_keyword_present']
    assert row['clock_accuracy_seconds'] is None and row['mid_exposure_utc'] is None
    assert not row['firmware_applicability_verified'] and not row['time_validated']
    assert not row['exposure_reference_verified'] and not row['scientific_time_export_allowed']


def test_missing_scale_and_unit_have_separate_normative_hints():
    header = rich_header(); del header['TIMESYS']; del header['TIMEUNIT']
    row = inspect_header(header, 1, 0)
    assert row['timesys_declared'] is None and row['fits_scale_default_hint'] == 'UTC'
    assert row['timeunit_declared'] is None and row['fits_timeunit_default_hint'] == 's'
    assert row['naive_span_minus_telapse_if_explicit_seconds'] is None
    assert not row['time_validated']


@pytest.mark.parametrize('date,status', [('2025-01-01', 'date_only_not_supported'),
    ('2025-01-01T00:00:00Z', 'timezone_suffix_not_supported'),
    ('2016-12-31T23:59:60', 'leap_second_not_supported'),
    ('2025-01-01T00:00:00.1234567', 'precision_not_supported'),
    ('not-a-date', 'invalid_or_unsupported_date')])
def test_unsupported_dates_preserved_without_conversion(date, status):
    header = rich_header(); header['DATE-OBS'] = date
    row = inspect_header(header, 1, 0)
    assert row['dates']['DATE-OBS']['status'] == status
    assert next(c['value'] for c in row['cards'] if c['keyword'] == 'DATE-OBS') == date
    assert row['dates']['DATE-OBS']['written_quantum_seconds'] is None


def test_duplicates_remain_ambiguous_and_keep_all_cards():
    header = rich_header()
    header.append(('DATE-OBS', '2025-01-01T00:00:01'))
    header.append(('DATE-BEG', '2025-01-01T00:00:02'))
    header.append(('TIMESYS', 'TAI'))
    row = inspect_header(header, 1, 0)
    assert row['dates']['DATE-OBS']['status'] == 'duplicate_ambiguous'
    assert row['scale_status'] == 'duplicate_ambiguous'
    assert row['naive_calendar_span_seconds'] is None
    assert len([c for c in row['cards'] if c['keyword'] == 'DATE-OBS']) == 2


def test_conflicts_and_calendar_order_do_not_assert_physical_time():
    header = rich_header(); header['DATE-END'] = '2024-12-31T23:59:59'; header['EXPOSURE'] = 12.
    row = inspect_header(header, 1, 0)
    assert row['naive_calendar_span_seconds'] == -1
    assert 'end_precedes_begin_in_declared_calendar' in row['flags']
    assert 'average_outside_declared_begin_end' in row['flags']
    assert 'duration_alias_values_differ_units_unverified' in row['flags']
    assert 'naive_calendar_span_differs_from_telapse' in row['flags']


@pytest.mark.parametrize('value', [-.1, 'unknown', True])
def test_invalid_error_declarations_are_not_uncertainties(value):
    header = rich_header(); header['TIMSYER'] = value
    row = inspect_header(header, 1, 0)
    assert 'invalid_declared_TIMSYER' in row['flags']
    assert row['clock_accuracy_seconds'] is None


def test_numeric_coordinates_and_day_units_are_never_interpreted():
    header = rich_header(); header['MJD-OBS'] = 60000.; header['TIMEUNIT'] = 'd'; header['TELAPSE'] = 10/86400
    row = inspect_header(header, 1, 0)
    assert row['numeric_time_keywords_not_interpreted'] == ['MJD-OBS']
    assert row['naive_span_minus_telapse_if_explicit_seconds'] is None
    assert row['timeunit_declared'] == 'd' and row['mid_exposure_utc'] is None


def test_program_is_not_firmware_and_creation_comment_is_not_exposure():
    header = fits.Header({'NAXIS': 2, 'PROGRAM': 'FICTITIOUS 1.2'})
    header['DATE-OBS'] = ('2025-01-01T00:00:00', 'Image created time')
    row = inspect_header(header, 1, 0)
    assert not row['explicit_firmware_keyword_present']
    assert row['date_obs_comment_hint'] == 'creation_wording_not_exposure_reference'
    assert 'PROGRAM' in row['software_declarations']


def test_stack_cube_and_table_are_not_individual_exposures():
    header = rich_header(); header['STACKCNT'] = 10
    assert not inspect_header(header, 1, 0)['applicable_to_individual_exposure']
    del header['STACKCNT']; header['NAXIS'] = 3
    assert not inspect_header(header, 1, 0)['applicable_to_individual_exposure']
    header['NAXIS'] = 2
    assert not inspect_header(header, 1, 0, is_image=False)['applicable_to_individual_exposure']


def test_complete_run_reads_only_local_headers_no_pixels_network_or_sources(tmp_path, monkeypatch):
    from gar.cli import main
    local = tmp_path/'local'; demo.make_demo(local/'input')
    files = list((local/'input/copies').glob('*.fit'))
    before = {p: digest(p) for p in [*files, local/'input/workset.json']}
    real_open = fits.open
    def guarded(path, *args, **kwargs):
        assert Path(path) in files and kwargs['mode'] == 'readonly'
        assert kwargs['do_not_scale_image_data']
        return real_open(path, *args, **kwargs)
    def forbidden(*args, **kwargs): raise AssertionError('Réseau/pixels interdits')
    monkeypatch.setattr(fits, 'open', guarded)
    monkeypatch.setattr(fits.PrimaryHDU, 'data', property(forbidden))
    monkeypatch.setattr(fits.ImageHDU, 'data', property(forbidden))
    monkeypatch.setattr(fits.CompImageHDU, 'data', property(forbidden))
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    result = run_time_evidence(local/'input/workset.json', local/'result', local)
    assert before == {p: digest(p) for p in before}
    assert result['summary']['files'] == 4 and result['summary']['individual_exposure_candidates'] == 3
    assert result['summary']['candidates_with_parsed_date_obs'] == 2
    assert result['summary']['qualified_hdus'] == 0 and result['summary']['independent_evidence_supplied'] == 0
    assert not result['pixels_loaded'] and result['time_conversion'] == 'none'
    assert len(list((local/'result').iterdir())) == 6
    from xml.etree import ElementTree
    ElementTree.parse(local/'result/time-evidence.svg')
    import gar.time_evidence
    monkeypatch.setattr(gar.time_evidence, 'run_time_evidence', lambda *args: result)
    assert main(['time-evidence', str(local/'input/workset.json'), '--output', str(local/'result')]) == 2


@pytest.mark.parametrize('problem', ['hash', 'outside', 'duplicate', 'existing', 'invalid_workset'])
def test_refused_inputs_and_destinations(tmp_path, problem):
    local = tmp_path/'local'; demo.make_demo(local/'input')
    wp = local/'input/workset.json'; workset = json.loads(wp.read_text())
    if problem == 'hash': workset['files'][0]['sha256_copy'] = '0'*64
    elif problem == 'outside': workset['files'][0]['local_copy'] = str(tmp_path/'external.fit')
    elif problem == 'duplicate': workset['files'][1] = workset['files'][0]
    elif problem == 'invalid_workset': workset = []
    else: (local/'result').mkdir()
    wp.write_text(json.dumps(workset))
    with pytest.raises(ValueError): run_time_evidence(wp, local/'result', local)


@pytest.mark.parametrize('target', ['workset', 'copy'])
def test_mutation_during_read_is_rejected(tmp_path, monkeypatch, target):
    from contextlib import contextmanager
    local = tmp_path/'local'; demo.make_demo(local/'input')
    wp = local/'input/workset.json'; real_open = fits.open
    @contextmanager
    def changing(path, *args, **kwargs):
        with real_open(path, *args, **kwargs) as hdus: yield hdus
        changed = wp if target == 'workset' else Path(path)
        with changed.open('ab') as stream: stream.write(b' ')
    monkeypatch.setattr(fits, 'open', changing)
    with pytest.raises(ValueError): run_time_evidence(wp, local/'result', local)
    assert not (local/'result').exists()


def test_extension_headers_are_not_silently_inherited(tmp_path):
    local = tmp_path/'local'; demo.make_demo(local/'input')
    wp = local/'input/workset.json'; workset = json.loads(wp.read_text())
    path = local/'input'/workset['files'][0]['local_copy']
    fits.HDUList([fits.PrimaryHDU(header=rich_header()), fits.ImageHDU(np.zeros((4, 4)))]).writeto(path, overwrite=True)
    workset['files'][0]['sha256_copy'] = digest(path); wp.write_text(json.dumps(workset))
    result = run_time_evidence(wp, local/'result', local)
    extension = next(r for r in result['records'] if r['file_index'] == 1 and r['hdu_index'] == 1)
    assert extension['dates']['DATE-OBS']['status'] == 'missing' and extension['timesys_declared'] is None


def test_filling_template_does_not_provide_ingested_evidence(tmp_path):
    local = tmp_path/'local'; demo.make_demo(local/'input')
    template = evidence_template('0'*64); template['measurement_performed'] = True; template['time_validated'] = True
    (local/'input/evidence-template.json').write_text(json.dumps(template))
    result = run_time_evidence(local/'input/workset.json', local/'result', local)
    assert not result['time_validated'] and not result['scientific_time_export_allowed']
    assert result['summary']['independent_evidence_supplied'] == 0


def test_csv_formula_protection_leaves_json_original_text(tmp_path):
    import csv
    local = tmp_path/'local'; demo.make_demo(local/'input')
    wp = local/'input/workset.json'; workset = json.loads(wp.read_text()); path = local/'input'/workset['files'][0]['local_copy']
    fits.writeto(path, np.zeros((4, 4)), fits.Header({'PROGRAM': '=1+1'}), overwrite=True)
    workset['files'][0]['sha256_copy'] = digest(path); wp.write_text(json.dumps(workset))
    result = run_time_evidence(wp, local/'result', local)
    assert result['records'][0]['software_declarations']['PROGRAM'][0]['value'] == '=1+1'
    with (local/'result/cards.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert next(r for r in rows if r['file_index'] == '1' and r['keyword'] == 'PROGRAM')['value'] == "'=1+1"
