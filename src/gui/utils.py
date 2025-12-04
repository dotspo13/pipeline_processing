import sys
from PySide6.QtCore import QObject, Signal

class StreamRedirector(QObject):
    messageWritten = Signal(str)

    def __init__(self, stream=None):
        super().__init__()
        self._stream = stream or sys.stdout

    def write(self, text):
        self._stream.write(text)
        self.messageWritten.emit(text)

    def flush(self):
        self._stream.flush()


