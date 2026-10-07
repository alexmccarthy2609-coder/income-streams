"""Clean a contact/lead list: trim whitespace, normalise emails and phones, drop duplicates."""
import csv
import re
from pathlib import Path

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalise_phone(value: str) -> str:
    digits = re.sub(r"[^\d+]", "", value)
    return digits if len(re.sub(r"\D", "", digits)) >= 7 else value.strip()


def clean(input_path: Path, output: Path, key: str | None = None) -> dict:
    with input_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = [h.strip() for h in reader.fieldnames or []]
        rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in reader]

    email_cols = [c for c in fields if "email" in c.lower()]
    phone_cols = [c for c in fields if any(w in c.lower() for w in ("phone", "mobile", "tel"))]
    if key is None:
        key = email_cols[0] if email_cols else None

    stats = {"input": len(rows), "empty": 0, "duplicates": 0, "invalid_email": 0}
    seen, out = set(), []
    for r in rows:
        if not any(r.values()):
            stats["empty"] += 1
            continue
        for c in email_cols:
            r[c] = r[c].lower()
            if r[c] and not EMAIL_RE.match(r[c]):
                stats["invalid_email"] += 1
        for c in phone_cols:
            if r[c]:
                r[c] = normalise_phone(r[c])
        ident = r.get(key, "").lower() if key else tuple(r.values())
        if ident and ident in seen:
            stats["duplicates"] += 1
            continue
        seen.add(ident)
        out.append(r)

    with output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    stats["output"] = len(out)
    return stats


def add_parser(sub):
    p = sub.add_parser("clean-csv", help="Trim, normalise and de-duplicate a CSV contact list")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("cleaned.csv"))
    p.add_argument("-k", "--key", help="Column to de-duplicate on (default: first email column)")

    def _run(a):
        s = clean(a.input, a.output, a.key)
        print(f"{s['input']} rows in -> {s['output']} rows out "
              f"({s['duplicates']} duplicates, {s['empty']} empty removed; "
              f"{s['invalid_email']} invalid emails flagged). Saved to {a.output}")
    p.set_defaults(func=_run)
