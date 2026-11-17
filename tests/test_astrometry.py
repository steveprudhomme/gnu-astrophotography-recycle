# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
import numpy as np
import pytest
from astropy.table import Table
from astropy.wcs import WCS
from gar.astrometry import compare_stars,residual_statistics,local_path


def synthetic_field():
    w=WCS(naxis=2);w.wcs.crpix=[256,256];w.wcs.crval=[120,30]
    w.wcs.cd=np.array([[-2/3600,0],[0,2/3600]])
    w.wcs.ctype=['RA---TAN','DEC--TAN']
    x,y=np.meshgrid(np.arange(50,451,80),np.arange(50,451,80));x=x.ravel();y=y.ravel()
    yy,xx=np.indices((512,512));rng=np.random.default_rng(7)
    image=rng.normal(100,2,(512,512))
    for a,b in zip(x,y):image+=1000*np.exp(-((xx-a)**2+(yy-b)**2)/(2*(3/2.355)**2))
    sky=w.pixel_to_world(x,y);n=len(x)
    cat=Table({'source_id':np.arange(n),'ra':sky.ra.deg,'dec':sky.dec.deg,
               'pmra':np.zeros(n),'pmdec':np.zeros(n),'ref_epoch':np.full(n,2016.),
               'phot_g_mean_mag':np.full(n,13.),'ruwe':np.ones(n)})
    return image,w,cat


def test_original_wcs_checked_without_fitting():
    image,w,cat=synthetic_field();r=compare_stars(image,w,cat,'2025-01-01')
    assert r['metrics']['matches']==36 and r['metrics']['empirical_criteria_passed']
    assert r['metrics']['median_arcsec']<0.05
    assert not r['wcs_refitted'] and not r['scientific_submission_certified']


def test_known_offset_is_not_removed():
    image,w,cat=synthetic_field();w.wcs.crval[0]+=3/(3600*np.cos(np.deg2rad(30)))
    r=compare_stars(image,w,cat,'2025-01-01')
    assert 2.8<r['metrics']['median_arcsec']<3.2
    assert not r['metrics']['empirical_criteria_passed']


def test_bad_wcs_cannot_pass_with_chance_matches():
    image,w,cat=synthetic_field();w.wcs.crval[0]+=0.1
    r=compare_stars(image,w,cat,'2025-01-01')
    assert r['metrics']['matches']<30 and not r['metrics']['empirical_criteria_passed']


def test_low_count_and_missing_coverage_fail():
    r=residual_statistics(np.arange(10),np.arange(10),np.zeros(10),np.zeros(10),512,512)
    assert not r['empirical_criteria_passed']
    assert residual_statistics([],[],np.array([]),np.array([]),512,512)['median_arcsec'] is None


def test_unique_mutual_pairs_and_reference_selection():
    image,w,cat=synthetic_field();cat['ruwe'][0]=2
    r=compare_stars(image,w,cat,'2025-01-01')
    ids=[p['source_id'] for p in r['pairs']]
    assert len(ids)==len(set(ids))==35


def test_inputs_not_modified():
    image,w,cat=synthetic_field();before=image.copy();header=w.to_header().tostring()
    compare_stars(image,w,cat,'2025-01-01')
    assert np.array_equal(before,image) and w.to_header().tostring()==header


def test_catalog_columns_and_flat_image_rejected():
    image,w,cat=synthetic_field()
    with pytest.raises(ValueError):compare_stars(np.ones_like(image),w,cat,'2025-01-01')
    cat.remove_column('pmra')
    with pytest.raises(ValueError):compare_stars(image,w,cat,'2025-01-01')


def test_local_scope_and_saturation(tmp_path):
    with pytest.raises(ValueError):local_path(tmp_path/'other',tmp_path/'local')
    image,w,cat=synthetic_field();image[50,50]=65535
    r=compare_stars(image,w,cat,'2025-01-01')
    assert r['metrics']['matches']<36


def test_scientific_comparison_does_not_open_network(monkeypatch):
    import socket
    image,w,cat=synthetic_field()
    def forbidden(*args,**kwargs):raise AssertionError('Network forbidden during analysis')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    result=compare_stars(image,w,cat,'2025-01-01')
    assert result['metrics']['matches']==36
