"""
husk_submit.py – Lightweight Houdini → Deadline submitter for Husk2Deadline
+ optional dependent HouRenderStatsOverlay job.

Call from an HDA / shelf / button:

    import husk_submit
    husk_submit.submit(kwargs["node"])                # main husk job (+ optional overlay)

    # or standalone overlay on already-rendered EXRs:
    husk_submit.submit_renderstats_overlay(kwargs["node"])

Only the options you actually need are exposed.  No dependency on the
official Deadline Houdini submission modules.
"""

from __future__ import print_function

import os
import re
import sys
import getpass
import tempfile
import time
import traceback

import hou


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
def submit(node):
    """
    Submit a Husk2Deadline job from a Houdini node that has the expected parameters.
    Optionally also submits a dependent HouRenderStatsOverlay job when the
    toggle `generate_renderstatsoverlay_job` is enabled.

    Returns the main Deadline job ID (string) or None on failure.
    """
    try:
        job_info, plugin_info = _build_husk_info_files(node)
        job_id = _submit_to_deadline(job_info, plugin_info)

        if not job_id:
            return None

        hou.ui.setStatusMessage(
            "Submitted Husk2Deadline job: {}".format(job_id),
            severity=hou.severityType.Message,
        )
        print("Husk2Deadline → Deadline job ID: {}".format(job_id))

        # Optional dependent overlay job
        if _parm_bool(node, "generate_renderstatsoverlay_job", False):
            overlay_id = _submit_dependent_overlay(node, job_id)
            if overlay_id:
                print("HouRenderStatsOverlay (dependent) → Deadline job ID: {}".format(overlay_id))
                hou.ui.setStatusMessage(
                    "Submitted Husk2Deadline + dependent overlay: {} → {}".format(job_id, overlay_id),
                    severity=hou.severityType.Message,
                )

        return job_id

    except Exception:
        msg = "Husk2Deadline submission failed:\n{}".format(traceback.format_exc())
        print(msg)
        hou.ui.displayMessage(msg, title="Husk2Deadline Submit", severity=hou.severityType.Error)
        return None


def submit_renderstats_overlay(node):
    """
    Standalone submitter for HouRenderStatsOverlay.
    Useful for already-rendered EXR sequences (no husk job required).

    Expected HDA parameters (most are optional and have sensible defaults):

        jobname, comment, pool, secondarypool, group, priority,
        framespertask, jobsuspended,
        frangex, frangey, fmlonly, frameinc,
        inputimage          (required – path with $F4 / #### tokens)
        outputimage         (optional)
        rs_mode, rs_align, rs_scale, rs_width, rs_edge, rs_margin,
        rs_colorspace, rs_template, rs_aov, rs_resize, rs_extras

    Returns the Deadline job ID or None.
    """
    try:
        job_info, plugin_info = _build_overlay_info_files(node, dependency_job_id=None)
        job_id = _submit_to_deadline(job_info, plugin_info)

        if job_id:
            hou.ui.setStatusMessage(
                "Submitted HouRenderStatsOverlay job: {}".format(job_id),
                severity=hou.severityType.Message,
            )
            print("HouRenderStatsOverlay → Deadline job ID: {}".format(job_id))
        return job_id

    except Exception:
        msg = "HouRenderStatsOverlay submission failed:\n{}".format(traceback.format_exc())
        print(msg)
        hou.ui.displayMessage(msg, title="RenderStats Overlay Submit", severity=hou.severityType.Error)
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
# Build info files for the main husk job
# ---------------------------------------------------------------------------
def _build_husk_info_files(node):
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

    # Frame range
    start = _parm_int(node, "frangex", int(hou.frame()))
    end   = _parm_int(node, "frangey", int(hou.frame()))
    fml_only  = _parm_bool(node, "fmlonly", False)
    frame_inc = _parm_int(node, "frameinc", 1)

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
    output_image = _get_husk_output_image(node)

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

    return _write_temp_job_files("husk2deadline", job_lines, plugin_lines)


# ---------------------------------------------------------------------------
# Dependent / standalone overlay job
# ---------------------------------------------------------------------------
def _submit_dependent_overlay(node, husk_job_id):
    """Build and submit a HouRenderStatsOverlay job that depends on the husk job."""
    job_info, plugin_info = _build_overlay_info_files(node, dependency_job_id=husk_job_id)
    return _submit_to_deadline(job_info, plugin_info)


def _build_overlay_info_files(node, dependency_job_id=None):
    """
    Shared builder used by both the dependent path and the standalone submitter.

    When called from the husk HDA (dependency_job_id is set) we derive the
    InputImage from the same outdir/imgname/ver logic.

    When called from a standalone overlay HDA we expect an explicit `inputimage` parm.
    """
    user = getpass.getuser()
    timestamp = time.strftime("%y-%m-%d %H:%M:%S")

    # ---- common job controls ----
    job_name = _parm(node, "jobname", "Untitled")
    if dependency_job_id:
        # make it obvious this is the overlay companion
        lower = job_name.lower()
        if (not lower.endswith("_stats")
                and not lower.endswith("_overlay")
                and not lower.endswith("renderstatsoverlay")):
            job_name = job_name + " :: renderstatsoverlay"

    comment        = _parm(node, "comment", "renderstats overlay – submitted by <{}> {}".format(user, timestamp))
    pool           = _parm(node, "pool", "")
    secondary_pool = _parm(node, "secondarypool", "")
    group          = _parm(node, "group", "none")
    priority       = _parm_int(node, "priority", 50)
    # overlay is very light – default to 1 frame per task is fine
    chunk_size     = _parm_int(node, "framespertask", 1)
    suspended      = _parm_bool(node, "jobsuspended", False)

    # Frame range (same logic as husk)
    start     = _parm_int(node, "frangex", int(hou.frame()))
    end       = _parm_int(node, "frangey", int(hou.frame()))
    fml_only  = _parm_bool(node, "fmlonly", False)
    frame_inc = _parm_int(node, "frameinc", 1)
    frames    = _build_frames(start, end, frame_inc, fml_only)

    # ---- Input / Output images ----
    if dependency_job_id:
        # Derive from the same paths the husk job will write
        input_image = _get_husk_output_image(node)
        if not input_image:
            raise RuntimeError(
                "Cannot create overlay job: husk output image path is empty "
                "(check outdir / imgname parms)."
            )
        # Optional explicit override, otherwise build the sibling-folder path
        output_image = _parm(node, "rso_outputimage", "")
        if not output_image:
            imgname = _parm(node, "imgname", "render")
            output_image = _build_overlay_output_path(input_image, imgname)
    else:
        # Standalone HDA – require explicit input
        input_image = _parm(node, "inputimage", "")
        if not input_image:
            raise RuntimeError("inputimage parameter is required for standalone overlay submission.")
        output_image = _parm(node, "outputimage", "")
        if not output_image:
            # Try to derive a sensible sibling path from the given input
            # Fall back to empty (tool default) only if we can't parse it.
            imgname = _parm(node, "imgname", "") or _guess_imgname_from_path(input_image)
            output_image = _build_overlay_output_path(input_image, imgname) if imgname else ""

    # ---- Overlay appearance (all optional – plugin has good defaults) ----
    # Note: user renamed the HDA parms from rs_* → rso_*
    mode        = _parm(node, "rso_mode", "overlay")
    align       = _parm(node, "rso_align", "bottomleft")
    scale       = _parm(node, "rso_scale", "1.0")
    # rso_width is a float parm on the HDA → append "%"
    stats_width = str(_parm(node, "rso_width", "30")).rstrip("%") + "%"
    edge        = _parm(node, "rso_edge", "")
    margin      = _parm(node, "rso_margin", "")
    color_space = _parm(node, "rso_colorspace", "")
    template    = _parm(node, "rso_template", "")
    aov         = _parm(node, "rso_aov", "")
    resize      = _parm(node, "rso_resize", "")
    extras      = _parm(node, "rso_extras", "")

    # ---- Job Info ----
    job_lines = [
        "Plugin=HouRenderStatsOverlay",
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

    if dependency_job_id:
        job_lines.append("JobDependencies={}".format(dependency_job_id))

    # ---- Plugin Info ----
    plugin_lines = [
        "InputImage={}".format(input_image.replace("\\", "/")),
        "OutputImage={}".format(output_image.replace("\\", "/")),
        "Mode={}".format(mode),
        "Align={}".format(align),
        "Scale={}".format(scale),
        "StatsWidth={}".format(stats_width),
        "Edge={}".format(edge),
        "Margin={}".format(margin),
        "ColorSpace={}".format(color_space),
        "Template={}".format(template.replace("\\", "/")),
        "AOV={}".format(aov),
        "Resize={}".format(resize),
        "Extras={}".format(extras),
    ]

    return _write_temp_job_files("hourenderstatsoverlay", job_lines, plugin_lines)


def _get_husk_output_image(node):
    """Reconstruct the same OutImage path that the husk job will use."""
    outdir  = _parm(node, "outdir", "")
    imgname = _parm(node, "imgname", "render")
    ver     = _parm_int(node, "ver", 1)
    ver_str = "v{:02d}".format(ver)

    if outdir and imgname:
        return "{}/{}/{}/{}.$F4.exr".format(
            outdir.rstrip("/\\"), imgname, ver_str, imgname
        )
    return ""


def _build_overlay_output_path(input_image, imgname):
    """
    Turn an EXR path into the sibling-folder preview path.

    Example
    -------
    input  : .../render/fx/v08/fx.$F4.exr
    output : .../render/fx/v08_renderstatsoverlay/preview.fx.$F4.jpg
    """
    if not input_image or not imgname:
        return ""

    # Normalise separators for easy splitting, then restore at the end
    path = input_image.replace("\\", "/")
    parts = path.rstrip("/").split("/")

    if len(parts) < 2:
        return ""

    # version folder is the parent of the file
    version_folder = parts[-2]          # e.g. "v08"
    parent_dir = "/".join(parts[:-2])   # e.g. ".../render/fx"

    new_folder = version_folder + "_renderstatsoverlay"
    filename = "preview.{}.$F4.jpg".format(imgname)

    if parent_dir:
        return "{}/{}/{}".format(parent_dir, new_folder, filename)
    return "{}/{}".format(new_folder, filename)


def _guess_imgname_from_path(path):
    """
    Best-effort extraction of the image stem from a path that may contain
    frame tokens ($F4, ####, etc.).
    """
    if not path:
        return ""
    base = os.path.basename(path.replace("\\", "/"))
    # strip extension
    stem = os.path.splitext(base)[0]
    # remove common frame token suffixes
    stem = re.sub(r"[\._]?(\$F\d*|#+)$", "", stem)
    return stem or "render"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _write_temp_job_files(prefix, job_lines, plugin_lines):
    tmp_dir = tempfile.gettempdir()
    job_info_path = os.path.join(tmp_dir, "{}_job_info.job".format(prefix))
    plugin_info_path = os.path.join(tmp_dir, "{}_plugin_info.job".format(prefix))

    with open(job_info_path, "w") as f:
        f.write("\n".join(job_lines) + "\n")

    with open(plugin_info_path, "w") as f:
        f.write("\n".join(plugin_lines) + "\n")

    return job_info_path, plugin_info_path


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
    if mode in ("preferred_height", "height"):
        h = value
        w = h * aspect
        return _nearest_even(w), _nearest_even(h)

    # ---- Preferred Width ----
    if mode in ("preferred_width", "width"):
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
        (0.5625, "9:16"),
        (0.75,   "3:4"),
        (0.8,    "4:5"),
    ]

    for target, name in known:
        if abs(r - target) < 0.012:
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
