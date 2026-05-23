# Intelligent Cloud Document Analyst

### n8n AI Engineering Project — Powered by Google Gemini API

---

## Project Summary

A fully automated cloud document intelligence pipeline built with n8n and the Google Gemini API. It watches a Google Drive folder for incoming files, extracts their content, and routes them through a multi-stage AI pipeline for summarization, classification, sentiment analysis, and entity extraction.

---

## Components

| Component         | Description                                                          |
| ----------------- | -------------------------------------------------------------------- |
| n8n               | Self-hosted via Docker — orchestrates all automation                 |
| Google Gemini API | `gemini-3-flash-preview` — text + vision analysis                    |
| Metadata API      | FastAPI microservice running on port 8000                            |
| Google Sheets     | Cloud results database                                               |
| Google Drive      | Trigger source (`incoming_docs/`) and output target (`output_docs/`) |
| Gmail             | Real-time email notifications                                        |

---

## Prerequisites

- Docker installed
- Python 3.10+
- A Google account with access to Google Drive, Sheets, and Gmail
- A Google Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## Setup Guide

### 1. Start the Python Metadata API

```bash
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Verify it's running:

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### 2. Start n8n with Docker Compose

```yaml
version: '3.8'

services:
  n8n:
    image: docker.n8n.io/n8nio/n8n
    container_name: n8n
    ports:
      - '5678:5678'
    environment:
      - N8N_ALLOW_EXEC=true
    volumes:
      - n8n_data:/home/node/.n8n
    restart: unless-stopped

volumes:
  n8n_data:
    external: true
    name: n8n_data
```

```bash
docker compose up
```

Access n8n at: `http://localhost:5678`

### 3. Configure Gemini API Key in n8n

1. Go to **Credentials → New → HTTP Header Auth**
2. Set **Name:** `x-goog-api-key`, **Value:** your Gemini API key
3. Use this credential in the **Gemini API** HTTP Request node

### 4. Configure Google Credentials in n8n

- **Google Drive:** Credentials → New → Google Drive OAuth2 API
- **Google Sheets:** Credentials → New → Google Sheets OAuth2 API
- **Gmail:** Credentials → New → Gmail OAuth2 API

### 5. Set up Google Drive folders

Create two folders in your Google Drive:

- `incoming_docs/` — drop documents here to trigger the pipeline
- `output_docs/` — processed JSON and Markdown reports are written here

### 6. Set up Google Sheets

Create a spreadsheet named **"Docs analysis report"** with a sheet named **"reports-metadata"** and these column headers in row 1:

```
document_id | filename | file type | processed_at | classification | department | sentiment | confidence_score | routing_tag | summary | sensitivity | action_items
```

### 7. Import the n8n Workflow

1. Open n8n → **Workflows → Import from file** → select `n8n-intelligent-doc-analyst.json`
2. Update the Google Drive folder IDs in the trigger and upload nodes to match your own folders
3. Update the Google Sheets document URL to your spreadsheet
4. Update the Gmail recipient address
5. Activate the workflow
