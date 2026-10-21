"""Minimal, dependency-free PEP 517 backend for this pure-Python package."""

import base64
import csv
import hashlib
import io
import zipfile
from pathlib import Path


NAME = "codeinenglish"
VERSION = "0.1.5"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"
ROOT = Path(__file__).parent


def _metadata() -> bytes:
    return (
        "Metadata-Version: 2.1\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        "Summary: A tiny offline English-like programming language\n"
        "Requires-Python: >=3.10\n\n"
    ).encode()


def _wheel() -> bytes:
    return (
        "Wheel-Version: 1.0\n"
        "Generator: codeinenglish-build-backend\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n\n"
    ).encode()


def _entry_points() -> bytes:
    return b"[console_scripts]\ncodeinenglish = codeinenglish.__main__:main\n"


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    dist_info = Path(metadata_directory) / DIST_INFO
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_bytes(_metadata())
    (dist_info / "WHEEL").write_bytes(_wheel())
    (dist_info / "entry_points.txt").write_bytes(_entry_points())
    return DIST_INFO


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    wheel_name = f"{NAME}-{VERSION}-py3-none-any.whl"
    wheel_path = Path(wheel_directory) / wheel_name
    wheel_path.parent.mkdir(parents=True, exist_ok=True)

    files = {
        path.relative_to(ROOT).as_posix(): path.read_bytes()
        for path in sorted((ROOT / NAME).glob("*.py"))
    }
    if metadata_directory:
        metadata_path = Path(metadata_directory)
        dist_files = {path.name: path.read_bytes() for path in metadata_path.iterdir()}
    else:
        dist_files = {
            "METADATA": _metadata(),
            "WHEEL": _wheel(),
            "entry_points.txt": _entry_points(),
        }

    for filename, content in dist_files.items():
        files[f"{DIST_INFO}/{filename}"] = content

    record_path = f"{DIST_INFO}/RECORD"
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for filename, content in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
        writer.writerow((filename, f"sha256={digest}", str(len(content))))
    writer.writerow((record_path, "", ""))
    files[record_path] = record.getvalue().encode()

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for filename, content in sorted(files.items()):
            wheel.writestr(filename, content)
    return wheel_name
