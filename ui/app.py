from __future__ import annotations

import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow
from ui.theme import apply_dark_theme
from utils.logging_config import get_logger
from utils.settings import AppSettings

logger = get_logger(__name__)
INSTANCE_SERVER_NAME = "MusicLyrizDesktopApp"


def _enable_high_dpi() -> None:
    for attribute_name in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
        attribute = getattr(Qt.ApplicationAttribute, attribute_name, None)
        if attribute is not None:
            QApplication.setAttribute(attribute, True)


def run_app(settings: AppSettings) -> int:
    _enable_high_dpi()
    app = QApplication(sys.argv)
    app.setApplicationName("Music Lyriz")
    app.setOrganizationName("Music Lyriz")
    app.setQuitOnLastWindowClosed(False)
    _install_exception_hook()
    apply_dark_theme(app, settings.ui.theme)

    if _request_running_instance_to_show():
        return 0

    window = MainWindow(settings)
    instance_server = _create_instance_server(window)
    if instance_server is not None:
        app._music_lyriz_instance_server = instance_server

    window.show()
    return app.exec()


def _request_running_instance_to_show() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(INSTANCE_SERVER_NAME)
    if not socket.waitForConnected(150):
        return False

    socket.write(b"show")
    socket.flush()
    socket.waitForBytesWritten(150)
    socket.disconnectFromServer()
    return True


def _create_instance_server(window: MainWindow) -> QLocalServer | None:
    QLocalServer.removeServer(INSTANCE_SERVER_NAME)
    server = QLocalServer(window)
    if not server.listen(INSTANCE_SERVER_NAME):
        logger.warning("Could not create single-instance server: %s", server.errorString())
        return None

    def activate_window() -> None:
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()
            connection.deleteLater()
        window.show_from_tray()

    server.newConnection.connect(activate_window)
    return server


def _install_exception_hook() -> None:
    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.error(
            "Unhandled exception\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        )
        QMessageBox.critical(
            None,
            "Music Lyriz",
            "Something went wrong. Music Lyriz wrote the details to the log file.",
        )

    sys.excepthook = handle_exception
