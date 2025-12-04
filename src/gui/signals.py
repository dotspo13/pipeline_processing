from PySide6.QtCore import QObject, Signal

class ExecutionSignals(QObject):
    status_changed = Signal(str, str) # node_id, status ("running", "completed", "error")
