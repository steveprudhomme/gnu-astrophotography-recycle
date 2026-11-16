# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: local timing audit reports.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
import csv
import json


def timing_chart(document):
    s = document['summary']
    values = [('HDU candidates',s['candidate_hdus']),('Retenues pour cadence',s['cadence_hdus']),
              ('Dates invalides/non prises en charge',sum(v for k,v in s['date_status_counts'].items() if k!='parsed_unqualified')),
              ('Conflits de durée',s['duration_conflicts']),('Interruptions',s['gap_count']),
              ('Intervalles courts',s['short_interval_count']),('Dates dupliquées',s['duplicate_timestamp_count']),
              ('Heures scientifiquement qualifiées',0)]
    maximum = max(v for _,v in values) or 1
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="520" viewBox="0 0 1100 520">',
           '<title>Diagnostic temporel : contrôles distincts, non additionnables</title>',
           '<rect width="1100" height="520" fill="#101d30"/>',
           '<g font-family="Segoe UI, Arial, sans-serif" fill="#edf4ff">',
           '<text x="30" y="40" font-size="24">Diagnostic temporel — horloge non qualifiée</text>']
    for i,(label,value) in enumerate(values):
        y=80+i*48
        parts += [f'<text x="30" y="{y+23}" font-size="16">{label}</text>',
                  f'<rect x="400" y="{y}" width="{560*value/maximum:.2f}" height="30" fill="#75c9e8" rx="4"/>',
                  f'<text x="990" y="{y+23}" font-size="18">{value}</text>']
    parts+=['<text x="30" y="495" font-size="15">Ces contrôles se recouvrent : ne pas additionner les barres. Aucun UTC effectif ni milieu de pose calculé.</text></g></svg>']
    return '\n'.join(parts)


def write_timing_reports(output, document):
    output.mkdir(parents=True, exist_ok=False)
    (output/'timing.json').write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    fields=['path','hdu_index','frame_id','applicable','eligible_for_cadence','date_obs_raw',
            'date_parse_status','decimal_places_written','written_quantum_seconds','timesys_declared',
            'scale_status','fits_scale_default_hint','comment_hint','exptime_declared','exposure_declared',
            'duration_keywords_conflict','time_validated','clock_accuracy_seconds','mid_exposure_utc',
            'exclusion_reason','flags']
    with (output/'timing.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in document['records']:
            values={k:row[k] for k in fields};values['flags']=';'.join(row['flags'])
            for k,v in values.items():
                if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')):
                    values[k]="'"+v
            writer.writerow(values)
    (output/'timing.svg').write_text(timing_chart(document),encoding='utf-8')
    s=document['summary']
    lines=['# Diagnostic temporel local','',
           '**Conclusion : horloge et convention instrumentale non qualifiées. Aucun export temporel scientifique autorisé par ce diagnostic.**','',
           f"- HDU candidates : {s['candidate_hdus']}",f"- Retenues pour cadence : {s['cadence_hdus']}",
           f"- Séquences de même configuration/date : {s['sequence_count']}",
           f"- Interruptions : {s['gap_count']} ; intervalles courts : {s['short_interval_count']} ; dates dupliquées : {s['duplicate_timestamp_count']}",
           f"- Conflits EXPTIME/EXPOSURE : {s['duration_conflicts']}",'',
           '![Contrôles temporels](timing.svg)','','## Interprétation','',
           '- Les défauts FITS sont des indications normatives séparées des preuves instrumentales.',
           '- Le nombre de décimales décrit la résolution écrite, pas l’exactitude de l’horloge.',
           '- Un commentaire parlant de création, début ou fin reste une déclaration non vérifiée.',
           '- Les différences de dates naïves ne sont pas des intervalles physiques corrigés ; aucune conversion d’échelle ni correction de seconde intercalaire.',
           '- Les comparaisons de cadence sont limitées à une configuration et une date déclarée ; pas de comparaison entre dossiers/configurations/dates.',
           '- Un intervalle court est une alerte, pas une preuve de chevauchement réel des poses.',
           '- Une cadence régulière ne détecte ni un décalage absolu constant, ni une dérive sans référence indépendante.',
           '- Les observations ne sont pas rouvertes ; le manifeste doit correspondre à l’état des archives à analyser.',
           '- Ce rapport peut contenir des données personnelles : le conserver localement.','',
           '## Pour lever les inconnues','',
           'Obtenir une référence applicable au firmware et au mode d’acquisition, ou un essai indépendant du déclenchement et de la synchronisation, avec incertitude mesurée. Ne pas modifier rétroactivement les originaux pour combler les inconnues.']
    (output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
