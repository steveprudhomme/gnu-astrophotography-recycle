# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: local inventory reports and vector chart.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Report only; no access to original images or scientific conversions."""
from collections import Counter
import csv
from html import escape
import json
from pathlib import Path


def summarize(files, incidents):
    hdus = [hdu for file in files for hdu in file["hdus"]]
    return {"files": len(files), "hdus": len(hdus),
            "file_status": dict(Counter(file["status"] for file in files)),
            "kinds": dict(Counter(hdu["kind"] for hdu in hdus)),
            "duplicates": sum(file["duplicate_of"] is not None for file in files),
            "traversal_incidents": len(incidents),
            "wcs_axes_present": sum(bool(h["wcs_axes_present"]) for h in hdus),
            "limits": ["En-têtes et empreintes seulement ; pixels non validés.",
                       "Heures brutes, sans conversion ni milieu de pose calculé.",
                       "Présence de mots-clés WCS sans validation astrométrique.",
                       "Classifications indicatives, sans preuve de calibration."]}


def chart(summary):
    kinds = sorted(summary["kinds"].items()) or [("aucune HDU", 0)]
    height = 160 + 55 * len(kinds)
    maximum = max((value for _, value in kinds), default=1) or 1
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="{height}" viewBox="0 0 960 {height}">',
             '<title>Inventaire : catégories de HDU, doublons inclus</title>',
             f'<rect width="960" height="{height}" fill="#101d30"/>',
             '<g font-family="Segoe UI, Arial, sans-serif" fill="#edf4ff">',
             '<text x="30" y="40" font-size="24">Inventaire FITS — catégories de HDU</text>',
             f'<text x="30" y="75" font-size="17">{summary["files"]} fichiers · {summary["hdus"]} HDU · {summary["duplicates"]} doublon(s)</text>']
    for index, (kind, value) in enumerate(kinds):
        y = 105 + index * 55
        parts.extend([f'<text x="30" y="{y+23}" font-size="17">{escape(kind)}</text>',
                      f'<rect x="300" y="{y}" width="{520*value/maximum:.2f}" height="32" rx="4" fill="#75c9e8"/>',
                      f'<text x="850" y="{y+23}" font-size="18">{value}</text>'])
    parts.append(f'<text x="30" y="{height-20}" font-size="15">Classification indicative ; chaque HDU et chaque copie sont comptées.</text></g></svg>')
    return "\n".join(parts)


def csv_cell(value):
    """Escape textual spreadsheet formulas; original values remain in JSON."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def write_reports(output: Path, document):
    """Never reuse an output directory or overwrite an existing report."""
    output.mkdir(parents=True, exist_ok=False)
    summary = document["summary"]
    (output / "manifest.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    fields = ["path", "file_status", "sha256", "duplicate_of", "hdu_index", "frame_id", "kind",
              "dimensions_fits_order", "date_obs_raw", "exptime_seconds_declared", "filter_declared",
              "bayer_declared", "wcs_axes_present", "flags", "error"]
    with (output / "inventory.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for file in document["files"]:
            for hdu in file["hdus"] or [None]:
                row = {"path": file["path"], "file_status": file["status"], "sha256": file["sha256"],
                       "duplicate_of": file["duplicate_of"], "error": file["error"]}
                if hdu is not None:
                    meta = hdu["metadata"]
                    row.update({key: hdu[key] for key in ("hdu_index", "frame_id", "kind", "wcs_axes_present")})
                    row.update(dimensions_fits_order=json.dumps(hdu["dimensions_fits_order"]),
                               date_obs_raw=meta["DATE-OBS"], exptime_seconds_declared=meta["EXPTIME"],
                               filter_declared=meta["FILTER"], bayer_declared=meta["BAYERPAT"],
                               flags=";".join(hdu["flags"]))
                writer.writerow({key: csv_cell(value) for key, value in row.items()})
    (output / "summary.svg").write_text(chart(summary), encoding="utf-8")
    lines = ["# Rapport d’inventaire local", "", "Ce dossier peut contenir des données privées. Ne pas le publier.", "",
             f"- Fichiers : {summary['files']}", f"- HDU : {summary['hdus']}",
             f"- Doublons binaires : {summary['duplicates']}",
             f"- Statuts fichiers : {json.dumps(summary['file_status'], ensure_ascii=False)}",
             f"- Incidents de parcours : {summary['traversal_incidents']}", "",
             "![Catégories des HDU](summary.svg)", "", "## Limites", ""]
    lines.extend(f"- {limit}" for limit in summary["limits"])
    lines.extend(["", "Le manifeste JSON conserve les valeurs brutes sélectionnées et les commentaires.",
                  "Le CSV contient une ligne par HDU, ou une ligne par fichier sans HDU lisible.",
                  "Les textes pouvant être interprétés comme formules sont préfixés par une apostrophe dans le CSV seulement.",
                  "Si un fichier change pendant la lecture, son empreinte est à recalculer. Aucune comparaison SHA-256 après exécution n’est automatique."])
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
