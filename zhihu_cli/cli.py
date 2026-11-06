"""CLI entry point for zhihu-cli.

Usage:
    zhihu login [--cookie "..."] / logout / status / whoami
    zhihu search <关键词> --type people [--top N] [--num N] [--offset N]
    zhihu user <url_token>
    zhihu answers <url_token> [--offset N] [--num N]
    zhihu pins <url_token> [--offset N] [--num N]
    zhihu following <url_token> [--offset N] [--num N]
"""

from __future__ import annotations

import click

from . import __version__
from .commands import account, common, search, user


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

cli.add_command(search.search)
cli.add_command(user.user)
cli.add_command(user.answers)
cli.add_command(user.pins)
cli.add_command(user.following)


if __name__ == "__main__":
    cli()
