# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Local satellite propagation, without network or reference-answer access."""
import numpy as np
from sgp4.api import Satrec,SatrecArray
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import TEME,ITRS,AltAz,EarthLocation,CartesianRepresentation,SkyCoord,SkyOffsetFrame
from astropy.utils import iers
iers.conf.auto_download=False

def altaz(satellites,times,site):
    error,position,_=SatrecArray(satellites).sgp4(np.asarray(times.jd1),np.asarray(times.jd2))
    representation=CartesianRepresentation(position[:,:,0]*u.km,position[:,:,1]*u.km,position[:,:,2]*u.km)
    geo=TEME(representation,obstime=times).transform_to(ITRS(obstime=times))
    topo=ITRS(geo.cartesian-site.get_itrs(times).cartesian,obstime=times,location=site)
    aa=topo.transform_to(AltAz(obstime=times,location=site,pressure=0*u.hPa))
    return aa,error

def checks():
    s=Satrec.twoline2rv('1 25544U 98067A   19343.69339541  .00001764  00000+0  38792-4 0  9991',
        '2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472202482')
    e,r,v=s.sgp4(2458826.5,.8625)
    assert e==0 and np.allclose(r,[-6088.92,-936.13,-2866.44],atol=.1)
    t=Time([2458826.5+.8625],format='jd',scale='utc');site=EarthLocation.from_geodetic(0*u.deg,0*u.deg,0*u.m)
    aa,error=altaz([s],t,site)
    assert np.isfinite(aa.alt.deg).all() and not error.any()
    angular=SkyCoord(az=aa.az,alt=aa.alt,frame=AltAz(obstime=t,location=site,pressure=0*u.hPa))
    back=angular.icrs.transform_to(AltAz(obstime=t,location=site,pressure=0*u.hPa))
    assert angular.separation(back).arcsec.max()<.001
    return dict(sgp4_reference_vector_passed=True,angular_roundtrip_arcsec=float(angular.separation(back).arcsec.max()))

def compatible_intervals(offsets,along,exposure):
    if np.nanmin(along)>0 or np.nanmax(along)<1:return None
    order=np.argsort(along);ta,tb=np.interp([0,1],along[order],offsets[order]);enter,leave=sorted([float(ta),float(tb)])
    if leave-enter>exposure:return None
    return dict(predicted_field_entry_offset_seconds=enter,predicted_field_exit_offset_seconds=leave,
        beginning_timestamp_offset_interval=[leave-exposure,enter],
        midpoint_timestamp_offset_interval=[leave-exposure/2,enter+exposure/2],
        ending_timestamp_offset_interval=[leave,enter+exposure],
        uncertainty='conditional_interval_ignores_unquantified_orbit_geometry_clock_errors')
