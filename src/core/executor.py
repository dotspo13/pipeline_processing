from concurrent.futures._base import Future


import time
import concurrent.futures
import multiprocessing
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque
from .graph import Graph

class Executor:
    """
    Исполнитель графа. Управляет запуском узлов и передачей данных.
    """
    def __init__(self, graph: Graph, max_workers: int = None, timeout: float = 20.0):
        self.graph = graph
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.timeout = timeout
        self.input_queues: Dict[str, Dict[str, deque]] = defaultdict[str, Dict[str, deque]](lambda: defaultdict(deque))   
        self.active_tasks: Set[concurrent.futures.Future] = set[Future]()
        self.future_to_node: Dict[concurrent.futures.Future, str] = {}
        self._executed_sources: Set[str] = set()

    def _feed_inputs(self, initial_inputs: Dict[str, Dict[str, Any]]):
        """
        Загружает начальные данные в граф.
        initial_inputs: {node_id: {input_name: value}}
        """
        for node_id, inputs in initial_inputs.items():
            for port, value in inputs.items():
                self.input_queues[node_id][port].append(value)

    def _check_ready_nodes(self) -> List[tuple]:
        """
        Находит узлы, готовые к выполнению (есть данные на всех обязательных входах).
        Returns: List[(node_id, inputs_dict)]
        """
        ready_nodes = []
        
        for node_id, node in self.graph.nodes.items():
            inputs = {}
            is_ready = True
            
            required_inputs = node.INPUT_TYPES.keys()
            connected_inputs = set()
            
            incoming_links = self.graph.get_incoming_links(node_id)
            for link in incoming_links:
                connected_inputs.add(link['to_input'])

            if not required_inputs:
                if node_id not in self._executed_sources:
                    self._executed_sources.add(node_id)
                    ready_nodes.append((node_id, {}))
                continue
            
            if getattr(node, 'INPUT_STRATEGY', 'ALL') == "ANY":
                has_any_data = False
                for port in connected_inputs:
                    if self.input_queues[node_id][port]:
                        has_any_data = True
                        break
                
                if has_any_data:
                    is_ready = True
                else:
                    is_ready = False
            else:
                for port in required_inputs:
                    if port in connected_inputs:
                        if not self.input_queues[node_id][port]:
                            is_ready = False
                            break
            
            if is_ready:
                node_inputs = {}
                
                ports_to_check = connected_inputs if getattr(node, 'INPUT_STRATEGY', 'ALL') == "ANY" else required_inputs
                
                for port in ports_to_check:
                    if port in self.input_queues[node_id] and self.input_queues[node_id][port]:
                         node_inputs[port] = self.input_queues[node_id][port].popleft()
                
                ready_nodes.append((node_id, node_inputs))
                
        return ready_nodes

    def run(self, initial_inputs: Dict[str, Dict[str, Any]] = None, status_callback=None):
        """
        Запускает выполнение графа.
        status_callback: функция(node_id, status), где status: "running" | "completed" | "error"
        """
        if initial_inputs:
            self._feed_inputs(initial_inputs)

        self._executed_sources.clear()

        last_event_time = time.time()
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                done, _ = concurrent.futures.wait(self.active_tasks, timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED)
                
                if done:
                    last_event_time = time.time()
                    for future in done:
                        self.active_tasks.remove(future)
                        node_id = self.future_to_node.pop(future)
                        
                        try:
                            result_data, updated_node = future.result()
                            
                            self.graph.nodes[node_id] = updated_node
                            
                            if status_callback: status_callback(node_id, "completed")
                            self._distribute_outputs(node_id, result_data)
                        except Exception as e:
                            if status_callback: status_callback(node_id, "error")
                            print(f"Error executing node {node_id}: {e}")

                if len(self.active_tasks) < self.max_workers * 2:
                    ready_tasks = self._check_ready_nodes()
                    for node_id, node_inputs in ready_tasks:
                        node = self.graph.nodes[node_id]

                        future = executor.submit(_execute_node_wrapper, node, node_inputs)
                        self.active_tasks.add(future)
                        self.future_to_node[future] = node_id
                        if status_callback: status_callback(node_id, "running")
                        last_event_time = time.time()

                is_idle = not self.active_tasks
                has_pending_data = any(any(q) for queues in self.input_queues.values() for q in queues.values())
                
                if is_idle and not has_pending_data:
                    print("Execution finished (no active tasks and no pending data).")
                    break
                
                if time.time() - last_event_time > self.timeout:
                    if is_idle and has_pending_data:
                         print(f"Deadlock detected? Pending data exists but no nodes ready. Timeout {self.timeout}s reached.")
                         break
                    elif not is_idle:

                        pass

    def _distribute_outputs(self, source_node_id: str, outputs: Dict[str, Any]):
        """
        Передает результаты выполнения узла в очереди следующих узлов.
        """
        if not outputs:
            return

        outgoing = self.graph.get_outgoing_links(source_node_id)
        for link in outgoing:
            port_name = link["from_output"]
            target_node = link["to_node"]
            target_input = link["to_input"]
            
            if port_name in outputs:
                value = outputs[port_name]
                self.input_queues[target_node][target_input].append(value)

def _execute_node_wrapper(node, inputs):
    """
    Функция-обертка для запуска в отдельном процессе.
    """
    time.sleep(3.0)
    return node.execute(**inputs), node

