from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree


class _TextOnlyHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def _tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower().replace("_", "-")


def _child_text(element: ElementTree.Element, name: str) -> str:
    for child in element.iter():
        if _tag_name(child.tag) == name:
            value = " ".join("".join(child.itertext()).split())
            if value:
                return value
    return ""


def _clean_html(value: str) -> str:
    parser = _TextOnlyHTML()
    parser.feed(value)
    return " ".join(parser.parts)


def build_snapshot(source: Path, destination: Path, snapshot_date: str) -> int:
    try:
        parsed_date = date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise ValueError("Snapshot date must use YYYY-MM-DD format.") from exc
    if parsed_date.isoformat() != snapshot_date:
        raise ValueError("Snapshot date must use YYYY-MM-DD format.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(dir=destination.parent, prefix=f".{destination.name}.")
    count = 0
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            for _, element in ElementTree.iterparse(source, events=("end",)):
                if _tag_name(element.tag) != "health-topic":
                    continue
                language = element.attrib.get("language") or _child_text(element, "language")
                if language and language.casefold() not in {"english", "en"}:
                    element.clear()
                    continue

                document_id = element.attrib.get("id") or _child_text(element, "id")
                title = element.attrib.get("title") or _child_text(element, "title")
                url = element.attrib.get("url") or _child_text(element, "url")
                summary = _child_text(element, "full-summary") or _child_text(element, "summary")
                if not document_id or not title or not url or not summary:
                    element.clear()
                    continue

                synonyms = [
                    " ".join("".join(child.itertext()).split())
                    for child in element.iter()
                    if _tag_name(child.tag) in {"also-called", "descriptor"}
                    and " ".join("".join(child.itertext()).split())
                ]
                text = " ".join(dict.fromkeys([title, *synonyms, _clean_html(summary)]))
                record = {
                    "document_id": document_id,
                    "title": title,
                    "text": text,
                    "url": url,
                    "snapshot_date": snapshot_date,
                }
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                element.clear()

        if count == 0:
            raise ValueError("No English MedlinePlus health-topic records were found in the XML input.")
        os.replace(temporary_name, destination)
        return count
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an official local MedlinePlus Health Topic XML file into an indexed JSONL snapshot."
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to the downloaded MedlinePlus XML file.")
    parser.add_argument("--output", required=True, type=Path, help="Path for the local JSON Lines snapshot.")
    parser.add_argument("--snapshot-date", required=True, help="Date associated with the downloaded snapshot (YYYY-MM-DD).")
    args = parser.parse_args()

    count = build_snapshot(args.input, args.output, args.snapshot_date)
    print(f"Wrote {count} English MedlinePlus documents to {args.output}")


if __name__ == "__main__":
    main()
