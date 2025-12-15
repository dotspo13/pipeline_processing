from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, 
                               QLineEdit, QDoubleSpinBox, QSpinBox, 
                               QLabel, QComboBox, QPushButton, QHBoxLayout, QFileDialog)
from PySide6.QtCore import Signal
from nodes.image_nodes import NODE_REGISTRY

class PropertiesWidget(QWidget):
    paramChanged = Signal(str, str, object) # node_id, param_name, value

    def __init__(self):
        super().__init__()
        self.current_node_item = None
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)
        self.layout.addStretch()

    def set_node(self, node_item):
        self.current_node_item = node_item
        self.clear()
        
        node_type = node_item.node_type
        node_class = NODE_REGISTRY.get(node_type)
        if not node_class:
            return
            
        # Заголовок
        self.layout.insertWidget(0, QLabel(f"Properties: {node_type}"))
        
        # Параметры
        current_params = node_item.params
        
        for param_name, param_type in node_class.PARAMETERS.items():
            value = current_params.get(param_name)
            
            if param_name == "path":
                widget = QWidget()
                h_layout = QHBoxLayout(widget)
                h_layout.setContentsMargins(0, 0, 0, 0)
                
                line_edit = QLineEdit()
                if value: line_edit.setText(str(value))
                line_edit.textChanged.connect(lambda v, n=param_name: self._on_change(n, v))
                
                btn = QPushButton("...")
                btn.setMaximumWidth(30)
                btn.clicked.connect(lambda _, le=line_edit: self._browse_file_open(le))
                
                h_layout.addWidget(line_edit)
                h_layout.addWidget(btn)
                self.form_layout.addRow(param_name, widget)

            elif param_name == "path_prefix":
                widget = QWidget()
                h_layout = QHBoxLayout(widget)
                h_layout.setContentsMargins(0, 0, 0, 0)
                
                line_edit = QLineEdit()
                if value: line_edit.setText(str(value))
                line_edit.textChanged.connect(lambda v, n=param_name: self._on_change(n, v))
                
                btn = QPushButton("...")
                btn.setMaximumWidth(30)
                btn.clicked.connect(lambda _, le=line_edit: self._browse_file_save(le))
                
                h_layout.addWidget(line_edit)
                h_layout.addWidget(btn)
                self.form_layout.addRow(param_name, widget)

            elif param_type == str:
                widget = QLineEdit()
                if value: widget.setText(str(value))
                widget.textChanged.connect(lambda v, n=param_name: self._on_change(n, v))
                self.form_layout.addRow(param_name, widget)
                
            elif param_type == float:
                widget = QDoubleSpinBox()
                widget.setRange(-1000000, 1000000)
                widget.setSingleStep(0.1)
                if value: widget.setValue(float(value))
                widget.valueChanged.connect(lambda v, n=param_name: self._on_change(n, v))
                self.form_layout.addRow(param_name, widget)
                
            elif param_type == int:
                widget = QSpinBox()
                widget.setRange(-1000000, 1000000)
                if value: widget.setValue(int(value))
                widget.valueChanged.connect(lambda v, n=param_name: self._on_change(n, v))
                self.form_layout.addRow(param_name, widget)
            
            else:
                widget = QLineEdit() # Fallback
                if value: widget.setText(str(value))
                widget.textChanged.connect(lambda v, n=param_name: self._on_change(n, v))
                self.form_layout.addRow(param_name, widget)

    def clear(self):
        # Очистка лейаута
        while self.layout.count() > 2: # Оставляем form_layout и stretch
             item = self.layout.takeAt(0)
             if item.widget(): item.widget().deleteLater()
             
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _on_change(self, param_name, value):
        if self.current_node_item:
            self.paramChanged.emit(self.current_node_item.node_id, param_name, value)

    def _browse_file_open(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)")
        if file_path:
            line_edit.setText(file_path)

    def _browse_file_save(self, line_edit):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Image Prefix", "", "All Files (*)")
        if file_path:
            # Remove extension if present, as SaveImage adds it
            import os
            root, _ = os.path.splitext(file_path)
            line_edit.setText(root)

