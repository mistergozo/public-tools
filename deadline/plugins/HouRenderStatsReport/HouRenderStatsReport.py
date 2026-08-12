#!/usr/bin/env python3
"""
HouRenderStatsReport – Deadline plugin that runs SideFX renderstatsreport
on Karma EXRs to generate a self-contained HTML render statistics report.

Uses hython + renderstatsreport.py (the same method that works reliably
in a local shell). The .bat wrapper is intentionally avoided because it
frequently fails under Deadline with “The system cannot find the path specified.”

Designed to be dependent on a Husk2Deadline (or any husk) job so that
once a frame finishes rendering, the report job can generate the
HTML stats report automatically.

Defaults only – no extra appearance / thumbnail / heatmap options are
exposed. The tool is left to its own defaults (single self-contained HTML,
default thumbnail level, etc.).
"""

from __future__ import print_function

import os
import re

from System.IO import Path
from Deadline.Plugins import DeadlinePlugin, PluginType
from Deadline.Scripting import RepositoryUtils, StringUtils, FrameUtils


def GetDeadlinePlugin():
    return HouRenderStatsReport()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()


class HouRenderStatsReport(DeadlinePlugin):

    def __init__(self):
        super(HouRenderStatsReport, self).__init__()
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

        # Basic success / failure patterns (renderstatsreport is quiet)
        self.AddStdoutHandlerCallback(
            r"(Error:|ERROR:|Traceback|Fatal|The system cannot find the path specified)"
        ).HandleCallback += self._handle_error

    # ------------------------------------------------------------------
    # Executable  →  hython
    # ------------------------------------------------------------------
    def RenderExecutable(self):
        # Prefer the path that travelled with this specific job.
        # The submitter injects the hython belonging to the Houdini build
        # that was used to submit, so different versions just work
        # without touching Configure Plugins.
        job_exe = self.GetPluginInfoEntryWithDefault("HythonExecutable", "")
        if job_exe:
            return RepositoryUtils.CheckPathMapping(job_exe).replace("\\", "/")

        # Fallback to the global plugin config (old jobs / manual submissions)
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

        # Optional explicit output HTML. If empty the tool writes next to the EXR
        # (same basename + .html).
        output_html = self.GetPluginInfoEntryWithDefault("OutputHTML", "")
        if output_html:
            output_html = RepositoryUtils.CheckPathMapping(output_html).replace("\\", "/")
            output_html = self._expand_frame_token(output_html, frame)

            # Ensure the destination directory exists
            out_dir = os.path.dirname(output_html)
            if out_dir and not os.path.isdir(out_dir):
                try:
                    os.makedirs(out_dir)
                    self.LogInfo("Created output directory: " + out_dir)
                except Exception as exc:
                    self.LogWarning("Could not create output directory {}: {}".format(out_dir, exc))

        # Script location (from plugin config – default is just the bare name)
        script = self.GetConfigEntryWithDefault("RenderStatsReportScript", "renderstatsreport.py")
        script = script.strip().strip('"')

        args = []

        # 1. The Python script itself (first argument to hython)
        if " " in script or (len(script) > 2 and script[1] == ":"):
            args.append('"{}"'.format(script.replace("\\", "/")))
        else:
            args.append(script)

        # 2. Input EXR (positional)
        args.append('"{}"'.format(input_image))

        # 3. Optional output HTML (second positional)
        if output_html:
            args.append('"{}"'.format(output_html))

        # Intentionally no extra flags – leave the tool at its defaults
        # (--single, default thumbnails, etc.)

        cmd = " ".join(args)
        self.LogInfo("hython + renderstatsreport command: " + cmd)
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
