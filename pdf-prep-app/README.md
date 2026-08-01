# Course Eval PDF Filter

A Streamlit front-end for `filter_course_evals.py`. It takes scanned course-evaluation
report PDFs and produces a `<name>_filtered.pdf` for each one, keeping only:

1. The printed header block (professor, course name/code, enrollment, responses, response rate), and
2. The target question, together with **all** of its handwritten student answers.

Everything else (score tables, other questions) is dropped. This is meant as a
prep step before feeding the filtered PDFs into EvalReader.

## Files

- `filter_course_evals.py` — the original, unmodified extraction/cropping logic (CLI-capable on its own; see its docstring).
- `app.py` — the Streamlit UI. Imports `filter_course_evals.py` as a module and calls its `process_pdf()` function directly; no logic in that file is changed.
- `requirements.txt` — Python dependencies.
- `packages.txt` — apt package (`tesseract-ocr`) so the optional `--ocr` fallback binary is available on Streamlit Community Cloud.

## Access control

The app is gated behind a single shared password (everyone uses the same one —
there are no individual accounts). It reads the password from Streamlit's
secrets as `APP_PASSWORD`.

**Local:** copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
and set your own password:
```toml
APP_PASSWORD = "your-password-here"
```
`.streamlit/secrets.toml` is already in `.gitignore`, so it never gets committed.

**Streamlit Community Cloud:** go to your app → **Settings** → **Secrets**,
and paste:
```toml
APP_PASSWORD = "your-password-here"
```
Save, and the app will restart with the gate active.

If `APP_PASSWORD` isn't set, the app shows a clear error asking for it to be
configured, rather than silently failing open.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a new GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Point it at your repo, branch, and set the main file path to `app.py`.
4. Deploy. `packages.txt` will automatically install the Tesseract binary if you
   plan to use the OCR fallback checkbox; if you never enable OCR you can
   delete `packages.txt`.

## Using the app

1. Upload one or more PDFs, or a single ZIP archive containing PDFs.
2. Adjust the target question text or output quality (DPI) in the sidebar if needed — 250 DPI works well for most reports.
3. Click **Run Filter**.
4. Review the results table (source file, output file, status, size, notice count).
5. Download individually via **Download individual files**, or click **Download All as ZIP**.
6. Open **Details (per-file processing notes)** if a file shows "No output" or
   has notices — this shows the original script's own diagnostic messages
   (e.g. "target question not found", "response rate exceeds 100%") per file.

Two advanced options from the original CLI (`--vector` output and the `--ocr`
fallback for text-less scans) are not exposed in the UI — they're left at the
script's own defaults (raster output, no OCR), since that's what every report
processed so far has needed. If you ever need either one, they can be added
back to the sidebar, or you can still run `filter_course_evals.py` directly
from the command line with `--vector` / `--ocr`.
