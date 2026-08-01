# EvalReader — Stanford Law Course Evaluation Extractor

Stanford Law School collects handwritten student course evaluations at the end of each term. Reading and analyzing hundreds of handwritten comments across dozens of courses is time-consuming and difficult to do at scale.

EvalReader solves this by automatically transcribing handwritten comments from evaluation PDFs using GPT-4.1 Vision, making them searchable, filterable, and downloadable as a spreadsheet.

## How it works

1. Upload course evaluation PDFs or a ZIP archive containing multiple PDFs
2. GPT-4.1 Vision reads and transcribes every handwritten student comment
3. Results are deduplicated, flagged for review if unclear, and organized by course
4. Browse, filter, and search comments — download as CSV

## Features

- **Batch processing** — handles hundreds of PDFs at once via ZIP upload
- **AI handwriting recognition** — GPT-4.1 Vision accurately transcribes handwritten text
- **Course ID detection** — automatically extracts course codes (e.g. `F25-LAW-7152-01`)
- **Smart deduplication** — flags duplicate comments across files
- **Review flagging** — marks uncertain transcriptions for human review
- **Results browser** — filter by course, review status, and duplicates
- **CSV export** — download all results as a clean spreadsheet

## Tech stack

- **Python** · **Streamlit** · **PyMuPDF** · **OpenAI GPT-4.1 Vision**

## Setup

```bash
git clone https://github.com/namigabbasov/streamlit-eval-app.git
cd streamlit-eval-app
pip install -r requirements.txt
streamlit run app.py
```

You will need an [OpenAI API key](https://platform.openai.com/api-keys) to run the extraction.

## Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Select this repo, set main file to `app.py`
3. Under **Advanced settings → Secrets** add:
```toml
OPENAI_API_KEY = "sk-proj-your-key-here"
```
4. Click **Deploy**
