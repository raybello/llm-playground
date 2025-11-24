from lib.execute import *

if __name__ == "__main__":

    # Create a more complex graph to demonstrate parallelization
    constA = NodeInstance("ConstA", NodeRegistry.create_definition("CONST"))
    constA.outputs["output1"] = 10

    constB = NodeInstance("ConstB", NodeRegistry.create_definition("CONST"))
    constB.outputs["output1"] = 4

    constC = NodeInstance("ConstC", NodeRegistry.create_definition("CONST"))
    constC.outputs["output1"] = 3

    constD = NodeInstance("ConstD", NodeRegistry.create_definition("CONST"))
    constD.outputs["output1"] = 10

    add1 = NodeInstance("Add1", NodeRegistry.create_definition("ADD"))
    add1.set_input(1, constA, 1)
    add1.set_input(2, constB, 1)

    multiply1 = NodeInstance(
        "Multiply1", NodeRegistry.create_definition("MULTIPLY")
    )
    multiply1.set_input(1, constC, 1)
    multiply1.set_input(2, constD, 1)

    add2 = NodeInstance("Add2", NodeRegistry.create_definition("ADD"))
    add2.set_input(1, add1, 1)
    add2.set_input(2, multiply1, 1)

    nodes = [constA, constB, constC, constD, add1, multiply1, add2]

    # Run execution engine with ThreadPoolExecutor (FIXED)
    engine = ExecutionEngine(
        nodes,
        max_workers=4,
        mode=ExecutionMode.THREAD,  # Changed from PROCESS to THREAD
        # mode=ExecutionMode.SEQUENTIAL,  # Changed from PROCESS to THREAD
        enable_checkpointing=False,
        enable_profiling=True,
    )

    stats = engine.run()

    # Print execution statistics
    print("\n" + "=" * 60)
    print("EXECUTION STATISTICS")
    print("=" * 60)
    print(f"Total time: {stats['total_execution_time']:.3f}s")
    print(f"Levels: {stats['level_count']}")
    print(f"\nNode Statistics:")
    for node_stat in stats["node_stats"]:
        print(
            f"  {node_stat['name']}: {node_stat['execution_count']} exec, "
            f"{node_stat['avg_time_ms']:.2f}ms avg"
        )

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Add1 result: {add1.outputs['output1']} (10 + 4)")
    print(f"Multiply1 result: {multiply1.outputs['output1']} (3 * 10)")
    print(f"Add2 result: {add2.outputs['output1']} (14 + 30)")

    # Export graph for debugging
    engine.export_graph("execution_graph.json")
    print("\nGraph exported to execution_graph.json")

    # Generate execution profile visualization
    engine.plot_execution_profile("execution_profile.png")
    print("Execution profile chart saved to execution_profile.png")
