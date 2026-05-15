import logging
import socket
import webbrowser

from prompt_optimizer_app.config import SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT


logger = logging.getLogger(__name__)


class SingleInstance:
    def __init__(
        self,
        host: str = SINGLE_INSTANCE_HOST,
        port: int = SINGLE_INSTANCE_PORT,
    ):
        self.host = host
        self.port = port
        self._socket: socket.socket | None = None

    def acquire(self, dashboard_url: str) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((self.host, self.port))
            sock.listen(1)
        except OSError:
            logger.info("Prompt Optimizer is already running.")
            webbrowser.open(dashboard_url)
            return False

        self._socket = sock
        return True

    def release(self) -> None:
        if self._socket is None:
            return

        self._socket.close()
        self._socket = None
