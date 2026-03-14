from pathlib import Path
import re

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader
from loguru import logger

from app.services.storage import resolve_to_local_path

def _extract_docx_text(path: str) -> str:
    doc = DocxDocument(path)
    lines: list[str] = []
    for p in doc.paragraphs:
        style_name = (p.style.name or "").lower()
        if "heading" in style_name:
            level_match = re.search(r"heading\s*(\d+)", style_name)
            level = int(level_match.group(1)) if level_match else 1
            prefix = "#" * max(1, min(level, 6))
            lines.append(f"{prefix} {p.text.strip()}")
        else:
            if p.text.strip():
                lines.append(p.text.strip())
    return "\n".join(lines)


def _extract_html_text(path: str) -> str:
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8"), "html.parser")
    lines: list[str] = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
        text = element.get_text(strip=True)
        if not text:
            continue
        if element.name and element.name.startswith("h"):
            level = int(element.name[1]) if element.name[1].isdigit() else 1
            prefix = "#" * max(1, min(level, 6))
            lines.append(f"{prefix} {text}")
        else:
            lines.append(text)
    return "\n".join(lines)


def extract_text(path: str) -> str:
    local_path = resolve_to_local_path(path)
    file_path = Path(local_path)
    suffix = file_path.suffix.lower()
    logger.info(f"extracting text | path={path} suffix={suffix}")
    if suffix == ".pdf":
        reader = PdfReader(local_path)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    if suffix == ".docx":
        return _extract_docx_text(local_path)
    if suffix in {".html", ".htm"}:
        return _extract_html_text(local_path)
    return file_path.read_text(encoding="utf-8")
