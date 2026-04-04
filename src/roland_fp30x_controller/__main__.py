from __future__ import annotations

import sys

from roland_fp30x_controller.app import run


def main() -> None:
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
