# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Frozen-WCS empirical comparison to a local reference catalog; no fitting."""
from pathlib import Path
import csv
import hashlib
import json
import os
import warnings

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.table import Table
from astropy.time import Time
from astropy.wcs import WCS
import numpy as np
from photutils.detection import DAOStarFinder
from scipy.spatial import cKDTree

from .workset import no_links, digest
from .astrometry_reports import residual_svg


CRITERIA={'min_matches':30,'match_radius_arcsec':8.0,'median_max_arcsec':2.0,
          'p95_max_arcsec':4.0,'min_grid_cells':6,'required_quadrants':4}


def local_path(path,base):
    # Reject external paths lexically, before any filesystem probe of that path.
    base=Path(os.path.abspath(base))
    path=Path(os.path.abspath(path))
    if base not in path.parents:raise ValueError('Tous les produits doivent rester dans local/.')
    if not no_links(path):raise ValueError('Liens/jonctions refusés.')
    path=path.resolve()
    if base.resolve() not in path.parents:raise ValueError('Tous les produits doivent rester dans local/.')
    return path


def residual_statistics(x,y,dx,dy,width,height,*,min_matches=30):
    n=len(x)
    r=np.hypot(dx,dy)
    cells=len(set(zip(np.minimum((np.asarray(x)*3/width).astype(int),2),
                      np.minimum((np.asarray(y)*3/height).astype(int),2)))) if n else 0
    quadrants=len(set(zip(np.asarray(x)>=width/2,np.asarray(y)>=height/2))) if n else 0
    median=float(np.median(r)) if n else None
    p95=float(np.percentile(r,95)) if n else None
    ci=None
    if n>=2:
        rng=np.random.default_rng(20261116)
        medians=np.median(r[rng.integers(0,n,size=(500,n))],axis=1)
        ci=[float(v) for v in np.percentile(medians,[2.5,97.5])]
    return {'matches':n,'median_arcsec':median,'p95_arcsec':p95,
            'rms_radial_arcsec':float(np.sqrt(np.mean(r*r))) if n else None,
            'bias_east_arcsec':float(np.mean(dx)) if n else None,
            'bias_north_arcsec':float(np.mean(dy)) if n else None,
            'median_bootstrap_95_percent_interval_arcsec':ci,
            'grid_cells_occupied':cells,'quadrants_occupied':quadrants,
            'empirical_criteria_passed':bool(n>=min_matches and median<=2 and p95<=4 and cells>=6 and quadrants==4)}


def prepare_references(catalog,date_obs):
    """Quality/epoch/isolation selection shared by frozen-model comparisons."""
    required=['source_id','ra','dec','pmra','pmdec','ref_epoch','phot_g_mean_mag','ruwe']
    if any(k not in catalog.colnames for k in required):raise ValueError('Colonnes Gaia requises manquantes.')
    ids=[str(value).strip() for value in catalog['source_id']]
    if any(not value for value in ids) or len(set(ids))!=len(ids):raise ValueError('Identifiants de référence absents ou dupliqués.')
    good=np.ones(len(catalog),dtype=bool)
    for k in required[1:]:good &= np.isfinite(np.asarray(catalog[k],dtype=float))
    good &= (np.asarray(catalog['phot_g_mean_mag'])>=9)&(np.asarray(catalog['phot_g_mean_mag'])<=17.5)&(np.asarray(catalog['ruwe'])<1.4)
    cat=catalog[good]
    quality_references=len(cat)
    if len(cat)<2:raise ValueError('Références insuffisantes.')
    # Calendar date only: epoch propagation does not qualify the instrument clock.
    epoch=Time(str(date_obs)[:10]+'T12:00:00',format='isot',scale='tcb')
    coords=SkyCoord(ra=np.asarray(cat['ra'])*u.deg,dec=np.asarray(cat['dec'])*u.deg,
                    pm_ra_cosdec=np.asarray(cat['pmra'])*u.mas/u.yr,
                    pm_dec=np.asarray(cat['pmdec'])*u.mas/u.yr,
                    obstime=Time(np.asarray(cat['ref_epoch']),format='jyear',scale='tcb'),frame='icrs')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');coords=coords.apply_space_motion(new_obstime=epoch)
    coords=SkyCoord(ra=coords.ra,dec=coords.dec,frame='icrs')
    _,nearest,_=coords.match_to_catalog_sky(coords,nthneighbor=2)
    isolated=nearest.arcsec>=16
    return cat[isolated],coords[isolated],{'catalog_input':len(catalog),'catalog_after_quality':quality_references,
        'catalog_after_isolation':int(isolated.sum()),'epoch_approx_tcb':epoch.isot,
        'propagation_warnings':[str(w.message) for w in caught]}


def compare_stars(image,wcs,catalog,date_obs):
    image=np.asarray(image,dtype=float)
    if image.ndim==3:
        saturated=np.any(image>=65000,axis=0);plane=np.mean(image,axis=0)
    elif image.ndim==2:
        plane=image;saturated=image>=65000
    else:raise ValueError('Image 2D ou cube de plans 3D requis.')
    height,width=plane.shape
    invalid=~np.isfinite(plane)|saturated
    _,background,noise=sigma_clipped_stats(plane,mask=invalid,sigma=3,maxiters=5)
    if not np.isfinite(noise) or noise<=0:raise ValueError('Fond ou bruit non mesurable.')
    finder=DAOStarFinder(threshold=8*noise,fwhm=3,exclude_border=True,
                         peak_max=65000-background,min_separation=8)
    found=finder(np.where(invalid,background,plane)-background,mask=invalid)
    if found is None:raise ValueError('Aucune étoile détectée avec les paramètres fixés.')
    x=np.asarray(found['x_centroid']);y=np.asarray(found['y_centroid'])
    detected_count=len(x)
    keep=(x>=10)&(x<width-10)&(y>=10)&(y<height-10)
    x=x[keep];y=y[keep]
    after_margin=len(x)
    if len(x)<2:raise ValueError('Trop peu de détections après marge.')
    distance,_=cKDTree(np.column_stack([x,y])).query(np.column_stack([x,y]),k=2)
    keep=distance[:,1]>=8;x=x[keep];y=y[keep]
    if not len(x):raise ValueError('Aucune détection isolée.')
    cat,coords,reference_info=prepare_references(catalog,date_obs)
    cx,cy=wcs.world_to_pixel(coords)
    inside=(cx>=10)&(cx<width-10)&(cy>=10)&(cy<height-10)
    coords=coords[inside];cat=cat[inside]
    if len(cat)==0:raise ValueError('Aucune référence isolée dans le champ.')
    measured=wcs.pixel_to_world(x,y).icrs
    index,separation,_=measured.match_to_catalog_sky(coords)
    reverse,_,_=coords.match_to_catalog_sky(measured)
    keep=(separation.arcsec<=8)&(reverse[index]==np.arange(len(x)))
    chosen=np.where(keep)[0];reference=index[chosen]
    east,north=coords[reference].spherical_offsets_to(measured[chosen])
    dx=east.arcsec;dy=north.arcsec
    pairs=[]
    for j,i in enumerate(chosen):
        pairs.append({'source_id':str(cat['source_id'][reference[j]]),'x':float(x[i]),'y':float(y[i]),
                      'east_arcsec':float(dx[j]),'north_arcsec':float(dy[j]),
                      'separation_arcsec':float(separation[i].arcsec)})
    return {'criteria':CRITERIA,'metrics':residual_statistics(x[chosen],y[chosen],dx,dy,width,height),
            'selection_counts':{'detected':detected_count,'after_margin':after_margin,
                                'after_isolation':len(x),'catalog_input':len(catalog),
                                'catalog_after_quality':reference_info['catalog_after_quality'],'catalog_inside_isolated':len(cat),
                                'saturated_pixels':int(np.sum(saturated))},
            'parameters':{'threshold_sigma':8,'fwhm_pixels':3,'margin_pixels':10,
                          'saturation_adu':65000,'detection_isolation_pixels':8,
                          'reference_isolation_arcsec':16,'bootstrap_seed':20261116,
                          'bootstrap_replicates':500,'image_selection':'mean_of_planes_if_3d'},
            'pairs':pairs,'detections_after_selection':len(x),'references_after_selection':len(cat),
            'image_shape':[height,width],'background':float(background),'noise_sigma':float(noise),
            'epoch_approx_tcb':reference_info['epoch_approx_tcb'],'propagation_warnings':reference_info['propagation_warnings'],
            'wcs_refitted':False,'residuals_clipped':False,'clock_qualified':False,
            'scientific_submission_certified':False}


def run_comparison(workset_path,file_index,catalog_path,output,base):
    wp=local_path(workset_path,base);cp=local_path(catalog_path,base);output=local_path(output,base)
    if output.exists():raise ValueError('La sortie existe déjà.')
    raw=wp.read_bytes();workset=json.loads(raw)
    if not workset.get('success') or not 1<=file_index<=len(workset['files']):raise ValueError('Lot ou index incorrect.')
    item=workset['files'][file_index-1]
    copy=local_path(wp.parent/item['local_copy'],base)
    if wp.parent.resolve() not in copy.parents:raise ValueError('Copie hors du lot.')
    before=digest(copy)
    if before!=item['sha256_copy']:raise ValueError('La copie ne correspond plus à son empreinte.')
    catalog=Table.read(cp,format='ascii.csv')
    provenance=None
    provenance_path=cp.parent/'provenance.json'
    if provenance_path.exists():
        provenance=json.loads(local_path(provenance_path,base).read_text(encoding='utf-8'))
        if provenance.get('sha256')!=digest(cp):raise ValueError('Empreinte de catalogue incohérente avec sa provenance.')
    if len(catalog)>=20000:raise ValueError('Catalogue possiblement tronqué : vérifier la requête.')
    with fits.open(copy,mode='readonly',memmap=False) as hdus:
        header=hdus[0].header
        wcs=WCS(header,fobj=hdus,naxis=2,fix=False)
        if not wcs.has_celestial:raise ValueError('Pas de WCS céleste primaire.')
        result=compare_stars(hdus[0].data,wcs,catalog,header.get('DATE-OBS'))
    if digest(copy)!=before:raise ValueError('La copie a changé pendant le traitement.')
    result.update(copy_sha256_before=before,copy_sha256_after=before,
                  catalog_provenance=provenance,
                  workset_sha256=hashlib.sha256(raw).hexdigest(),catalog_sha256=digest(cp),file_index=file_index)
    output.mkdir(parents=True,exist_ok=False)
    (output/'astrometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    (output/'residuals.svg').write_text(residual_svg(result),encoding='utf-8')
    with (output/'matches.csv').open('w',encoding='utf-8-sig',newline='') as s:
        writer=csv.DictWriter(s,fieldnames=['source_id','x','y','east_arcsec','north_arcsec','separation_arcsec'])
        writer.writeheader()
        for pair in result['pairs']:
            row=dict(pair)
            if row['source_id'].lstrip().startswith(('=','+','-','@')):row['source_id']="'"+row['source_id']
            writer.writerow(row)
    (output/'report.md').write_text('# Comparaison astrométrique exploratoire\n\n```json\n'+json.dumps(result['metrics'],indent=2)+
        '\n```\n\n![Répartition et résidus](residuals.svg)\n\nAucun réajustement ni retrait de grands résidus après association. Le rayon de sélection limite néanmoins les erreurs observables.\n'
        'Les erreurs de référence/centroïde, les corrélations et effets de perspective ne constituent pas ici un budget complet.\n'
        'Les mouvements propres sont appliqués sans distance/vitesse radiale ; époque calendaire approximative, horloge non qualifiée.\n'
        'Les résultats ne certifient pas une soumission MPC. Données privées : ne pas publier.\n',encoding='utf-8')
    return result
