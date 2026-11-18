# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Fictitious timing intervals: arithmetic is not clock qualification."""
import argparse
from pathlib import Path
import json
import math


def compatible_interval(entry, exit, exposure, convention='start'):
    """Actual exposure start minus recorded epoch, under the chosen convention.

    These bounds require a complete field crossing within the exposure, correct
    identity and orbit, and known geometry. They omit unquantified uncertainties.
    For midpoint/end the returned offset concerns the corresponding event.
    """
    if (any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
            for v in (entry,exit,exposure)) or exposure<=0 or entry>exit):
        raise ValueError('Entrée et sortie ordonnées, valeurs finies et durée positive requises.')
    if convention not in ('start','midpoint','end'):
        raise ValueError('Choisir start, midpoint ou end.')
    if exit-entry>exposure:
        return None
    shift={'start':0,'midpoint':exposure/2,'end':exposure}[convention]
    return [exit-exposure+shift,entry+shift]


def intersection(intervals):
    if not intervals or any(i is None for i in intervals):
        return None
    left=max(i[0] for i in intervals);right=min(i[1] for i in intervals)
    return [left,right] if left<=right else None


def demonstration(output):
    if output.exists():
        raise ValueError('Choisir un fichier SVG nouveau.')
    rows=[('Fictif A',3,5),('Fictif B',1,4),('Fictif C : contrôle séparé',2,6)]
    intervals=[compatible_interval(a,b,10) for _,a,b in rows]
    estimated=intersection(intervals[:2]);checked=intersection([estimated,intervals[2]])
    assert estimated==[-5,1] and checked==[-4,1]
    assert compatible_interval(0,11,10) is None
    assert compatible_interval(3,5,10,'midpoint')==[0,8]
    assert compatible_interval(3,5,10,'end')==[5,13]
    x=lambda value:500+30*value
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="420" viewBox="0 0 1000 420" role="img" aria-labelledby="title desc">',
        '<title id="title">Exemple entièrement fictif de plages temporelles compatibles</title>',
        '<desc id="desc">Deux passages fictifs donnent une intersection de moins cinq à plus une seconde. Un troisième passage distinct laisse moins quatre à plus une seconde. Cela ne certifie pas une horloge.</desc>',
        '<rect width="1000" height="420" fill="white"/>',
        '<g font-family="Arial,sans-serif" fill="#16324f"><text x="35" y="35" font-size="24">IMAGES ET VALEURS FICTIVES — aucun résultat Seestar</text>',
        '<text x="35" y="67" font-size="18">Décalage compatible du début réel par rapport à l’heure enregistrée</text>']
    for index,((label,_,_),interval) in enumerate(zip(rows,intervals)):
        y=120+index*65
        svg += [f'<text x="30" y="{y+6}" font-size="17">{label}</text>',
            f'<line x1="{x(interval[0])}" x2="{x(interval[1])}" y1="{y}" y2="{y}" stroke="#16324f" stroke-width="12"/>',
            f'<text x="825" y="{y+6}" font-size="17">[{interval[0]}, {interval[1]}] s</text>']
    svg += [f'<rect x="{x(checked[0])}" y="282" width="{x(checked[1])-x(checked[0])}" height="24" fill="#d4e9f7" stroke="#16324f"/>',
        '<text x="30" y="300" font-size="17">Intersection conditionnelle</text>']
    for value in range(-10,11,2):
        svg += [f'<line x1="{x(value)}" x2="{x(value)}" y1="325" y2="333" stroke="#16324f"/>',
            f'<text x="{x(value)}" y="353" font-size="15" text-anchor="middle">{value}</text>']
    svg += ['<text x="35" y="395" font-size="18">Hypothèses et erreurs non quantifiées restent à vérifier : ce dessin ne qualifie aucune horloge.</text></g></svg>']
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('\n'.join(svg),encoding='utf-8')
    return dict(kind='entirely_fictitious',intervals=intervals,development_intersection=estimated,
        intersection_with_separate_control=checked,clock_qualified=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    print(json.dumps(demonstration(args.output),ensure_ascii=False))
