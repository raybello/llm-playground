from dataclasses import dataclass
from enum import Enum
from typing import  Optional


class ExecutionMode(Enum):
    """Execution mode for the engine."""

    SEQUENTIAL = "sequential"
    THREAD = "thread"


@dataclass
class ExecutionTrace:
    """Trace data for a single node execution."""

    node_name: str
    node_type: str
    start_time: float
    end_time: float
    duration: float
    level: int
    thread_id: str
    success: bool = True
    error: Optional[str] = None

    @property
    def relative_start(self) -> float:
        """Start time relative to execution start."""
        return self.start_time

    @property
    def relative_end(self) -> float:
        """End time relative to execution start."""
        return self.end_time


@dataclass
class NodeMetrics:
    """Metrics for node execution."""

    execution_count: int = 0
    total_execution_time: float = 0.0
    last_execution_time: float = 0.0
    error_count: int = 0

    def record_execution(self, duration: float):
        self.execution_count += 1
        self.total_execution_time += duration
        self.last_execution_time = duration

    def record_error(self):
        self.error_count += 1

    @property
    def avg_execution_time(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.total_execution_time / self.execution_count
