# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU GPL version 3 or later; WITHOUT ANY WARRANTY. See COPYING.
"""Draw checked diagnostic tables and orientation errors without searching."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from gar.astrometry import local_path
from gar.workset import digest
import diagnose_slow_misses as diagnostic
from plot_seestar_pilot import render

ROOT = Path(__file__).resolve().parents[1]


def plot(path, output, base=None):
    base = ROOT/'local' if base is None else base
    path = local_path(path, base)
    result, watched = diagnostic.checked_diagnostic(path, base)
    output = local_path(output, base); output.mkdir(parents=True, exist_ok=False)
    label = 'ENTIÈREMENT FICTIF' if result['source_kind'] == 'synthetic_demo' else 'FOND RÉEL + AJOUTS — PRIVÉ'
    fig, ax = plt.subplots(figsize=(13, 6), layout='constrained'); ax.axis('off')
    cells, row_labels, selected = [], [], []
    for row in result['rows']:
        state = 'indisponible' if not row['available'] else 'retrouvé' if row['originally_recovered'] == 1 else 'manqué'
        row_labels.append(row['case_id']+' · '+state)
        local = row['radii'][0] if row['radii'] else None
        selected.append(local)
        if local:
            support = local['mapped_support']
            cells.append([*['oui' if f['mapped']['within_radius'] else 'non' for f in local['frames']],
                          f"{support['frames']}/8", f"{support['span_declared_seconds']:.0f} s"])
        else:
            cells.append(['?']*10)
    table = ax.table(cellText=cells, rowLabels=row_labels,
                     colLabels=[f'Photo {k+1}' for k in range(8)]+['Nombre', 'Durée'],
                     cellLoc='center', bbox=[.23, .25, .77, .60])
    table.auto_set_font_size(False); table.set_fontsize(10)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#152b40'); cell.set_text_props(color='#152b40')
        yes = r > 0 and 0 <= c < 8 and selected[r-1] and selected[r-1]['frames'][c]['mapped']['within_radius']
        cell.set_facecolor('#cde5f7' if yes else '#ffffff')
    ax.set_title(label+' — les points proches déjà enregistrés\nSix ajouts brillants ; aucun nouveau candidat calculé.', color='#152b40', fontsize=13)
    fig.supxlabel('« oui » : mesure à 1,5 pixel natif au plus de la réponse connue après recherche.\n'
        'Le profil exige au moins six photos couvrant 1800 secondes ; nombre et durée comptent ensemble.\n'
        'Un point proche peut être une autre source. La proximité ne prouve pas une identité.', fontsize=10)
    render(fig).save(output/'support.png')
    fig, ax = plt.subplots(figsize=(11, 5), layout='constrained')
    audit = result['registration_audit']
    if audit['applicable']:
        frames = audit['frames']
        ax.plot([f['frame_index']+1 for f in frames], [f['rotation_error_degrees'] for f in frames],
                's-', color='#152b40', label='Écart au modèle inverse de fabrication')
        ax.axhline(0, color='#555555', linestyle='--', linewidth=1)
        ax.set(xlabel='Numéro de la photo fictive', ylabel='Écart de rotation signé (degrés)', xticks=range(1, 9))
        ax.legend(loc='best'); ax.grid(alpha=.2)
    else:
        ax.axis('off'); ax.text(.5, .5, 'Fabrication inconnue : comparaison sans objet sur fond réel.', ha='center', transform=ax.transAxes)
    ax.set_title(label+' — contrôle indépendant de la fabrication connue', fontsize=12)
    fig.supxlabel('La courbe décrit les modèles conservés. Aucun modèle corrigé ou remplacé.\n'
        'Un écart proche de 180° correspond à un demi-tour ; ce constat ne suffit pas à expliquer tous les manques.', fontsize=10)
    render(fig).save(output/'orientation.png')
    diagnostic.slow.unchanged(watched)
    journal = dict(slow_diagnostic_figures_version='1.0', diagnostic_sha256=watched[path],
                   source_kind=result['source_kind'], detector_called=False, association_called=False,
                   figures_sha256={p.name: digest(p) for p in sorted(output.glob('*.png'))})
    diagnostic.slow.save(output/'figures.json', journal)
    print('Deux figures dessinées depuis les preuves conservées, sans nouvelle recherche.')
    return journal


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diagnostic', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        plot(args.diagnostic, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Erreur : {exc}\n')
