"""FENIX CLI banner."""

from __future__ import annotations

import sys

RED = "\033[0;31m"
NC = "\033[0m"

BANNER_LINES = (
    "oooooooooooo oooooooooooo ooooo      ooo ooooo ooooooo  ooooo ",
    "`888'     `8 `888'     `8 `888b.     `8' `888'  `8888    d8'  ",
    " 888          888          8 `88b.    8   888     Y888..8P    ",
    " 888oooo8     888oooo8     8   `88b.  8   888      `8888'     ",
    " 888    \"     888    \"     8     `88b.8   888     .8PY888.    ",
    " 888          888       o  8       `888   888    d8'  `888b   ",
    "o888o        o888ooooood8 o8o        `8  o888o o888o  o88888o ",
)

TAGLINE = "Fileless Execution for NIX"


def print_banner(*, file=None) -> None:
    """Print the FENIX banner (stdout by default, same order as other CLI output)."""
    from fenix import __version__

    out = file if file is not None else sys.stdout
    print("", file=out)
    for line in BANNER_LINES:
        print(f"{RED}{line}{NC}", file=out)
    print("", file=out)
    print(TAGLINE, file=out)
    print(f"v{__version__}", file=out)
    print("", file=out)


def should_show_banner(quiet: bool) -> bool:
    return not quiet
