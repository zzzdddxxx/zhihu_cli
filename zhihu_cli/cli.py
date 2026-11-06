"""CLI entry point for zhihu-cli.

Usage:
    zhihu login [--cookie "..."] / logout / status / whoami
"""

from __future__ import annotations

import click

from . import __version__
from .commands import account, common


@click.group()
@click.version_option(version=__version__, prog_name="zhihu")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool):
    """zhihu — Zhihu CLI tool"""
    common.setup_logging(verbose)


# Register commands.
cli.add_command(account.login)
cli.add_command(account.logout)
cli.add_command(account.status)
cli.add_command(account.whoami)


if __name__ == "__main__":
    cli()
