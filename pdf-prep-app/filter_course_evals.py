#!/usr/bin/env python3
"""
filter_course_evals.py
======================

Given a scanned course-evaluation report PDF (or a folder of them), produce a
new "<name>_filtered.pdf" that keeps ONLY:

  1. The printed header block on the report's page 2
     (professor name, course name + code, course enrollment,
      number of responses, response rate), and

  2. The target question
        "What would you say to a classmate who was planning to take this class?"
     together with ALL of its handwritten student answers.

Everything in between -- survey score tables and every other question -- is
dropped.

Design notes
------------
* Runs 100% locally. No cloud calls.
* These reports already carry a clean PRINTED-TEXT layer (metadata + questions
  are real, extractable text). We use that text layer to LOCATE the crop
  regions precisely -- this is faster and far more accurate than OCR.
  Tesseract OCR is used ONLY as a fallback to locate text on pages that have no
  usable text layer (true scans). Enable with --ocr.
* The student answers are handwriting. They are NEVER OCR'd or parsed -- they
  are preserved purely as image, exactly as scanned.
* Output is RASTERIZED per crop region (default). This guarantees that the
  dropped content (score tables, other students' answers to other questions) is
  genuinely absent from the output bytes -- not merely hidden. Use --vector for
  a smaller, text-selectable output IF you accept that clipped-away content
  remains embedded (hidden) in the file.

Usage
-----
    python3 filter_course_evals.py INPUT [-o OUTDIR] [--dpi 250] [--ocr] [--vector]

    INPUT   a single .pdf, or a folder containing .pdf files.
    OUTDIR  output directory (default: ./FilteredData, created automatically).

Dependencies: PyMuPDF (fitz). Optional: pytesseract + Tesseract binary (--ocr).
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("ERROR: PyMuPDF is required.  Install with:  python3 -m pip install PyMuPDF")


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DEFAULT_QUESTION = "What would you say to a classmate who was planning to take this class?"

# Page geometry margins (PDF points). Body = between the top running-header and
# the bottom footer band.
BODY_TOP = 32.0        # below the top running header line
BODY_BOTTOM = 738.0    # above the footer (date / "Class Climate Evaluation" / "Page N")
HEADER_TOP = 32.0      # top of the header crop (captures the metadata box + logo)

# Small vertical pads so we never clip the very line we anchor to.
PAD_ABOVE_QUESTION = 9.0   # keep the "N.M)" marker + question text, drop the answer above it
PAD_BEFORE_BOUNDARY = 6.0  # stop just above the next question header
PAD_ABOVE_SURVEY = 5.0     # header crop stops just above the "Survey Results" banner

# Regex for the comment-question marker, e.g. "1.8)"  "2.10)"
MARKER_RE = re.compile(r"^\s*\d+\.\d+\)\s*$")

# Course-code line inside the metadata box, e.g. "(F25-LAW-1087-01)" or
# "(W26-LAW-3001-01-1)".
COURSE_CODE_RE = re.compile(r"\([A-Z]{1,4}\d{2}-[A-Z0-9]+-[\w-]+\)")

# Text signals used to segment the file into individual reports and to find the
# metadata header page of each report.
COVER_SIGNALS = ("Survey Evaluation Results", "Dear Mr./Dear Ms.", "Dear Mr.")
HEADER_SIGNALS = ("enrollment =", "responses =", "esponse rate =")  # 'R'/'r' tolerant


# --------------------------------------------------------------------------- #
# Text-layer helpers
# --------------------------------------------------------------------------- #

def normalize(s: str) -> str:
    """Lowercase, collapse everything non-alphanumeric to single spaces."""
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def page_lines(page):
    """Return body text lines as list of dicts: {text, x0, y0, x1, y1}."""
    out = []
    d = page.get_text("dict")
    for block in d["blocks"]:
        if block.get("type") != 0:  # skip image blocks
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            out.append({"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1})
    return out


def collect_question_headers(page, page_index):
    """
    Find comment-question headers on a page.

    A header is a "N.M)" marker line in the body, paired with the question text
    printed just to its right / same visual line. Returns list of dicts:
        {page, marker_y0, marker, question_text}
    """
    lines = page_lines(page)
    headers = []
    for ln in lines:
        if not MARKER_RE.match(ln["text"]):
            continue
        if not (BODY_TOP < ln["y0"] < BODY_BOTTOM):
            continue
        if ln["x0"] > 70:  # markers sit at the far-left column
            continue
        my0 = ln["y0"]
        # Gather the question text on the same visual line (allow small wrap).
        qparts = [
            o["text"]
            for o in lines
            if 40 <= o["x0"] < 320 and (my0 - 4) <= o["y0"] <= (my0 + 16)
        ]
        qtext = " ".join(qparts).strip()
        headers.append(
            {
                "page": page_index,
                "marker_y0": my0,
                "marker": ln["text"].strip(),
                "question_text": qtext,
            }
        )
    return headers


def find_survey_results_y(page):
    """y0 of the 'Survey Results' banner on a header page (None if absent)."""
    for ln in page_lines(page):
        if normalize(ln["text"]) == "survey results":
            return ln["y0"]
    return None


def header_bottom_fallback(page):
    """
    Bottom of the header crop when there is no 'Survey Results' banner to anchor
    on: just below the lowest recognizable metadata line (course-code line or an
    enrollment / responses / response-rate line). Falls back to a fixed offset.
    """
    bottom = 0.0
    for ln in page_lines(page):
        t = ln["text"]
        if COURSE_CODE_RE.search(t) or any(s in t for s in HEADER_SIGNALS):
            bottom = max(bottom, ln["y1"])
    return (bottom + 10.0) if bottom else 120.0


# --------------------------------------------------------------------------- #
# Optional OCR fallback (only for pages with no text layer)
# --------------------------------------------------------------------------- #

_OCR_READY = None


def ocr_available():
    global _OCR_READY
    if _OCR_READY is not None:
        return _OCR_READY
    try:
        import pytesseract  # noqa
        from PIL import Image  # noqa
        pytesseract.get_tesseract_version()
        _OCR_READY = True
    except Exception:
        _OCR_READY = False
    return _OCR_READY


def ocr_page_words(page, zoom=3.0):
    """
    OCR fallback: returns lines like page_lines() but from Tesseract, with
    bounding boxes converted back to PDF points. Used only when a page has no
    text layer.
    """
    import pytesseract
    from PIL import Image
    import io

    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    # Group words into lines by (block, par, line) keys.
    groups = {}
    n = len(data["text"])
    for i in range(n):
        txt = data["text"][i].strip()
        if not txt:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        g = groups.setdefault(key, {"words": [], "x0": 1e9, "y0": 1e9, "x1": 0, "y1": 0})
        g["words"].append(txt)
        x, y, w, h = (data[k][i] for k in ("left", "top", "width", "height"))
        g["x0"] = min(g["x0"], x)
        g["y0"] = min(g["y0"], y)
        g["x1"] = max(g["x1"], x + w)
        g["y1"] = max(g["y1"], y + h)

    lines = []
    for g in groups.values():
        lines.append(
            {
                "text": " ".join(g["words"]),
                "x0": g["x0"] / zoom,
                "y0": g["y0"] / zoom,
                "x1": g["x1"] / zoom,
                "y1": g["y1"] / zoom,
            }
        )
    return lines


# --------------------------------------------------------------------------- #
# Core analysis
# --------------------------------------------------------------------------- #

class Notice:
    """Collects abnormal-condition messages to print to the terminal."""

    def __init__(self, name):
        self.name = name
        self.items = []

    def add(self, msg):
        self.items.append(msg)

    def flush(self):
        if not self.items:
            return
        print(f"\n  !! ABNORMAL ({self.name}):")
        for m in self.items:
            print(f"     - {m}")


def analyze(doc, target_question, notice, use_ocr):
    """
    Locate, for every occurrence of the target question, its crop plan:
    a header crop + one or more question-band crops.

    Returns list of "plans": each plan is a list of (page_index, y0, y1) crops
    in output order (header first, then the question band pages).
    """
    n_pages = len(doc)
    full_text = [doc[i].get_text("text") for i in range(n_pages)]

    # --- Segment into reports via cover/letter pages -----------------------
    cover_pages = [
        i for i in range(n_pages)
        if any(sig in full_text[i] for sig in COVER_SIGNALS)
    ]
    if not cover_pages or cover_pages[0] != 0:
        cover_pages = [0] + [c for c in cover_pages if c != 0]

    def report_end(p):
        later = [c for c in cover_pages if c > p]
        return later[0] if later else n_pages

    def report_start(p):
        earlier = [c for c in cover_pages if c <= p]
        return earlier[-1] if earlier else 0

    def report_label(rstart):
        """A short, human-readable name for a report, e.g. its course-code line."""
        pat = re.compile(r"([^\n]*\(W[0-9][\w./-]*\))")
        for j in range(rstart, report_end(rstart)):
            m = pat.search(full_text[j])
            if m:
                return m.group(1).strip()
        return f"report@index{rstart}"

    # --- Collect every comment-question header, doc-wide -------------------
    headers = []
    for i in range(n_pages):
        page = doc[i]
        hs = collect_question_headers(page, i)
        if not hs and use_ocr and len(full_text[i].strip()) < 20 and ocr_available():
            # No text layer on this page -> OCR fallback for locating.
            notice.add(f"page index {i} had no text layer; used OCR to locate text")
            # (OCR line detection for markers is best-effort; typically not needed.)
        headers.extend(hs)
    headers.sort(key=lambda h: (h["page"], h["marker_y0"]))

    # --- Flag odd response rates (printed metadata) ------------------------
    for i in cover_pages:
        # look a few pages ahead for the metadata line
        for j in range(i, min(i + 4, n_pages)):
            m = re.search(r"Response rate\s*=\s*([\d.]+)%", full_text[j])
            if m:
                try:
                    rate = float(m.group(1))
                    if rate > 100.0:
                        notice.add(
                            f"response rate {rate}% exceeds 100% "
                            f"(report starting at page index {i})"
                        )
                except ValueError:
                    pass
                break

    # --- Find target-question occurrences ----------------------------------
    tgt = normalize(target_question)
    matches = [h for h in headers if tgt in normalize(h["question_text"])]

    # --- Multi-report bundle: report which headers are kept vs omitted -----
    reports_with_target = {report_start(m["page"]) for m in matches}
    if len(cover_pages) > 1:
        notice.add(
            f"{len(cover_pages)} separate reports are concatenated in one PDF "
            f"(cover pages at 0-based indices {cover_pages}). A single course "
            f"evaluation normally contains one report."
        )
        kept = [f'"{report_label(c)}" (index {c})'
                for c in cover_pages if c in reports_with_target]
        omitted = [f'"{report_label(c)}" (index {c})'
                   for c in cover_pages if c not in reports_with_target]
        if kept:
            notice.add("kept header + target question from: " + "; ".join(kept))
        if omitted:
            notice.add(
                f"omitted the header(s) of {len(omitted)} report(s) that do NOT "
                f"contain the target question: " + "; ".join(omitted)
            )

    if not matches:
        notice.add(
            f'target question not found: "{target_question}". '
            f"No question band produced."
        )
        return []

    if len(matches) > 1:
        notice.add(
            f"target question found {len(matches)} times "
            f"(pages {[m['page'] for m in matches]}); a band is produced for each."
        )

    plans = []
    for m in matches:
        tp, ty = m["page"], m["marker_y0"]
        rstart, rend = report_start(tp), report_end(tp)

        # ---- Header band: the report's metadata box (page 2) --------------
        # The metadata box sits at the top of the "Survey Results" page. We keep
        # WHATEVER is in that box -- we do NOT require any particular field
        # (enrollment / responses / response rate) to be present. A partial
        # header (e.g. only "No. of responses = 9") is kept intact.
        header_page = None
        survey_y = None
        # Primary anchor: the "Survey Results" banner marks the metadata page.
        for j in range(rstart, rend):
            sy = find_survey_results_y(doc[j])
            if sy is not None:
                header_page, survey_y = j, sy
                break
        # Fallback: no banner -> first page carrying a course-code line or any
        # single metadata field.
        if header_page is None:
            for j in range(rstart, rend):
                if COURSE_CODE_RE.search(full_text[j]) or any(
                    s in full_text[j] for s in HEADER_SIGNALS
                ):
                    header_page = j
                    break

        crops = []
        if header_page is None:
            notice.add(
                f"header/metadata page not found for report starting at index "
                f"{rstart}; header band omitted."
            )
        else:
            if survey_y is not None:
                hb_bottom = survey_y - PAD_ABOVE_SURVEY
            else:
                hb_bottom = header_bottom_fallback(doc[header_page])
            crops.append((header_page, HEADER_TOP, hb_bottom))

        # ---- Question band boundary: next header within this report -------
        later = [
            h for h in headers
            if h["page"] < rend
            and (h["page"] > tp or (h["page"] == tp and h["marker_y0"] > ty + 1))
        ]
        start_y = ty - PAD_ABOVE_QUESTION

        if later:
            b = later[0]
            bp, by = b["page"], b["marker_y0"]
            if bp == tp:
                crops.append((tp, start_y, by - PAD_BEFORE_BOUNDARY))
            else:
                crops.append((tp, start_y, BODY_BOTTOM))
                for mid in range(tp + 1, bp):
                    crops.append((mid, BODY_TOP, BODY_BOTTOM))
                crops.append((bp, BODY_TOP, by - PAD_BEFORE_BOUNDARY))
        else:
            # Target is the last question of its report -> run to report end.
            crops.append((tp, start_y, BODY_BOTTOM))
            for mid in range(tp + 1, rend):
                crops.append((mid, BODY_TOP, BODY_BOTTOM))

        plans.append(crops)

    return plans


# --------------------------------------------------------------------------- #
# Output assembly
# --------------------------------------------------------------------------- #

# Output page layout (points). Content flows onto uniform, full-size pages.
OUT_MARGIN_TOP = 30.0
OUT_MARGIN_BOTTOM = 30.0
OUT_GAP = 14.0  # vertical space between stacked crop blocks on a page


def build_output(doc, plans, out_path, dpi, vector):
    """
    Assemble kept crops onto UNIFORM, full-size pages (same page size as the
    source, typically US Letter). Crops are stacked top-to-bottom and flow onto
    a new page when the current one is full -- so the result reads like a normal
    document: header + question + first answers on page 1, remaining answers on
    following full pages.
    """
    out = fitz.open()
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    page_w = doc[0].rect.width
    page_h = doc[0].rect.height
    usable_h = page_h - OUT_MARGIN_TOP - OUT_MARGIN_BOTTOM

    # Flatten every crop from every plan into an ordered list of blocks.
    blocks = []  # (src_page_index, y0, y1, height_pt)
    for crops in plans:
        for (pi, y0, y1) in crops:
            src = doc[pi]
            y0 = max(0.0, y0)
            y1 = min(src.rect.height, y1)
            if y1 - y0 < 2:
                continue
            blocks.append((pi, y0, y1, y1 - y0))

    page = None
    cursor = 0.0

    def start_page():
        return out.new_page(width=page_w, height=page_h), OUT_MARGIN_TOP

    for (pi, y0, y1, h) in blocks:
        # Cap a single block to the usable height (safety; normal crops fit).
        draw_h = min(h, usable_h)

        if page is None or (cursor + draw_h) > (page_h - OUT_MARGIN_BOTTOM) + 0.5:
            page, cursor = start_page()

        dest = fitz.Rect(0, cursor, page_w, cursor + draw_h)
        clip = fitz.Rect(0, y0, page_w, y1)

        if vector:
            # Text-selectable, smaller -- but clipped-away content stays
            # embedded (hidden) in the file.
            page.show_pdf_page(dest, doc, pi, clip=clip)
        else:
            # Rasterize ONLY the clip region: dropped content is truly gone.
            pix = doc[pi].get_pixmap(matrix=mat, clip=clip, alpha=False)
            page.insert_image(dest, pixmap=pix)

        cursor += draw_h + OUT_GAP

    if out.page_count == 0:
        out.close()
        return False

    out.save(str(out_path), garbage=4, deflate=True)
    out.close()
    return True


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def process_pdf(pdf_path, out_dir, target_question, dpi, use_ocr, vector):
    print(f"\n=== {pdf_path.name} ===")
    notice = Notice(pdf_path.name)
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        print(f"  ERROR: cannot open ({e})")
        return

    plans = analyze(doc, target_question, notice, use_ocr)

    if not plans:
        notice.flush()
        print("  -> nothing produced (target question not present).")
        doc.close()
        return

    # Human-readable summary of what will be kept.
    for k, crops in enumerate(plans, 1):
        pages = sorted({pi for (pi, _, _) in crops})
        tag = f" (occurrence {k})" if len(plans) > 1 else ""
        print(f"  keep{tag}: header + question band across page indices {pages}")

    out_name = f"{pdf_path.stem}_filtered.pdf"
    out_path = out_dir / out_name
    ok = build_output(doc, plans, out_path, dpi, vector)
    doc.close()

    notice.flush()
    if ok:
        size_kb = out_path.stat().st_size / 1024
        print(f"  -> wrote {out_path}  ({size_kb:.0f} KB, {'vector' if vector else str(dpi)+' DPI raster'})")
    else:
        print("  -> nothing written.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="A PDF file, or a folder of PDFs.")
    ap.add_argument("-o", "--outdir", default="FilteredData",
                    help="Output directory (default: ./FilteredData).")
    ap.add_argument("-q", "--question", default=DEFAULT_QUESTION, help="Target question text to keep.")
    ap.add_argument("--dpi", type=int, default=250, help="Rasterization DPI (default 250).")
    ap.add_argument("--ocr", action="store_true", help="Enable Tesseract OCR fallback for pages with no text layer.")
    ap.add_argument("--vector", action="store_true", help="Vector output (selectable text, smaller) -- WARNING: retains hidden clipped content.")
    args = ap.parse_args()

    in_path = Path(args.input).expanduser()
    out_dir = Path(args.outdir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.ocr and not ocr_available():
        print("NOTE: --ocr requested but Tesseract/pytesseract is not available; "
              "continuing with text-layer only.")

    if in_path.is_dir():
        pdfs = sorted(p for p in in_path.iterdir() if p.suffix.lower() == ".pdf")
        if not pdfs:
            sys.exit(f"No PDFs found in {in_path}")
    elif in_path.is_file() and in_path.suffix.lower() == ".pdf":
        pdfs = [in_path]
    else:
        sys.exit(f"Not a PDF or folder: {in_path}")

    if args.vector:
        print("WARNING: --vector keeps dropped content hidden-but-embedded in the output. "
              "Use the default raster mode for a guaranteed clean drop.")

    for pdf in pdfs:
        process_pdf(pdf, out_dir, args.question, args.dpi, args.ocr, args.vector)

    print("\nDone.")


if __name__ == "__main__":
    main()
