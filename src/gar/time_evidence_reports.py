# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Timing evidence reports: declarations never become clock measurements."""
import csv
import json
from html import escape


def evidence_svg(result):
    summary = result['summary']
    n = summary['individual_exposure_candidates']
    rows = [('Date OBS lisible (déclaration)', summary['candidates_with_parsed_date_obs']),
            ('Début et fin lisibles (déclarations)', summary['candidates_with_begin_end_declarations']),
            ('Échelle reconnue (déclaration)', summary['candidates_with_declared_scale']),
            ('Mot-clé firmware explicite (déclaration)', summary['candidates_with_explicit_firmware_keyword']),
            ('HDU temporellement qualifiées', 0)]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="440" viewBox="0 0 1100 440">',
             '<rect width="100%" height="100%" fill="#f6f8fb"/>', '<g font-family="sans-serif" fill="#18394d">',
             '<text x="25" y="38" font-size="23">Préparer les preuves temporelles — aucune horloge qualifiée</text>',
             f'<text x="25" y="72" font-size="16">{summary["files"]} copies ; {summary["hdus"]} HDU ; {n} images 2D candidates. En-têtes uniquement.</text>']
    for i, (label, count) in enumerate(rows):
        y = 115+49*i
        width = 390*count/max(1, n)
        parts += [f'<text x="25" y="{y+20}" font-size="16">{escape(label)}</text>',
                  f'<rect x="420" y="{y}" width="390" height="28" fill="#e0e8ee"/>',
                  f'<rect x="420" y="{y}" width="{width}" height="28" fill="#2b7b95"/>',
                  f'<text x="835" y="{y+20}" font-size="16">{count}/{n}</text>']
    parts += [f'<text x="25" y="390" font-size="16">{summary["independent_evidence_requirements"]} exigences de preuve à compléter ; aucune preuve indépendante fournie à cette analyse.</text>',
              '<text x="25" y="420" font-size="14">Les barres se recouvrent. Résolution écrite, cohérence et précision instrumentale sont distinctes.</text>', '</g></svg>']
    return '\n'.join(parts)


def write_time_evidence_reports(output, result, template):
    (output/'time-evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    (output/'evidence-template.json').write_text(json.dumps(template, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    (output/'time-evidence.svg').write_text(evidence_svg(result), encoding='utf-8')
    with (output/'cards.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        fields = ['file_index', 'hdu_index', 'card_index', 'keyword', 'value', 'value_type', 'comment']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for record in result['records']:
            for card in record['cards']:
                row = {key: card[key] for key in fields if key in card}
                row.update(file_index=record['file_index'], hdu_index=record['hdu_index'])
                for key in ('keyword', 'value', 'comment'):
                    if isinstance(row[key], str) and row[key].lstrip().startswith(('=', '+', '-', '@')):
                        row[key] = "'"+row[key]
                writer.writerow(row)
    text = '# Préparation de la qualification temporelle\n\n```json\n'+json.dumps(result['summary'], ensure_ascii=False, indent=2)+'\n```\n\n'
    text += '![Déclarations temporelles](time-evidence.svg)\n\n'
    for record in result['records']:
        text += f"## Copie {record['file_index']}, HDU {record['hdu_index']}\n\n"
        text += f"Nature : `{record['hdu_kind']}`. Indice du commentaire DATE-OBS : `{record['date_obs_comment_hint']}`.\n\n"
        text += 'Points à examiner : '+', '.join('`'+flag+'`' for flag in record['flags'])+'.\n\n'
    text += ('Les cartes et commentaires sont dans cards.csv et le JSON. Aucune valeur par défaut n’est appliquée à une conversion. '
             'L’intervalle calendaire naïf n’est pas un temps physique écoulé certifié. Les erreurs écrites sont des déclarations ; '
             'PROGRAM ne démontre pas un firmware exact. Aucune heure de milieu UTC n’est calculée.\n\n'
             'Compléter evidence-template.json avec des preuves traçables puis demander une revue ; ce canevas n’est pas ingéré ou approuvé par la commande. '
             'Un essai futur ne certifie pas rétroactivement les archives. Les statuts de qualification/export restent faux. '
             'Données privées : ne pas publier.\n')
    (output/'report.md').write_text(text, encoding='utf-8')
    protocol = ('# Plan de preuves à compléter — aucun essai réalisé\n\n'
        '1. Fixer l’usage, la tolérance et les critères avant essai ; identifier modèle, firmware, application, mode et époque.\n'
        '2. Définir une référence indépendante traçable et son incertitude ; une horloge affichée sur téléphone seule ne suffit pas.\n'
        '3. Enregistrer des événements optiques/électriques datés et relier leur observation au début/fin réel des expositions.\n'
        '4. Mesurer décalage, dérive, dispersion et durée sur des répétitions représentatives ; conserver données brutes et échecs.\n'
        '5. Documenter latences et séquencement du capteur, méthodes, limites et configurations testées.\n'
        '6. Construire un budget avec unités, type d’incertitude, couverture et covariances ; ne pas additionner arbitrairement des sigmas.\n'
        '7. Établir séparément le rattachement aux archives anciennes ; sinon garder leur heure non qualifiée.\n'
        '8. Faire revoir les preuves ; aucune qualification automatique par ce logiciel.\n\n'
        'Protocole détaillé du projet : [Qualification temporelle](https://github.com/steveprudhomme/gnu-astrophotography-recycle/blob/main/docs/PROTOCOLE-QUALIFICATION-TEMPS.md).\n')
    (output/'measurement-plan.md').write_text(protocol, encoding='utf-8')
