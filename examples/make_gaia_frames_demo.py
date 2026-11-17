# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Three synthetic frames and a fictitious Gaia-shaped catalog; no download."""
from pathlib import Path
import argparse
import importlib.util
import json
import numpy as np
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
from gar.workset import digest

spec = importlib.util.spec_from_file_location('registration_generator', Path(__file__).with_name('make_registration_demo.py'))
registration_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registration_generator)


def make_demo(output, bias_arcsec=.5):
    output = Path(output)
    registration_generator.make_demo(output)
    points, _ = registration_generator.synthetic_points()
    wp = output/'workset.json'
    workset = json.loads(wp.read_text(encoding='utf-8'))
    path = output/workset['files'][3]['local_copy']
    with fits.open(path, mode='readonly', memmap=False) as hdus:
        true_wcs = WCS(hdus[0].header, naxis=2)
    sky = true_wcs.pixel_to_world(points[:, 0], points[:, 1])
    n = len(points)
    catalog = Table({'source_id': np.arange(n)+100000, 'ra': sky.ra.deg, 'dec': sky.dec.deg,
                     'pmra': np.zeros(n), 'pmdec': np.zeros(n), 'ref_epoch': np.full(n, 2016.),
                     'phot_g_mean_mag': np.full(n, 13.), 'ruwe': np.ones(n)})
    catalog_path = output/'catalog.csv'
    catalog.write(catalog_path, format='ascii.csv')
    (output/'provenance.json').write_text(json.dumps({'provider': 'SYNTHETIC — NOT GAIA OBSERVATIONS',
        'sha256': digest(catalog_path), 'injected_east_bias_arcsec': bias_arcsec}, indent=2), encoding='utf-8')
    for index, item in enumerate(workset['files']):
        path = output/item['local_copy']
        with fits.open(path, mode='readonly', memmap=False) as hdus:
            data, header = hdus[0].data.copy(), hdus[0].header.copy()
        header['DATE-OBS'] = '2025-01-01T00:00:00'
        if index == 3:
            header['CRVAL1'] += bias_arcsec/(3600*np.cos(np.deg2rad(30)))
        # Rewriting only freshly generated synthetic inputs, before their registration.
        fits.writeto(path, data, header, overwrite=True)
        item['sha256_copy'] = digest(path)
    wp.write_text(json.dumps(workset, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--bias-arcsec', type=float, default=.5)
    args = parser.parse_args()
    make_demo(args.output, args.bias_arcsec)
