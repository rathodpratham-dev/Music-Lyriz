from __future__ import annotations

import os
from pathlib import Path
import sys


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
    except ImportError as exc:
        print(f"PySide6 is required to generate the icon: {exc}", file=sys.stderr)
        return 1

    app = QGuiApplication.instance() or QGuiApplication([])

    assets_dir = Path(__file__).resolve().parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    icon_path = assets_dir / "music_lyriz.ico"

    size = 256
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor("#20252B"))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QColor("#E2B84D"))
    painter.setFont(QFont("Segoe UI", 92, QFont.Weight.Bold))
    painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, "ML")
    painter.end()

    if not image.save(str(icon_path), "ICO"):
        print(f"Could not write icon: {icon_path}", file=sys.stderr)
        return 1

    print(icon_path)
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
