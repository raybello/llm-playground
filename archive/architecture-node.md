``` mermaid
sequenceDiagram 
    autonumber

    User->>NodeEditor: Create Node ❌
    Note over User,NodeEditor: GUI Interaction <br/>Add node to graph

    User->>NodeEditor: Create Edge ❌
    Note over User,NodeEditor: GUI Interaction <br/>Add edge to graph

    NodeEditor->>ExecEngine: Execute Nodes ❌
    Note over NodeEditor,ExecEngine: Iterate over nodes <br/>after Topological Sort


    loop NodeInputs Ready 
        ExecEngine->>ExecEngine: Execute node function ❌
    end


```

# Legend

- ❌ - Not implemented
- ✅ - Completed & Implemented
