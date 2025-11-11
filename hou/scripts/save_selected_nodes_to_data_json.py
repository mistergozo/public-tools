import os, json

nodes = hou.selectedItems()

data = hou.data.itemsAsData(nodes, position=False)


json_path = hou.ui.selectFile(
    start_directory = hou.getenv("HIP"),
    title = "Save Nodes to JSON",
    pattern = "*.json"
)

if not json_path.endswith(".json"):
    json_path += ".json"

if json_path:
    with open(json_path, "w") as json_file:
        json.dump(data, json_file, indent=4)


    
