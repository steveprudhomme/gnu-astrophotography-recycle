# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Separate fixed radius-three detector; the historical detector stays untouched."""
from hashlib import sha256
import warnings
import numpy as np
from astropy.stats import sigma_clipped_stats
import photutils
from photutils.detection import DAOStarFinder


def signature(noise, separation=3):
    """Describe an unchanged kernel/shape/threshold configuration, without searching."""
    if separation not in (3,5) or not np.isfinite(noise) or noise<=0:
        raise ValueError('Bruit positif et voisinage 3 ou 5 requis.')
    finder=DAOStarFinder(threshold=5*noise,fwhm=3,min_separation=separation,exclude_border=True)
    return describe(finder)


def describe(finder):
    return dict(threshold_sigma=5.,threshold_effective=float(finder.threshold_eff),fwhm_reduced=3.,
                minimum_separation_reduced=int(finder.min_separation),exclude_border=bool(finder.exclude_border),
                sharpness_range=list(finder.sharpness_range),roundness_range=list(finder.roundness_range),
                kernel_sha256=sha256(finder.kernel.data.tobytes()).hexdigest(),margin_reduced=8,
                saturation_adu=65000,maximum_sources=500,photutils_version=photutils.__version__)


def detect_sources(image):
    if photutils.__version__!='3.1.1':
        raise ValueError('Ce profil exige Photutils 3.1.1.')
    plane=np.asarray(image,dtype=float)
    if plane.ndim!=2 or min(plane.shape)<32:
        raise ValueError('Un plan 2D d’au moins 32 cases par côté est requis.')
    mask=~np.isfinite(plane)|(plane>=65000)
    _,background,noise=sigma_clipped_stats(plane,mask=mask,sigma=3,maxiters=5)
    if not np.isfinite(noise) or noise<=0:
        raise ValueError('Bruit non mesurable.')
    finder=DAOStarFinder(threshold=5*noise,fwhm=3,min_separation=3,exclude_border=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        found=finder(np.where(mask,background,plane)-background,mask=mask)
    xy=np.empty((0,2)) if found is None else np.column_stack([found['x_centroid'],found['y_centroid']])
    h,w=plane.shape
    keep=np.isfinite(xy).all(axis=1)&(xy>=8).all(axis=1)&(xy<[w-8,h-8]).all(axis=1)
    xy=xy[keep]
    if len(xy)>500:
        raise ValueError('Plus de 500 sources : hors limites du profil, sans troncature.')
    return xy,dict(selected=len(xy),background=float(background),noise_sigma=float(noise),
                   warnings=[str(v.message) for v in caught],detector_signature=describe(finder))
