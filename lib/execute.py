from lib.nodes import *
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import multiprocessing


class ExecutionEngine:
    """Production-ready execution engine with advanced features."""

    def __init__(
        self,
        nodes: List[NodeInstance],
        max_workers: int = None,
        mode: ExecutionMode = ExecutionMode.THREAD,
        enable_checkpointing: bool = False,
        checkpoint_callback: Optional[Callable] = None,
        enable_profiling: bool = True,
    ):
        self.nodes = nodes
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.mode = mode
        self.execution_order: List[List[NodeInstance]] = []
        self.enable_checkpointing = enable_checkpointing
        self.checkpoint_callback = checkpoint_callback
        self.enable_profiling = enable_profiling

        # Build node lookup for fast access
        self.node_lookup = {node.node_id: node for node in nodes}

        # Execution statistics
        self.total_execution_time = 0.0
        self.level_execution_times: List[float] = []
        self.execution_start_time = 0.0

        # Profiling data
        self.execution_traces: List[ExecutionTrace] = []
        self.traces_lock = threading.Lock()

    def topological_sort(self) -> List[List[NodeInstance]]:
        """
        Perform topological sort and group nodes by execution level.
        Nodes at the same level can be executed in parallel.

        Returns: List of levels, where each level is a list of nodes
                 that can execute in parallel.
        """
        # Calculate in-degree for each node
        in_degree = {node: len(node.parents) for node in self.nodes}

        # Find all nodes with no dependencies (in-degree = 0)
        queue = deque([node for node in self.nodes if in_degree[node] == 0])

        levels = []
        processed = 0

        while queue:
            # All nodes in current queue can execute in parallel
            current_level = list(queue)
            levels.append(current_level)
            queue.clear()
            processed += len(current_level)

            # Process all nodes in current level
            for node in current_level:
                # Reduce in-degree of children
                for child in node.children:
                    in_degree[child] -= 1
                    # If all dependencies satisfied, add to next level
                    if in_degree[child] == 0:
                        queue.append(child)

        # Check for cycles
        if processed < len(self.nodes):
            unprocessed = [n.name for n in self.nodes if in_degree[n] > 0]
            raise ValueError(
                f"Cycle detected in node graph. Unprocessed: {unprocessed}"
            )

        logger.info(
            f"Topological sort complete: {len(levels)} levels, {processed} nodes"
        )
        return levels

    def mark_dirty(self, node: NodeInstance):
        """Mark a node and its children dirty (incremental updates)."""
        if not node.is_dirty:
            node.is_dirty = True
            for child in node.children:
                self.mark_dirty(child)

    def execute_node(self, node: NodeInstance, level: int) -> NodeInstance:
        """Execute a single node with error handling and metrics."""
        start_time = time.time()
        thread_id = threading.current_thread().name
        success = True
        error_msg = None

        try:
            logger.info(f"Executing {node.name}")

            # Const nodes just have preset output1
            if node.definition.type_name != "CONST":
                resolved_inputs = node.resolve_inputs()

                # Validate inputs
                if not node.definition.validate_inputs(resolved_inputs):
                    raise ValueError(f"Invalid inputs for {node.name}")

                outputs = node.definition.compute(resolved_inputs)

                with node.lock:
                    node.outputs = outputs

            logger.info(f"Completed {node.name}: {node.outputs}")

            with node.lock:
                node.is_dirty = False
                node.retry_count = 0
                node.last_error = None

            # Record metrics
            end_time = time.time()
            duration = end_time - start_time
            node.metrics.record_execution(duration)

            # Checkpoint if enabled
            if self.enable_checkpointing and self.checkpoint_callback:
                self.checkpoint_callback(node)

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            node.metrics.record_error()
            success = False
            error_msg = str(e)

            with node.lock:
                node.last_error = e
                node.retry_count += 1

            logger.error(f"Error executing {node.name}: {e}")

            # Retry logic
            if node.retry_count < node.max_retries:
                logger.warning(
                    f"Retrying {node.name} (attempt {node.retry_count + 1}/{node.max_retries})"
                )
                return self.execute_node(node, level)
            else:
                logger.error(f"Max retries exceeded for {node.name}")
                raise

        # Record execution trace
        if self.enable_profiling:
            trace = ExecutionTrace(
                node_name=node.name,
                node_type=node.definition.type_name,
                start_time=start_time - self.execution_start_time,
                end_time=end_time - self.execution_start_time,
                duration=duration,
                level=level,
                thread_id=thread_id,
                success=success,
                error=error_msg,
            )
            with self.traces_lock:
                self.execution_traces.append(trace)

        return node

    def execute_level_parallel(self, level: List[NodeInstance], level_idx: int):
        """Execute all nodes in a level using either sequential or parallel execution."""
        dirty_nodes = [node for node in level if node.is_dirty]

        if not dirty_nodes:
            return

        level_start = time.time()

        if self.mode == ExecutionMode.SEQUENTIAL:
            # Sequential execution
            logger.info(f"Executing level with {len(dirty_nodes)} node(s) sequentially")
            completed = 0
            for node in dirty_nodes:
                try:
                    self.execute_node(node, level_idx)
                    completed += 1
                except Exception as e:
                    logger.error(f"Failed to execute {node.name}: {e}")
                    raise
        else:
            # Parallel execution with ThreadPoolExecutor
            logger.info(f"Executing level with {len(dirty_nodes)} node(s) in parallel")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.execute_node, node, level_idx): node
                    for node in dirty_nodes
                }

                completed = 0
                for future in as_completed(futures):
                    node = futures[future]
                    try:
                        future.result()
                        completed += 1
                    except Exception as e:
                        logger.error(f"Failed to execute {node.name}: {e}")
                        raise

        level_time = time.time() - level_start
        self.level_execution_times.append(level_time)
        logger.info(
            f"Level completed in {level_time:.3f}s ({completed}/{len(dirty_nodes)} nodes)"
        )

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics."""
        node_stats = []
        for node in self.nodes:
            node_stats.append(
                {
                    "name": node.name,
                    "type": node.definition.type_name,
                    "execution_count": node.metrics.execution_count,
                    "avg_time_ms": node.metrics.avg_execution_time * 1000,
                    "error_count": node.metrics.error_count,
                }
            )

        return {
            "total_execution_time": self.total_execution_time,
            "level_count": len(self.execution_order),
            "level_execution_times": self.level_execution_times,
            "node_stats": node_stats,
            "total_nodes": len(self.nodes),
            "execution_traces": self.execution_traces,
        }

    def run(self):
        """Run execution with comprehensive logging and metrics."""
        self.execution_start_time = time.time()
        execution_start = self.execution_start_time

        logger.info("=" * 60)
        logger.info("Starting execution engine")
        logger.info(f"Mode: {self.mode.value}, Max workers: {self.max_workers}")
        logger.info("=" * 60)

        # Compute execution order
        self.execution_order = self.topological_sort()

        logger.info(f"Execution plan ({len(self.execution_order)} levels):")
        for i, level in enumerate(self.execution_order):
            node_names = [node.name for node in level]
            logger.info(f"  Level {i}: {node_names}")

        # Execute each level
        for level_idx, level in enumerate(self.execution_order):
            logger.info(f"\n{'='*60}")
            logger.info(f"Executing Level {level_idx}")
            logger.info(f"{'='*60}")
            self.execute_level_parallel(level, level_idx)

        self.total_execution_time = time.time() - execution_start

        logger.info("\n" + "=" * 60)
        logger.info(f"Execution completed in {self.total_execution_time:.3f}s")
        logger.info("=" * 60)

        return self.get_execution_stats()

    def plot_execution_profile(self, output_file: str = "execution_profile.png"):
        """Generate execution profile visualization as a Gantt chart."""
        if not self.execution_traces:
            logger.warning("No execution traces available for profiling")
            return

        fig, ax = plt.subplots(figsize=(14, max(8, len(self.execution_traces) * 0.4)))

        # Define colors for different node types
        type_colors = {
            "CONST": "#3498db",  # Blue
            "ADD": "#2ecc71",  # Green
            "MULTIPLY": "#e74c3c",  # Red
            "BASE": "#95a5a6",  # Gray
        }

        # Sort traces by start time for better visualization
        sorted_traces = sorted(self.execution_traces, key=lambda t: t.start_time)

        # Create y-axis positions
        y_positions = {}
        current_y = 0

        for trace in sorted_traces:
            if trace.node_name not in y_positions:
                y_positions[trace.node_name] = current_y
                current_y += 1

        # Plot each execution trace as a horizontal bar
        for trace in sorted_traces:
            y_pos = y_positions[trace.node_name]
            color = type_colors.get(trace.node_type, "#95a5a6")

            # Add alpha for failed executions
            alpha = 0.4 if not trace.success else 0.8

            ax.barh(
                y_pos,
                trace.duration,
                left=trace.start_time,
                height=0.8,
                color=color,
                alpha=alpha,
                edgecolor="black",
                linewidth=0.5,
            )

            # Add duration label on the bar
            if trace.duration > 0.001:  # Only show label if bar is wide enough
                ax.text(
                    trace.start_time + trace.duration / 2,
                    y_pos,
                    f"{trace.duration*1000:.1f}ms",
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    color="white" if trace.duration > 0.02 else "black",
                )

        # Customize the plot
        ax.set_yticks(range(len(y_positions)))
        ax.set_yticklabels([name for name in y_positions.keys()])
        ax.set_xlabel("Time (seconds)", fontsize=12, fontweight="bold")
        ax.set_ylabel("Node Name", fontsize=12, fontweight="bold")
        ax.set_title(
            "Execution Profile - Parallel Node Execution Timeline",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )

        # Add grid for better readability
        ax.grid(True, axis="x", alpha=0.3, linestyle="--")
        ax.set_axisbelow(True)

        # Create legend
        legend_elements = [
            mpatches.Patch(color=color, label=node_type, alpha=0.8)
            for node_type, color in type_colors.items()
            if any(t.node_type == node_type for t in sorted_traces)
        ]
        ax.legend(
            handles=legend_elements,
            loc="lower right",
            title="Node Types",
            framealpha=0.5,
        )

        # Add execution summary text
        total_time = max(t.end_time for t in sorted_traces)
        summary_text = f"Total Execution Time: {total_time:.3f}s\n"
        summary_text += f"Nodes Executed: {len(sorted_traces)}\n"
        summary_text += (
            f"Parallelization: {self.mode.value} ({self.max_workers} workers)"
        )

        ax.text(
            0.02,
            0.98,
            summary_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        logger.info(f"Execution profile saved to {output_file}")
        plt.close()

    def export_graph(self, filepath: str):
        """Export graph structure to JSON for visualization/debugging."""
        graph_data = {"nodes": [node.to_json() for node in self.nodes], "edges": []}

        for node in self.nodes:
            for child in node.children:
                graph_data["edges"].append({"from": node.node_id, "to": child.node_id})

        with open(filepath, "w") as f:
            json.dump(graph_data, f, indent=2)

        logger.info(f"Graph exported to {filepath}")
