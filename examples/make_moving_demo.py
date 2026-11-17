# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Controlled synthetic images and separate truth; never use real observations."""
import argparse
import json
from pathlib import Path
import numpy as np
from astropy.io import fits
from gar.workset import digest

SCENARIOS = ('nominal','control','missing','faint_slow','blend','jitter')
SEEDS = (17, 23, 41)


def add_star(image, x, y, peak, sigma=1.3):
    h, w = image.shape
    x0, x1 = max(0, int(x)-6), min(w, int(x)+8)
    y0, y1 = max(0, int(y)-6), min(h, int(y)+8)
    if x0 >= x1 or y0 >= y1: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    image[y0:y1, x0:x1] += peak*np.exp(-((xx-x)**2+(yy-y)**2)/(2*sigma*sigma))


def make_demo(output, *, seeds=SEEDS, scenarios=SCENARIOS):
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    (output/'copies').mkdir()
    manifest = {'moving_schema_version':'1.0','synthetic':True,'time_kind':'fictitious_relative_seconds',
                'description':'Monoplane Gaussian PSF, aligned pixel frame; no Bayer or motion blur.', 'sequences':[]}
    truth = {'truth_schema_version':'1.0','sequences':[]}
    times = np.arange(8)*10.
    for scenario in scenarios:
        for seed in seeds:
            rng = np.random.default_rng(seed); name = f'{scenario}-{seed}'
            specs = []
            if scenario == 'nominal': specs = [(50.,85.,.45,.22,120.),(200.,180.,-.6,-.35,120.)]
            elif scenario == 'missing': specs = [(50.,85.,.45,.22,120.)]
            elif scenario == 'faint_slow': specs = [(50.,180.,.4,-.3,12.),(180.,70.,.03,.02,120.)]
            elif scenario == 'blend': specs = [(45.,128.,1.,0.,120.)]
            elif scenario == 'jitter': specs = [(50.,85.,.45,.22,120.)]
            elif scenario != 'control': raise ValueError('Scénario inconnu.')
            stars = []
            while len(stars) < 40:
                x, y = rng.uniform(15, 241, 2)
                if stars and min(np.hypot(x-a,y-b) for a,b,_ in stars) < 9: continue
                # Nominal separation is by construction; blending is tested separately.
                if any(np.min(np.hypot(x-(a+vx*times),y-(b+vy*times))) < 12 for a,b,vx,vy,_ in specs): continue
                stars.append((x,y,rng.uniform(500,1500)))
            if scenario == 'blend': stars.append((85.,128.,1200.))
            targets = [{'injection_id':f'object-{j+1}', 'velocity_pixels_per_second':[s[2],s[3]],
                        'peak_adu':s[4], 'positions':[]} for j,s in enumerate(specs)]
            frames = []
            for k, t in enumerate(times):
                image = rng.normal(100,2,(256,256))
                shift = np.array([.35*np.sin(k), .35*np.cos(k)]) if scenario == 'jitter' else np.zeros(2)
                for x,y,peak in stars: add_star(image,x+shift[0],y+shift[1],peak)
                for target,(x,y,vx,vy,peak) in zip(targets,specs):
                    p = np.array([x+vx*t,y+vy*t])+shift
                    visible = not (scenario == 'missing' and k in (2,5))
                    if visible: add_star(image,*p,peak)
                    target['positions'].append({'frame_index':k,'x':float(p[0]),'y':float(p[1]),'visible':visible})
                if scenario == 'control':
                    image[30,30] = image[210,40] = 4000  # Persistent hot pixels.
                    flash_x, flash_y = rng.uniform(20,236,2)
                    add_star(image,flash_x,flash_y,300)  # Independent transient positions, not a coherent trajectory.
                    # Only two time samples in a line: deliberately insufficient support.
                    if k in (2,3): image[100:101,130:150] += 3000
                header = fits.Header({'GARSYNTH':True,'SYNCTIME':float(t)})
                path = output/'copies'/f'{name}-{k:02d}.fit'
                fits.writeto(path,image.astype('float32'),header)
                frames.append({'local_copy':f'copies/{path.name}','sha256':digest(path),'relative_time_seconds':float(t)})
            manifest['sequences'].append({'sequence_id':name,'scenario':scenario,'seed':seed,'frames':frames})
            truth['sequences'].append({'sequence_id':name,'injections':targets})
    mp = output/'manifest.json'; mp.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    truth['manifest_sha256'] = digest(mp)
    (output/'truth.json').write_text(json.dumps(truth,indent=2),encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output',type=Path)
    make_demo(parser.parse_args().output)
