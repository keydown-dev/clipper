# Use video workspaces as the CLI contract

Clipper commands operate primarily on named video workspaces rooted at `.clipper/{video}/` rather than passing individual artifact files between steps. This makes the staged workflow easier for humans and automation agents because each command can infer standard inputs and outputs from the workspace layout, while still allowing explicit video names or paths when needed. The trade-off is less ad hoc standalone-file flexibility, which is acceptable for v1 because the product goal is a coherent local-first pipeline with reliable, inspectable artifacts.
