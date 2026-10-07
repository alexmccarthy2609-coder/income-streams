"""Merge, split and extract text from PDFs."""
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def merge(inputs: list[Path], output: Path) -> int:
    writer = PdfWriter()
    for path in inputs:
        for page in PdfReader(path).pages:
            writer.add_page(page)
    with output.open("wb") as f:
        writer.write(f)
    return len(writer.pages)


def parse_ranges(spec: str, total: int) -> list[list[int]]:
    """'1-3,5,7-' -> [[0,1,2],[4],[6..total-1]] (zero-based page indexes)."""
    groups = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a) if a else 1
            end = int(b) if b else total
        else:
            start = end = int(part)
        if not 1 <= start <= end <= total:
            raise ValueError(f"Invalid page range '{part}' for a {total}-page PDF")
        groups.append(list(range(start - 1, end)))
    return groups


def split(input_path: Path, out_dir: Path, ranges: str | None = None) -> list[Path]:
    """Split into one file per range, or one file per page if no ranges given."""
    reader = PdfReader(input_path)
    total = len(reader.pages)
    groups = parse_ranges(ranges, total) if ranges else [[i] for i in range(total)]
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for g in groups:
        writer = PdfWriter()
        for i in g:
            writer.add_page(reader.pages[i])
        label = f"{g[0] + 1}" if len(g) == 1 else f"{g[0] + 1}-{g[-1] + 1}"
        out = out_dir / f"{input_path.stem}_p{label}.pdf"
        with out.open("wb") as f:
            writer.write(f)
        outputs.append(out)
    return outputs


def extract_text(input_path: Path) -> str:
    return "\n\n".join(page.extract_text() or "" for page in PdfReader(input_path).pages)


def add_parser(sub):
    p = sub.add_parser("pdf-merge", help="Merge PDFs in the given order")
    p.add_argument("inputs", nargs="+", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("merged.pdf"))
    p.set_defaults(func=lambda a: print(f"Wrote {merge(a.inputs, a.output)} pages to {a.output}"))

    p = sub.add_parser("pdf-split", help="Split a PDF per page or by ranges like '1-3,5,7-'")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--out-dir", type=Path, default=Path("split"))
    p.add_argument("-r", "--ranges")
    p.set_defaults(func=lambda a: print(
        f"Wrote {len(split(a.input, a.out_dir, a.ranges))} files to {a.out_dir}/"))

    p = sub.add_parser("pdf-text", help="Extract text from a PDF")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, help="Write to file instead of stdout")

    def _text(a):
        text = extract_text(a.input)
        if a.output:
            a.output.write_text(text, encoding="utf-8")
            print(f"Wrote text to {a.output}")
        else:
            print(text)
    p.set_defaults(func=_text)
