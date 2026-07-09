"""Application entry point."""

from utils import setup_logging
from gui import App


def main() -> None:
    setup_logging()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
