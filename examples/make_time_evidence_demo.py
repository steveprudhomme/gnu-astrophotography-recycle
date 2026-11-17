# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Synthetic local workset for evidence preparation; no external source."""
import argparse
import json
from pathlib import Path
from astropy.io import fits
import numpy as np
from gar.workset import digest


def make_demo(output):
    output = Path(output)
    (output/'copies').mkdir(parents=True, exist_ok=False)
    files = []
    for i in range(1, 5):
        header = fits.Header()
        header['DATE-OBS'] = ('2025-01-01T00:00:00.123456', 'Image created time')
        header['EXPTIME'] = 10.
        header['PROGRAM'] = 'Synthetic acquisition software'
        if i >= 2:
            header['TIMESYS'] = 'UTC'; header['TIMEUNIT'] = 's'
            header['DATE-BEG'] = '2025-01-01T00:00:00'
            header['DATE-END'] = '2025-01-01T00:00:10'
            header['DATE-AVG'] = '2025-01-01T00:00:05'
            header['TELAPSE'] = 10.; header['TIMSYER'] = .001; header['TIMRDER'] = .0001
            header['FIRMWARE'] = 'FICTITIOUS-1.0'
        if i == 3:
            header.append(('DATE-OBS', '2025-01-01T00:00:01', 'Conflicting declaration'))
            header['DATE-END'] = '2024-12-31T23:59:59'
            header['EXPOSURE'] = 12.; header['TIMSYER'] = -.1
        data = np.zeros((3, 32, 32) if i == 4 else (32, 32), dtype=np.uint16)
        if i == 4:
            header['STACKCNT'] = 20; header['TOTALEXP'] = 200.
        path = output/'copies'/f'synthetic-{i}.fit'
        fits.writeto(path, data, header)
        files.append({'local_copy': f'copies/{path.name}', 'sha256_copy': digest(path),
                      'source': 'UNUSED_EXTERNAL_SOURCE_DO_NOT_OPEN'})
    (output/'workset.json').write_text(json.dumps({'success': True, 'files': files}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    make_demo(parser.parse_args().output)
