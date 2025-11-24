from typing import Dict, Any, List, Set, Optional
from enum import Enum
import pickle
import uuid
import threading

from lib.metrics import *


class PortDirection(Enum):
    INPUT = 0
    OUTPUT = 1


class PortType(Enum):
    STR = str
    NUM = int
    FLT = float
    DCT = dict


class Port(object):
    def __init__(
        self,
        name: str,
        direction: PortDirection,
        port_type: PortType,
        val: PortType = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.direction = direction
        self.port_type = port_type
        self.val = val


class NodeDefinition(object):
    num_inputs = 0
    num_outputs = 0

    def __init__(
        self,
        name: str = "BASE",
        is_expensive: bool = False,
        is_io_bound: bool = False,
        duration_ms: int = 100,
    ):
        self.name = name
        self.is_expensive = is_expensive
        self.is_io_bound = is_io_bound
        self.duration_ms = duration_ms

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclasses to implement logic."""
        raise NotImplementedError()

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate inputs before execution."""
        return len(inputs) == self.num_inputs

    def serialize(self) -> bytes:
        """Serialize for distributed execution."""
        return pickle.dumps(self)


class NodeInstance:
    """Runtime instance with wiring, state, and execution metadata."""

    def __init__(
        self, name: str, definition: NodeDefinition
    ):
        self.name = name
        self.node_id = str(uuid.uuid4())  # Unique identifier
        self.definition = definition

        # inputN → (source_node, source_output_name)
        self.inputs: Dict[str, Any] = {}

        # outputN → computed values
        self.outputs: Dict[str, Any] = {}

        # reverse dependency graph (children needing this output)
        self.children: List["NodeInstance"] = []

        # parent nodes (dependencies)
        self.parents: Set[NodeInstance] = set()

        # flag for incremental execution
        self.is_dirty = True

        # lock for thread-safe output updates
        self.lock = threading.Lock()

        # Execution metrics
        self.metrics = NodeMetrics()

        # Error handling
        self.last_error: Optional[Exception] = None
        self.retry_count = 0
        self.max_retries = 3

    def input_name(self, index: int) -> str:
        return f"input{index}"

    def output_name(self, index: int) -> str:
        return f"output{index}"

    def set_input(
        self, input_index: int, src_node: "NodeInstance", src_output_index: int
    ):
        input_key = self.input_name(input_index)
        output_key = src_node.output_name(src_output_index)
        self.inputs[input_key] = (src_node, output_key)

        # Build dependency graph
        src_node.children.append(self)
        self.parents.add(src_node)

    def resolve_inputs(self) -> Dict[str, Any]:
        """Resolve inputs with validation."""
        resolved = {}
        for input_name, (src_node, src_output_name) in self.inputs.items():
            if src_output_name not in src_node.outputs:
                raise ValueError(
                    f"Output {src_output_name} not available from {src_node.name}"
                )
            resolved[input_name] = src_node.outputs[src_output_name]
        return resolved

    def to_json(self) -> Dict[str, Any]:
        """Serialize node state to JSON (for persistence/debugging)."""
        return {
            "name": self.name,
            "node_id": self.node_id,
            "type": self.definition.type_name,
            "outputs": self.outputs,
            "is_dirty": self.is_dirty,
            "metrics": {
                "execution_count": self.metrics.execution_count,
                "avg_execution_time": self.metrics.avg_execution_time,
                "error_count": self.metrics.error_count,
            },
        }

    def __repr__(self):
        return f"<NodeInstance {self.name}>"

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        return isinstance(other, NodeInstance) and self.node_id == other.node_id
