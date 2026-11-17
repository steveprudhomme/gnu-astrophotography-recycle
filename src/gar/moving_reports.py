# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Synthetic benchmark reports; no real image, astrometry or time certification."""
import csv
import json
from html import escape


def moving_svg(result):
    height = 100+28*len(result['sequences'])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1150" height="{height}" viewBox="0 0 1150 {height}">',
             '<rect width="100%" height="100%" fill="#f6f8fb"/><g font-family="sans-serif" fill="#173b50">',
             '<text x="25" y="35" font-size="22">Mobiles synthétiques : résultats réellement calculés</text>',
             '<text x="25" y="65" font-size="15">Séquence / graine</text><text x="390" y="65">Retrouvés / injectés</text><text x="650" y="65">Faux candidats</text><text x="880" y="65">Interprétation</text>']
    for i, s in enumerate(result['sequences']):
        y = 95+i*28; e = s['evaluation']; scope = 'Critères principaux' if s['scenario'] in ('nominal','missing','control') else 'Sensibilité descriptive'
        parts += [f'<text x="25" y="{y}" font-size="14">{escape(s["sequence_id"])}</text>',
                  f'<text x="390" y="{y}">{e["recovered"]}/{e["injected"]}</text>',
                  f'<text x="650" y="{y}">{e["false_candidates"]}</text><text x="880" y="{y}" font-size="13">{scope}</text>']
    return '\n'.join(parts+['</g></svg>'])


def write_moving_reports(output, result):
    (output/'moving.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    (output/'moving.svg').write_text(moving_svg(result), encoding='utf-8')
    with (output/'candidates.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['sequence_id','candidate_id','frame_count','vx_pixels_per_second','vy_pixels_per_second','rms_pixels','p95_pixels']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for sequence in result['sequences']:
            name = sequence['sequence_id']; name = "'"+name if name.lstrip().startswith(('=','+','-','@')) else name
            for t in sequence['tracks']:
                writer.writerow({'sequence_id': name, 'candidate_id': t['candidate_id'], 'frame_count': len(t['points']),
                    'vx_pixels_per_second': t['velocity_pixels_per_second'][0], 'vy_pixels_per_second': t['velocity_pixels_per_second'][1],
                    'rms_pixels': t['rms_pixels'], 'p95_pixels': t['p95_pixels']})
    text = '# Prototype de mobiles — données synthétiques uniquement\n\n```json\n'+json.dumps(result['summary'], indent=2)+'\n```\n\n'
    text += '![Bilan par séquence](moving.svg)\n\n'
    for s in result['sequences']:
        e = s['evaluation']
        text += f"- `{s['sequence_id']}` : {e['recovered']}/{e['injected']} retrouvés, {e['false_candidates']} faux candidats ; manqués : "+', '.join(e['missed_injection_ids'])+'.\n'
    text += ('\nLa vérité injectée sert uniquement au bilan après gel des candidats. Les cas difficiles sont conservés. '
             'Filtrage stationnaire et rayon d’association limitent la sensibilité. Images déjà dans un repère commun, modèle rectiligne, '
             'temps fictifs : aucune vitesse céleste, qualification de l’horloge réelle ou découverte confirmée. '
             'Le total mélange les scénarios ; utiliser leurs bilans séparés. Aucun budget complet de covariance ou domaine réel étalonné.\n')
    (output/'report.md').write_text(text, encoding='utf-8')
