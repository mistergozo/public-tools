"""
husk_submit.py – Lightweight Houdini → Deadline submitter for Husk2Deadline.

Call from an HDA / shelf / button:

    import husk_submit
    husk_submit.submit(kwargs["node"])

Only the options you actually need are exposed.  No dependency on the
official Deadline Houdini submission modules.
"""

from __future__ import print_function

import os
import sys
import json
import getpass
import tempfile
import time
import traceback

import hou


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def submit(node):
    """
    Submit a Husk2Deadline job from a Houdini node that has the expected parameters.
    Returns the Deadline job ID (string) or None on failure.
    """
    try:
        job_info, plugin_info = _build_info_files(node)
        job_id = _submit_to_deadline(job_info, plugin_info)
        if job_id:
            hou.ui.setStatusMessage(
                "Submitted Husk2Deadline job: {}".format(job_id),
                severity=hou.severityType.Message,
            )
            print("Husk2Deadline → Deadline job ID: {}".format(job_id))
        return job_id
    except Exception as exc:
        msg = "Husk2Deadline submission failed:\n{}".format(traceback.format_exc())
        print(msg)
        hou.ui.displayMessage(msg, title="Husk2Deadline Submit", severity=hou.severityType.Error)
        return None


# ---------------------------------------------------------------------------
# Frame list builder (F/M/L + increment)
# ---------------------------------------------------------------------------
def _build_frames(start, end, inc=1, fml_only=False):
    """
    Return a Deadline-friendly Frames string.

    Logic (as requested):

    fmlonly ON:
      - frameinc == 0  → only First / Mid / Last
      - frameinc == 1  → full continuous range  (F/M/L already included)
      - frameinc  > 1  → stepped + force F/M/L

    fmlonly OFF:
      - frameinc == 0  → full continuous range (frangex-frangey)
      - frameinc == 1  → full continuous range
      - frameinc  > 1  → pure stepped (no forced F/M/L)
    """
    if start > end:
        start, end = end, start

    if start == end:
        return str(start)

    mid = start + (end - start) // 2
    inc = max(0, int(inc))          # never negative

    # ---------- fmlonly ON ----------
    if fml_only:
        if inc == 0:
            # pure F / M / L
            frames = sorted({start, mid, end})
            return ",".join(str(f) for f in frames)

        if inc == 1:
            # full range (F/M/L already present)
            return "{}-{}".format(start, end)

        # stepped + force F/M/L
        frames = set(range(start, end + 1, inc))
        frames.update((start, mid, end))
        return ",".join(str(f) for f in sorted(frames))

    # ---------- fmlonly OFF ----------
    if inc <= 1:
        # continuous full range
        return "{}-{}".format(start, end)

    # pure stepped – use Deadline's compact x syntax
    return "{}-{}x{}".format(start, end, inc)


# ---------------------------------------------------------------------------
# Build the two temporary .job files Deadline expects
# ---------------------------------------------------------------------------
def _build_info_files(node):
    user = getpass.getuser()
    timestamp = time.strftime("%y-%m-%d %H:%M:%S")

    # ---- required / common parameters (adjust names to match your HDA) ----
    job_name       = _parm(node, "jobname", "Untitled")
    comment        = _parm(node, "comment", "submitted by <{}> {}".format(user, timestamp))
    pool           = _parm(node, "pool", "")
    secondary_pool = _parm(node, "secondarypool", "")
    group          = _parm(node, "group", "none")
    priority       = _parm_int(node, "priority", 50)
    chunk_size     = _parm_int(node, "framespertask", 1)
    suspended      = _parm_bool(node, "jobsuspended", False)

    # Frame range (vector2-style x/y or separate ints)
    start = _parm_int(node, "frangex", int(hou.frame()))
    end   = _parm_int(node, "frangey", int(hou.frame()))

    # New controls
    fml_only = _parm_bool(node, "fmlonly", False)
    frame_inc = _parm_int(node, "frameinc", 1)   # 0 is meaningful

    frames = _build_frames(start, end, frame_inc, fml_only)

    # USD + render settings
    usd_file       = _parm(node, "usdfile", "")
    engine         = _parm(node, "engine", "karma")
    settings_prim  = _parm(node, "primpath", "/Render/rendersettings")
    render_pass    = _parm(node, "renderpass", "")
    camera         = _parm(node, "camera", "")

    # Non-destructive resolution modifier
    res_x, res_y = _get_effective_resolution(node)
    resolution   = "{} {}".format(res_x, res_y).strip() if res_x and res_y else ""

    extras         = _parm(node, "extras", "")
    log_level      = _parm_int(node, "usdloglevel", 2)

    # Output image (supports $F4 etc. – the plugin expands the token)
    outdir   = _parm(node, "outdir", "")
    imgname  = _parm(node, "imgname", "render")
    ver      = _parm_int(node, "ver", 1)
    ver_str  = "v{:02d}".format(ver)
    output_image = ""
    if outdir and imgname:
        output_image = "{}/{}/{}/{}.$F4.exr".format(outdir.rstrip("/\\"), imgname, ver_str, imgname)

    if not usd_file or not os.path.exists(usd_file):
        raise RuntimeError("USD file does not exist: {}".format(usd_file))

    # ---- Job Info ----
    job_lines = [
        "Plugin=Husk2Deadline",
        "Name={}".format(job_name),
        "Comment={}".format(comment),
        "Pool={}".format(pool),
        "SecondaryPool={}".format(secondary_pool),
        "Group={}".format(group),
        "Priority={}".format(priority),
        "Frames={}".format(frames),
        "ChunkSize={}".format(chunk_size),
        "OnJobComplete=Nothing",
    ]
    if suspended:
        job_lines.append("InitialStatus=Suspended")

    # Optional machine limit / blacklist etc. can be added here later

    # ---- Plugin Info ----
    plugin_lines = [
        "SceneFile={}".format(usd_file.replace("\\", "/")),
        "LogLevel={}".format(log_level),
        "Engine={}".format(engine),
        "RenderSettingsPrim={}".format(settings_prim),
        "RenderPass={}".format(render_pass),
        "Camera={}".format(camera),
        "Resolution={}".format(resolution),
        "OutImage={}".format(output_image.replace("\\", "/")),
        "Extras={}".format(extras),
    ]

    # Write temporary files
    tmp_dir = tempfile.gettempdir()
    job_info_path = os.path.join(tmp_dir, "husk2deadline_job_info.job")
    plugin_info_path = os.path.join(tmp_dir, "husk2deadline_plugin_info.job")

    with open(job_info_path, "w") as f:
        f.write("\n".join(job_lines) + "\n")

    with open(plugin_info_path, "w") as f:
        f.write("\n".join(plugin_lines) + "\n")

    return job_info_path, plugin_info_path


# ---------------------------------------------------------------------------
# Call deadlinecommand
# ---------------------------------------------------------------------------
def _submit_to_deadline(job_info, plugin_info):
    deadline_cmd = _find_deadline_command()
    if not deadline_cmd:
        raise RuntimeError(
            "Could not locate deadlinecommand. "
            "Set DEADLINE_PATH or ensure Deadline Client is installed."
        )

    # Prefer the official helper if it is already on sys.path
    try:
        from CallDeadlineCommand import CallDeadlineCommand
        result = CallDeadlineCommand([job_info, plugin_info])
    except ImportError:
        import subprocess
        proc = subprocess.Popen(
            [deadline_cmd, job_info, plugin_info],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = proc.communicate()
        if sys.version_info[0] >= 3 and isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        result = out

    # Extract JobID=…
    job_id = ""
    for line in result.splitlines():
        line = line.strip()
        if line.startswith("JobID="):
            job_id = line.split("=", 1)[1].strip()
            break

    print("----- Deadline submission result -----")
    print(result)
    print("--------------------------------------")
    return job_id or None


def _find_deadline_command():
    # 1. Environment variable (most common)
    deadline_bin = os.environ.get("DEADLINE_PATH", "")
    if deadline_bin:
        candidate = os.path.join(deadline_bin, "deadlinecommand")
        if os.path.isfile(candidate) or os.path.isfile(candidate + ".exe"):
            return candidate

    # 2. macOS shared path
    mac_path = "/Users/Shared/Thinkbox/DEADLINE_PATH"
    if os.path.exists(mac_path):
        with open(mac_path) as f:
            deadline_bin = f.read().strip()
        candidate = os.path.join(deadline_bin, "deadlinecommand")
        if os.path.isfile(candidate):
            return candidate

    # 3. Hope it is on PATH
    return "deadlinecommand"


# ---------------------------------------------------------------------------
# Resolution modifier (non-destructive)
# ---------------------------------------------------------------------------
def _nearest_even(value):
    """Round to nearest even integer (renderers prefer even dimensions)."""
    return int(round(float(value) / 2.0) * 2)


def _get_effective_resolution(node):
    """
    Compute the final (width, height) after applying resmodifier + resvalue.
    Base values always come from the current resolutionx / resolutiony parms.
    Returns (0, 0) if the base resolution is invalid.
    """
    rx = _parm(node, "resolutionx", "")
    ry = _parm(node, "resolutiony", "")

    try:
        base_w = float(rx) if rx else 0.0
        base_h = float(ry) if ry else 0.0
    except (TypeError, ValueError):
        return 0, 0

    if base_w <= 0 or base_h <= 0:
        return 0, 0

    mode = _parm(node, "resmodifier", "full").strip().lower()
    value = _parm_float(node, "resvalue", 1.0)

    # ---- Full ----
    if mode in ("", "full"):
        return _nearest_even(base_w), _nearest_even(base_h)

    # ---- Multiply (x) ----
    if mode in ("x", "multiply", "multiply (x)"):
        return _nearest_even(base_w * value), _nearest_even(base_h * value)

    aspect = base_w / base_h

    # ---- Preferred Height ----
    if mode in ("preferred height", "height"):
        h = value
        w = h * aspect
        return _nearest_even(w), _nearest_even(h)

    # ---- Preferred Width ----
    if mode in ("preferred width", "width"):
        w = value
        h = w / aspect
        return _nearest_even(w), _nearest_even(h)

    # fallback
    return _nearest_even(base_w), _nearest_even(base_h)


def _aspect_ratio_name(w, h):
    """
    Return a friendly name for common aspect ratios, or the raw ratio if unknown.
    Uses a small tolerance so 1918×1080 still counts as 16:9.
    """
    if h <= 0:
        return "?"
    r = w / float(h)

    # (target_ratio, name) – ordered from most specific / common
    known = [
        (1.0,    "1:1"),
        (1.25,   "5:4"),
        (1.333,  "4:3"),
        (1.5,    "3:2"),
        (1.6,    "16:10"),
        (1.777,  "16:9"),
        (1.85,   "1.85:1"),
        (2.0,    "2:1"),
        (2.35,   "2.35:1"),
        (2.39,   "2.39:1"),
        (2.40,   "2.40:1"),
        # vertical / portrait
        (0.5625, "9:16"),
        (0.75,   "3:4"),
        (0.8,    "4:5"),
    ]

    for target, name in known:
        if abs(r - target) < 0.012:          # ~1.2% tolerance
            return name

    return "{:.3f}".format(r)


def get_resolution_label(node):
    """
    Returns a human-readable string for a live label parm, e.g.:
        1920 × 1080   (2.07M px)   ·   16:9
    Safe to call from a Python expression or callback.
    """
    w, h = _get_effective_resolution(node)
    if w <= 0 or h <= 0:
        return "—  (invalid resolution)"

    pixels = w * h
    if pixels >= 1_000_000:
        px_str = "{:.2f}M px".format(pixels / 1_000_000.0)
    else:
        px_str = "{:,} px".format(pixels)

    aspect_name = _aspect_ratio_name(w, h)
    return "{} × {}   ({})   ·   {}".format(w, h, px_str, aspect_name)


# ---------------------------------------------------------------------------
# Tiny parameter helpers (safe defaults)
# ---------------------------------------------------------------------------
def _parm(node, name, default=""):
    p = node.parm(name)
    return p.evalAsString() if p else default


def _parm_int(node, name, default=0):
    p = node.parm(name)
    return int(p.eval()) if p else default


def _parm_float(node, name, default=0.0):
    p = node.parm(name)
    return float(p.eval()) if p else default


def _parm_bool(node, name, default=False):
    p = node.parm(name)
    return bool(p.eval()) if p else default
