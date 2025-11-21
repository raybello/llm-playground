import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport(title="Node Calculator", width=900, height=600)

# Store node values
node_values = {}


def print_me(sender, app_data):
    print(f"Menu Item: {sender} {app_data}")


def update_addition_node(sender, app_data):
    """Callback to update addition node sum when input changes."""
    # app_data is the new value of the input
    node_values[sender] = app_data

    # Get input values for addition node
    input1 = node_values.get("add_input_1", 0)
    input2 = node_values.get("add_input_2", 0)

    # Update addition node output
    dpg.set_value("add_output", input1 + input2)


def create_integer_node(label, pos, tag):
    """Creates an integer input node with output."""
    with dpg.node(label=label, pos=pos, tag=tag):
        with dpg.node_attribute():
            dpg.add_input_int(
                label="Value",
                width=150,
                default_value=0,
                callback=update_addition_node,
                tag=f"{tag}_value",
            )
        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text(label="Output", tag=f"{tag}_output")
            node_values[f"{tag}_output"] = 0


def create_addition_node(pos):
    """Creates an addition node with 2 inputs and 1 output."""
    with dpg.node(label="Addition", pos=pos, tag="addition_node"):
        with dpg.node_attribute():
            dpg.add_input_int(
                label="Input 1",
                width=150,
                callback=update_addition_node,
                tag="add_input_1",
            )
        with dpg.node_attribute():
            dpg.add_input_int(
                label="Input 2",
                width=150,
                callback=update_addition_node,
                tag="add_input_2",
            )
        with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text(label="Sum", tag="add_output")
            node_values["add_output"] = 0


with dpg.window(label="Node Calculator", tag="primary_window"):
    with dpg.menu_bar():
        with dpg.menu(label="File"):
            with dpg.menu(label="Settings"):
                dpg.add_checkbox(label="Pick Me", callback=print_me)
                dpg.add_menu_item(label="Setting 1", callback=print_me, check=True)
                dpg.add_menu_item(label="Setting 2", callback=print_me, check=True)

        with dpg.menu(label="Nodes"):
            dpg.add_menu_item(label="Add Basic Node", callback=print_me)
            
    with dpg.node_editor(
        minimap=True, minimap_location=dpg.mvNodeMiniMap_Location_BottomRight
    ):
        # Create integer nodes
        create_integer_node("Integer 1", pos=[50, 50], tag="int_node_1")
        create_integer_node("Integer 2", pos=[50, 200], tag="int_node_2")

        # Create addition node
        create_addition_node(pos=[400, 100])

        # Optional: pre-link nodes (for visuals, not functional)
        # dpg.add_node_link("int_node_1_value", "add_input_1")
        # dpg.add_node_link("int_node_2_value", "add_input_2")

dpg.setup_dearpygui()
dpg.set_primary_window("primary_window", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
