# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: local reports for candidate sessions.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
import csv
import json


def _cell(value):
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def session_chart(document):
    sessions = document['sessions']
    visible = sessions[:30]
    height = 180 + len(visible) * 42
    maximum = max((s['frame_count'] for s in visible), default=1) or 1
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}">',
             '<title>Séances candidates : nombre de HDU regroupées</title>',
             f'<rect width="960" height="{height}" fill="#101d30"/>',
             '<g font-family="Segoe UI, Arial, sans-serif" fill="#edf4ff">',
             '<text x="30" y="40" font-size="24">Séances candidates — aucune conversion horaire</text>',
             f'<text x="30" y="76" font-size="17">{len(sessions)} groupe(s) · {document["summary"]["grouped_hdus"]} HDU retenues · {document["summary"]["excluded_hdus"]} exclues</text>']
    for index, session in enumerate(visible):
        y = 100 + index * 42
        parts.extend([f'<text x="30" y="{y+23}" font-size="16">Groupe {index+1:02d}</text>',
                      f'<rect x="220" y="{y}" width="{560*session["frame_count"]/maximum:.2f}" height="30" rx="4" fill="#83d7b7"/>',
                      f'<text x="820" y="{y+23}" font-size="17">{session["frame_count"]}</text>'])
    parts.append(f'<text x="30" y="{height-35}" font-size="15">{len(visible)} groupe(s) affiché(s), dans l’ordre du JSON ; copies et empilements exclus.</text>')
    parts.append(f'<text x="30" y="{height-12}" font-size="15">Le découpage par date déclarée ne définit pas une nuit astronomique.</text></g></svg>')
    return '\n'.join(parts)


def write_session_reports(output, document):
    output.mkdir(parents=True, exist_ok=False)
    (output/'sessions.json').write_text(json.dumps(document, ensure_ascii=False, indent=2,
                                                  allow_nan=False), encoding='utf-8')
    fields = ['session_id', 'directory', 'object_declared', 'filter_declared', 'timesys_declared',
              'declared_date', 'frame_count', 'first_time_raw', 'last_time_raw',
              'timestamp_span_seconds', 'total_exposure_seconds_declared',
              'known_exposure_sum_seconds', 'unknown_exposure_count', 'largest_gap_seconds', 'flags']
    with (output/'sessions.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for session in document['sessions']:
            config = session['configuration']
            row = {key: session[key] for key in fields if key in session and key != 'flags'}
            row.update(directory=config['directory'], object_declared=config['OBJECT'],
                       filter_declared=config['FILTER'], timesys_declared=config['TIMESYS'],
                       declared_date=config['declared_date'], flags=';'.join(session['flags']))
            writer.writerow({key: _cell(value) for key, value in row.items()})
    (output/'sessions.svg').write_text(session_chart(document), encoding='utf-8')
    summary = document['summary']
    lines = ['# Regroupement indicatif des séances', '',
             'Rapport privé : ne pas publier les dates, coordonnées ou chemins sans revue.', '',
             f"- Groupes : {summary['session_count']}", f"- HDU retenues : {summary['grouped_hdus']}",
             f"- HDU exclues : {summary['excluded_hdus']}",
             f"- Motifs d’exclusion : {json.dumps(summary['exclusion_reasons'], ensure_ascii=False)}", '',
             '![Nombre de HDU par séance candidate](sessions.svg)', '', '## Lecture et limites', '',
             '- Dates brutes : aucun fuseau, UTC, début ou milieu de pose n’est supposé.',
             '- Le découpage à minuit peut diviser une vraie séance ; les dossiers restent séparés.',
             '- La couverture est l’écart entre premier et dernier horodatages, sans ajout de durée de pose.',
             '- Une intégration totale inconnue reste vide/null ; la somme partielle connue est distincte.',
             '- Les durées sont celles déclarées pour chaque HDU retenue, sans validation instrumentale.',
             '- Les dates identiques de fichiers différents sont signalées, pas fusionnées par supposition.',
             '- Le JSON conserve les membres et toutes les exclusions ; le CSV est une vue de consultation.',
             '- Les numéros du graphique suivent l’ordre du JSON/CSV ; seuls les 30 premiers sont affichés.']
    (output/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
