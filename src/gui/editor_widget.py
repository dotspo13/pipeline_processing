import uuid
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QTransform, QWheelEvent, QMouseEvent
from .graphics_items import NodeItem, EdgeItem, PortItem

class NodeEditorWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(0, 0, 5000, 5000)
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        self.nodes = {} # id -> NodeItem
        self.edges = [] # EdgeItem
        
        # Логика соединения
        self.temp_edge = None
        self.start_port = None

    def add_node(self, node_type, pos=None):
        node_id = str(uuid.uuid4())
        node = NodeItem(node_type, node_id)
        
        if pos:
            node.setPos(pos)
        else:
            # Center of viewport
            center = self.mapToScene(self.viewport().rect().center())
            node.setPos(center)
            
        self.scene.addItem(node)
        self.nodes[node_id] = node
        return node

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)

    # Обработка создания связей
    # Для простоты перехватываем mousePress на сцене через view, 
    # но лучше это делать в itemChange или mousePressEvent айтемов.
    # Но так как PortItem - дочерний элемент NodeItem, с событиями может быть возня.
    # Сделаем простую реализацию:
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, PortItem):
                self.start_port = item
                self.setDragMode(QGraphicsView.NoDrag)
                return # Не передаем событие дальше (чтобы не драгать сцену)
                
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.start_port:
            # Рисуем временную линию
            pass 
            # TODO: Рисовать резиновую линию (QGraphicsLineItem)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.start_port:
            item = self.itemAt(event.pos())
            if isinstance(item, PortItem) and item != self.start_port:
                # Проверяем валидность (output -> input)
                if self.start_port.is_output != item.is_output:
                    # Нормализуем source/target
                    source = self.start_port if self.start_port.is_output else item
                    target = item if self.start_port.is_output else self.start_port
                    
                    self.add_edge(source, target)
            
            self.start_port = None
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            return

        super().mouseReleaseEvent(event)

    def add_edge(self, source_port, target_port):
        # Удаляем существующие связи в этот вход (один ко многим для выхода, но один к одному для входа?)
        # В нашем движке нет ограничения, но обычно вход принимает одно значение.
        # Проверим существующие связи
        for edge in self.edges[:]:
            if edge.target_port == target_port:
                self.scene.removeItem(edge)
                self.edges.remove(edge)

        edge = EdgeItem(source_port, target_port)
        self.scene.addItem(edge)
        self.edges.append(edge)

    def update_node_param(self, node_id, param_name, value):
        if node_id in self.nodes:
            self.nodes[node_id].params[param_name] = value

    def serialize_graph(self):
        graph_data = {"nodes": [], "links": []}
        
        for node_id, node_item in self.nodes.items():
            graph_data["nodes"].append({
                "id": node_id,
                "type": node_item.node_type,
                "params": node_item.params
            })
            
        for edge in self.edges:
            graph_data["links"].append({
                "from_node": edge.source_port.parentItem().node_id,
                "from_output": edge.source_port.name,
                "to_node": edge.target_port.parentItem().node_id,
                "to_input": edge.target_port.name
            })
            
        return graph_data

    def clear(self):
        self.scene.clear()
        self.nodes = {}
        self.edges = []


