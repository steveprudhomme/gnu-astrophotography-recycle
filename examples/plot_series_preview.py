# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Read-only local overview, fixed stretch from the first image; no FITS rewriting."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from PIL import Image
from gar.astrometry import local_path
from gar.workset import digest

ROOT = Path(__file__).resolve().parents[1]


def plot(audit_path, output, base=None, public_cc0=False):
    base = ROOT/'local' if base is None else base
    ap, output = [local_path(p, base) for p in (audit_path, output)]
    r = json.loads(ap.read_text(encoding='utf-8'))
    if not r.get('copies_prepared') or r.get('status') != 'complete': raise ValueError('Copies préparées requises.')
    if output.exists(): raise ValueError('Choisir une nouvelle sortie de figures.')
    watched = {ap: digest(ap)}; images = []; synthetic_flags = []
    for f in r['files']:
        p = local_path(f['local_copy'], base)
        if digest(p) != f['sha256']: raise ValueError('Copie modifiée.')
        watched[p] = f['sha256']
        with fits.open(p, mode='readonly', memmap=False) as h:
            a = np.asarray(h[0].data, dtype=float)
            synthetic_flags.append(h[0].header.get('GARSYNTH') is True)
            height, width = a.shape
            a = a[:height//2*2, :width//2*2].reshape(height//2, 2, width//2, 2).mean(axis=(1, 3))
            images.append(a)
    synthetic = all(synthetic_flags)
    if public_cc0 and any(synthetic_flags):
        raise ValueError('Le mode exemple réel CC0 exige une série entièrement réelle autorisée.')
    low, high = np.percentile(images[0], [5, 99.7])
    if high <= low: raise ValueError('Contraste insuffisant pour l’aperçu.')
    output.mkdir(parents=True, exist_ok=False)
    fig, axes = plt.subplots((len(images)+3)//4, 4, figsize=(12, 3.4*((len(images)+3)//4)), layout='constrained', squeeze=False)
    for k, ax in enumerate(axes.flat):
        ax.axis('off')
        if k < len(images):
            shown = np.arcsinh(np.maximum(images[k]-low, 0)/max((high-low)/10, 1))
            ax.imshow(shown, origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10))
            ax.set_title(f'Pose {k+1}', fontsize=11)
    title = ('SEESTAR S50 — IMAGES RÉELLES AUTORISÉES, CC0 1.0' if public_cc0 else
             'IMAGES FICTIVES' if synthetic else 'APERÇU PRIVÉ DE COPIES RÉELLES — NE PAS PUBLIER')
    fig.suptitle(title+'\nMoyenne 2×2 et étirement commun depuis la première pose ; aucune calibration scientifique', fontsize=11)
    fig.savefig(output/'series-preview.png', dpi=145); plt.close(fig)
    if public_cc0:
        fig, ax = plt.subplots(figsize=(5, 8.6), layout='constrained')
        ax.imshow(np.arcsinh(np.maximum(images[0]-low, 0)/max((high-low)/10, 1)),
                  origin='lower', cmap='gray', vmin=0, vmax=np.arcsinh(10))
        ax.axis('off')
        ax.set_title('SEESTAR S50 — POSE RÉELLE, CC0 1.0\nRendu gris 2×2, étirement d’affichage\nAucune calibration scientifique', fontsize=10)
        fig.savefig(output/'first-pose.png', dpi=145); plt.close(fig)
        for name in ['series-preview.png', 'first-pose.png']:
            path = output/name
            with Image.open(path) as image:
                clean = image.convert('RGB')
            clean.save(path, format='PNG')  # No EXIF, text chunks, DPI or inherited metadata.
            with Image.open(path) as image:
                if image.info: raise ValueError('Métadonnées PNG inattendues dans l’exemple public.')
    if any(digest(p) != h for p, h in watched.items()): raise ValueError('Une entrée a changé pendant le dessin.')
    (output/'preview.json').write_text(json.dumps(dict(synthetic_only=bool(synthetic), input_audit_sha256=watched[ap],
         file_count=len(images), stretch_from_first_image=dict(percentile_5=float(low), percentile_99_7=float(high)),
         binning=2, fits_pixels_rewritten=False, science_validated=False,
         public_cc0_explicitly_requested=public_cc0,
         public_png_sha256={name: digest(output/name) for name in ['series-preview.png', 'first-pose.png']} if public_cc0 else {}), indent=2), encoding='utf-8')
    print('Aperçu local produit ; FITS inchangés. Nature fictive : '+str(synthetic))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audit', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--public-cc0', action='store_true', help='Diffusion réelle CC0 explicitement autorisée par le titulaire uniquement')
    args = parser.parse_args(); plot(args.audit, args.output, public_cc0=args.public_cc0)
