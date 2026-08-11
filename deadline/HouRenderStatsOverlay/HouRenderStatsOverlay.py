#!/usr/bin/env python3
"""
HouRenderStatsOverlay – Deadline plugin that runs SideFX renderstatsoverlay
on Karma EXRs to bake render statistics into a preview image.

Uses hython + renderstatsoverlay.py (the same method that works reliably
in a local shell). The .bat wrapper is intentionally avoided because it
frequently fails under Deadline with “The system cannot find the path specified.”

Designed to be dependent on a Husk2Deadline (or any husk) job so that
once a frame finishes rendering, the overlay job can generate the
stats-annotated preview automatically.
"""

from __future__ import print_function

import os
import re

from System.IO import Path
from Deadline.Plugins import DeadlinePlugin, PluginType
from Deadline.Scripting import RepositoryUtils, StringUtils, FrameUtils


def GetDeadlinePlugin():
    return HouRenderStatsOverlay()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()


class HouRenderStatsOverlay(DeadlinePlugin):

    def __init__(self):
        super(HouRenderStatsOverlay, self).__init__()
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument

    def Cleanup(self):
        for callback in (
            self.InitializeProcessCallback,
            self.RenderExecutableCallback,
            self.RenderArgumentCallback,
        ):
            del callback

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def InitializeProcess(self):
        self.PluginType = PluginType.Simple
        self.SingleFramesOnly = True          # one EXR / frame per task
        self.StdoutHandling = True
        self.PopupHandling = False

        # Basic success / failure patterns (renderstatsoverlay is quiet)
        self.AddStdoutHandlerCallback(
            r"(Error:|ERROR:|Traceback|Fatal|The system cannot find the path specified)"
        ).HandleCallback += self._handle_error

    # ------------------------------------------------------------------
    # Executable  →  hython
    # ------------------------------------------------------------------
    def RenderExecutable(self):
        # Config key set in Deadline Monitor → Configure Plugins → HouRenderStatsOverlay
        return self.GetConfigEntry("HythonExecutable")

    # ------------------------------------------------------------------
    # Command-line arguments
    # ------------------------------------------------------------------
    def RenderArgument(self):
        frame = self.GetStartFrame()

        # Required input EXR (supports $F / #### tokens)
        input_image = self.GetPluginInfoEntryWithDefault("InputImage", "")
        if not input_image:
            self.FailRender("InputImage is required")

        input_image = RepositoryUtils.CheckPathMapping(input_image).replace("\\", "/")
        input_image = self._expand_frame_token(input_image, frame)

        # Optional explicit output. If empty the tool writes next to the EXR
        # (or uses the default _preview naming).
        output_image = self.GetPluginInfoEntryWithDefault("OutputImage", "")
        if output_image:
            output_image = RepositoryUtils.CheckPathMapping(output_image).replace("\\", "/")
            output_image = self._expand_frame_token(output_image, frame)

            # Ensure the destination directory exists (renderstatsoverlay does not
            # create parent folders the way husk does with --make-output-path).
            out_dir = os.path.dirname(output_image)
            if out_dir and not os.path.isdir(out_dir):
                try:
                    os.makedirs(out_dir)
                    self.LogInfo("Created output directory: " + out_dir)
                except Exception as exc:
                    self.LogWarning("Could not create output directory {}: {}".format(out_dir, exc))

        # Appearance / placement
        mode = self.GetPluginInfoEntryWithDefault("Mode", "overlay").strip().lower()
        align = self.GetPluginInfoEntryWithDefault("Align", "bottomleft")
        scale = self.GetPluginInfoEntryWithDefault("Scale", "1.0")
        stats_width = self.GetPluginInfoEntryWithDefault("StatsWidth", "30%")
        edge = self.GetPluginInfoEntryWithDefault("Edge", "")
        margin = self.GetPluginInfoEntryWithDefault("Margin", "")
        color_space = self.GetPluginInfoEntryWithDefault("ColorSpace", "")
        template = self.GetPluginInfoEntryWithDefault("Template", "")
        aov = self.GetPluginInfoEntryWithDefault("AOV", "")
        resize = self.GetPluginInfoEntryWithDefault("Resize", "")
        extras = self.GetPluginInfoEntryWithDefault("Extras", "")

        # Script location (from plugin config – default is just the bare name)
        script = self.GetConfigEntryWithDefault("RenderStatsOverlayScript", "renderstatsoverlay.py")
        script = script.strip().strip('"')

        args = []

        # 1. The Python script itself (first argument to hython)
        #    Quote it only if it contains spaces / is an absolute path.
        if " " in script or (len(script) > 2 and script[1] == ":"):
            args.append('"{}"'.format(script.replace("\\", "/")))
        else:
            args.append(script)

        # 2. Input EXR (positional)
        args.append('"{}"'.format(input_image))

        # 3. Optional output (second positional)
        if output_image:
            args.append('"{}"'.format(output_image))

        # Mode: --overlay or --sidebar
        if mode in ("overlay", "over"):
            args.append("--overlay")
        else:
            args.append("--sidebar")

        # Alignment
        if align:
            args.append("-A")
            args.append(align)

        # Scale of the stats graphic contents
        if scale:
            args.append("--scale")
            args.append(str(scale))

        # Width of the stats block (pixels or %)
        if stats_width:
            args.append("-w")
            args.append(str(stats_width))

        # Optional edge (mainly useful with sidebar, or to tweak overlay)
        if edge:
            args.append("-e")
            args.append(edge)

        if margin:
            args.append("-M")
            args.append(str(margin))

        if color_space:
            args.append("--color-space")
            args.append(color_space)

        if template:
            args.append("-t")
            args.append('"{}"'.format(RepositoryUtils.CheckPathMapping(template).replace("\\", "/")))

        if aov:
            args.append("-a")
            args.append(aov)

        if resize:
            args.append("-s")
            args.append(str(resize))

        # Any extra user-supplied flags
        if extras:
            args.extend(extras.split())

        cmd = " ".join(args)
        self.LogInfo("hython + renderstatsoverlay command: " + cmd)
        return cmd

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _expand_frame_token(self, path, frame):
        """
        Replace common Houdini frame tokens ($F, $F2, $F3, $F4, ####, etc.)
        with a zero-padded frame number.
        """
        def replacer(match):
            token = match.group(0)
            if token.startswith("$F"):
                width = int(token[2:]) if len(token) > 2 else 1
            else:                       # #### style
                width = len(token)
            return StringUtils.ToZeroPaddedString(frame, width)

        # $F, $F2, $F3, $F4 …
        path = re.sub(r"\$F\d*", replacer, path)
        # #### style padding
        path = re.sub(r"#+", replacer, path)
        return path

    def _handle_error(self):
        self.FailRender(self.GetRegexMatch(0))
