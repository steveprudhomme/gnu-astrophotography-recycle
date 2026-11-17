# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""SVG of actual held-out registration residuals; no fabricated screenshot."""
from html import escape


def registration_svg(document):
    height = 90+260*len(document['frames'])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}">',
             '<rect width="100%" height="100%" fill="#fff"/>',
             '<g font-family="sans-serif" fill="#182433">',
             '<text x="25" y="28" font-size="20">Recalage relatif : étoiles de contrôle réservées</text>',
             '<text x="25" y="54" font-size="13">Vecteurs amplifiés ×20 ; pixels natifs ; origine en haut à gauche. Rayon d’association : 3 px.</text>']
    for n, result in enumerate(document['frames']):
        top = 85+260*n
        label = 'critères satisfaits' if result['criteria_passed'] else 'critères non satisfaits'
        parts.append(f'<text x="25" y="{top+18}" font-size="17">Pose {result["file_index"]} : {label}</text>')
        if 'metrics' not in result:
            parts.append(f'<text x="25" y="{top+50}">{escape(result.get("error", "Erreur"))}</text>')
            continue
        h, w = result['image_shape']
        scale = min(350/w, 200/h)
        x0, y0 = 30, top+30
        parts.append(f'<rect x="{x0}" y="{y0}" width="{w*scale}" height="{h*scale}" fill="#f1f5f9" stroke="#8b98a6"/>')
        for k in [1, 2]:
            parts.append(f'<path d="M {x0+w*scale*k/3} {y0} v {h*scale} M {x0} {y0+h*scale*k/3} h {w*scale}" stroke="#cad4df" fill="none"/>')
        for p in result['pairs']:
            if p['split'] != 'control':
                continue
            x, y = x0+p['x']*scale, y0+p['y']*scale
            parts.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="2" fill="#126682"/><path d="M{x:.3f} {y:.3f} l{p["dx_pixels"]*scale*20:.3f} {p["dy_pixels"]*scale*20:.3f}" stroke="#c4491c"/>')
        c = result['metrics']['control']
        med = f'{c["median_pixels"]:.3f}' if c['median_pixels'] is not None else 'indéterminée'
        p95 = f'{c["p95_pixels"]:.3f}' if c['p95_pixels'] is not None else 'indéterminé'
        lines = [f'Rotation : {result["rotation_degrees"]:.5f}°',
                 f'Ajustement : {result["metrics"]["training"]["matches"]} étoiles ; contrôle : {c["matches"]}',
                 f'Médiane : {med} px ; P95 : {p95} px',
                 f'Couverture : {c["grid_cells_occupied"]}/9 cellules, {c["quadrants_occupied"]}/4 quadrants',
                 'Erreur absolue héritée de la référence.', 'Horloge non qualifiée ; aucune certification.']
        for k, line in enumerate(lines):
            parts.append(f'<text x="420" y="{top+55+k*28}" font-size="14">{escape(line)}</text>')
    parts.append('</g></svg>')
    return '\n'.join(parts)
