"""CLI entrypoint for python -m quranmedialib.check."""

import sys

from quranmedialib.check._harness import cli

sys.exit(cli())
