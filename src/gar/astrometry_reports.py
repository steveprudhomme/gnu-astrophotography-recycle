# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Residual maps without refitting the measured WCS."""


def residual_svg(result):
    height,width=result['image_shape']
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="640" viewBox="0 0 1200 640">',
           '<title>Positions des associations et résidus tangentiels, sans ajustement</title>',
           '<rect width="1200" height="640" fill="#101d30"/>',
           '<g font-family="Segoe UI, Arial, sans-serif" fill="#edf4ff">',
           '<text x="30" y="40" font-size="24">Contrôle de la WCS originale — sans réajustement</text>',
           '<text x="30" y="80" font-size="18">Positions dans l’image (vert ≤2″, ambre ≤4″, rouge au-delà)</text>',
           '<text x="690" y="80" font-size="18">Résidus Est/Nord (centre = zéro ; 20 pixels par ″)</text>',
           '<rect x="40" y="110" width="500" height="450" fill="none" stroke="#b9cce1"/>',
           '<path d="M700 330H1160 M930 110V550" stroke="#b9cce1" fill="none"/>',
           '<circle cx="930" cy="330" r="40" fill="none" stroke="#83d7b7"/>',
           '<circle cx="930" cy="330" r="80" fill="none" stroke="#f0c77d"/>']
    for p in result['pairs']:
        color='#83d7b7' if p['separation_arcsec']<=2 else '#f0c77d' if p['separation_arcsec']<=4 else '#ff8f8f'
        parts += [f'<circle cx="{40+500*p["x"]/width:.2f}" cy="{560-450*p["y"]/height:.2f}" r="2" fill="{color}"/>',
                  f'<circle cx="{930+20*p["east_arcsec"]:.2f}" cy="{330-20*p["north_arcsec"]:.2f}" r="2" fill="{color}"/>']
    parts += ['<text x="30" y="605" font-size="16">Échantillon sélectionné par rayon de 8″ ; l’intervalle bootstrap ne constitue pas une erreur astrométrique absolue.</text></g></svg>']
    return '\n'.join(parts)
