# FILE: rag/loaders.py
"""Multi-format document loaders -> list of {text, metadata} dicts."""
import os
import csv
import json
from pypdf import PdfReader
from docx import Document as DocxDocument
from bs4 import BeautifulSoup


def load_pdf(path: str) -> list[dict]:
    reader = PdfReader(path)
    out = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            out.append({"text": text, "metadata": {"source": os.path.basename(path), "page": i + 1}})
    return out


def load_docx(path: str) -> list[dict]:
    doc = DocxDocument(path)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"text": full_text, "metadata": {"source": os.path.basename(path)}}]


def load_html(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    text = soup.get_text(separator="\n")
    return [{"text": text, "metadata": {"source": os.path.basename(path)}}]


def load_txt(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [{"text": f.read(), "metadata": {"source": os.path.basename(path)}}]


def load_csv(path: str) -> list[dict]:
    out = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            out.append({"text": json.dumps(row), "metadata": {"source": os.path.basename(path), "row": i}})
    return out


LOADER_MAP = {
    ".pdf": load_pdf,
    ".docx": load_docx,
    ".html": load_html,
    ".htm": load_html,
    ".txt": load_txt,
    ".csv": load_csv,
}


def load_document(path: str) -> list[dict]:
    ext = os.path.splitext(path)[1].lower()
    if ext not in LOADER_MAP:
        raise ValueError(f"Unsupported file type: {ext}")
    return LOADER_MAP[ext](path)