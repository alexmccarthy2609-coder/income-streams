"""Rename many files with a template. Dry-run by default so nothing changes by accident.

Template fields: {n} counter, {name} original stem, {ext} extension (with dot),
{date} file modified date (YYYY-MM-DD). Counter supports padding, e.g. {n:03}.
"""
import re
from datetime import datetime
from pathlib import Path


def plan(files: list[Path], template: str, start: int = 1,
         find: str | None = None, replace: str = "") -> list[tuple[Path, Path]]:
    pairs = []
    for i, f in enumerate(sorted(files), start=start):
        stem = re.sub(find, replace, f.stem) if find else f.stem
        date = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
        new_name = template.format(n=i, name=stem, ext=f.suffix, date=date)
        pairs.append((f, f.with_name(new_name)))
    targets = [new for _, new in pairs]
    if len(set(targets)) != len(targets):
        raise ValueError("Template produces duplicate names; include {n} or {name}")
    sources = {old for old, _ in pairs}
    for _, new in pairs:
        if new.exists() and new not in sources:
            raise ValueError(f"Would overwrite existing file: {new}")
    return pairs


def apply(pairs: list[tuple[Path, Path]]) -> None:
    # Two-phase rename so swaps like a->b, b->a don't collide.
    temps = []
    for i, (old, new) in enumerate(pairs):
        tmp = old.with_name(f".officekit_tmp_{i}{old.suffix}")
        old.rename(tmp)
        temps.append((tmp, new))
    for tmp, new in temps:
        tmp.rename(new)


def add_parser(sub):
    p = sub.add_parser("rename", help="Bulk-rename files using a template (dry-run unless --apply)")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("-t", "--template", default="{name}{ext}",
                   help="e.g. 'invoice_{n:03}{ext}' or '{date}_{name}{ext}'")
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--find", help="Regex to replace in the original name")
    p.add_argument("--replace", default="")
    p.add_argument("--apply", action="store_true", help="Actually rename (default is preview)")

    def _run(a):
        pairs = plan([f for f in a.files if f.is_file()], a.template, a.start, a.find, a.replace)
        for old, new in pairs:
            print(f"{old.name}  ->  {new.name}")
        if a.apply:
            apply(pairs)
            print(f"Renamed {len(pairs)} files.")
        else:
            print(f"\nDry run: {len(pairs)} files. Re-run with --apply to rename.")
    p.set_defaults(func=_run)
