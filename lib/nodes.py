import logging
import random
import time
from typing import Dict, Any, List, Set, Optional, Callable
from lib.node import *


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NodeRegistry:
    """Registry for node definitions with versioning support."""

    _registry: Dict[str, Dict[str, NodeDefinition]] = (
        {}
    )  # type -> version -> definition
    _latest_versions: Dict[str, str] = {}  # type -> latest version

    @classmethod
    def register(cls, definition: NodeDefinition, version: str = "1.0.0"):
        """Register a node definition with version."""
        type_name = definition.type_name

        if type_name not in cls._registry:
            cls._registry[type_name] = {}
            cls._latest_versions[type_name] = version

        cls._registry[type_name][version] = definition

        # Update latest version (simple string comparison)
        if version > cls._latest_versions[type_name]:
            cls._latest_versions[type_name] = version

        logger.info(f"Registered {type_name} v{version}")

    @classmethod
    def create_definition(
        cls, type_name: str, version: Optional[str] = None
    ) -> NodeDefinition:
        """Create a node definition, optionally specifying version."""
        if type_name not in cls._registry:
            raise ValueError(f"Unknown node type: {type_name}")

        version = version or cls._latest_versions[type_name]

        if version not in cls._registry[type_name]:
            raise ValueError(f"Version {version} not found for {type_name}")

        return cls._registry[type_name][version]

    @classmethod
    def list_types(cls) -> List[str]:
        """List all registered node types."""
        return list(cls._registry.keys())


class ConstDefinition(NodeDefinition):
    type_name = "CONST"
    num_inputs = 0
    num_outputs = 1

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Const nodes do not compute—they're set directly in NodeInstance.
        time.sleep(2)
        return {}


class AddDefinition(NodeDefinition):
    type_name = "ADD"
    num_inputs = 2
    num_outputs = 1
    estimated_duration_ms = 10

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        time.sleep(random.randrange(0, 10) * 0.01)
        return {"output1": inputs["input1"] + inputs["input2"]}


class MultiplyDefinition(NodeDefinition):
    type_name = "MULTIPLY"
    num_inputs = 2
    num_outputs = 1
    is_expensive = True
    estimated_duration_ms = 50

    def compute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Simulate expensive computation
        time.sleep(random.randrange(0, 10) * 0.01)
        return {"output1": inputs["input1"] * inputs["input2"]}


# Register definitions
NodeRegistry.register(ConstDefinition(), "1.0.0")
NodeRegistry.register(AddDefinition(), "1.0.0")
NodeRegistry.register(MultiplyDefinition(), "1.0.0")
