"""Package OfficeKit into a zip ready to upload to Gumroad / Lemon Squeezy."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
INCLUDE = ["README.md", "LICENSE-BUYER.txt", "pyproject.toml", "src", "tests"]


def build() -> Path:
    version = next(line.split('"')[1] for line in (ROOT / "pyproject.toml").read_text().splitlines()
                   if line.startswith("version"))
    out = ROOT / "dist" / f"officekit-{version}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE:
            path = ROOT / item
            files = [path] if path.is_file() else sorted(path.rglob("*"))
            for f in files:
                if f.is_file() and "__pycache__" not in f.parts and ".egg-info" not in str(f):
                    z.write(f, Path("officekit") / f.relative_to(ROOT))
    return out


if __name__ == "__main__":
    print(f"Built {build()}")
