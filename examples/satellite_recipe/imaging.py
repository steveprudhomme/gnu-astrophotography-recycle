# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Frozen measurement and line-integral recipes from the targeted study."""
import numpy as np
from scipy import ndimage,optimize
from astropy.stats import sigma_clipped_stats

def line_fit(image,initial):
    image=np.asarray(image,dtype=float);h,w=image.shape
    initial=np.asarray(initial);slope,intercept=np.polyfit(initial[:,0],initial[:,1],1)
    middle=intercept+slope*(w-1)/2
    residual=image-ndimage.gaussian_filter(image,10)
    _,_,noise=sigma_clipped_stats(residual,sigma=3,maxiters=5)
    clipped=np.clip(residual/noise,-3,3)
    x=np.arange(8,w-8,2,dtype=float);dx=x-(w-1)/2
    def signal(parameters,shift=0):
        mid,m=parameters;y=mid+m*dx+shift
        samples=sum(weight*ndimage.map_coordinates(clipped,[y+offset,x],order=1,mode='constant',cval=0)
            for offset,weight in [(-1,.25),(0,.5),(1,.25)])
        return float(np.mean(samples))
    choices=[(signal([mid,m]),mid,m) for mid in np.linspace(middle-12,middle+12,49)
        for m in np.linspace(slope-.04,slope+.04,33)]
    _,mid,m=max(choices)
    fit=optimize.minimize(lambda p:-signal(p),[mid,m],method='Powell',
        bounds=[(mid-1,mid+1),(m-.003,m+.003)],options={'xtol':1e-5,'ftol':1e-7})
    mid,m=fit.x;endpoints=np.array([[0,mid-m*(w-1)/2],[w-1,mid+m*(w-1)/2]])
    controls=[signal(fit.x,offset) for offset in [-20,-12,-8,8,12,20]]
    chunks=[]
    for x0,x1 in [(0,w/3),(w/3,2*w/3),(2*w/3,w)]:
        select=(x>=x0)&(x<x1);y=mid+m*dx
        values=ndimage.map_coordinates(clipped,[y,x],order=1)
        chunks.append(float(np.mean(values[select])))
    return dict(native_endpoints=endpoints.tolist(),slope_y_per_x=float(m),
        mean_clipped_native_signal=signal(fit.x),parallel_control_signals=controls,
        signals_in_three_spatial_parts=chunks,noise_sigma=float(noise),
        centroid_is_model_fit_not_independent_pixel_detections=True,field_truncated=True)

def detect_lines(plane):
    valid=np.isfinite(plane);a=np.where(valid,plane,0)
    weights=ndimage.gaussian_filter(valid.astype(float),5)
    background=ndimage.gaussian_filter(a,5)/np.maximum(weights,1e-9)
    a=np.where(valid,a-background,0)
    h,w=a.shape;yy,xx=np.indices(a.shape);x=xx[valid];y=yy[valid];values=a[valid]
    diagonal=int(np.ceil(np.hypot(h,w)));scores=np.full((360,2*diagonal+1),-999.,dtype=float)
    for index in range(360):
        theta=np.deg2rad(index*.5);rho=np.rint(x*np.cos(theta)+y*np.sin(theta)).astype(int)+diagonal
        count=np.bincount(rho,minlength=2*diagonal+1)
        total=np.bincount(rho,weights=values,minlength=2*diagonal+1)
        eligible=count>=100
        profile=ndimage.gaussian_filter1d(total/np.sqrt(np.maximum(count,1)),.6)
        if eligible.sum()<20:continue
        median=np.median(profile[eligible]);dispersion=1.4826*np.median(abs(profile[eligible]-median))
        if dispersion>0:scores[index,eligible]=(profile[eligible]-median)/dispersion
    maxima=(scores>=8)&(scores==ndimage.maximum_filter(scores,size=(9,9),mode='constant',cval=-999))
    peaks=np.argwhere(maxima);results=[]
    for index,rho in sorted(peaks.tolist(),key=lambda p:-scores[tuple(p)]):
        theta=np.deg2rad(index*.5);normal=np.array([np.cos(theta),np.sin(theta)])
        # Intersect a geometric line with the finite image rectangle.
        intersections=[]
        for x0 in [0,w-1]:
            if abs(normal[1])>1e-8:
                y0=(rho-diagonal-normal[0]*x0)/normal[1]
                if 0<=y0<h:intersections.append([x0,y0])
        for y0 in [0,h-1]:
            if abs(normal[0])>1e-8:
                x0=(rho-diagonal-normal[1]*y0)/normal[0]
                if 0<=x0<w:intersections.append([x0,y0])
        if len(intersections)<2:continue
        endpoints=np.array(intersections[:2]);center=endpoints.mean(axis=0)
        if any(abs(index*.5-q['normal_degrees'])<=2 and abs((center-np.mean(q['endpoints_reduced'],axis=0))@normal)<=4 for q in results):continue
        results.append(dict(normal_degrees=index*.5,rho_reduced=float(rho-diagonal),
            empirical_score=float(scores[index,rho]),endpoints_reduced=endpoints.tolist(),
            status='proposal_requires_visual_and_native_review'))
    return results
