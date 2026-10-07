"""Package OfficeKit for sale, plus a free Lite edition to publish on GitHub.

    python build_product.py          # paid zip -> dist/officekit-<version>.zip
    python build_product.py --lite   # free edition -> dist/officekit-lite/ (push this to a public repo)
"""
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
INCLUDE = ["README.md", "LICENSE-BUYER.txt", "pyproject.toml", "src", "tests"]
LITE_MODULES = ["pdf_tools", "bulk_rename"]
STORE_URL = "https://YOUR-STORE.gumroad.com/l/officekit"


def version() -> str:
    return next(line.split('"')[1] for line in (ROOT / "pyproject.toml").read_text().splitlines()
                if line.startswith("version"))


def build() -> Path:
    out = ROOT / "dist" / f"officekit-{version()}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE:
            path = ROOT / item
            files = [path] if path.is_file() else sorted(path.rglob("*"))
            for f in files:
                if f.is_file() and "__pycache__" not in f.parts and ".egg-info" not in str(f):
                    z.write(f, Path("officekit") / f.relative_to(ROOT))
    return out


def build_lite() -> Path:
    out = ROOT / "dist" / "officekit-lite"
    shutil.rmtree(out, ignore_errors=True)
    pkg = out / "src" / "officekit"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    for mod in LITE_MODULES:
        shutil.copy(ROOT / "src" / "officekit" / f"{mod}.py", pkg)
    (pkg / "__main__.py").write_text(f'''import argparse
import sys

from . import {", ".join(LITE_MODULES)}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="officekit", description="OfficeKit Lite. Full version: {STORE_URL}")
    sub = parser.add_subparsers(dest="command", required=True)
    for mod in ({", ".join(LITE_MODULES)},):
        mod.add_parser(sub)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (ValueError, FileNotFoundError, PermissionError) as e:
        sys.exit(f"Error: {{e}}")


if __name__ == "__main__":
    main()
''')
    pyproject = (ROOT / "pyproject.toml").read_text()
    pyproject = pyproject.replace('name = "officekit"', 'name = "officekit-lite"')
    pyproject = pyproject.replace(
        'dependencies = ["openpyxl>=3.1", "pypdf>=4.0", "requests>=2.31", "beautifulsoup4>=4.12"]',
        'dependencies = ["pypdf>=4.0"]')
    (out / "pyproject.toml").write_text(pyproject)
    (out / "LICENSE").write_text(MIT)
    (out / "README.md").write_text(LITE_README.format(url=STORE_URL))
    return out


MIT = """MIT License

Copyright (c) 2026 OfficeKit

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
"""

LITE_README = """# OfficeKit Lite

Free command-line tools for merging, splitting and extracting text from PDFs, and bulk-renaming files.

```bash
pip install .
officekit pdf-merge a.pdf b.pdf -o combined.pdf
officekit pdf-split report.pdf -r "1-3,10-" -o parts/
officekit rename scans/*.jpg -t "{{date}}_receipt_{{n:02}}{{ext}}"          # preview
officekit rename scans/*.jpg -t "{{date}}_receipt_{{n:02}}{{ext}}" --apply  # do it
```

## Want more?

**[OfficeKit Full]({url})** adds:
- `excel-merge`: combine dozens of Excel/CSV files into one workbook in seconds
- `clean-csv`: de-duplicate and tidy contact lists
- `scrape`: save any web page table as CSV
- Commercial license and free updates

⭐ Star this repo if it saved you time!
"""


if __name__ == "__main__":
    print(f"Built {build_lite() if '--lite' in sys.argv else build()}")
