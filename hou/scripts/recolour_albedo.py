import hou
import OpenImageIO as oiio
import numpy as np
from PySide6.QtWidgets import QApplication # hou_version >= 21.0 

def copy_to_houdini_clipboard(text):
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    app.clipboard().setText(text)


def average_color_aces(image_path,
                       src_space="Output - sRGB",
                       dst_space="ACES - ACEScg"):
    """
    Compute the average color of an image, converting from the
    display/output space (e.g. Output - sRGB) into ACEScg using OCIO.
    """
    buf_in = oiio.ImageBuf(image_path)
    if not buf_in.initialized:
        raise RuntimeError(f"Could not load image: {image_path}")

    buf_lin = oiio.ImageBuf()

    # OCIO conversion (uses $OCIO automatically)
    ok = oiio.ImageBufAlgo.colorconvert(buf_lin, buf_in, src_space, dst_space)
    if not ok:
        raise RuntimeError(f"Color conversion failed: {oiio.geterror()}")

    # Compute per-channel averages in ACEScg (linear)
    stats = oiio.ImageBufAlgo.computePixelStats(buf_lin)
    avg = tuple(float(c) for c in stats.avg[:3])

    return avg


result = hou.ui.selectFile(
    start_directory = hou.getenv('HIP'),
    title = "Read Image",
    chooser_mode = hou.fileChooserMode.Read
)
if result:
    path = hou.text.expandString(result)
else:
    raise hou.OperationInterrupted


choice = hou.ui.displayMessage(
    "Select the color space of the image:",
    buttons=("Raw", "Output - sRGB", "Cancel"),
    default_choice=0, close_choice=2)

if choice == 2:
    raise hou.OperationInterrupted

colorspace = 'Output - sRGB' if choice == 1 else 'Raw'
color = average_color_aces(path, src_space=colorspace)

if color:
    text = f"{color[0]:.4f} {color[1]:.4f} {color[2]:.4f}"
    copy_to_houdini_clipboard(text)
    hou.ui.displayMessage(f"Average color copied to clipboard:\n{text}")
