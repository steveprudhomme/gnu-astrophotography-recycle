# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: evidence-limited timestamp diagnostics.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Audit declarations and relative cadence without qualifying the device clock."""
from collections import Counter, defaultdict
import hashlib
import json
import math
import re
from statistics import median

from .contracts import parse_declared_time

CORE_SCALES = {'UTC', 'TAI', 'TT', 'TCG', 'TCB', 'TDB', 'GPS', 'UT1'}
FITS_REFERENCE = 'https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf'


def date_status(value):
    if value is None or value == '':
        return 'missing'
    if not isinstance(value, str):
        return 'invalid_type'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return 'date_only_not_supported'
    if re.search(r'(?:Z|[+-]\d{2}:\d{2})$', value):
        return 'timezone_suffix_not_supported'
    if re.search(r'T\d{2}:\d{2}:60(?:\.|$)', value):
        return 'leap_second_not_supported'
    if re.search(r'\.\d{7,}$', value):
        return 'precision_not_supported'
    try:
        parse_declared_time(value)
    except ValueError:
        return 'invalid_or_unsupported_date'
    return 'parsed_unqualified'


def positive_duration(value):
    try:
        if type(value) in (int, float) and math.isfinite(value) and value > 0:
            return value
    except OverflowError:
        pass
    return None


def comment_hint(comments):
    text = ' '.join(comments).lower()
    if re.search(r'\b(created|creation|création)\b', text):
        return 'creation_wording_not_exposure_reference'
    markers = set()
    if re.search(r'\b(start|begin|début)\b', text):
        markers.add('start')
    if re.search(r'\b(end|fin)\b', text):
        markers.add('end')
    if re.search(r'\b(midpoint|mid[- ]exposure|middle|milieu)\b', text):
        markers.add('midpoint')
    return next(iter(markers)) + '_wording_unverified' if len(markers) == 1 else (
        'conflicting_wording' if len(markers) > 1 else 'unspecified')


def audit_timing(document, grouped, gap_seconds=1800):
    """CLI validates input and supplies grouping products; no FITS or I/O here."""
    if type(gap_seconds) not in (int, float) or not math.isfinite(gap_seconds) or gap_seconds <= 0:
        raise ValueError('Le seuil temporel doit être positif et fini, en secondes.')
    exclusions = {(e['path'], e['hdu_index']): e['reason'] for e in grouped['excluded']}
    records, by_ref = [], {}
    for file in document['files']:
        for hdu in file['hdus']:
            ref = (file['path'], hdu['hdu_index'])
            meta = hdu['metadata']
            raw = meta.get('DATE-OBS')
            status = date_status(raw)
            applicable = hdu['kind'] == 'image_2d_candidate'
            cards = [c for c in hdu.get('raw_cards', [])
                     if isinstance(c, dict) and c.get('keyword') == 'DATE-OBS']
            comments = [c['comment'] for c in cards if isinstance(c.get('comment'), str)]
            scale = meta.get('TIMESYS')
            scale_class = ('missing' if scale in (None, '') else 'recognized_declaration'
                           if isinstance(scale, str) and scale in CORE_SCALES
                           else 'outside_supported_scale_set')
            duration = positive_duration(meta.get('EXPTIME'))
            alias_duration = positive_duration(meta.get('EXPOSURE'))
            conflict = duration is not None and alias_duration is not None and not math.isclose(
                duration, alias_duration, rel_tol=0, abs_tol=1e-6)
            decimals = len(raw.split('.')[1]) if status == 'parsed_unqualified' and '.' in raw else (
                0 if status == 'parsed_unqualified' else None)
            fits_hint = None
            if status == 'parsed_unqualified' and scale_class == 'missing':
                # Normative hint only, never an assertion about the actual device clock.
                fits_hint = 'UTC' if parse_declared_time(raw).year >= 1972 else 'UT_legacy_date_rule'
            flags = []
            if applicable:
                flags.extend(['clock_accuracy_not_established', 'exposure_reference_not_established'])
                if status != 'parsed_unqualified':
                    flags.append(status)
                if scale_class != 'recognized_declaration':
                    flags.append('timesys_' + scale_class)
                if duration is None:
                    flags.append('missing_or_invalid_exptime')
                if conflict:
                    flags.append('exptime_exposure_disagree')
                if len(cards) > 1:
                    flags.append('multiple_date_obs_cards')
            row = {'path':file['path'], 'hdu_index':hdu['hdu_index'], 'frame_id':hdu['frame_id'],
                   'applicable':applicable, 'date_obs_raw':raw, 'date_parse_status':status,
                   'date_obs_comments':comments, 'comment_hint':comment_hint(comments),
                   'decimal_places_written':decimals,
                   'written_quantum_seconds':10.0**(-decimals) if decimals is not None else None,
                   'timesys_declared':scale, 'scale_status':scale_class,
                   'fits_scale_default_hint':fits_hint,
                   'exptime_declared':meta.get('EXPTIME'), 'exposure_declared':meta.get('EXPOSURE'),
                   'duration_keywords_conflict':conflict, 'eligible_for_cadence':ref not in exclusions,
                   'exclusion_reason':exclusions.get(ref), 'flags':flags,
                   'clock_accuracy_seconds':None, 'exposure_reference_verified':False,
                   'time_validated':False, 'mid_exposure_utc':None}
            records.append(row)
            by_ref[ref] = row
    # Reassemble same configuration/day across session gaps to actually report interruptions.
    buckets = defaultdict(list)
    for session in grouped['sessions']:
        key = json.dumps(session['configuration'], sort_keys=True, ensure_ascii=False)
        buckets[key].extend(session['frames'])
    sequences = []
    for key, frames in sorted(buckets.items()):
        frames.sort(key=lambda f: (parse_declared_time(f['date_obs_raw']), f['frame_id'], f['path']))
        intervals, positive, gaps, short, duplicates = [], [], 0, 0, 0
        for first, second in zip(frames, frames[1:]):
            delta = (parse_declared_time(second['date_obs_raw']) - parse_declared_time(first['date_obs_raw'])).total_seconds()
            exposure = first['exptime_seconds_declared']
            shorter = exposure is not None and 0 < delta < exposure
            interrupted = delta > gap_seconds
            duplicate = delta == 0
            intervals.append({'from_frame_id':first['frame_id'], 'to_frame_id':second['frame_id'],
                              'naive_timestamp_delta_seconds':delta,
                              'above_gap_threshold':interrupted,
                              'shorter_than_previous_exptime':shorter, 'duplicate_timestamp':duplicate})
            row = by_ref[(second['path'], second['hdu_index'])]
            if shorter:
                row['flags'].append('delta_shorter_than_previous_exptime')
            if interrupted:
                row['flags'].append('gap_above_threshold')
            if duplicate:
                row['flags'].append('duplicate_timestamp')
            gaps += interrupted; short += shorter; duplicates += duplicate
            if delta > 0:
                positive.append(delta)
        identity = (key + json.dumps([f['frame_id'] for f in frames])).encode()
        sequences.append({'sequence_id':hashlib.sha256(identity).hexdigest(),
                          'configuration':json.loads(key), 'frame_count':len(frames),
                          'interval_count':len(intervals), 'intervals':intervals,
                          'median_positive_delta_seconds':median(positive) if positive else None,
                          'min_positive_delta_seconds':min(positive) if positive else None,
                          'max_positive_delta_seconds':max(positive) if positive else None,
                          'gap_count':gaps, 'short_interval_count':short,
                          'duplicate_timestamp_count':duplicates, 'time_validated':False})
    applicable = [r for r in records if r['applicable']]
    eligible = [r for r in applicable if r['eligible_for_cadence']]
    summary = {'input_hdus':len(records), 'candidate_hdus':len(applicable),
               'cadence_hdus':len(eligible), 'excluded_hdus':len(grouped['excluded']),
               'sequence_count':len(sequences),
               'date_status_counts':dict(Counter(r['date_parse_status'] for r in applicable)),
               'scale_status_counts':dict(Counter(r['scale_status'] for r in applicable)),
               'comment_hint_counts':dict(Counter(r['comment_hint'] for r in applicable)),
               'duration_conflicts':sum(r['duration_keywords_conflict'] for r in eligible),
               'gap_count':sum(s['gap_count'] for s in sequences),
               'short_interval_count':sum(s['short_interval_count'] for s in sequences),
               'duplicate_timestamp_count':sum(s['duplicate_timestamp_count'] for s in sequences),
               'qualified_hdus':0, 'instrument_clock_status':'not_established',
               'scientific_time_export_allowed':False}
    return {'timing_schema_version':'1.0', 'parameters':{'gap_seconds':gap_seconds,
            'exposure_comparison_tolerance_seconds':1e-6, 'time_conversion':'none'},
            'summary':summary, 'records':records, 'sequences':sequences,
            'excluded':grouped['excluded'], 'file_events':grouped['file_events'],
            'normative_reference':FITS_REFERENCE,
            'evidence_status':'No firmware-specific independent timing validation supplied.'}
