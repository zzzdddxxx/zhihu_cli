"""zhihu-cli — browse Zhihu from the terminal."""

try:
    from importlib.metadata import version

    __version__ = version("zhihu-cli")
except Exception:
    __version__ = "0.0.0"
