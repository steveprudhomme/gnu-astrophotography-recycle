# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Local before/after blink; interpolation is for display, never for detection."""
import argparse
import io
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from astropy.io import fits
from scipy.ndimage import map_coordinates
from gar.astrometry import local_path
from gar.workset import digest
from run_seestar_pilot import intensity_plane, from_reference

ROOT = Path(__file__).resolve().parents[1]


def align_for_display(plane, model):
    """Inverse map: reduced reference grid -> native source -> reduced source."""
    yy, xx = np.indices(plane.shape, dtype=float)
    grid = np.column_stack([xx.ravel(), yy.ravel()])
    native_source = from_reference(2*grid+.5, model)
    reduced_source = (native_source-.5)/2
    coords = [reduced_source[:, 1].reshape(plane.shape), reduced_source[:, 0].reshape(plane.shape)]
    return map_coordinates(plane, coords, order=1, mode='constant', cval=np.nan, prefilter=False)


def render(fig):
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=110); plt.close(fig)
    buf.seek(0)
    with Image.open(buf) as image:
        return image.convert('RGB')


def plot(result_path, output, base=None):
    base = ROOT/'local' if base is None else base
    rp, output = [local_path(p, base) for p in (result_path, output)]
    result = json.loads(rp.read_text(encoding='utf-8'))
    if result.get('status') != 'complete' or not result.get('input_hashes_unchanged'):
        raise ValueError('Rapport de pilote terminé et entrées intactes requis.')
    if output.exists():
        raise ValueError('Choisir une nouvelle sortie de figures.')
    watched = {rp: digest(rp)}
    images = []
    for item in result['copies']:
        path = local_path(item['local_copy'], base)
        if digest(path) != item['sha256']:
            raise ValueError('Copie modifiée avant le dessin.')
        watched[path] = item['sha256']
        with fits.open(path, mode='readonly', memmap=False) as hdus:
            images.append(intensity_plane(hdus[0].data))
    low, high = np.nanpercentile(images[0], [5, 99.7])
    if not np.isfinite([low, high]).all() or high <= low:
        raise ValueError('Contraste insuffisant.')
    def stretch(image):
        return np.arcsinh(np.maximum(image-low, 0)/max((high-low)/10, 1))
    output.mkdir(parents=True, exist_ok=False)
    title = 'IMAGES FICTIVES' if result['input_kind'] == 'synthetic_demo' else 'IMAGES RÉELLES — APERÇU PRIVÉ'
    aligned = [align_for_display(image, m) for image, m in zip(images, result['models'])] if result['registration_available'] else None
    tracks = (result.get('search') or {}).get('tracks', [])
    frames = []
    for k, image in enumerate(images):
        count = 2 if aligned is not None else 1
        fig, axes = plt.subplots(1, count, figsize=(9, 6), layout='constrained', squeeze=False)
        for ax, plane, label in zip(axes.flat, [image, aligned[k]] if aligned is not None else [image],
                                    ['Pose brute', 'Alignée pour affichage seulement']):
            ax.imshow(stretch(plane), origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10))
            ax.set_title(label, fontsize=10); ax.axis('off')
        if aligned is not None:
            for track in tracks:
                for p in track['points']:
                    if p['frame_index'] == k:
                        axes[0, -1].plot((p['x']-.5)/2, (p['y']-.5)/2, 'o', mfc='none', mec='cyan', ms=12)
                        axes[0, -1].annotate(str(track['candidate_id']), ((p['x']-.5)/2, (p['y']-.5)/2), color='cyan')
        status = (f"{result['candidate_count']} candidat(s), non confirmé(s)" if result['motion_searched'] else 'RECHERCHE BLOQUÉE — voir le rapport')
        fig.suptitle(f'{title} — pose {k+1}/{len(images)}\n{status}', fontsize=11)
        fig.supxlabel('Lecture artificielle : 0,6 s/pose · étirement commun · aucune vitesse physique déduite', fontsize=9)
        frames.append(render(fig))
    frames[0].save(output/'blink.gif', save_all=True, append_images=frames[1:], duration=600, loop=0, optimize=False)
    frames[0].save(output/'blink-first.png')

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), layout='constrained')
    ids = np.arange(2, len(result['models'])+1)
    controls = [m.get('metrics', {}).get('control', {}) for m in result['models'][1:]]
    p95 = [s.get('p95_pixels') if s.get('p95_pixels') is not None else np.nan for s in controls]
    counts = [s.get('matches', 0) for s in controls]
    axes[0].plot(ids, p95, 'o-'); axes[0].axhline(1.5, color='red', ls='--', label='Limite 1,5 pixel')
    axes[0].set(xlabel='Pose (1 = référence)', ylabel='P95 contrôle, pixels natifs'); axes[0].legend()
    axes[1].bar(ids, counts, color=['teal' if m['model_usable'] else 'orange' for m in result['models'][1:]])
    axes[1].axhline(10, color='red', ls='--', label='Minimum 10'); axes[1].legend()
    axes[1].set(xlabel='Pose', ylabel='Étoiles de contrôle associées')
    fig.suptitle(title+'\nContrôles réservés : couverture spatiale et autres critères aussi requis', fontsize=11)
    image = render(fig); image.save(output/'controls.png')

    for track in tracks:
        positions = np.array([[p['x'], p['y']] for p in track['points']])
        lo, hi = (positions.min(axis=0)-.5)/2-12, (positions.max(axis=0)-.5)/2+12
        fig, axes = plt.subplots((len(images)+3)//4, 4, figsize=(12, 6), layout='constrained', squeeze=False)
        for k, ax in enumerate(axes.flat):
            ax.axis('off')
            if k >= len(images):
                continue
            ax.imshow(stretch(aligned[k]), origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10))
            ax.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]), title=f'Pose {k+1}')
            for p in track['points']:
                if p['frame_index'] == k:
                    ax.plot((p['x']-.5)/2, (p['y']-.5)/2, 'o', mfc='none', mec='cyan')
        fig.suptitle(f"{title} — candidat {track['candidate_id']} à revoir\nVignettes alignées pour affichage ; origine astronomique non confirmée", fontsize=11)
        render(fig).save(output/f"candidate-{track['candidate_id']:02d}-review.png")
    if any(digest(p) != h for p, h in watched.items()):
        raise ValueError('Une entrée a changé pendant le dessin.')
    files = sorted(p for p in output.iterdir() if p.suffix in ('.png', '.gif'))
    (output/'figures.json').write_text(json.dumps(dict(
        input_result_sha256=watched[rp], synthetic_only=result['input_kind'] == 'synthetic_demo',
        real_outputs_private=True, displayed_frame_count=len(images), gif_duration_ms=600,
        stretch_from_first_image=[float(low), float(high)], interpolation_display_only=True,
        measured_positions_resampled=False, fits_pixels_rewritten=False, input_hashes_unchanged=True,
        figures_sha256={p.name: digest(p) for p in files}), indent=2), encoding='utf-8')
    print('GIF et contrôles produits localement ; interpolation réservée à l’affichage.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); plot(args.result, args.output)
