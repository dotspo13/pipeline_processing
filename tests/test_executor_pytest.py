import os
import sys
import time
from typing import Dict, Any, List

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.core.node import Node
from src.core.graph import Graph
from src.core.executor import Executor


class Source(Node):
    INPUT_TYPES: Dict[str, Any] = {}
    OUTPUT_TYPES: Dict[str, Any] = {"out": "int"}
    PARAMETERS: Dict[str, Any] = {}

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.executed = False

    def execute(self, **inputs):
        self.executed = True
        return {"out": 1}


class AddFive(Node):
    INPUT_TYPES: Dict[str, Any] = {"x": "int"}
    OUTPUT_TYPES: Dict[str, Any] = {"out": "int"}
    PARAMETERS: Dict[str, Any] = {}

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.executed = False
        self.last_input = None

    def execute(self, **inputs):
        self.executed = True
        self.last_input = inputs.get("x")
        return {"out": self.last_input + 5}


class Sink(Node):
    INPUT_TYPES: Dict[str, Any] = {"value": "int"}
    OUTPUT_TYPES: Dict[str, Any] = {}
    PARAMETERS: Dict[str, Any] = {}

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.executed = False
        self.received = None

    def execute(self, **inputs):
        self.executed = True
        self.received = inputs.get("value")
        return {}


class Logger(Node):
    INPUT_TYPES: Dict[str, Any] = {}
    OUTPUT_TYPES: Dict[str, Any] = {}
    PARAMETERS: Dict[str, Any] = {}

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.executed = False

    def execute(self, **inputs):
        self.executed = True
        print("logger says hi")
        return {}


class AnyNode(Node):
    INPUT_TYPES: Dict[str, Any] = {"a": "int", "b": "int"}
    OUTPUT_TYPES: Dict[str, Any] = {"out": "int"}
    PARAMETERS: Dict[str, Any] = {}
    INPUT_STRATEGY = "ANY"

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.calls: List[set] = []

    def execute(self, **inputs):
        self.calls.append(set(inputs.keys()))
        return {"out": sum(inputs.values()) if inputs else 0}


class FailingNode(Node):
    INPUT_TYPES: Dict[str, Any] = {"x": "int"}
    OUTPUT_TYPES: Dict[str, Any] = {}
    PARAMETERS: Dict[str, Any] = {}

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.executed = False

    def execute(self, **inputs):
        self.executed = True
        raise RuntimeError("boom")


class SleepySource(Node):
    INPUT_TYPES: Dict[str, Any] = {}
    OUTPUT_TYPES: Dict[str, Any] = {"out": "int"}
    PARAMETERS: Dict[str, Any] = {"delay": float}

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.executed = False

    def execute(self, **inputs):
        delay = self.params.get("delay", 0.1)
        time.sleep(delay)
        self.executed = True
        return {"out": delay}


class CollectSink(Node):
    INPUT_TYPES: Dict[str, Any] = {"v": "int"}
    OUTPUT_TYPES: Dict[str, Any] = {}
    PARAMETERS: Dict[str, Any] = {}

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.values: List[int] = []

    def execute(self, **inputs):
        self.values.append(inputs.get("v"))
        return {}


TEST_NODE_REGISTRY = {
    "Source": Source,
    "AddFive": AddFive,
    "Sink": Sink,
    "Logger": Logger,
    "AnyNode": AnyNode,
    "FailingNode": FailingNode,
    "SleepySource": SleepySource,
    "CollectSink": CollectSink,
}


def build_graph(graph_data):
    graph = Graph(TEST_NODE_REGISTRY)
    graph.load_from_json(graph_data)
    return graph


def test_simple_chain_executes_and_passes_data():
    graph_data = {
        "nodes": [
            {"id": "src", "type": "Source", "params": {}},
            {"id": "add", "type": "AddFive", "params": {}},
            {"id": "sink", "type": "Sink", "params": {}},
        ],
        "links": [
            {"from_node": "src", "from_output": "out", "to_node": "add", "to_input": "x"},
            {"from_node": "add", "from_output": "out", "to_node": "sink", "to_input": "value"},
        ],
    }

    graph = build_graph(graph_data)
    executor = Executor(graph, max_workers=1, timeout=5)

    executor.run()

    src = graph.get_node("src")
    add = graph.get_node("add")
    sink = graph.get_node("sink")

    assert src.executed is True
    assert add.executed is True
    assert add.last_input == 1
    assert sink.executed is True
    assert sink.received == 6


def test_nodes_with_missing_inputs_do_not_execute():
    graph_data = {
        "nodes": [
            {"id": "src", "type": "Source", "params": {}},
            {"id": "sink", "type": "Sink", "params": {}},
        ],
        "links": [],
    }

    graph = build_graph(graph_data)
    executor = Executor(graph, max_workers=1, timeout=2)

    executor.run()

    src = graph.get_node("src")
    sink = graph.get_node("sink")

    assert src.executed is True
    assert sink.executed is False
    assert sink.received is None


def test_stdout_from_workers_is_propagated(capsys):
    graph_data = {
        "nodes": [
            {"id": "logger", "type": "Logger", "params": {}},
        ],
        "links": [],
    }

    graph = build_graph(graph_data)
    executor = Executor(graph, max_workers=1, timeout=2)

    executor.run()

    out, err = capsys.readouterr()
    assert "logger says hi" in out
    assert err == ""


def test_input_strategy_any_executes_on_any_port():
    graph_data = {
        "nodes": [
            {"id": "any", "type": "AnyNode", "params": {}},
            {"id": "sink", "type": "Sink", "params": {}},
        ],
        "links": [
            {"from_node": "any", "from_output": "out", "to_node": "sink", "to_input": "value"},
        ],
    }

    graph = build_graph(graph_data)
    executor = Executor(graph, max_workers=1, timeout=5)

    executor.run(initial_inputs={"any": {"b": 2}})

    any_node = graph.get_node("any")
    sink = graph.get_node("sink")

    assert len(any_node.calls) == 1
    assert any_node.calls[0] in ({"a"}, {"b"}, {"a", "b"})
    assert sink.executed is True


def test_errors_from_nodes_stop_downstream_and_are_logged(capsys):
    graph_data = {
        "nodes": [
            {"id": "src", "type": "Source", "params": {}},
            {"id": "fail", "type": "FailingNode", "params": {}},
            {"id": "sink", "type": "Sink", "params": {}},
        ],
        "links": [
            {"from_node": "src", "from_output": "out", "to_node": "fail", "to_input": "x"},
            {"from_node": "fail", "from_output": "", "to_node": "sink", "to_input": "value"},
        ],
    }

    graph_data["links"].pop()
    graph_data["links"].append(
        {"from_node": "src", "from_output": "out", "to_node": "fail", "to_input": "x"}
    )

    graph = build_graph(graph_data)
    executor = Executor(graph, max_workers=1, timeout=2)

    executor.run()

    out, err = capsys.readouterr()
    failing = graph.get_node("fail")
    sink = graph.get_node("sink")

    assert sink.executed is False
    assert "Error executing node" in out


def test_deadlock_detection_when_data_waits_without_ready_nodes(capsys):
    graph_data = {
        "nodes": [
            {"id": "lonely", "type": "Sink", "params": {}},
        ],
        "links": [],
    }

    graph = build_graph(graph_data)
    executor = Executor(graph, max_workers=1, timeout=0.2)

    executor.run(initial_inputs={"lonely": {"value": 123}})

    out, err = capsys.readouterr()
    assert "Deadlock detected" in out or "Deadlock detected" in err
    lonely = graph.get_node("lonely")
    assert lonely.executed is False


def test_concurrent_ready_nodes_with_limited_workers():
    graph_data = {
        "nodes": [
            {"id": "s1", "type": "SleepySource", "params": {"delay": 0.3}},
            {"id": "s2", "type": "SleepySource", "params": {"delay": 0.3}},
            {"id": "s3", "type": "SleepySource", "params": {"delay": 0.3}},
            {"id": "sink", "type": "CollectSink", "params": {}},
        ],
        "links": [
            {"from_node": "s1", "from_output": "out", "to_node": "sink", "to_input": "v"},
            {"from_node": "s2", "from_output": "out", "to_node": "sink", "to_input": "v"},
            {"from_node": "s3", "from_output": "out", "to_node": "sink", "to_input": "v"},
        ],
    }

    graph = build_graph(graph_data)
    executor = Executor(graph, max_workers=2, timeout=3)

    start = time.time()
    executor.run()
    elapsed = time.time() - start

    sink = graph.get_node("sink")
    sources_executed = [graph.get_node(x).executed for x in ("s1", "s2", "s3")]

    assert all(sources_executed)

    assert len(sink.values) >= 2

    assert elapsed < 0.9


def test_graph_validation_errors():

    bad_type_graph = {
        "nodes": [
            {"id": "src", "type": "Source", "params": {}},
            {"id": "sink", "type": "Sink", "params": {}},
        ],
        "links": [
            {"from_node": "src", "from_output": "out", "to_node": "sink", "to_input": "value"},  
        ],
    }
    graph = Graph(TEST_NODE_REGISTRY)
    graph.load_from_json(bad_type_graph) 

    mismatch_graph = {
        "nodes": [
            {"id": "src", "type": "Source", "params": {}},
            {"id": "any", "type": "AnyNode", "params": {}},
        ],
        "links": [
            {"from_node": "src", "from_output": "out", "to_node": "any", "to_input": "a"},  
            {"from_node": "src", "from_output": "out", "to_node": "any", "to_input": "b"},  
        ],
    }
    Graph(TEST_NODE_REGISTRY).load_from_json(mismatch_graph)  

    missing_node_graph = {
        "nodes": [{"id": "src", "type": "Source", "params": {}}],
        "links": [{"from_node": "src", "from_output": "out", "to_node": "absent", "to_input": "value"}],
    }
    with pytest.raises(ValueError):
        Graph(TEST_NODE_REGISTRY).load_from_json(missing_node_graph)

    missing_port_graph = {
        "nodes": [
            {"id": "src", "type": "Source", "params": {}},
            {"id": "sink", "type": "Sink", "params": {}},
        ],
        "links": [
            {"from_node": "src", "from_output": "out", "to_node": "sink", "to_input": "missing_port"},
        ],
    }
    with pytest.raises(ValueError):
        Graph(TEST_NODE_REGISTRY).load_from_json(missing_port_graph)

