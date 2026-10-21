"""Build the installable release ZIP, GitHub release notes, and SHA-256 checksum."""

import argparse
import hashlib
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "__init__.py", "emotions.py", "gallery.py", "model_profiles.py", "nodes.py", "routes.py", "triggers.py",
    "web/gallery.js", "web/gallery.css", "web/internal_nodes.js", "web/launcher.js", "web/locale.js", "web/models.js", "web/triggers.js",
    "README.md", "README.ru.md", "CHANGELOG.md", "LICENSE", "pyproject.toml", "install.ps1",
)


def main():
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "(\d+\.\d+\.\d+)"$', metadata, re.MULTILINE).group(1)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / f"v{version}")
    args = parser.parse_args()
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    entry = re.search(rf"^## \[{re.escape(version)}\] - [^\n]+\n(.*?)(?=^## |\Z)", changelog, re.MULTILINE | re.DOTALL)
    if entry is None:
        parser.error(f"CHANGELOG.md has no entry for {version}")
    for name in FILES:
        if not (ROOT / name).is_file():
            parser.error(f"Missing release file: {name}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = args.output_dir / f"comfyui-emotional-gallery-v{version}.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(FILES):
            info = ZipInfo(f"comfyui_emotional_gallery/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (ROOT / name).read_bytes())

    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (args.output_dir / "SHA256SUMS.txt").write_text(f"{checksum}  {archive_path.name}\n", encoding="utf-8")
    notes = f"# ComfyUI Emotional Gallery v{version}\n\n{entry.group(1).strip()}\n"
    (args.output_dir / "RELEASE_NOTES.md").write_text(notes, encoding="utf-8")
    print(f"Archive: {archive_path}")
    print(f"Files: {len(FILES)}")
    print(f"SHA256: {checksum}")


if __name__ == "__main__":
    main()
