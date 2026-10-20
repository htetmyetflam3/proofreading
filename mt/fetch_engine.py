# /// script
# requires-python = ">=3.10"
# dependencies = ["ctranslate2>=4", "sentencepiece>=0.1.99"]
# ///
"""Install offline translation models for the four MT routes.

    zh-en   Argos / OPUS-MT Chinese -> English        83 MB   available offline
    en-zh   Argos / OPUS-MT English -> Chinese        82 MB   (reverse, for testing)
    en-my   not published as a downloadable model     --      needs an API engine
    my-en   not published as a downloadable model     --      needs an API engine
    zh-my   no direct model; would have to pivot      --      needs en-my first

The models are Marian/OPUS checkpoints packaged as `.argosmodel` files. Argos
publishes them on argosopentech.com, which this machine cannot reach; the same
files are mirrored in the GitHub repository `jiangwensm/OPUS-argosmodels`, which
is reachable, and are fetched with a sparse git clone instead of a plain HTTP
download.

Models are large, so they are installed outside the repository, in
`$XDG_DATA_HOME/argos-translate/packages`, which is not committed. Re-run this
script at any time; it is idempotent.

    uv run mt/fetch_engine.py --check
    uv run mt/fetch_engine.py --install zh-en
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MIRROR = "https://github.com/jiangwensm/OPUS-argosmodels"
FILES = {
    "zh-en": "1.0/translate-zh_en-1_0.argosmodel",
    "en-zh": "1.0/translate-en_zh-1_0.argosmodel",
    "zt-en": "1.0/translate-zt_en-1_0.argosmodel",
    "en-zt": "1.0/translate-en_zt-1_0.argosmodel",
}
PACKAGE_ROOT = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "argos-translate" / "packages"
ROUTES = {
    "zh-en": "downloadable",
    "zt-en": "downloadable",
    "en-my": "no_model",
    "my-en": "no_model",
    "zh-my": "no_model",
}


def installed(route: str) -> Path | None:
    name = "translate-" + route.replace("-", "_") + "-1_0"
    path = PACKAGE_ROOT / name
    return path if (path / "model" / "model.bin").is_file() else None


def fetch(route: str) -> Path:
    if route not in FILES:
        raise SystemExit(f"no downloadable model for {route}; "
                         f"available: {', '.join(sorted(FILES))}")
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as workspace:
        workspace = Path(workspace)
        print(f"[engine] cloning {MIRROR} (sparse: {FILES[route]})")
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", MIRROR, str(workspace / "m")],
            check=True, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "-C", str(workspace / "m"), "sparse-checkout", "set", "--skip-checks", FILES[route]],
            check=True, capture_output=True, text=True,
        )
        archive = workspace / "m" / FILES[route]
        if not archive.is_file():
            raise SystemExit(f"clone did not produce {FILES[route]}")
        print(f"[engine] installing {archive.name} ({archive.stat().st_size / 1e6:.0f} MB)")
        from argostranslate import package as argos_package  # noqa: PLC0415
        argos_package.install_from_path(str(archive))
    target = installed(route)
    if target is None:
        raise SystemExit("model installed but not found under the package directory")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--install", action="append", choices=sorted(FILES), default=[],
                        help="route to install, e.g. zh-en")
    parser.add_argument("--all-available", action="store_true", help="install every downloadable model")
    parser.add_argument("--check", action="store_true", help="report what is installed")
    parser.add_argument("--remove", action="append", choices=sorted(FILES), default=[],
                        help="delete an installed model")
    args = parser.parse_args(argv)

    if args.remove:
        for route in args.remove:
            target = installed(route)
            if target:
                shutil.rmtree(target)
                print(f"[engine] removed {target}")
            else:
                print(f"[engine] {route}: not installed")

    wanted = list(args.install)
    if args.all_available:
        wanted = sorted(FILES)

    for route in wanted:
        if installed(route) and not args.check:
            print(f"[engine] {route}: already installed at {installed(route)}")
            continue
        print(f"[engine] {route}: {fetch(route)}")

    print(f"\n[engine] package directory: {PACKAGE_ROOT}")
    print(f"{'route':<8}{'status':<14}path")
    for route, kind in ROUTES.items():
        path = installed(route)
        state = "installed" if path else kind
        print(f"{route:<8}{state:<14}{path or '-'}")

    report = {
        "package_dir": str(PACKAGE_ROOT),
        "routes": {
            route: {"state": "installed" if installed(route) else kind,
                    "path": str(installed(route)) if installed(route) else None}
            for route in ROUTES
        },
    }
    (Path(__file__).resolve().parent / "engines.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
