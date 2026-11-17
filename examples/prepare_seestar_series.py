# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Offline series selection, then local-copy audit; copying uses gar workset."""
import argparse
import csv
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

from astropy.io import fits
import numpy as np

from gar.astrometry import local_path
from gar.contracts import json_value, parse_declared_time
from gar.sessions import load_manifest, group_sessions
from gar.workset import digest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_KEYS = ('OBJECT', 'INSTRUME', 'FILTER', 'GAIN', 'EQMODE', 'BAYERPAT', 'BITPIX', 'BSCALE', 'BZERO')
PLAN_COMMIT = '594c19ede1e38a227e966f09ae7fc9588e6768ce'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def source_path(root, relative):
    """Lexical binding only: do NOT resolve, stat or open an archive path here."""
    p = PurePosixPath(relative)
    if (not relative or p.is_absolute() or PureWindowsPath(relative).drive or '\\' in relative
            or ':' in relative or '..' in p.parts or relative != p.as_posix()):
        raise ValueError('Chemin relatif d’archive dangereux ou non canonique.')
    return root.joinpath(*p.parts)


def plan_series(manifest_path, source_root, output, count=8, base=None):
    base = ROOT/'local' if base is None else base
    mp, output = [local_path(p, base) for p in (manifest_path, output)]
    if type(count) is not int or not 8 <= count <= 64:
        raise ValueError('Demander entre huit et 64 poses.')
    source_root = Path(os.path.abspath(source_root))  # Explicit root, no filesystem probe.
    manifest, manifest_hash = load_manifest(mp)
    for f in manifest['files']:
        source_path(source_root, f['path'])
    grouped = group_sessions(manifest, 1800)
    indexed = {(f['path'], h['hdu_index']): (f, h) for f in manifest['files'] for h in f['hdus']}
    candidates, chosen = [], None
    for session in sorted(grouped['sessions'], key=lambda s: (-s['frame_count'], s['session_id'])):
        eligible = None
        rejected = {}
        for start in range(max(0, len(session['frames'])-count+1)):
            block = session['frames'][start:start+count]
            reason = None
            if any(f['hdu_index'] != 0 for f in block): reason = 'not_primary'
            elif len({indexed[f['path'], 0][0]['sha256'] for f in block}) != count: reason = 'repeated_file_hash'
            elif len({f['path'] for f in block}) != count: reason = 'repeated_file_path'
            elif any(indexed[f['path'], 0][1]['metadata'].get('STACKCNT') not in (None, 1) for f in block): reason = 'stack_counter'
            if reason is None:
                times = [parse_declared_time(f['date_obs_raw']) for f in block]
                if any(not 0 < (b-a).total_seconds() <= 30 for a, b in zip(times, times[1:])):
                    reason = 'duplicate_or_gap_over_30_declared_seconds'
            if reason:
                rejected[reason] = rejected.get(reason, 0)+1
                continue
            eligible = (start, block)
            break
        candidates.append(dict(session_id=session['session_id'], frame_count=session['frame_count'],
                               admissible=eligible is not None, first_block_offset=eligible[0] if eligible else None,
                               rejected_window_reasons=rejected))
        if chosen is None and eligible:
            chosen = (session, *eligible)
    plan = dict(series_plan_schema_version='1.0', plan_commit=PLAN_COMMIT, requested_count=count,
                inventory_sha256=manifest_hash, source_root=str(source_root),
                sources_accessed_during_planning=False, source_root_bound_explicitly=True,
                policy=dict(session_gap_seconds=1800, maximum_block_gap_declared_seconds=30,
                            ranking='session size descending then session id; first admissible chronological block'),
                candidates=candidates, inventory_exclusions=grouped['summary'], selection_available=chosen is not None,
                clock_qualified=False, source_availability_verified=False)
    if chosen:
        session, offset, block = chosen
        selected = []
        for frame in block:
            file, hdu = indexed[frame['path'], 0]
            selected.append(dict(**frame, sha256=file['sha256'], dimensions_fits_order=hdu['dimensions_fits_order'],
                                 metadata=hdu['metadata']))
        selection = dict(selection_schema_version='1.0', files=[dict(source=str(source_path(source_root, f['path'])),
                         expected_sha256=f['sha256'], role='individual_series_frame') for f in selected])
        plan.update(session_id=session['session_id'], first_block_offset=offset,
                    configuration=session['configuration'], frames=selected, selection=selection)
    if digest(mp) != manifest_hash: raise ValueError('Le manifeste local a changé.')
    output.mkdir(parents=True, exist_ok=False)
    save(output/'plan.json', plan)
    if chosen: save(output/'selection.json', selection)
    text = '# Préparation locale d’une série\n\n'
    text += f'Sélection disponible dans le manifeste : {plan["selection_available"]}. Sources non ouvertes pendant la planification.\n\n'
    text += 'Cette liste ne prouve ni disponibilité du support ni qualité scientifique. Racine source explicitement liée ; copie par gar workset avant audit local.\n'
    (output/'report.md').write_text(text, encoding='utf-8')
    print(f'Plan local produit ; sélection de {count} poses : {plan["selection_available"]}. Sources non ouvertes.')
    return plan


def audit_series(plan_path, workset_path, output, base=None):
    base = ROOT/'local' if base is None else base
    pp, wp, output = [local_path(p, base) for p in (plan_path, workset_path, output)]
    watched = {pp: digest(pp), wp: digest(wp)}
    plan, workset = [json.loads(p.read_text(encoding='utf-8')) for p in (pp, wp)]
    if (plan.get('series_plan_schema_version') != '1.0' or not plan.get('selection_available')
            or type(plan.get('requested_count')) is not int or not 8 <= plan['requested_count'] <= 64
            or len(plan.get('frames', [])) != plan['requested_count'] or not workset.get('success')
            or len(workset.get('files', [])) != plan['requested_count'] or workset.get('selection') != plan['selection']):
        raise ValueError('Plan et workset complets et correspondants requis.')
    if output.exists(): raise ValueError('Choisir une nouvelle sortie locale.')
    paths, seen = [], set()
    for frame, item in zip(plan['frames'], workset['files']):
        path = local_path(wp.parent/item['local_copy'], base)
        if (wp.parent not in path.parents or path in seen or frame['sha256'] in seen
                or any(item.get(k) != frame['sha256'] for k in ('sha256_before', 'sha256_copy', 'sha256_after'))
                or digest(path) != frame['sha256']):
            raise ValueError('Copie incohérente, dupliquée ou modifiée.')
        watched[path] = frame['sha256']; paths.append(path)
        seen.add(path); seen.add(frame['sha256'])
    output.mkdir(parents=True, exist_ok=False)
    result = dict(series_audit_schema_version='1.0', status='running', copies_prepared=False,
                  requested_count=plan['requested_count'], files=[], issues=[],
                  clock_qualified=False, common_field_validated_on_stars=False,
                  motion_searched=False, science_validated=False, pixels_rewritten=False,
                  source_files_opened_during_audit=False, plan_sha256=watched[pp], workset_sha256=watched[wp])
    save(output/'series.json', result)
    try:
        for index, (frame, path) in enumerate(zip(plan['frames'], paths), 1):
            with fits.open(path, mode='readonly', memmap=False) as hdus:
                h = hdus[0].header
                if h.get('NAXIS') != 2 or hdus[0].data is None: raise ValueError('Primaire 2D requise.')
                pixels = hdus[0].data
                meta = {k: json_value(h.get(k)) for k in CONFIG_KEYS}
                dims = [h.get('NAXIS1'), h.get('NAXIS2')]
                issues = []
                if dims != frame['dimensions_fits_order'] or list(pixels.shape) != list(reversed(dims)):
                    issues.append('dimensions_differ_from_plan')
                for key in CONFIG_KEYS:
                    if meta[key] != frame['metadata'].get(key): issues.append('header_differs_'+key)
                    if sum(c.keyword == key for c in h.cards) > 1: issues.append('ambiguous_duplicate_'+key)
                date = json_value(h.get('DATE-OBS')); exposure = json_value(h.get('EXPTIME'))
                if date != frame['date_obs_raw']: issues.append('date_differs_from_plan')
                if exposure != frame['exptime_seconds_declared']: issues.append('exposure_differs_from_plan')
                if sum(c.keyword == 'DATE-OBS' for c in h.cards) != 1: issues.append('ambiguous_date')
                plane = np.asarray(pixels, dtype=float)
                finite = np.isfinite(plane)
                if not finite.all(): issues.append('nonfinite_pixels')
                values = plane[finite]
                stats = dict(shape=list(pixels.shape), decoded_dtype=str(pixels.dtype), finite_pixels=int(finite.sum()),
                             total_pixels=int(plane.size), pixels_ge_65000=int(np.count_nonzero(plane >= 65000)),
                             minimum=float(values.min()) if values.size else None,
                             maximum=float(values.max()) if values.size else None,
                             median=float(np.median(values)) if values.size else None)
                entry = dict(sequence_index=index, local_copy=str(path), sha256=frame['sha256'], metadata=meta,
                             date_obs_raw=date, exptime_seconds_declared=exposure, pixels=stats, issues=issues,
                             unknown_configuration_fields=[k for k, v in meta.items() if v is None],
                             declared_time_scale=json_value(h.get('TIMESYS')),
                             primary_celestial_axes_declared=bool(h.get('CTYPE1') and h.get('CTYPE2')),
                             synthetic_marker_present=h.get('GARSYNTH') is True)
            result['files'].append(entry)
            result['issues'].extend(dict(sequence_index=index, reason=i) for i in issues)
            save(output/'series.json', result)
        times = [parse_declared_time(f['date_obs_raw']) for f in result['files']]
        gaps = [(b-a).total_seconds() for a, b in zip(times, times[1:])]
        if any(not 0 < gap <= 30 for gap in gaps): result['issues'].append(dict(reason='invalid_declared_order_or_gap'))
        if any(f['metadata'] != result['files'][0]['metadata'] for f in result['files']):
            result['issues'].append(dict(reason='configuration_not_constant'))
        if any(digest(path) != value for path, value in watched.items()): raise ValueError('Une entrée locale a changé.')
        result.update(status='complete', copies_prepared=not result['issues'],
                      input_hashes_unchanged=True, declared_span_seconds=(times[-1]-times[0]).total_seconds(),
                      declared_gaps_seconds=gaps, prepared_count=len(result['files']))
        save(output/'series.json', result)
        with (output/'series.csv').open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['sequence_index', 'sha256', 'width', 'height', 'finite_pixels', 'pixels_ge_65000', 'issue_count'])
            for f in result['files']:
                writer.writerow([f['sequence_index'], f['sha256'], f['pixels']['shape'][1], f['pixels']['shape'][0],
                                 f['pixels']['finite_pixels'], f['pixels']['pixels_ge_65000'], len(f['issues'])])
        text = (f'# Série locale préparatoire\n\nCopies préparées : {result["copies_prepared"]}. '
                f'Fichiers contrôlés : {len(result["files"])}.\n\n'
                'Contrôle d’intégrité, configuration et lecture des pixels uniquement. Les champs absents restent inconnus. '
                'La durée et les intervalles sont calendaires déclarés, sans qualification d’horloge ou heure UTC de milieu de pose. '
                'Le comptage ≥65 000 ne prouve pas une saturation étalonnée. Aucun recalage stellaire, mouvement ou mesure scientifique validé. '
                'Les copies exactes ne sont pas modifiées ; les chemins sources ne sont pas consultés par cet audit.\n')
        (output/'report.md').write_text(text, encoding='utf-8')
    except Exception as exc:
        result.update(status='incomplete', copies_prepared=False, error=str(exc)); save(output/'series.json', result)
        raise
    print(f'{len(result["files"])} copies locales contrôlées ; préparation : {result["copies_prepared"]}. Aucune recherche de mobile.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    plan = sub.add_parser('plan'); plan.add_argument('manifest', type=Path)
    plan.add_argument('--source-root', type=Path, required=True); plan.add_argument('--count', type=int, default=8)
    plan.add_argument('--output', type=Path, required=True)
    audit = sub.add_parser('audit')
    for field in ('plan', 'workset'): audit.add_argument(field, type=Path)
    audit.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'plan':
            r = plan_series(args.manifest, args.source_root, args.output, args.count)
            raise SystemExit(0 if r['selection_available'] else 2)
        r = audit_series(args.plan, args.workset, args.output)
        raise SystemExit(0 if r['copies_prepared'] else 2)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
