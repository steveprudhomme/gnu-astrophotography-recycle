# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: command-line orchestration and provenance.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
import argparse
from datetime import datetime, timezone
from pathlib import Path
import platform
import subprocess
import sys
import uuid

import astropy
import numpy

from . import __version__
from .contracts import SCHEMA_VERSION
from .inventory import check_paths, inventory
from .reports import summarize, write_reports
from .sessions import check_session_output, group_sessions, load_manifest
from .session_reports import write_session_reports
from .timing import audit_timing
from .timing_reports import write_timing_reports
from .wcs_audit import audit_wcs
from .wcs_reports import write_wcs_reports
from .workset import prepare_workset
import hashlib
import json


def source_commit():
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"],
                                cwd=Path(__file__).resolve().parents[2],
                                capture_output=True, text=True, timeout=5, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=normal"],
                               cwd=Path(__file__).resolve().parents[2], capture_output=True,
                               text=True, timeout=5, check=True)
        return {"commit": result.stdout.strip(), "working_tree_dirty": bool(dirty.stdout)}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "working_tree_dirty": None}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inventaire FITS local, en lecture seule.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("inventory", help="Hacher et relever les en-têtes FITS.")
    command.add_argument("source", type=Path, help="Dossier des archives originales.")
    command.add_argument("--output", required=True, type=Path, help="Nouveau dossier de rapports, hors des archives.")
    sessions_command = sub.add_parser("sessions", help="Regrouper les poses d’un manifeste existant.")
    sessions_command.add_argument("manifest", type=Path, help="manifest.json issu de l’inventaire.")
    sessions_command.add_argument("--output", required=True, type=Path, help="Nouveau dossier de rapports privés.")
    sessions_command.add_argument("--gap-seconds", type=float, default=1800,
                                  help="Séparer après un intervalle strictement supérieur au seuil (défaut : 1800 s).")
    timing_command = sub.add_parser("timing", help="Diagnostiquer les heures sans qualifier l’horloge.")
    timing_command.add_argument("manifest", type=Path, help="Manifeste local d’inventaire.")
    timing_command.add_argument("--output", required=True, type=Path, help="Nouveau dossier local de rapports privés.")
    timing_command.add_argument("--gap-seconds", type=float, default=1800,
                               help="Signaler les interruptions au-delà de ce seuil (défaut : 1800 s).")
    wcs_command = sub.add_parser("wcs", help="Examiner les informations WCS d’un manifeste partiel.")
    wcs_command.add_argument("manifest", type=Path, help="Manifeste local d’inventaire.")
    wcs_command.add_argument("--output", required=True, type=Path, help="Nouveau dossier local de rapports privés.")
    wcs_command.add_argument("--max-condition", type=float, default=1e8,
                            help="Seuil de conditionnement numérique du bloc CD, pas de précision astrométrique.")
    workset_command=sub.add_parser('workset',help='Copier une sélection explicite et capturer les en-têtes complets.')
    workset_command.add_argument('selection',type=Path,help='Sélection JSON locale, chemins sources absolus.')
    workset_command.add_argument('--output',required=True,type=Path,help='Nouveau dossier dans local/ du projet.')
    args = parser.parse_args(argv)
    if args.command == "sessions":
        return run_sessions(args)
    if args.command == "timing":
        return run_timing(args)
    if args.command == "wcs":
        return run_wcs(args)
    if args.command == 'workset':
        return run_workset(args)
    try:
        root, output = check_paths(args.source, args.output)
        started = datetime.now(timezone.utc).isoformat()
        files, incidents = inventory(root, progress=lambda done, total: print(
            f"Inventaire : {done}/{total}", file=sys.stderr, flush=True))
        document = {"schema_version": SCHEMA_VERSION, "run_id": str(uuid.uuid4()),
                    "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    "program_version": __version__, "source_revision": source_commit(),
                    "environment": {"python": platform.python_version(), "system": platform.system(),
                                    "astropy": astropy.__version__, "numpy": numpy.__version__},
                    "input_root": str(root), "read_mode": "readonly", "hash_algorithm": "SHA-256",
                    "pixels_loaded": False, "files": files, "traversal_incidents": incidents,
                    "summary": summarize(files, incidents)}
        write_reports(output, document)
    except (ValueError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    summary = document["summary"]
    print(f"{summary['files']} fichiers, {summary['hdus']} HDU, {summary['duplicates']} doublon(s).")
    print(f"Rapports locaux : {output}")
    if (not files or incidents or any(file["status"] != "ok" for file in files)):
        return 2
    return 0


def run_sessions(args):
    try:
        manifest, digest = load_manifest(args.manifest)
        output = check_session_output(args.manifest, args.output, manifest)
        document = group_sessions(manifest, args.gap_seconds)
        document.update(run_id=str(uuid.uuid4()), created_at_utc=datetime.now(timezone.utc).isoformat(),
                        program_version=__version__, source_revision=source_commit(),
                        input_manifest_sha256=digest, input_manifest_path=str(args.manifest.resolve()),
                        input_inventory_run_id=manifest.get('run_id'),
                        input_inventory_revision=manifest.get('source_revision'))
        write_session_reports(output, document)
    except (ValueError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    summary = document['summary']
    print(f"{summary['session_count']} séance(s) candidate(s), {summary['grouped_hdus']} HDU retenues, {summary['excluded_hdus']} exclues.")
    print(f"Rapports locaux : {output}")
    issues = (not document['sessions'] or summary['excluded_hdus'] or summary['file_incidents']
              or summary['inventory_traversal_incidents']
              or any(s['unknown_exposure_count'] or s['duplicate_timestamp_count'] for s in document['sessions']))
    return 2 if issues else 0


def run_timing(args):
    try:
        manifest, digest = load_manifest(args.manifest)
        output = check_session_output(args.manifest, args.output, manifest)
        grouped = group_sessions(manifest, args.gap_seconds)
        document = audit_timing(manifest, grouped, args.gap_seconds)
        document.update(run_id=str(uuid.uuid4()), created_at_utc=datetime.now(timezone.utc).isoformat(),
                        program_version=__version__, source_revision=source_commit(),
                        input_manifest_sha256=digest, input_manifest_path=str(args.manifest.resolve()),
                        input_inventory_run_id=manifest.get('run_id'),
                        input_inventory_revision=manifest.get('source_revision'))
        write_timing_reports(output, document)
    except (ValueError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    summary = document['summary']
    print(f"{summary['candidate_hdus']} HDU candidates, {summary['cadence_hdus']} retenues pour cadence, 0 heure scientifiquement qualifiée.")
    print(f"Rapports locaux : {output}")
    # This version never turns header consistency into clock certification.
    return 2


def run_wcs(args):
    try:
        manifest,digest=load_manifest(args.manifest)
        output=check_session_output(args.manifest,args.output,manifest)
        document=audit_wcs(manifest,args.max_condition)
        document.update(run_id=str(uuid.uuid4()),created_at_utc=datetime.now(timezone.utc).isoformat(),
                        program_version=__version__,source_revision=source_commit(),
                        input_manifest_sha256=digest,input_manifest_path=str(args.manifest.resolve()),
                        input_inventory_run_id=manifest.get('run_id'),
                        input_inventory_revision=manifest.get('source_revision'))
        write_wcs_reports(output,document)
    except (ValueError,OSError) as exc:
        print(f"Erreur : {exc}",file=sys.stderr)
        return 1
    print(f"{document['summary']['input_hdus']} HDU examinées, 0 WCS scientifiquement validée.")
    print(f"Rapports locaux : {output}")
    return 2


def run_workset(args):
    try:
        data=args.selection.read_bytes();selection=json.loads(data)
        report=prepare_workset(selection,args.output,Path(__file__).resolve().parents[2]/'local')
        output=args.output.resolve()
        report.update(program_version=__version__,source_revision=source_commit(),
                      environment={'python':platform.python_version(),'astropy':astropy.__version__,'numpy':numpy.__version__},
                      selection_sha256=hashlib.sha256(data).hexdigest(),
                      created_at_utc=datetime.now(timezone.utc).isoformat())
        (output/'workset.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    except (ValueError,OSError) as exc:
        print(f'Erreur : {exc}',file=sys.stderr);return 1
    print(f"{len(report['files'])} copies vérifiées ; en-têtes complets dans {output}.")
    return 0
