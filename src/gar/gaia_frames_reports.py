# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Maps from actual reserved-star residuals; no image or WCS is altered."""
from html import escape


def gaia_frames_svg(document):
    height = 90+280*len(document['frames'])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" viewBox="0 0 1100 {height}">',
             '<rect width="100%" height="100%" fill="white"/>', '<g font-family="sans-serif" fill="#182433">',
             '<text x="25" y="30" font-size="22">Comparaison Gaia — étoiles réservées, modèles gelés</text>',
             '<text x="25" y="58" font-size="14">Origine des pixels en haut à gauche. Résidus Est/Nord : 12 pixels par seconde d’arc. Rayon d’association : 8″.</text>']
    for n, frame in enumerate(document['frames']):
        top = 85+280*n
        state = 'critères satisfaits' if frame['criteria_passed'] else 'critères non satisfaits'
        parts.append(f'<text x="25" y="{top+15}" font-size="17">Pose {frame["file_index"]} : {state}</text>')
        if 'control' not in frame:
            parts.append(f'<text x="25" y="{top+50}">{escape(frame.get("error", "Échec"))}</text>')
            continue
        h, w = frame['image_shape']; scale = min(260/w, 210/h)
        x0, y0 = 30, top+35
        parts.append(f'<rect x="{x0}" y="{y0}" width="{w*scale}" height="{h*scale}" fill="#f1f5f9" stroke="#a0afbd"/>')
        for k in [1, 2]:
            parts.append(f'<path d="M{x0+w*scale*k/3} {y0} v{h*scale} M{x0} {y0+h*scale*k/3} h{w*scale}" fill="none" stroke="#cad4df"/>')
        center_x, center_y = 475, top+140
        parts.append(f'<path d="M{center_x-160} {center_y} h320 M{center_x} {center_y-105} v210" stroke="#bdc8d3"/>')
        for radius in [2, 4]:
            parts.append(f'<circle cx="{center_x}" cy="{center_y}" r="{12*radius}" fill="none" stroke="#adb9c5"/>')
        for pair in frame['control']['pairs']:
            color = '#126682' if pair['separation_arcsec'] <= 2 else '#cc741d' if pair['separation_arcsec'] <= 4 else '#ae3030'
            parts.append(f'<circle cx="{x0+pair["x"]*scale:.3f}" cy="{y0+pair["y"]*scale:.3f}" r="3" fill="{color}"/>')
            parts.append(f'<circle cx="{center_x+12*pair["east_arcsec"]:.3f}" cy="{center_y-12*pair["north_arcsec"]:.3f}" r="3" fill="{color}"/>')
        c = frame['control']['metrics']
        med = f'{c["median_arcsec"]:.3f}″' if c['median_arcsec'] is not None else '?'
        p95 = f'{c["p95_arcsec"]:.3f}″' if c['p95_arcsec'] is not None else '?'
        lines = [f'Contrôles associés : {c["matches"]}', f'Médiane : {med} ; P95 : {p95}',
                 f'Couverture : {c["grid_cells_occupied"]}/9 ; quadrants : {c["quadrants_occupied"]}/4',
                 f'Contrôles non associés dans le recouvrement : {frame["control"]["unmatched_in_overlap"]}',
                 'Aucun réajustement ni biais soustrait.', 'Horloge et budget absolu non qualifiés.']
        for k, line in enumerate(lines):
            parts.append(f'<text x="660" y="{top+55+28*k}" font-size="14">{escape(line)}</text>')
    return '\n'.join(parts+['</g></svg>'])
