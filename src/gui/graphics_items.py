from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsTextItem, QMenu
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject
from PySide6.QtGui import QBrush, QPen, QPainter, QPainterPath, QColor, QFont
from nodes.image_nodes import NODE_REGISTRY

class PortItem(QGraphicsItem):
    def __init__(self, name, port_type, is_output, parent=None):
        super().__init__(parent)
        self.name = name
        self.port_type = port_type
        self.is_output = is_output
        self.radius = 6
        self.margin = 2
        
        self.setAcceptHoverEvents(True)
        
        # Определяем цвет порта (можно добавить маппинг типов к цветам)
        self.color = QColor("#FFFF00") if port_type == "Image" else QColor("#00FF00")

    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, 2*self.radius, 2*self.radius)

    def paint(self, painter, option, widget):
        painter.setBrush(self.color)
        if self.is_output:
             painter.setPen(QPen(Qt.white, 1))
        else:
             painter.setPen(QPen(Qt.black, 1))
             
        painter.drawEllipse(-self.radius, -self.radius, 2*self.radius, 2*self.radius)

class NodeItem(QGraphicsItem):
    def __init__(self, node_type, node_id, scene, params=None):
        super().__init__()
        self.node_type = node_type
        self.node_id = node_id
        self.params = params or {}
        self.scene = scene
        
        self.width = 150
        self.height = 100 # Будет пересчитано
        self.header_height = 25
        
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        
        self.inputs = []
        self.outputs = []
        self.status = "idle" # idle, running, completed, error
        
        self._init_ports()

    def set_status(self, status):
        self.status = status
        self.update() # Trigger repaint

    def _init_ports(self):
        node_class = NODE_REGISTRY[self.node_type]
        
        # Inputs
        y = self.header_height + 10
        for name, type_ in node_class.INPUT_TYPES.items():
            port = PortItem(name, type_, is_output=False, parent=self)
            port.setPos(-self.radius_offset(), y)
            self.inputs.append(port)
            y += 20
            
        input_height = y
        
        # Outputs
        y = self.header_height + 10
        for name, type_ in node_class.OUTPUT_TYPES.items():
            port = PortItem(name, type_, is_output=True, parent=self)
            port.setPos(self.width + self.radius_offset(), y)
            self.outputs.append(port)
            y += 20
            
        output_height = y
        
        self.height = max(input_height, output_height, 50) + 10

    def radius_offset(self):
        return 0 # Порты на границе

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget):
        # Body
        if self.status == "running":
            painter.setBrush(QColor("#445544")) # Greenish background
        elif self.status == "error":
            painter.setBrush(QColor("#553333")) # Reddish background
        else:
            painter.setBrush(QColor("#333333"))
            
        if self.isSelected():
            painter.setPen(QPen(QColor("#FF9900"), 2))
        elif self.status == "running":
            painter.setPen(QPen(QColor("#00FF00"), 2))
        elif self.status == "completed":
            painter.setPen(QPen(QColor("#00CC00"), 2))
        elif self.status == "error":
            painter.setPen(QPen(QColor("#FF0000"), 2))
        else:
            painter.setPen(Qt.NoPen)
            
        painter.drawRoundedRect(self.boundingRect(), 5, 5)
        
        # Header
        painter.setBrush(QColor("#555555"))
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width, self.header_height, 5, 5)
        painter.drawPath(path) # Simplified, draws over full rect then fills header
        
        # Для красоты перерисуем низ хедера прямоугольником, чтобы убрать скругления снизу
        painter.drawRect(0, self.header_height-5, self.width, 5) 
        
        # Title
        painter.setPen(Qt.white)
        font = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, self.width, self.header_height), Qt.AlignCenter, f"{self.node_type}")
        
        # Port Labels
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        for port in self.inputs:
            painter.drawText(QRectF(10, port.y()-10, self.width/2, 20), Qt.AlignLeft | Qt.AlignVCenter, port.name)
            
        for port in self.outputs:
            painter.drawText(QRectF(self.width/2, port.y()-10, self.width/2 - 10, 20), Qt.AlignRight | Qt.AlignVCenter, port.name)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # Здесь можно обновлять связи
            # В QGraphicsScene связи обновятся автоматически, если они правильно привязаны,
            # или нужно вызывать update() для них.
            pass
        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        menu = QMenu()

        delete_action = menu.addAction("Delete node")

        action = menu.exec(event.screenPos())

        if action == delete_action:
            self.scene.remove_node(self)

        event.accept()

class EdgeItem(QGraphicsPathItem):
    def __init__(self, source_port, target_port):
        super().__init__()
        self.source_port = source_port
        self.target_port = target_port
        
        self.setZValue(-1) # На заднем плане
        self.update_path()
        
        pen = QPen(QColor("#AAAAAA"), 2)
        self.setPen(pen)

    def update_path(self):
        if not self.source_port or not self.target_port:
            return
            
        start_pos = self.source_port.scenePos()
        end_pos = self.target_port.scenePos()
        
        path = QPainterPath()
        path.moveTo(start_pos)
        
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        
        ctrl1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
        ctrl2 = QPointF(end_pos.x() - dx * 0.5, end_pos.y())
        
        path.cubicTo(ctrl1, ctrl2, end_pos)
        self.setPath(path)

    def paint(self, painter, option, widget):
        self.update_path() # Обновляем при перерисовке
        super().paint(painter, option, widget)

