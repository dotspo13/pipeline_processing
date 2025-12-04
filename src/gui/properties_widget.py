from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, 
                               QLineEdit, QDoubleSpinBox, QSpinBox, 
                               QLabel, QComboBox)
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
            
            if param_type == str:
                widget = QLineEdit()
                if value: widget.setText(str(value))
                widget.textChanged.connect(lambda v, n=param_name: self._on_change(n, v))
                
            elif param_type == float:
                widget = QDoubleSpinBox()
                widget.setRange(-1000000, 1000000)
                widget.setSingleStep(0.1)
                if value: widget.setValue(float(value))
                widget.valueChanged.connect(lambda v, n=param_name: self._on_change(n, v))
                
            elif param_type == int:
                widget = QSpinBox()
                widget.setRange(-1000000, 1000000)
                if value: widget.setValue(int(value))
                widget.valueChanged.connect(lambda v, n=param_name: self._on_change(n, v))
            
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

