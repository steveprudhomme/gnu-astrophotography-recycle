# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Optional Matplotlib plot of actual header-dossier counts, not clock accuracy."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(report, output, synthetic=False):
    result = json.loads(Path(report).read_text(encoding='utf-8')); s = result['summary']
    n = s['individual_exposure_candidates']
    labels = ['DATE-OBS lisible', 'Début et fin lisibles', 'Échelle reconnue déclarée',
              'Mot-clé firmware explicite', 'Images candidates qualifiées']
    values = [s['candidates_with_parsed_date_obs'], s['candidates_with_begin_end_declarations'],
              s['candidates_with_declared_scale'], s['candidates_with_explicit_firmware_keyword'], s['qualified_hdus']]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), gridspec_kw={'height_ratios': [3, 1]})
    ax, note = axes
    ax.barh(labels, values, color=['#287e98']*4+['#b24e36'])
    ax.invert_yaxis(); ax.set_xlim(0, max(1, n)+.65)
    ax.set_xticks(range(max(1, n)+1)); ax.grid(axis='x', alpha=.2); ax.set_axisbelow(True)
    for i, value in enumerate(values): ax.text(value+.07, i, f'{value}/{n}', va='center', fontsize=12)
    ax.set_xlabel('Nombre d’images 2D candidates — déclarations non indépendantes')
    ax.set_title(f'{s["files"]} copies ; {s["hdus"]} HDU ; {n} images candidates\nLisibilité et présence de mots-clés ne démontrent pas leur exactitude', fontsize=12, pad=18)
    note.axis('off')
    note.text(.5, .8, f'{s["independent_evidence_requirements"]} exigences de preuve à compléter', ha='center', fontsize=15, weight='bold', color='#173b50')
    note.text(.5, .42, 'Référence traçable → événements mesurés → budget d’incertitude → revue d’applicabilité', ha='center', fontsize=11)
    note.text(.5, .07, 'Aucune mesure d’horloge réalisée ; aucun milieu UTC calculé ; export scientifique refusé.', ha='center', fontsize=11)
    origin = 'EXEMPLE SYNTHÉTIQUE — données fictives' if synthetic else 'RAPPORT RÉEL PRIVÉ — ne pas publier'
    fig.suptitle(origin+'\nPréparer la qualification temporelle', fontsize=16)
    fig.tight_layout(rect=(0, 0, 1, .91))
    fig.savefig(output, dpi=160, metadata={'Description': origin})
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--synthetic', action='store_true')
    args = parser.parse_args(); plot(args.report, args.output, args.synthetic)
