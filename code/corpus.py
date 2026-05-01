import re
from pathlib import Path

from schemas import Chunk


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _source_from_path(path: Path) -> str:
    try:
        return path.relative_to(DATA_DIR).parts[0].lower()
    except (IndexError, ValueError):
        return "unknown"


def _parse_markdown(text: str) -> tuple[str, str]:
    title = ""
    body = text or ""

    if body.startswith("---"):
        end = body.find("---", 3)
        if end != -1:
            frontmatter = body[3:end]
            for line in frontmatter.splitlines():
                if line.lower().startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip("\"'")
                    break
            body = body[end + 3 :].strip()

    if not title:
        match = re.search(r"^#\s+(.+)", body, re.MULTILINE)
        title = match.group(1).strip() if match else "unknown"

    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    cleaned = re.sub(r"^#+\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return title, cleaned


def load_corpus(data_dir: Path | None = None) -> list[Chunk]:
    root = data_dir or DATA_DIR
    chunks: list[Chunk] = []
    for md_file in sorted(root.rglob("*.md")):
        source = _source_from_path(md_file) if root == DATA_DIR else md_file.parts[-2].lower()
        raw = md_file.read_text(encoding="utf-8", errors="ignore")
        title, text = _parse_markdown(raw)
        if text:
            chunks.append(Chunk(source=source, file=str(md_file), title=title, text=text))
    return chunks
