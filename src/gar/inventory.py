# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Steve Prud'Homme
# GNU Astrophotography Recycle: read-only traversal and FITS header inventory.
# This program is free software under the GNU GPL, version 3 or later.
# It is distributed WITHOUT ANY WARRANTY. See COPYING for the full license.
"""Inventory without loading pixel arrays or changing source files."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import warnings

from astropy.io import fits

from .contracts import KEYWORDS, json_value

FITS_NAME = re.compile(r"\.(fits?|fts)(\.(gz|fz))?$", re.I)


def is_link(path: Path) -> bool:
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def check_paths(source: Path, output: Path) -> tuple[Path, Path]:
    """Reject collisions and existing outputs before reading any input."""
    if is_link(source) or is_link(output):
        raise ValueError("Les liens et jonctions ne sont pas acceptés comme racines.")
    source = source.resolve(strict=True)
    output = output.resolve()
    if not source.is_dir():
        raise ValueError("La source doit être un dossier.")
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("Le dossier de sortie doit être distinct et extérieur à la source.")
    if output.exists():
        raise ValueError("La sortie existe déjà : choisir un nouveau dossier, sans écrasement.")
    return source, output


def discover(root: Path):
    """Return ordered paths and explicit traversal incidents (no silent skips)."""
    paths, incidents = [], []
    stack = [root]
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    try:
                        if is_link(path):
                            incidents.append({"path": path.relative_to(root).as_posix(),
                                              "status": "skipped_link"})
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(path)
                        elif entry.is_file(follow_symlinks=False) and FITS_NAME.search(entry.name):
                            paths.append(path)
                    except OSError as exc:
                        incidents.append({"path": path.relative_to(root).as_posix(),
                                          "status": "traversal_error", "error": str(exc)})
        except OSError as exc:
            incidents.append({"path": folder.relative_to(root).as_posix(),
                              "status": "traversal_error", "error": str(exc)})
    return sorted(paths), sorted(incidents, key=lambda i: (i["path"], i["status"]))


def sha256_stream(stream):
    digest = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        digest.update(block)
    return digest.hexdigest()


def describe_hdu(hdu, index, digest, filename):
    header = hdu.header
    naxis = header.get("NAXIS", 0)
    dimensions = [header.get(f"NAXIS{i}") for i in range(1, naxis + 1)]
    image = bool(hdu.is_image and naxis > 0)
    stack_count = header.get("STACKCNT")
    stacked = image and (filename.lower().startswith("stacked_") or
                         isinstance(stack_count, (int, float)) and stack_count > 1)
    kind = ("stacked_candidate" if stacked else "image_2d_candidate" if image and naxis == 2
            else "image_other" if image else "empty_primary" if index == 0 and naxis == 0
            else "table_or_other")
    metadata = {key: json_value(header.get(key)) for key in KEYWORDS}
    flags = []
    for key in ("DATE-OBS", "EXPTIME", "TIMESYS"):
        if metadata[key] is None:
            flags.append(f"missing_{key.lower()}")
    if image:
        flags.append("time_semantics_unverified")
    if image and naxis != 2 and metadata["BAYERPAT"] is not None:
        flags.append("bayer_keyword_on_non_2d_image")
    cards = [{"keyword": card.keyword, "value": json_value(card.value), "comment": card.comment}
             for card in header.cards if card.keyword in KEYWORDS]
    return {"hdu_index": index, "frame_id": f"{digest}:{index}", "type": type(hdu).__name__,
            "kind": kind, "dimensions_fits_order": dimensions, "metadata": metadata,
            "raw_cards": cards, "flags": flags,
            "wcs_axes_present": all(header.get(k) for k in ("CTYPE1", "CTYPE2")),
            "wcs_validated": False, "time_validated": False}


def inspect_file(path: Path, root: Path):
    record = {"path": path.relative_to(root).as_posix(), "status": "ok", "sha256": None,
              "size_bytes": None, "hdus": [], "warnings": [], "error": None,
              "duplicate_of": None}
    observed_stat = None
    try:
        if is_link(path):
            raise OSError("Le fichier est devenu un lien depuis le parcours.")
        with path.open("rb") as stream:
            observed_stat = os.fstat(stream.fileno())
            record["size_bytes"] = observed_stat.st_size
            record["sha256"] = sha256_stream(stream)
            stream.seek(0)
            gzip_wrapped = stream.read(2) == b"\x1f\x8b"
            stream.seek(0)
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                try:
                    with fits.open(stream, mode="readonly", memmap=False,
                                   do_not_scale_image_data=True, lazy_load_hdus=False) as hdus:
                        for index, hdu in enumerate(hdus):
                            hdu.verify("exception")
                            item = describe_hdu(hdu, index, record["sha256"], path.name)
                            record["hdus"].append(item)
                            info = hdu.fileinfo()
                            if (not gzip_wrapped and info is not None and
                                    info["datLoc"] + info["datSpan"] > observed_stat.st_size):
                                raise ValueError("FITS tronqué : taille déclarée supérieure au fichier.")
                finally:
                    record["warnings"] = list(dict.fromkeys(str(w.message) for w in captured))
        if record["warnings"]:
            record["status"] = "warning"
    except Exception as exc:
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
    if observed_stat is not None:
        try:
            current_stat = path.stat()
            signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
            if signature(current_stat) != signature(observed_stat):
                record["status"] = "changed"
                record["error"] = "Le fichier a changé pendant l’inventaire ; empreinte non fiable."
        except OSError as exc:
            record["status"], record["error"] = "changed", str(exc)
    return record


def inventory(root: Path, progress=None):
    paths, incidents = discover(root)
    files, seen = [], {}
    for index, path in enumerate(paths, 1):
        record = inspect_file(path, root)
        if record["sha256"] and record["status"] not in ("changed", "error"):
            record["duplicate_of"] = seen.get(record["sha256"])
            seen.setdefault(record["sha256"], record["path"])
        files.append(record)
        if progress is not None and (index % 100 == 0 or index == len(paths)):
            progress(index, len(paths))
    return files, incidents
