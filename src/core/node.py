from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Node(ABC):
    """
    Абстрактный базовый класс для всех узлов в графе.
    """
    
    INPUT_TYPES: Dict[str, Any] = {}
    OUTPUT_TYPES: Dict[str, Any] = {}
    PARAMETERS: Dict[str, Any] = {}
    

    INPUT_STRATEGY = "ALL"

    def __init__(self, node_id: str, params: Dict[str, Any] = None):
        self.node_id = node_id
        self.params = params or {}
        self.concurrency_level = 1  
        
        self._validate_params()

    def _validate_params(self):
        """Проверяет, что переданные параметры соответствуют описанию PARAMETERS."""
        for param_name, param_type in self.PARAMETERS.items():
            if param_name in self.params:
                value = self.params[param_name]
                if param_type is not Any and not isinstance(value, param_type):
                    try:
                        self.params[param_name] = param_type(value)
                    except (ValueError, TypeError):
                        raise TypeError(f"Parameter '{param_name}' must be of type {param_type.__name__}, got {type(value).__name__}")

    @abstractmethod
    def execute(self, **inputs) -> Dict[str, Any]:
        """
        Основная логика узла.
        
        Args:
            **inputs: Словарь входных данных, где ключи соответствуют INPUT_TYPES.
            
        Returns:
            Dict[str, Any]: Словарь выходных данных, где ключи соответствуют OUTPUT_TYPES.
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.node_id}>"

