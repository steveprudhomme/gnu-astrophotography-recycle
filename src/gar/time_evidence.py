# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Prepare a timing evidence dossier from verified copy headers, never qualify."""
from collections import Counter
import json
import math

from astropy.io import fits

from .astrometry import local_path
from .contracts import json_value, parse_declared_time
from .timing import CORE_SCALES, comment_hint, date_status, positive_duration
from .workset import digest
from .time_evidence_reports import write_time_evidence_reports


DATE_KEYS = ('DATE-OBS', 'DATE-BEG', 'DATE-AVG', 'DATE-END', 'DATE', 'DATEREF')
NUMERIC_TIME_KEYS = ('MJD-OBS', 'MJD-BEG', 'MJD-AVG', 'MJD-END', 'JD-OBS', 'JD-BEG',
                     'JD-AVG', 'JD-END', 'MJDREF', 'MJDREFI', 'MJDREFF', 'JDREF', 'JDREFI',
                     'JDREFF', 'TSTART', 'TSTOP', 'TIMEZERO', 'TIMEOFFS', 'TIMEPIXR')
CONTEXT_KEYS = ('TIMESYS', 'TIMEUNIT', 'TIMEREF', 'TREFPOS', 'TREFDIR', 'PLEPHEM')
DURATION_KEYS = ('EXPTIME', 'EXPOSURE', 'XPOSURE', 'TELAPSE', 'ELAPTIME', 'ONTIME', 'LIVETIME', 'DEADC')
ERROR_KEYS = ('TIMEDEL', 'TIMSYER', 'TIMRDER', 'TIMEERR')
SOFTWARE_KEYS = ('INSTRUME', 'PROGRAM', 'CREATOR', 'SWCREATE', 'FIRMWARE', 'FWVERSION', 'SWVER', 'VERSION')
KEYS = (*DATE_KEYS, *NUMERIC_TIME_KEYS, *CONTEXT_KEYS, *DURATION_KEYS, *ERROR_KEYS, *SOFTWARE_KEYS,
        'IMAGETYP', 'STACKCNT', 'TOTALEXP')
REQUIREMENTS = (
    ('configuration', 'Modèle, firmware, application et mode applicables aux acquisitions'),
    ('timestamp_event', 'Lien vérifié entre horodatage et exposition physique début/fin'),
    ('time_reference', 'Échelle et synchronisation vers une référence indépendante traçable'),
    ('reference_measurement', 'Mesure des événements optiques/électriques et incertitude de la référence'),
    ('offset_drift_jitter', 'Décalage absolu, dérive, dispersion et répétitions représentatives'),
    ('duration_readout', 'Durée effective et effets éventuels du séquencement/lecture du capteur'),
    ('uncertainty_budget', 'Budget d’incertitude, dépendances et critères d’usage fixés avant essai'),
    ('historical_applicability', 'Preuves de rattachement à l’époque et à la configuration des archives'),
)


def numeric_nonnegative(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def inspect_header(header, file_index, hdu_index, *, is_image=True):
    """No inheritance, time conversion, pixel access or instrumental inference."""
    cards = [{'card_index': i, 'keyword': card.keyword, 'value': json_value(card.value),
              'value_type': type(card.value).__name__, 'comment': card.comment, 'image': card.image}
             for i, card in enumerate(header.cards) if card.keyword in KEYS]
    by_key = {key: [card for card in cards if card['keyword'] == key] for key in KEYS}
    def unique(key):
        return by_key[key][0]['value'] if len(by_key[key]) == 1 else None
    duplicates = [key for key in KEYS if len(by_key[key]) > 1]
    dates = {}
    for key in DATE_KEYS:
        raw = unique(key)
        status = 'duplicate_ambiguous' if len(by_key[key]) > 1 else date_status(raw)
        decimals = len(raw.split('.')[1]) if status == 'parsed_unqualified' and '.' in raw else (0 if status == 'parsed_unqualified' else None)
        dates[key] = {'status': status, 'decimal_places_written': decimals,
                      'written_quantum_seconds': 10.**(-decimals) if decimals is not None else None}
    naxis = header.get('NAXIS', 0)
    count = unique('STACKCNT')
    stacked = naxis == 3 or (type(count) in (int, float) and count > 1)
    kind = 'stack_or_cube_not_single_exposure' if is_image and stacked else (
        'image_2d_candidate' if is_image and naxis == 2 else 'not_a_single_2d_image')
    scale, unit = unique('TIMESYS'), unique('TIMEUNIT')
    scale_status = 'duplicate_ambiguous' if 'TIMESYS' in duplicates else (
        'missing' if scale in (None, '') else 'recognized_declaration' if isinstance(scale, str) and scale in CORE_SCALES else 'unrecognized_declaration')
    unit_status = 'duplicate_ambiguous' if 'TIMEUNIT' in duplicates else (
        'missing' if unit in (None, '') else 'declared_not_converted' if isinstance(unit, str) else 'invalid_type')
    flags = ['independent_timing_evidence_not_supplied']
    flags += ['duplicate_'+key for key in duplicates]
    for key in ('DATE-OBS', 'DATE-BEG', 'DATE-END'):
        if dates[key]['status'] != 'parsed_unqualified':
            flags.append(key+'_'+dates[key]['status'])
    if scale_status != 'recognized_declaration': flags.append('timesys_'+scale_status)
    comments = [card['comment'] for card in by_key['DATE-OBS']]
    hint = comment_hint(comments)
    if hint == 'creation_wording_not_exposure_reference': flags.append('date_obs_creation_wording')
    for key in ERROR_KEYS:
        if len(by_key[key]) == 1 and not numeric_nonnegative(unique(key)):
            flags.append('invalid_declared_'+key)
    for key in ('EXPTIME', 'EXPOSURE', 'XPOSURE', 'TELAPSE', 'ELAPTIME', 'ONTIME', 'LIVETIME'):
        if len(by_key[key]) == 1 and not numeric_nonnegative(unique(key)):
            flags.append('invalid_declared_'+key)
    exptime, alias = positive_duration(unique('EXPTIME')), positive_duration(unique('EXPOSURE'))
    if exptime is None: flags.append('positive_exptime_not_established')
    if exptime is not None and alias is not None and not math.isclose(exptime, alias, rel_tol=0, abs_tol=1e-6):
        flags.append('duration_alias_values_differ_units_unverified')
    span, span_minus_telapse = None, None
    if all(dates[key]['status'] == 'parsed_unqualified' for key in ('DATE-BEG', 'DATE-END')):
        begin, end = [parse_declared_time(unique(key)) for key in ('DATE-BEG', 'DATE-END')]
        span = (end-begin).total_seconds()
        if span < 0: flags.append('end_precedes_begin_in_declared_calendar')
        if dates['DATE-AVG']['status'] == 'parsed_unqualified':
            if not begin <= parse_declared_time(unique('DATE-AVG')) <= end:
                flags.append('average_outside_declared_begin_end')
        elapsed = unique('TELAPSE')
        if unit == 's' and numeric_nonnegative(elapsed):
            span_minus_telapse = span-elapsed
            if abs(span_minus_telapse) > 1e-6: flags.append('naive_calendar_span_differs_from_telapse')
    numeric_keys = [key for key in NUMERIC_TIME_KEYS if by_key[key]]
    if numeric_keys: flags.append('numeric_time_coordinates_preserved_not_interpreted')
    software = {key: by_key[key] for key in SOFTWARE_KEYS if by_key[key]}
    firmware = [key for key in ('FIRMWARE', 'FWVERSION') if len(by_key[key]) == 1 and unique(key) not in (None, '')]
    default_scale = None
    if scale_status == 'missing' and dates['DATE-OBS']['status'] == 'parsed_unqualified':
        default_scale = 'UTC' if parse_declared_time(unique('DATE-OBS')).year >= 1972 else 'UT_legacy_date_rule'
    return {'file_index': file_index, 'hdu_index': hdu_index, 'hdu_kind': kind,
            'applicable_to_individual_exposure': kind == 'image_2d_candidate',
            'cards': cards, 'absent_selected_keywords': [key for key in KEYS if not by_key[key]],
            'duplicate_keywords': duplicates, 'dates': dates, 'date_obs_comment_hint': hint,
            'timesys_declared': scale, 'scale_status': scale_status, 'fits_scale_default_hint': default_scale,
            'timeunit_declared': unit, 'unit_status': unit_status,
            'fits_timeunit_default_hint': 's' if unit_status == 'missing' else None,
            'naive_calendar_span_seconds': span, 'naive_span_minus_telapse_if_explicit_seconds': span_minus_telapse,
            'numeric_time_keywords_not_interpreted': numeric_keys, 'software_declarations': software,
            'explicit_firmware_keyword_present': bool(firmware), 'firmware_applicability_verified': False,
            'flags': flags, 'clock_accuracy_seconds': None, 'exposure_reference_verified': False,
            'time_validated': False, 'scientific_time_export_allowed': False, 'mid_exposure_utc': None}


def evidence_template(workset_sha256):
    return {'template_schema_version': '1.0', 'workset_sha256': workset_sha256,
            'purpose': 'Canevas à compléter et revoir ; non lu comme preuve par cette commande.',
            'measurement_performed': False, 'scope': {'instrument': None, 'firmware': None, 'application': None,
                'acquisition_mode': None, 'acquisition_epoch': None, 'archive_link_evidence': None},
            'requirements': [{'id': key, 'description': text, 'status': 'not_supplied_to_this_run',
                              'evidence_reference': None, 'reviewer': None} for key, text in REQUIREMENTS],
            'measurement_plan': {'measurand': None, 'independent_reference': None, 'utc_traceability': None,
                'reference_uncertainty_seconds': None, 'uncertainty_kind_and_coverage': None,
                'event_recording_method': None, 'repetitions_and_configurations': None,
                'acceptance_criteria_fixed_before_measurement': None},
            'results': {'offset_seconds': None, 'drift_seconds_per_second': None, 'jitter_seconds': None,
                'exposure_duration_seconds': None, 'combined_standard_uncertainty_seconds': None,
                'correlations_and_systematic_effects': None, 'historical_applicability_demonstrated': False},
            'time_validated': False, 'scientific_time_export_allowed': False}


def run_time_evidence(workset_path, output, base):
    wp, output = local_path(workset_path, base), local_path(output, base)
    if output.exists(): raise ValueError('La sortie existe déjà.')
    before = digest(wp)
    workset = json.loads(wp.read_text(encoding='utf-8'))
    if (not isinstance(workset, dict) or not workset.get('success') or
            not isinstance(workset.get('files'), list) or not workset['files']):
        raise ValueError('Workset local vérifié requis.')
    paths, hashes = {}, {'workset': before}
    for i, item in enumerate(workset['files'], 1):
        if not isinstance(item, dict) or not isinstance(item.get('local_copy'), str):
            raise ValueError('Chemin de copie locale requis.')
        path = local_path(wp.parent/item['local_copy'], base)
        if wp.parent.resolve() not in path.parents or path in paths.values():
            raise ValueError('Copie hors du lot ou répétée.')
        value = digest(path)
        if value != item.get('sha256_copy'): raise ValueError('Empreinte de copie incorrecte.')
        paths[i] = path; hashes[f'copy_{i}'] = value
    records = []
    for i, path in paths.items():
        with fits.open(path, mode='readonly', memmap=False, do_not_scale_image_data=True, lazy_load_hdus=False) as hdus:
            for j, hdu in enumerate(hdus):
                records.append(inspect_header(hdu.header, i, j,
                    is_image=isinstance(hdu, (fits.PrimaryHDU, fits.ImageHDU, fits.CompImageHDU))))
    if digest(wp) != before: raise ValueError('Le workset a changé pendant l’analyse.')
    for i, path in paths.items():
        if digest(path) != hashes[f'copy_{i}']: raise ValueError('Une copie a changé pendant l’analyse.')
    candidates = [r for r in records if r['applicable_to_individual_exposure']]
    summary = {'files': len(paths), 'hdus': len(records), 'individual_exposure_candidates': len(candidates),
               'kind_counts': dict(Counter(r['hdu_kind'] for r in records)),
               'candidates_with_parsed_date_obs': sum(r['dates']['DATE-OBS']['status'] == 'parsed_unqualified' for r in candidates),
               'candidates_with_begin_end_declarations': sum(r['naive_calendar_span_seconds'] is not None for r in candidates),
               'candidates_with_declared_scale': sum(r['scale_status'] == 'recognized_declaration' for r in candidates),
               'candidates_with_explicit_firmware_keyword': sum(r['explicit_firmware_keyword_present'] for r in candidates),
               'qualified_hdus': 0, 'independent_evidence_requirements': len(REQUIREMENTS), 'independent_evidence_supplied': 0}
    result = {'time_evidence_schema_version': '1.0', 'summary': summary, 'records': records,
              'selected_keywords': list(KEYS), 'inputs_sha256_before': hashes, 'inputs_sha256_after': hashes.copy(),
              'workset_source_revision': workset.get('source_revision'), 'pixels_loaded': False, 'offline': True,
              'proof_scope': 'headers_only_no_independent_measurement', 'time_conversion': 'none',
              'calendar_comparison_tolerance_seconds': 1e-6, 'clock_accuracy_seconds': None,
              'exposure_reference_verified': False, 'time_validated': False, 'mid_exposure_utc': None,
              'scientific_time_export_allowed': False}
    output.mkdir(parents=True, exist_ok=False)
    write_time_evidence_reports(output, result, evidence_template(before))
    return result
