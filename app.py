#!/usr/bin/env python3
"""
CBZ/CBR to KePub Converter - web UI

Pick a folder, choose conversion settings, watch live per-file progress.
Pipeline per file: CBZ/CBR -> EPUB (Calibre's ebook-convert) -> real KePub
(kepubify - the same tool Grimmory uses internally).

Runs conversions in a background thread so the browser tab never hangs
waiting on a single long HTTP request (lesson learned the hard way with
Grimmory's bulk sidecar import).

Env vars:
  INPUT_ROOT   Folder containing your series subfolders (default /input)
  OUTPUT_ROOT  Where converted .kepub.epub files go (default /output)
"""

import os
import re
import subprocess
import threading
import uuid
from pathlib import Path

from flask import Flask, render_template, request as flask_request, redirect, url_for, jsonify, flash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

INPUT_ROOT = Path(os.environ.get("INPUT_ROOT", "/input"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/output"))
COMIC_EXTENSIONS = {".cbz", ".cbr"}

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def list_subfolders() -> list[str]:
    if not INPUT_ROOT.is_dir():
        return []
    return sorted(p.name for p in INPUT_ROOT.iterdir() if p.is_dir())


def resolve_input_folder(folder_name: str) -> Path | None:
    if folder_name == "":
        return INPUT_ROOT
    if folder_name in list_subfolders():
        return INPUT_ROOT / folder_name
    return None


def list_comic_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in COMIC_EXTENSIONS)


def update_job(job_id: str, **kwargs):
    with JOBS_LOCK:
        JOBS[job_id].update(kwargs)


def update_file_status(job_id: str, index: int, **kwargs):
    with JOBS_LOCK:
        JOBS[job_id]["files"][index].update(kwargs)


def run_conversion_job(job_id: str, input_folder: Path, output_folder: Path, settings: dict, files: list[Path]):
    output_folder.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_folder / f".tmp-{job_id}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for i, src in enumerate(files):
        update_file_status(job_id, i, status="converting")
        name = src.stem
        epub_path = tmp_dir / f"{name}.epub"
        kepub_path = output_folder / f"{name}.kepub.epub"

        if kepub_path.exists() and settings["skip_existing"]:
            update_file_status(job_id, i, status="skipped")
            with JOBS_LOCK:
                JOBS[job_id]["completed"] += 1
            continue

        convert_cmd = ["xvfb-run", "-a", "ebook-convert", str(src), str(epub_path), "--output-profile", "kobo"]
        if settings["right2left"]:
            convert_cmd.append("--right2left")
        if settings["grayscale"]:
            convert_cmd += ["--colors", "16"]
        if settings["image_width"] and settings["image_height"]:
            convert_cmd += ["--comic-image-size", f"{settings['image_width']}x{settings['image_height']}"]

        result = subprocess.run(convert_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            update_file_status(job_id, i, status="failed", error=f"ebook-convert: {result.stderr[-2000:]}")
            with JOBS_LOCK:
                JOBS[job_id]["completed"] += 1
            continue

        kepubify_cmd = ["kepubify", "--update", "-o", str(output_folder)]
        if settings["hyphenate"]:
            kepubify_cmd.append("--hyphenate")
        if settings["smarten_punctuation"]:
            kepubify_cmd.append("--smarten-punctuation")
        kepubify_cmd.append(str(epub_path))

        result = subprocess.run(kepubify_cmd, capture_output=True, text=True)
        epub_path.unlink(missing_ok=True)

        if result.returncode != 0:
            update_file_status(job_id, i, status="failed", error=f"kepubify: {result.stderr[-2000:]}")
        elif kepub_path.exists():
            update_file_status(job_id, i, status="done")
        else:
            update_file_status(job_id, i, status="failed", error="kepubify reported success but output file not found")

        with JOBS_LOCK:
            JOBS[job_id]["completed"] += 1

    try:
        tmp_dir.rmdir()
    except OSError:
        pass  # leftover files (failed conversions) - fine to leave for inspection

    update_job(job_id, status="done")


@app.route("/")
def index():
    folders = list_subfolders()
    return render_template("index.html", folders=folders, input_root=str(INPUT_ROOT), output_root=str(OUTPUT_ROOT))


@app.route("/convert", methods=["POST"])
def convert():
    folder_name = flask_request.form.get("folder", "")
    input_folder = resolve_input_folder(folder_name)
    if input_folder is None:
        flash(f"Folder not found: {folder_name}")
        return redirect(url_for("index"))

    files = list_comic_files(input_folder)
    if not files:
        flash(f"No .cbz/.cbr files found in {input_folder}")
        return redirect(url_for("index"))

    settings = {
        "right2left": "right2left" in flask_request.form,
        "grayscale": "grayscale" in flask_request.form,
        "hyphenate": "hyphenate" in flask_request.form,
        "smarten_punctuation": "smarten_punctuation" in flask_request.form,
        "skip_existing": "skip_existing" in flask_request.form,
        "image_width": flask_request.form.get("image_width", "").strip(),
        "image_height": flask_request.form.get("image_height", "").strip(),
    }

    output_subdir = OUTPUT_ROOT / folder_name if folder_name else OUTPUT_ROOT

    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "folder": folder_name or "(input root)",
            "status": "running",
            "total": len(files),
            "completed": 0,
            "files": [{"name": f.name, "status": "pending", "error": None} for f in files],
        }

    thread = threading.Thread(
        target=run_conversion_job, args=(job_id, input_folder, output_subdir, settings, files), daemon=True
    )
    thread.start()

    return redirect(url_for("status_page", job_id=job_id))


@app.route("/status/<job_id>")
def status_page(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if job is None:
        flash("Job not found (the app may have restarted).")
        return redirect(url_for("index"))
    return render_template("progress.html", job_id=job_id, job=job)


@app.route("/api/status/<job_id>")
def api_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if job is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
