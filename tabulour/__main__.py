from __future__ import annotations

import argparse


class TabulourArgs(argparse.Namespace):
    """tabulour specific arguments"""

    profile: bool
    user_dir: bool
    debug: bool
    init_config: bool
    init_history: bool
    open_file: str | None


class TabulourParser(argparse.ArgumentParser):
    """tabulour specific argument parser"""

    def __init__(self):
        from . import __version__

        super().__init__(description="Command line interface of tabulour.")
        self.add_argument(
            "-v",
            "--version",
            action="version",
            version=f"tabulour version {__version__}",
        )
        self.add_argument("--profile", action="store_true")
        self.add_argument("--user-dir", action="store_true")
        self.add_argument("--debug", action="store_true")
        self.add_argument("--init-config", action="store_true")
        self.add_argument("--init-history", action="store_true")

    def parse_known_args(
        self, args=None, namespace=None
    ) -> tuple[TabulourArgs, list[str]]:
        args, unknown = super().parse_known_args(args, namespace)
        args = TabulourArgs(**vars(args))
        if not unknown:
            args.open_file = None
        elif len(unknown) == 1:
            args.open_file = unknown[0]
        else:
            raise argparse.ArgumentError("Too many arguments.")
        return args, unknown


def main():
    parser = TabulourParser()

    args, _ = parser.parse_known_args()

    if args.profile or args.user_dir:
        from ._utils import CONFIG_PATH

        return print(CONFIG_PATH.parent)

    if args.debug:
        import logging

        logger = logging.getLogger("tabulour")
        logging.basicConfig(format="%(levelname)s|| %(message)s")
        logger.setLevel(logging.DEBUG)

    if args.init_config:
        from ._utils import CONFIG_PATH, tabulourConfig

        CONFIG_PATH.unlink(missing_ok=True)
        tabulourConfig.from_toml(CONFIG_PATH).as_toml()
        return print(f"tabulour config file initialized at {str(CONFIG_PATH)}.")

    if args.init_history:
        from ._utils import TXT_PATH

        TXT_PATH.write_text("")

    from . import TableViewer

    viewer = TableViewer()
    viewer.show()

    if args.open_file:
        viewer.open(args.open_file)
    return


if __name__ == "__main__":
    main()
