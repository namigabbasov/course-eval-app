# Course Evaluation Pipeline

This repository contains three small apps that together make up one workflow for
digitizing handwritten comments from scanned course evaluation reports. Each app
is independent, deployed separately, and requires a person to review its output
before moving to the next step. Nothing runs automatically end to end by design,
since keeping a human in the loop at every handoff is the whole point of this
setup.

## What the three apps do

### 1. PDF Prep (folder: pdf_prep)

This app takes scanned course evaluation PDFs and trims each one down to only
the parts that matter: the printed header block (which identifies the course)
and the handwritten answers to one specific target question. Everything else on
the page is discarded.

A person uploads the raw scanned PDFs, clicks Run Filter, and reviews the
results table before downloading. The table shows, for each file, whether
processing succeeded, the resulting file size, and any diagnostic notices worth
checking. Once satisfied, the person downloads all the filtered PDFs together
as a single zip file.

### 2. EvalReader (folder: eval_reader)

This app takes that zip of filtered PDFs and uses an LLM (GPT 4.1 with vision)
to transcribe every handwritten comment on each page. Since these pages are
scanned images with no selectable text, the model reads the handwriting
directly from an image of each page.

A person uploads the zip, clicks Run Extraction, and reviews the resulting
table of extracted comments. Each row includes the course identifier, the
transcribed comment, whether the model flagged that transcription as uncertain
and needing review, whether it looks like a duplicate of another row, and which
source file and page it came from. Once the reviewer is satisfied, they
download the full result as a CSV file, which is the final deliverable of the
pipeline.

### 3. Landing Page (folder: landing)

This app has no processing logic at all. It exists purely to explain the
workflow to a person using it: it shows the two steps above as cards, links out
to each app's live deployment, and lays out the handoff instructions in plain
language so nobody has to remember the process from memory or from a previous
conversation.

## How the three apps connect

The connection between PDF Prep and EvalReader is a single file: the zip that
PDF Prep produces and that a person downloads and then manually uploads into
EvalReader. There is no shared database, no shared server, and no automatic
handoff between the two apps. The person doing the review is the connection.
This is intentional, since it means a human always looks at the filtered PDFs
before they are ever sent to an LLM for transcription, and again looks at the
transcribed comments before they are treated as final data.

The full process, in order, looks like this.

1. Open PDF Prep and upload the scanned evaluation reports, either as
   individual PDF files or as a zip archive containing them.
2. Click Run Filter. The app processes each file and shows a results table.
3. Review that table. Check file sizes and any processing notices. If a file
   shows no output or looks wrong, that is the moment to catch it, before it
   goes any further.
4. Click Download All as Zip. This produces one zip file containing all the
   filtered PDFs.
5. Open EvalReader and upload that same zip file directly, without unzipping
   or repacking it.
6. Click Run Extraction. The app processes each filtered PDF page by page
   using GPT 4.1 vision and builds a table of extracted comments.
7. Review the Results tab. Pay particular attention to rows flagged as needing
   review and rows flagged as possible duplicates. These flags exist so a
   person, not the model, makes the final call on anything uncertain.
8. Click Download CSV. This is the final output of the entire pipeline: one
   CSV file with course identifiers, transcribed comments, and diagnostic
   columns, ready for whatever analysis comes next.

The Landing Page is simply the starting point for this whole sequence. Someone
new to the workflow can open it first, read the two step cards and the numbered
instructions above, and follow the links out to each app in turn.

## Repository layout

```
course_eval_pipeline/
  pdf_prep/
    app.py
    filter_course_evals.py
    requirements.txt
  eval_reader/
    app.py
    requirements.txt
  landing/
    app.py
    requirements.txt
  README.md
```

Each subfolder is deployed as its own separate app on Streamlit Community
Cloud. All three point at this same repository, but each deployment specifies
a different main file path (for example pdf_prep/app.py), so each app only
installs the dependencies listed in its own requirements.txt and only runs its
own code. Secrets such as the shared password for PDF Prep, and the OpenAI and
Supabase credentials for EvalReader, are configured separately per deployment
and are not shared across apps.

## Why these stay separate apps instead of one combined app

Combining PDF Prep and EvalReader into a single app would remove the natural
pause between filtering and extraction, and it would be easy for a person to
click through both steps without ever really looking at the intermediate
output. Keeping them as two apps, joined only by a file that a person carries
from one to the other, means the review step cannot be skipped by accident.
The Landing Page exists to make that two step process easy to follow without
making it automatic.
