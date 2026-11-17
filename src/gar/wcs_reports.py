# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: reports for partial WCS diagnostics.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
import csv
from html import escape
import json


def wcs_chart(document):
    counts=sorted(document['summary']['status_counts'].items())
    height=180+45*len(counts)
    maximum=max((v for _,v in counts),default=1) or 1
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}">',
           '<title>Diagnostic WCS : catégories exclusives, sans qualification astrométrique</title>',
           f'<rect width="1200" height="{height}" fill="#101d30"/>',
           '<g font-family="Segoe UI, Arial, sans-serif" fill="#edf4ff">',
           '<text x="30" y="40" font-size="24">Informations WCS observées — aucune solution certifiée</text>']
    for index,(label,value) in enumerate(counts):
        y=85+index*45
        lines += [f'<text x="30" y="{y+23}" font-size="16">{escape(label)}</text>',
                  f'<rect x="560" y="{y}" width="{500*value/maximum:.2f}" height="30" fill="#75c9e8" rx="4"/>',
                  f'<text x="1100" y="{y+23}" font-size="18">{value}</text>']
    lines += [f'<text x="30" y="{height-40}" font-size="16">Manifeste partiel : aucune transformation pixels-vers-ciel ni comparaison à un catalogue.</text>',
              f'<text x="30" y="{height-15}" font-size="15">Un champ non collecté n’est pas déclaré absent du FITS original.</text></g></svg>']
    return '\n'.join(lines)


def write_wcs_reports(output, document):
    output.mkdir(parents=True,exist_ok=False)
    (output/'wcs.json').write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    fields=['path','hdu_index','frame_id','kind','status','pointing_values_present',
            'primary_axes_observed','matrix_nonsingular','matrix_condition_number_raw_units',
            'reference_pixel_outside_pixel_center_range','wcs_validated','astrometric_accuracy_arcsec',
            'recommended_next_step','flags']
    with (output/'wcs.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in document['records']:
            values={k:row[k] for k in fields};values['flags']=';'.join(row['flags'])
            for key,value in values.items():
                if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):
                    values[key]="'"+value
            writer.writerow(values)
    (output/'wcs.svg').write_text(wcs_chart(document),encoding='utf-8')
    s=document['summary']
    lines=['# Diagnostic WCS local','',
           '**Le contexte du manifeste est partiel : aucune solution astrométrique n’est certifiée.**','',
           f"- Fichiers : {s['input_files']} ; HDU : {s['input_hdus']}",
           f"- Blocs linéaires numériquement cohérents : {s['numeric_linear_blocks_consistent']}",
           '- WCS scientifiquement validées : 0','',
           '![Statuts du diagnostic WCS](wcs.svg)','','## Limites et suite','',
           '- RA/DEC de pointage ne sont pas une transformation pixels-vers-ciel.',
           '- Le manifeste ne capture pas tous les paramètres, unités, référentiels, distorsions ou versions WCS alternatives.',
           '- Les contrôles portent sur les axes primaires et, si disponible, le bloc CD de deux axes.',
           '- Une matrice incomplète peut relever d’une autre paramétrisation valide ; aucune valeur par défaut n’est inventée.',
           '- Un pixel de référence extérieur à l’image peut être valide ; il est seulement signalé.',
           '- Le conditionnement est calculé dans les unités numériques brutes ; son seuil n’est pas une précision astrométrique.',
           '- Aucun étalonnage d’échelle angulaire, test pixels-vers-ciel ou résidu de catalogue n’est calculé.',
           '- Ne pas transférer la WCS d’un empilement sur les poses sans traiter leur géométrie propre.',
           '- La prochaine étape est une collecte complète du contexte, puis une résolution ou une comparaison au catalogue si nécessaire.',
           '- Conserver ces rapports localement : ils peuvent contenir des chemins et métadonnées privés.']
    (output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
