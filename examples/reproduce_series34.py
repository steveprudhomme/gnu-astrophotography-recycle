# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Bounded, guided reproduction of the sixteen authorized Seestar frames."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from satellite_recipe.pipeline import prepare, references, images, measure, orbits
from satellite_recipe.report import report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'references', 'images', 'measure', 'orbits', 'report'])
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--fits', type=Path, help='Exact folder containing the sixteen files; no recursive scan.')
    parser.add_argument('--catalog', type=Path, help='Previously downloaded complete SatChecker JSON cache.')
    parser.add_argument('--geoid', type=Path, help='Previously downloaded HT2_2010v70 grid.')
    parser.add_argument('--download-references', action='store_true', help='Permit the two documented reference downloads.')
    args = parser.parse_args()
    run = args.run.resolve()
    if ROOT / 'local' not in run.parents or run == ROOT / 'local':
        parser.error('--run must be a dedicated subfolder of this checkout local/.')
    try:
        if args.phase == 'prepare':
            result = prepare(run, args.fits)
        elif args.phase == 'references':
            result = references(run, args.catalog, args.geoid, args.download_references)
        else:
            result = dict(images=images, measure=measure, orbits=orbits, report=report)[args.phase](run)
    except (ValueError, OSError, RuntimeError) as error:
        print(f'Arrêt : {error}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
