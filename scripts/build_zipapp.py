"""Build dist/en.pyz: the whole tool as one file that runs anywhere Python 3.10+ is installed (no pip, no editor).

Usage: python3 scripts/build_zipapp.py   then   python3 dist/en.pyz run program.en
"""
import shutil
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> Path:
    destination = ROOT / "dist" / "en.pyz"
    destination.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        staging = Path(directory)
        shutil.copytree(ROOT / "codeinenglish", staging / "codeinenglish", ignore=shutil.ignore_patterns("__pycache__"))
        (staging / "__main__.py").write_text("import sys\nfrom codeinenglish.__main__ import main\nsys.exit(main())\n")
        zipapp.create_archive(staging, destination, interpreter="/usr/bin/env python3", compressed=True)
    return destination


if __name__ == "__main__":
    print(main())
