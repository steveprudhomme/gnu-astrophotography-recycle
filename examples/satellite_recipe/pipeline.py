# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Read-only inputs, explicit references, frozen guided measurement and search."""
from pathlib import Path
from importlib.metadata import version
import hashlib
import json
import shutil
import subprocess
import warnings
from urllib.parse import urlencode
import numpy as np
from scipy import ndimage
from astropy.io import fits
from astropy.wcs import WCS
from gar.registration import detect, register_points
from spatial_controls import register_spatial
from .imaging import line_fit, detect_lines
from .orbit import (Satrec, Time, u, SkyCoord, SkyOffsetFrame, EarthLocation,
                    AltAz, altaz, checks, compatible_intervals)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'examples/data/seestar-series34'
GRID = 'ca_nrc_HT2_2010v70.tif'
GRID_SHA = '5033fa377cb734a99a849b11bf6f8e99ec998b131224969f00f22f966456b773'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, document):
    Path(path).write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_copy(source, target, expected=None):
    source, target = Path(source), Path(target)
    before = digest(source)
    if expected is not None and before != expected:
        raise ValueError(f'Empreinte différente : {source.name}')
    with source.open('rb') as incoming, target.open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing)
    if digest(source) != before or digest(target) != before:
        raise ValueError('Source ou copie modifiée pendant la copie.')
    return before


def frames(run):
    rows = read(run / 'inputs.json')['frames']
    for row in rows:
        if digest(run / 'fits' / row['file']) != row['sha256']:
            raise ValueError(f'Copie modifiée : {row["frame_id"]}')
    return rows


def prepare(run, source_folder=None):
    if run.exists():
        raise ValueError('Choisir un nouveau dossier de travail ; aucune sortie ancienne écrasée.')
    source_folder = (source_folder or DATA).resolve()
    manifest = read(DATA / 'manifest.json')
    # Validate ALL inputs before creating the run. Exact names only; never enumerate sources.
    sources = []
    for row in manifest['frames']:
        source = source_folder / row['file']
        if not source.exists():
            source = source_folder / row['original_name']
        if digest(source) != row['sha256']:
            raise ValueError(f'Ce fichier diffère de la sélection publiée : {row["frame_id"]}')
        with fits.open(source, mode='readonly', memmap=False) as hdus:
            header = hdus[0].header
            if hdus[0].data.shape != (1920, 1080) or float(header['EXPTIME']) != 10:
                raise ValueError('Dimensions ou durée inattendues.')
            if header['DATE-OBS'] != row['date_obs']:
                raise ValueError('Date différente du manifeste.')
        sources.append(source)
    run.mkdir(parents=True)
    (run / 'fits').mkdir()
    for source, row in zip(sources, manifest['frames']):
        checked_copy(source, run / 'fits' / row['file'], row['sha256'])
    write(run / 'inputs.json', manifest)
    write(run / 'environment.json', {n: version(n) for n in ['numpy', 'scipy', 'astropy',
          'astropy-iers-data', 'photutils', 'matplotlib', 'pillow', 'sgp4', 'pyproj']})
    return dict(copies=16, hashes_equal=True, source_access='exact_read_only_paths', large_archive_started=False)


def download(url, target):
    """A bounded HTTPS request, no redirects or hidden retries."""
    partial = target.with_suffix(target.suffix + '.part')
    command = ['curl.exe' if __import__('os').name == 'nt' else 'curl', '-4', '--fail',
               '--connect-timeout', '10', '--max-time', '45', '--silent', '--show-error',
               '--output', str(partial), url]
    result = subprocess.run(command, capture_output=True, text=True, timeout=50,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Téléchargement arrêté : ' + result.stderr[:400])
    partial.replace(target)


def references(run, catalog=None, geoid=None, permit=False):
    frames(run)
    folder = run / 'references'
    folder.mkdir(exist_ok=True)
    if (catalog is None or geoid is None) and not permit:
        raise ValueError('Fournir les deux caches, ou --download-references après lecture du tutoriel.')
    if catalog:
        checked_copy(catalog, folder / 'catalogue.json')
    elif not (folder / 'catalogue.json').exists():
        provenance = read(DATA / 'orbital-provenance.json')
        rows, page, total = [], 1, None
        while total is None or len(rows) < total:
            url = provenance['endpoint'] + '?' + urlencode(dict(epoch=provenance['epoch_jd'],
                   page=page, per_page=2000, format='json'))
            target = folder / f'page-{page:04}.json'
            if not target.exists():
                download(url, target)
            data = read(target)
            response = data[0] if isinstance(data, list) else data
            if total is None:
                total = response['total_results']
            if (response['total_results'] != total or response['page'] != page
                    or not response['data'] or page >= 1000):
                raise ValueError('Pagination incohérente ; catalogue incomplet conservé.')
            rows.extend(response['data'])
            print(f'Catalogue : {len(rows)}/{total}', flush=True)
            page += 1
        if len(rows) != total:
            raise ValueError('Nombre de lignes différent du total annoncé.')
        write(folder / 'catalogue.json', dict(total=total, rows=rows, pagination_complete=True,
              epoch=provenance['epoch_jd'], transmitted='date_only'))
    doc = read(folder / 'catalogue.json')
    provenance = read(DATA / 'orbital-provenance.json')
    if (not doc.get('pagination_complete') or len(doc['rows']) != doc['total']
            or str(doc['epoch']) != provenance['epoch_jd']):
        raise ValueError('Le cache ne décrit pas le catalogue complet à la date attendue.')
    if geoid:
        checked_copy(geoid, folder / GRID, GRID_SHA)
    elif not (folder / GRID).exists():
        download('https://cdn.proj.org/' + GRID, folder / GRID)
    if digest(folder / GRID) != GRID_SHA:
        raise ValueError('La grille géodésique diffère de la grille documentée.')
    receipt = dict(rows=doc['total'], catalogue_sha256=digest(folder / 'catalogue.json'),
                   grid_sha256=GRID_SHA, external_payload='date_only; grid_request_without_coordinates',
                   exact_historical_cache=digest(folder / 'catalogue.json') == provenance['original_cache_sha256'])
    write(run / 'reference-receipt.json', receipt)
    return receipt


def map_points(points, model):
    return np.asarray(points) @ np.array(model['rotation_matrix']).T + model['translation_pixels']


def images(run):
    rows = frames(run)
    calibration = read(DATA / 'calibration.json')
    if digest(DATA / 'reference-stars.csv') != calibration['reference_stars_sha256']:
        raise ValueError('Centres de référence modifiés.')
    pixels = {r['frame_id']: fits.getdata(run / 'fits' / r['file']).astype(float) for r in rows}
    points = {key: detect(value)[0] for key, value in pixels.items()}
    reference = np.loadtxt(DATA / 'reference-stars.csv', delimiter=',', skiprows=1)
    bridge = register_points(points['S03-01'], reference, pixels['S03-01'].shape)
    cross = register_spatial(points['S04-01'], points['S03-01'], pixels['S03-01'].shape)
    models = {}
    for row in rows:
        key = row['frame_id']
        # Preserve the historical exact identity: tiny fit roundoff changes edge masks.
        models[key] = (dict(model_usable=True, kind='measured_reference_identity',
                           rotation_matrix=np.eye(2).tolist(), translation_pixels=[0., 0.], independent_control=False)
                       if row['pose'] == 1 else register_spatial(points[key], points[row['series'] + '-01'], pixels[key].shape))
        if not models[key]['model_usable']:
            raise ValueError('Recalage refusé : ' + key)
    if not bridge['model_usable'] or not cross['model_usable']:
        raise ValueError('Pont vers la référence refusé.')
    write(run / 'registration.json', dict(bridge=bridge, cross=cross, models=models,
          supplied_calibration=True, independent_WCS_reconstruction=False))
    proposals = []
    for series in ['S03', 'S04']:
        planes = []
        for pose in range(1, 9):
            key = f'{series}-{pose:02}'
            image = pixels[key]
            h, w = image.shape
            blocks = image.reshape(h // 4, 4, w // 4, 4)
            reduced = blocks.mean(axis=(1, 3))
            reduced[(~np.isfinite(blocks) | (blocks >= 65000)).any(axis=(1, 3))] = np.nan
            reduced -= np.nanmedian(reduced)
            r = np.array(models[key]['rotation_matrix'])
            t = np.array(models[key]['translation_pixels'])
            offset = ((np.array([1.5, 1.5]) - t) @ r - 1.5) / 4
            planes.append(ndimage.affine_transform(reduced, r.T[::-1, ::-1],
                          offset=offset[::-1], order=1, cval=np.nan, prefilter=False))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            background = np.nanmedian(planes, axis=0)
        for pose, plane in enumerate(planes, 1):
            key = f'{series}-{pose:02}'
            difference = plane - background
            found = detect_lines(difference)
            np.savez_compressed(run / (key + '-difference.npz'), difference=difference)
            proposals.append(dict(frame_id=key, proposals=found, count=len(found)))
            print(f'{key} : {len(found)} propositions, pas des objets confirmés', flush=True)
    write(run / 'proposals.json', dict(rows=proposals, threshold=8, binning=4,
          angular_step_deg=.5, minimum_support=100, false_alarm_rate_validated=False))
    frames(run)
    return dict(frames=16, proposals=sum(p['count'] for p in proposals), registrations_accepted=True)


def measure(run):
    rows = {r['frame_id']: r for r in frames(run)}
    registration = read(run / 'registration.json')
    calibration = read(DATA / 'calibration.json')
    wcs = WCS(fits.Header.fromstring(calibration['reference_wcs_header'], sep='\n'), naxis=2, fix=False)
    results = []
    for selection in read(DATA / 'review-selection.json')['selection']:
        key = selection['frame_id']
        row = rows[key]
        measurement = line_fit(fits.getdata(run / 'fits' / row['file']), selection['initial_native_endpoints'])
        points = map_points(measurement['native_endpoints'], registration['models'][key])
        if row['series'] == 'S04':
            points = map_points(points, registration['cross'])
        points = map_points(points, registration['bridge'])
        sky = wcs.pixel_to_world(points[:, 0], points[:, 1])
        results.append(dict(frame_id=key, sha256=row['sha256'], date_obs=row['date_obs'],
             exptime=row['exposure_seconds'], measurement=measurement, visual_status=selection['visual_status'],
             sky_endpoints=[dict(ra_deg=float(a), dec_deg=float(d)) for a, d in zip(sky.ra.deg, sky.dec.deg)],
             identity_confirmed=False, clock_qualified=False))
    write(run / 'measurements.json', dict(traces=results, guided_selection=True, blind_detection=False))
    return dict(measured=4, source_FITS_unchanged=True, independent_WCS_reconstruction=False)


def height(run):
    from pyproj import Transformer, network, datadir
    network.set_network_enabled(False)
    datadir.append_data_dir(str(run / 'references'))
    if digest(run / 'references' / GRID) != GRID_SHA:
        raise ValueError('Grille modifiée.')
    header = fits.getheader(run / 'fits/S03-01.fit')
    lon, lat = float(header['SITELONG']), float(header['SITELAT'])
    transformer = Transformer.from_pipeline('+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad '
                 '+step +proj=vgridshift +grids=' + GRID + ' +multiplier=1 '
                 '+step +proj=unitconvert +xy_in=rad +xy_out=deg')
    converted = transformer.transform(lon, lat, 68, errcheck=True)
    back = transformer.transform(*converted, direction='INVERSE', errcheck=True)
    if not np.allclose(back, [lon, lat, 68], atol=1e-7):
        raise ValueError('Retour de conversion géodésique incorrect.')
    write(run / 'height.json', dict(terrain_CGVD28_m=68, ellipsoidal_NAD83CSRS_m=converted[2],
          terrain_source='RNCan CDEM lookup recorded in the study; value supplied, not surveyed',
          horizontal_realization_verified=False, telescope_height_surveyed=False))
    return EarthLocation.from_geodetic(lon * u.deg, lat * u.deg, converted[2] * u.m)


def orbits(run):
    rows = frames(run)
    write(run / 'orbit-checks.json', checks())
    receipt = read(run / 'reference-receipt.json')
    if digest(run / 'references/catalogue.json') != receipt['catalogue_sha256']:
        raise ValueError('Catalogue modifié depuis sa réception.')
    catalog = read(run / 'references/catalogue.json')
    unique = {}
    for row in catalog['rows']:
        unique.setdefault((row['satellite_id'], row['tle_line1'], row['tle_line2']), row)
    epoch0 = Time(rows[0]['date_obs'], scale='utc')
    records, satellites, excluded = [], [], dict(parse_error=0, epoch_more_than_seven_days=0)
    for row in unique.values():
        try:
            satellite = Satrec.twoline2rv(row['tle_line1'], row['tle_line2'])
        except (ValueError, TypeError):
            excluded['parse_error'] += 1
            continue
        if abs(epoch0.jd - satellite.jdsatepoch - satellite.jdsatepochF) > 7:
            excluded['epoch_more_than_seven_days'] += 1
            continue
        records.append(row)
        satellites.append(satellite)
    if not satellites:
        raise ValueError('Aucun élément orbital admissible.')
    site = height(run)
    results = []
    for trace in read(run / 'measurements.json')['traces']:
        epoch = Time(trace['date_obs'], scale='utc')
        endpoints = SkyCoord([p['ra_deg'] for p in trace['sky_endpoints']] * u.deg,
                            [p['dec_deg'] for p in trace['sky_endpoints']] * u.deg, frame='icrs')
        center = SkyCoord(ra=endpoints.ra.mean(), dec=endpoints.dec.mean(), frame='icrs')
        coarse_t = epoch + np.array([-10, 0, 10, 20]) * u.s
        aa, error = altaz(satellites, coarse_t, site)
        field = center.transform_to(AltAz(obstime=coarse_t, location=site, pressure=0 * u.hPa))
        distance = aa.separation(field).deg
        selected = np.flatnonzero(np.any((error == 0) & (aa.alt.deg > 0)
                                  & np.isfinite(distance) & (distance < 10), axis=1))
        offsets = np.linspace(-10, 20, 301)
        times = epoch + offsets * u.s
        ranked = []
        error_counts = {str(int(code)): int((error == code).sum()) for code in np.unique(error) if code}
        fine_error_counts = {}
        if len(selected):
            aa, error = altaz([satellites[i] for i in selected], times, site)
            fine_error_counts = {str(int(code)): int((error == code).sum()) for code in np.unique(error) if code}
            angular = SkyCoord(az=aa.az, alt=aa.alt,
                       frame=AltAz(obstime=times, location=site, pressure=0 * u.hPa)).icrs
            tangent = angular.transform_to(SkyOffsetFrame(origin=center))
            xy = np.stack([tangent.lon.deg, tangent.lat.deg], axis=-1)
            reference = endpoints.transform_to(SkyOffsetFrame(origin=center))
            a = np.array([reference.lon.deg[0], reference.lat.deg[0]])
            b = np.array([reference.lon.deg[1], reference.lat.deg[1]])
            length = np.linalg.norm(b - a)
            unit = (b - a) / length
            for k, index in enumerate(selected):
                delta = xy[k] - a
                along = delta @ unit / length
                cross = (delta[:, 0] * unit[1] - delta[:, 1] * unit[0]) * 3600
                valid = (error[k] == 0) & np.isfinite(xy[k]).all(axis=1) & (aa.alt.deg[k] > 0) & (along >= 0) & (along <= 1)
                if valid.sum() < 3:
                    continue
                j = np.argmin(np.where(valid, abs(cross), np.inf))
                gradient = np.gradient(xy[k], offsets, axis=0)
                speed = np.linalg.norm(gradient[j])
                angle = float(np.rad2deg(np.arccos(np.clip(abs(gradient[j] @ unit) / max(speed, 1e-20), 0, 1))))
                row = records[index]
                ranked.append(dict(norad_id=row['satellite_id'], name=row['satellite_name'], source=row['data_source'],
                    median_cross_track_arcsec=float(np.median(abs(cross[valid]))),
                    minimum_cross_track_arcsec=float(abs(cross[j])), orientation_difference_degrees=angle,
                    orbital_element_age_days=float(abs(epoch.jd - satellites[index].jdsatepoch - satellites[index].jdsatepochF)),
                    time_compatibility=compatible_intervals(offsets, along, trace['exptime']),
                    tle_sha256=hashlib.sha256((row['tle_line1']+'\n'+row['tle_line2']).encode()).hexdigest(),
                    status='ranked_hypothesis_not_confirmed'))
        ranked.sort(key=lambda r: (r['median_cross_track_arcsec'], r['orientation_difference_degrees']))
        results.append(dict(frame_id=trace['frame_id'], ranked_hypotheses=ranked,
              fine_orbital_sets=len(selected), coarse_sgp4_errors=error_counts,
              fine_sgp4_errors=fine_error_counts, identity_confirmed=False))
        print(trace['frame_id'], ' : ', [(r['name'], round(r['median_cross_track_arcsec'], 2)) for r in ranked[:2]], flush=True)
    write(run / 'orbital-results.json', dict(results=results, unique_element_sets=len(unique),
          eligible_element_sets=len(satellites), excluded=excluded, all_eligible_names_searched=True,
          expected_answers_read=False, clock_qualified=False, large_archive_started=False))
    return dict(traces=4, eligible_element_sets=len(satellites), expected_answers_read=False)
