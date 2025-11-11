import os, json
import toolutils

pane = toolutils.activePane(kwargs)
if not isinstance(pane, hou.NetworkEditor):
    pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    if pane is None:
       hou.ui.displayMessage(
               'Cannot create node: cannot find any network pane')
       sys.exit(0)
else: # We're creating this tool from the TAB menu inside a network editor
    pane_node = pane.pwd()
    #print(pane_node.path())

pos = pane.cursorPosition()

json_path = hou.ui.selectFile(
    start_directory = hou.getenv('HIP'),
    title = "Read JSON data",
    pattern = "*.json",
    chooser_mode = hou.fileChooserMode.Read
)


if json_path:
    
    with open(hou.text.expandString(json_path), "r") as json_file:
        nodedata = json.load(json_file)
    
    
    d = hou.data.createItemsFromData(parent=pane_node, data=nodedata)
    k, v = next(iter(d.items()))
    
    v.setPosition(pos)

