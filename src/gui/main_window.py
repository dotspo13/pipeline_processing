from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QDockWidget, QListWidget, QPushButton, QTextEdit, 
                               QMessageBox, QSplitter)
from PySide6.QtCore import Qt
from .editor_widget import NodeEditorWidget
from .properties_widget import PropertiesWidget
from core.executor import Executor
from core.graph import Graph
from nodes.image_nodes import NODE_REGISTRY
from .utils import StreamRedirector
from .signals import ExecutionSignals
import threading
import time
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dataflow Pipeline Editor")
        self.resize(1200, 800)

        # Сигналы для обновления UI из потока выполнения
        self.exec_signals = ExecutionSignals()
        self.exec_signals.status_changed.connect(self._on_node_status_changed)

        # Перенаправление stdout
        self.redirector = StreamRedirector(sys.stdout)
        self.redirector.messageWritten.connect(self._on_stdout_message)
        sys.stdout = self.redirector

        # Центральный виджет - Редактор графа
        self.editor = NodeEditorWidget(self)
        self.setCentralWidget(self.editor)

        # Создание док-панелей
        self._create_library_dock()
        self._create_properties_dock()
        self._create_logs_dock()
        self._create_toolbar()

        # Связывание сигналов
        self.editor.scene.selectionChanged.connect(self._on_selection_changed)

    def _create_library_dock(self):
        self.library_dock = QDockWidget("Library", self)
        self.library_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.library_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.library_list = QListWidget()
        for node_name in NODE_REGISTRY.keys():
            self.library_list.addItem(node_name)
            
        self.library_list.itemDoubleClicked.connect(self._on_library_item_dbl_click)
        
        self.library_dock.setWidget(self.library_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.library_dock)

    def _create_properties_dock(self):
        self.properties_dock = QDockWidget("Properties", self)
        self.properties_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.properties_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.properties_widget = PropertiesWidget()
        self.properties_widget.paramChanged.connect(self._on_param_changed)
        
        self.properties_dock.setWidget(self.properties_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)

    def _create_logs_dock(self):
        self.logs_dock = QDockWidget("Logs", self)
        self.logs_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.logs_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        self.logs_dock.setWidget(self.log_output)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.logs_dock)

    def _create_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")
        
        run_action = toolbar.addAction("Run Pipeline")
        run_action.triggered.connect(self._run_pipeline)
        
        clear_action = toolbar.addAction("Clear Graph")
        clear_action.triggered.connect(self.editor.clear)

    def _on_library_item_dbl_click(self, item):
        node_type = item.text()
        self.editor.add_node(node_type)

    def _on_selection_changed(self):
        selected_items = self.editor.scene.selectedItems()
        # Фильтруем, оставляем только узлы (игнорируем соединения и порты)
        # Предполагаем, что у NodeItem есть метод get_model_data
        
        # Пока просто берем первый попавшийся узел
        from .graphics_items import NodeItem
        node_item = None
        for item in selected_items:
            if isinstance(item, NodeItem):
                node_item = item
                break
        
        if node_item:
            self.properties_widget.set_node(node_item)
        else:
            self.properties_widget.clear()

    def _on_param_changed(self, node_id, param_name, value):
        self.editor.update_node_param(node_id, param_name, value)

    def _on_node_status_changed(self, node_id, status):
        if node_id in self.editor.nodes:
            node_item = self.editor.nodes[node_id]
            node_item.set_status(status)

    def _on_stdout_message(self, text):
        self.log_output.moveCursor(self.log_output.textCursor().End)
        self.log_output.insertPlainText(text)
        self.log_output.moveCursor(self.log_output.textCursor().End)

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def _run_pipeline(self):
        graph_data = self.editor.serialize_graph()
        if not graph_data["nodes"]:
            self.log("Graph is empty!")
            return

        self.log("Building graph...")
        try:
            graph = Graph(NODE_REGISTRY)
            graph.load_from_json(graph_data)
            self.log("Graph valid.")
        except Exception as e:
            self.log(f"Error building graph: {e}")
            QMessageBox.critical(self, "Graph Error", str(e))
            return

        self.log("Starting execution...")
        
        # Запуск в отдельном потоке, чтобы не блокировать UI
        # Executor использует multiprocessing, но сам метод run() блокирующий.
        threading.Thread(target=self._execute_thread, args=(graph,), daemon=True).start()

    def _execute_thread(self, graph):
        try:
            # Функция обратного вызова, которая будет вызываться из executor
            # Так как это выполняется в другом потоке, используем сигналы для передачи в UI
            def status_callback(node_id, status):
                self.exec_signals.status_changed.emit(node_id, status)

            executor = Executor(graph)
            executor.run(status_callback=status_callback)
            
            print("Execution finished successfully.") 
        except Exception as e:
            print(f"Execution error: {e}")

    def closeEvent(self, event):
        # Restore stdout
        sys.stdout = sys.__stdout__
        super().closeEvent(event)
