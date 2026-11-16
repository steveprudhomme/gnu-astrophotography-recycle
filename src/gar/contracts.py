# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: inventory exchange constants and safe values.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Version 1 contract: JSON null means unknown, not zero."""
import math
from datetime import datetime
import re

SCHEMA_VERSION = "1.0"
KEYWORDS = (
    "OBJECT", "INSTRUME", "IMAGETYP", "DATE-OBS", "TIMESYS", "EXPTIME",
    "EXPOSURE", "FILTER", "RA", "DEC", "SITELAT", "SITELONG", "BAYERPAT",
    "XBAYROFF", "YBAYROFF", "BSCALE", "BZERO", "BITPIX", "BUNIT", "GAIN",
    "EQMODE", "STACKCNT", "TOTALEXP", "CTYPE1", "CTYPE2", "CRPIX1", "CRPIX2",
    "CRVAL1", "CRVAL2", "CD1_1", "CD1_2", "CD2_1", "CD2_2",
)

DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\Z')


def parse_declared_time(value):
    """Parse the supported subset without assigning or converting a time scale."""
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise ValueError('Date complète sans suffixe, avec au plus 6 décimales, attendue.')
    return datetime.fromisoformat(value)


def json_value(value):
    """Keep primitive FITS values; never emit JSON NaN or Infinity."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return str(value)
