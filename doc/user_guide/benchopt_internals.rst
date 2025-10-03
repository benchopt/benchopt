.. _benchopt_internals:

Benchopt internals
==================


.. mermaid::
    :zoom:

    flowchart LR
        subgraph "`**Dataset**`"
            D1("get_data")
        end

        D1 -.-> O1

        subgraph objective ["`**Objective**`"]

            O1("pre hooks") --> O2("set_data")
            O2 --> O3("get_objective")
            O4("evaluate_result")

        end

        O3 -.-> S1

        subgraph solver ["`**Solver**`"]
    
            S1("pre hooks") --> S2("set_objective")
            S2("set_objective") --> S3("run")
            S3 --> S4("get_result")

        end

        S4 <-.-> O4
