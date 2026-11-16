# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: conservative groups from inventory metadata.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Group declared dates; never read FITS or assert an astronomical time scale."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re

CONFIG_KEYS = ('OBJECT', 'INSTRUME', 'FILTER', 'BAYERPAT', 'EQMODE', 'TIMESYS',
               'GAIN', 'BITPIX', 'BUNIT', 'BSCALE', 'BZERO', 'SITELAT', 'SITELONG')
DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\Z')
HASH_PATTERN = re.compile(r'[0-9a-f]{64}\Z')


def _reject_constant(value):
    raise ValueError(f'Constante JSON non standard : {value}')


def load_manifest(path):
    """Validate the supported contract before creating output files."""
    data = path.read_bytes()
    try:
        document = json.loads(data, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Le manifeste doit être un document JSON UTF-8 valide.') from exc
    validate_manifest(document)
    return document, hashlib.sha256(data).hexdigest()


def validate_manifest(document):
    if not isinstance(document, dict) or document.get('schema_version') != '1.0':
        raise ValueError('Schéma de manifeste non pris en charge (1.0 attendu).')
    if not isinstance(document.get('input_root'), str) or not Path(document['input_root']).is_absolute():
        raise ValueError('Le manifeste doit déclarer une racine d’archives absolue.')
    if not isinstance(document.get('files'), list):
        raise ValueError('La liste files est absente ou incorrecte.')
    if not isinstance(document.get('traversal_incidents', []), list):
        raise ValueError('La liste des incidents est incorrecte.')
    for file in document['files']:
        if (not isinstance(file, dict) or not isinstance(file.get('path'), str)
                or file.get('status') not in {'ok', 'warning', 'error', 'changed'}
                or not isinstance(file.get('hdus'), list)):
            raise ValueError('Enregistrement de fichier incorrect.')
        if file['hdus'] and not HASH_PATTERN.fullmatch(str(file.get('sha256', ''))):
            raise ValueError('Empreinte SHA-256 de fichier incorrecte.')
        indices = set()
        for hdu in file['hdus']:
            if not isinstance(hdu, dict):
                raise ValueError('Enregistrement HDU incorrect.')
            index = hdu.get('hdu_index')
            if type(index) is not int or index < 0 or index in indices:
                raise ValueError('Index HDU absent, négatif ou dupliqué.')
            indices.add(index)
            if hdu.get('frame_id') != f"{file['sha256']}:{index}":
                raise ValueError('Identifiant HDU incohérent avec son fichier.')
            meta = hdu.get('metadata')
            if (not isinstance(hdu.get('kind'), str) or not isinstance(meta, dict)
                    or not isinstance(hdu.get('dimensions_fits_order'), list)):
                raise ValueError('Métadonnées ou dimensions HDU incorrectes.')
            if any(type(v) not in (str, int, float, bool, type(None)) for v in meta.values()):
                raise ValueError('Les métadonnées doivent contenir des valeurs simples.')
            if any(isinstance(v, float) and not math.isfinite(v) for v in meta.values()):
                raise ValueError('Métadonnée numérique non finie.')


def check_session_output(manifest, output, document):
    manifest = manifest.resolve(strict=True)
    if output.is_symlink() or getattr(output, 'is_junction', lambda: False)():
        raise ValueError('La sortie ne peut pas être un lien ou une jonction.')
    output = output.resolve()
    source = Path(document['input_root']).resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('La sortie doit rester distincte et extérieure aux archives déclarées.')
    if output.exists() or output == manifest:
        raise ValueError('La sortie existe déjà : choisir un nouveau dossier.')
    return output


def parse_declared_time(value):
    # Restrict precision rather than silently truncating fractional seconds.
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError('Date complète sans suffixe, avec au plus 6 décimales, attendue.')
    return datetime.fromisoformat(value)


def _exposure(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value > 0 else None


def group_sessions(document, gap_seconds=1800):
    validate_manifest(document)
    if type(gap_seconds) not in (int, float) or not math.isfinite(gap_seconds) or gap_seconds <= 0:
        raise ValueError('Le seuil d’interruption doit être un nombre positif fini, en secondes.')
    buckets, excluded, file_events, seen = defaultdict(list), [], [], set()
    for file in sorted(document['files'], key=lambda f: f['path']):
        if file['status'] != 'ok':
            file_events.append({'path': file['path'], 'reason': f"file_{file['status']}"})
        for hdu in file['hdus']:
            ref = {'path': file['path'], 'hdu_index': hdu['hdu_index'], 'frame_id': hdu['frame_id']}
            reason = None
            dimensions = hdu['dimensions_fits_order']
            if file['status'] != 'ok':
                reason = f"file_{file['status']}"
            elif hdu['kind'] != 'image_2d_candidate':
                reason = 'not_individual_2d_candidate'
            elif len(dimensions) != 2 or any(type(d) is not int or d <= 0 for d in dimensions):
                reason = 'invalid_dimensions'
            elif hdu['frame_id'] in seen:
                reason = 'duplicate_frame'
            else:
                try:
                    time = parse_declared_time(hdu['metadata'].get('DATE-OBS'))
                except ValueError:
                    reason = 'missing_invalid_or_unsupported_date'
            if reason:
                excluded.append(dict(ref, reason=reason))
                continue
            seen.add(hdu['frame_id'])
            meta = hdu['metadata']
            config = {key: meta.get(key) for key in CONFIG_KEYS}
            # Always retain the parent directory: unknown identities cannot merge across folders.
            config['directory'] = str(PurePosixPath(file['path']).parent)
            config['dimensions_fits_order'] = dimensions
            config['declared_date'] = time.date().isoformat()
            key = json.dumps(config, sort_keys=True, ensure_ascii=False, allow_nan=False)
            frame = dict(ref, date_obs_raw=meta.get('DATE-OBS'),
                         exptime_seconds_declared=_exposure(meta.get('EXPTIME')))
            buckets[key].append((time, frame))
    sessions = []
    for key, frames in sorted(buckets.items()):
        frames.sort(key=lambda item: (item[0], item[1]['frame_id'], item[1]['path']))
        chunks = [[]]
        for item in frames:
            if chunks[-1] and (item[0] - chunks[-1][-1][0]).total_seconds() > gap_seconds:
                chunks.append([])
            chunks[-1].append(item)
        for chunk in chunks:
            config = json.loads(key)
            members = [item[1] for item in chunk]
            gaps = [(b[0] - a[0]).total_seconds() for a, b in zip(chunk, chunk[1:])]
            exposures = [m['exptime_seconds_declared'] for m in members]
            known = [v for v in exposures if v is not None]
            missing = len(exposures) - len(known)
            flags = ['time_semantics_unverified', 'declared_calendar_date_not_observing_night']
            if config['TIMESYS'] is None:
                flags.append('missing_timesys')
            if any(config[key] in (None, '') for key in ('OBJECT', 'INSTRUME', 'FILTER', 'BAYERPAT', 'EQMODE')):
                flags.append('incomplete_configuration')
            if missing:
                flags.append('incomplete_exposure_sum')
            duplicate_times = sum(g == 0 for g in gaps)
            if duplicate_times:
                flags.append('duplicate_timestamps')
            identity = json.dumps({'method': 'sessions-1.0', 'configuration': config,
                                   'members': [m['frame_id'] for m in members]},
                                  sort_keys=True, ensure_ascii=False)
            sessions.append({'session_id': hashlib.sha256(identity.encode()).hexdigest(),
                             'configuration': config, 'frame_count': len(members), 'frames': members,
                             'first_time_raw': members[0]['date_obs_raw'],
                             'last_time_raw': members[-1]['date_obs_raw'],
                             'timestamp_span_seconds': (chunk[-1][0] - chunk[0][0]).total_seconds(),
                             'largest_gap_seconds': max(gaps, default=0),
                             'known_exposure_sum_seconds': sum(known) if known else None,
                             'total_exposure_seconds_declared': sum(known) if not missing else None,
                             'unknown_exposure_count': missing, 'duplicate_timestamp_count': duplicate_times,
                             'flags': flags, 'time_validated': False})
    sessions.sort(key=lambda item: (item['first_time_raw'], item['session_id']))
    hdus = sum(len(f['hdus']) for f in document['files'])
    summary = {'input_files': len(document['files']), 'input_hdus': hdus,
               'grouped_hdus': sum(s['frame_count'] for s in sessions),
               'excluded_hdus': len(excluded), 'session_count': len(sessions),
               'exclusion_reasons': dict(Counter(e['reason'] for e in excluded)),
               'file_incidents': len(file_events),
               'inventory_traversal_incidents': len(document.get('traversal_incidents', []))}
    assert summary['input_hdus'] == summary['grouped_hdus'] + summary['excluded_hdus']
    return {'session_schema_version': '1.0',
            'parameters': {'gap_seconds': gap_seconds, 'split_declared_date': True,
                           'separate_directories': True, 'time_conversion': 'none'},
            'sessions': sessions, 'excluded': excluded, 'file_events': file_events, 'summary': summary}
