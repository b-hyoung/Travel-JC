import argparse
import sys
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui.main import MainWindow


def parse_args():
    parser = argparse.ArgumentParser(description="PyQt5 kiosk smoke screenshot")
    parser.add_argument(
        "--output",
        default="artifacts/qt_smoke.png",
        help="Output PNG path",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=2000,
        help="Delay before capture in ms",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1280,
        help="Window width",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Window height",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(args.width, args.height)
    window.show()

    def grab():
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            print("No primary screen available", file=sys.stderr)
            app.quit()
            return
        pixmap = screen.grabWindow(window.winId())
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(out_path))
        app.quit()

    QTimer.singleShot(max(0, args.delay_ms), grab)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
