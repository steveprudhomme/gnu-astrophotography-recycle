# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: partial-manifest WCS diagnostics.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Inspect observed parameters, without constructing or certifying a sky WCS."""
from collections import Counter
import math
import re

import numpy as np

AXIS = re.compile(r'^(RA---|DEC--)([A-Z0-9]{3})(-SIP)?$')
PROJECTIONS = {'TAN','SIN','ARC','STG','ZEA','AIR','CAR','MER','CEA','CYP','SFL',
               'PAR','MOL','AIT','COP','COE','COD','COO','BON','PCO','TSC','CSC',
               'QSC','HPX','XPH','ZPN','NCP','GLS'}
REFERENCE_KEYS = ('CRPIX1','CRPIX2','CRVAL1','CRVAL2')
CD_KEYS = ('CD1_1','CD1_2','CD2_1','CD2_2')


def finite_number(value):
    try:
        return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:
        return False


def _check_parameters(row, meta, dimensions, max_condition):
    missing = [k for k in REFERENCE_KEYS + CD_KEYS if meta.get(k) is None]
    invalid = [k for k in REFERENCE_KEYS + CD_KEYS
               if meta.get(k) is not None and not finite_number(meta[k])]
    row['missing_parameters'] = missing
    row['invalid_parameters'] = invalid
    if missing:
        if any(meta.get(k) is not None for k in ('CDELT1','CDELT2','PC1_1','PC1_2','PC2_1','PC2_2')):
            row['flags'].append('other_linear_parameterization_not_evaluated')
        return 'parameters_incomplete'
    if invalid:
        return 'parameters_invalid'
    dec_axis = 1 if meta['CTYPE1'].startswith('DEC--') else 2
    unit = meta.get(f'CUNIT{dec_axis}')
    factors = {'deg':1.0,'rad':180/math.pi,'arcmin':1/60,'arcsec':1/3600}
    if isinstance(unit,str) and unit in factors:
        if abs(meta[f'CRVAL{dec_axis}']*factors[unit])>90:
            row['invalid_parameters'].append(f'CRVAL{dec_axis}')
            row['flags'].append('declination_outside_range_in_observed_units')
            return 'parameters_invalid'
    # A reference pixel outside the image is legal, so this is informational only.
    row['reference_pixel_outside_pixel_center_range'] = not (
        1 <= meta['CRPIX1'] <= dimensions[0] and 1 <= meta['CRPIX2'] <= dimensions[1])
    if row['reference_pixel_outside_pixel_center_range']:
        row['flags'].append('reference_pixel_outside_centers_not_inherently_invalid')
    matrix = np.array([[meta['CD1_1'],meta['CD1_2']],
                       [meta['CD2_1'],meta['CD2_2']]],dtype=float)
    scale = float(np.max(np.abs(matrix)))
    if scale == 0:
        row['matrix_nonsingular'] = False
        return 'linear_matrix_singular'
    # Scaling avoids overflow without changing singularity or the condition number.
    scaled = matrix / scale
    if np.any((matrix != 0) & (scaled == 0)):
        row['flags'].append('normalization_underflow_numerical_limit')
        return 'linear_matrix_ill_conditioned'
    try:
        sign, logdet = np.linalg.slogdet(scaled)
        condition = float(np.linalg.cond(scaled))
    except np.linalg.LinAlgError:
        row['flags'].append('linear_algebra_failed')
        return 'parameters_invalid'
    row['matrix_nonsingular'] = bool(sign != 0)
    row['matrix_condition_number_raw_units'] = condition if math.isfinite(condition) else None
    if sign == 0:
        return 'linear_matrix_singular'
    if not math.isfinite(condition) or condition > max_condition:
        return 'linear_matrix_ill_conditioned'
    return 'linear_block_consistent_context_incomplete'


def describe_wcs(hdu, max_condition):
    meta = hdu['metadata']
    ctypes = [meta.get('CTYPE1'),meta.get('CTYPE2')]
    row = {'ctype_observed':ctypes,
           'parameters_observed':{k:meta.get(k) for k in REFERENCE_KEYS+CD_KEYS+('CUNIT1','CUNIT2')},
           'pointing_values_present':meta.get('RA') is not None and meta.get('DEC') is not None,
           'primary_axes_observed':all(v is not None for v in ctypes),
           'flags':['full_wcs_context_not_captured_by_inventory_1_0'],
           'missing_parameters':[], 'invalid_parameters':[],
           'matrix_nonsingular':None, 'matrix_condition_number_raw_units':None,
           'reference_pixel_outside_pixel_center_range':None,
           'celestial_transform_reconstructed':False, 'wcs_validated':False,
           'astrometric_accuracy_arcsec':None, 'catalog_residuals_arcsec':None,
           'recommended_next_step':'inspect_full_header_before_any_astrometric_use'}
    if hdu['kind'] in ('empty_primary','table_or_other'):
        row['status']='not_image_hdu'
        return row
    dimensions = hdu['dimensions_fits_order']
    if len(dimensions)<2 or any(type(d) is not int or d<=0 for d in dimensions[:2]):
        row['status']='invalid_image_dimensions'
        return row
    if all(v is None for v in ctypes):
        row['status']='primary_axes_not_observed'
        row['recommended_next_step']='inspect_full_header_or_plate_solve_if_no_solution_exists'
        return row
    if any(v is None for v in ctypes):
        row['status']='axes_incomplete'
        return row
    axes = [AXIS.fullmatch(v) if isinstance(v,str) else None for v in ctypes]
    if not all(axes) or {a.group(1) for a in axes} != {'RA---','DEC--'}:
        row['status']='axis_pair_not_supported'
        return row
    if axes[0].group(2)!=axes[1].group(2) or axes[0].group(3)!=axes[1].group(3):
        row['status']='axes_inconsistent'
        return row
    if axes[0].group(2) not in PROJECTIONS:
        row['status']='projection_outside_audit_set'
        return row
    if axes[0].group(3):
        row['flags'].append('sip_distortion_context_not_captured')
    if meta.get('CUNIT1') is None or meta.get('CUNIT2') is None:
        row['flags'].append('units_not_observed_no_angular_scale_computed')
    row['status'] = _check_parameters(row,meta,dimensions,max_condition)
    if row['status']=='linear_block_consistent_context_incomplete':
        row['recommended_next_step']='collect_full_wcs_context_then_validate_against_independent_catalog'
    return row


def audit_wcs(document, max_condition=1e8):
    if not finite_number(max_condition) or max_condition<1:
        raise ValueError('Le seuil de conditionnement doit être fini et au moins égal à 1.')
    records, seen, file_events = [], set(), []
    for file in sorted(document['files'],key=lambda f:f['path']):
        if file['status']!='ok':
            file_events.append({'path':file['path'],'status':file['status']})
        for hdu in file['hdus']:
            row=describe_wcs(hdu,max_condition)
            row.update(path=file['path'],hdu_index=hdu['hdu_index'],frame_id=hdu['frame_id'],kind=hdu['kind'])
            if file['status']!='ok':
                row['status']='unusable_file'
            elif hdu['frame_id'] in seen:
                row['status']='duplicate_frame'
            else:
                seen.add(hdu['frame_id'])
            records.append(row)
    statuses=Counter(r['status'] for r in records)
    summary={'input_files':len(document['files']),'input_hdus':len(records),
             'status_counts':dict(statuses),'file_incidents':len(file_events),
             'inventory_traversal_incidents':len(document.get('traversal_incidents',[])),
             'numeric_linear_blocks_consistent':statuses.get('linear_block_consistent_context_incomplete',0),
             'wcs_scientifically_validated':0,'scientific_position_export_allowed':False}
    return {'wcs_schema_version':'1.0','capture_scope':'partial_inventory_manifest_1.0',
            'parameters':{'max_condition_number_raw_units':max_condition},
            'summary':summary,'records':records,'file_events':file_events,
            'pixels_read':False,'sky_coordinates_computed':False,
            'reference':'https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf'}
