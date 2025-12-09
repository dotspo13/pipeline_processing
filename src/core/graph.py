from typing import Dict, List, Any, Type
from .node import Node

class Graph:
    """
    Представление графа вычислений.
    Отвечает за хранение структуры, валидацию и создание узлов.
    """
    def __init__(self, node_registry: Dict[str, Type[Node]]):
        self.node_registry = node_registry
        self.nodes: Dict[str, Node] = {}
        self.links: List[Dict[str, str]] = [] # [{'from_node': 'id', 'from_socket': 'name', 'to_node': 'id', 'to_socket': 'name'}]
        self.adj_list: Dict[str, List[Dict]] = {} # Для быстрого доступа к связям: node_id -> [outgoing_links]
        self.reverse_adj_list: Dict[str, List[Dict]] = {} # node_id -> [incoming_links]

    def load_from_json(self, data: Dict[str, Any]):
        """
        Загружает граф из словаря (JSON-структуры).
        
        Format:
        {
            "nodes": [
                {"id": "1", "type": "LoadImage", "params": {"path": "img.jpg"}},
                ...
            ],
            "links": [
                {"from_node": "1", "from_output": "image", "to_node": "2", "to_input": "image"},
                ...
            ]
        }
        """
        self.nodes = {}
        self.links = []
        self.adj_list = {}
        self.reverse_adj_list = {}

        for node_data in data.get("nodes", []):
            node_id = node_data["id"]
            node_type = node_data["type"]
            params = node_data.get("params", {})
            
            if node_type not in self.node_registry:
                raise ValueError(f"Unknown node type: {node_type}")
            
            node_class = self.node_registry[node_type]
            node_instance = node_class(node_id, params)
            self.nodes[node_id] = node_instance
            self.adj_list[node_id] = []
            self.reverse_adj_list[node_id] = []

        for link_data in data.get("links", []):
            from_node = link_data["from_node"]
            from_output = link_data["from_output"]
            to_node = link_data["to_node"]
            to_input = link_data["to_input"]
            
            if from_node not in self.nodes:
                raise ValueError(f"Source node not found: {from_node}")
            if to_node not in self.nodes:
                raise ValueError(f"Target node not found: {to_node}")
            
            source_node = self.nodes[from_node]
            target_node = self.nodes[to_node]
            
            if from_output not in source_node.OUTPUT_TYPES:
                raise ValueError(f"Output port '{from_output}' not found in node {from_node} ({source_node.__class__.__name__})")
            if to_input not in target_node.INPUT_TYPES:
                raise ValueError(f"Input port '{to_input}' not found in node {to_node} ({target_node.__class__.__name__})")

            out_type = source_node.OUTPUT_TYPES[from_output]
            in_type = target_node.INPUT_TYPES[to_input]
            
            if out_type != in_type and out_type != "Any" and in_type != "Any":
                 raise ValueError(f"Type mismatch: Node {from_node} output '{from_output}' ({out_type}) -> Node {to_node} input '{to_input}' ({in_type})")

            link = {
                "from_node": from_node,
                "from_output": from_output,
                "to_node": to_node,
                "to_input": to_input
            }
            self.links.append(link)
            self.adj_list[from_node].append(link)
            self.reverse_adj_list[to_node].append(link)

    def get_node(self, node_id: str) -> Node:
        return self.nodes.get(node_id)

    def get_incoming_links(self, node_id: str) -> List[Dict[str, str]]:
        return self.reverse_adj_list.get(node_id, [])
    
    def get_outgoing_links(self, node_id: str) -> List[Dict[str, str]]:
        return self.adj_list.get(node_id, [])


