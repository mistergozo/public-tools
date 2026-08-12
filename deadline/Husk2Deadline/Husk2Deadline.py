#!/usr/bin/env python3
"""
Husk2Deadline – Deadline plugin for rendering USD stages with husk.

Simple, readable plugin independent of the original HuskStandalone
and official Houdini Deadline submitter code.
"""

from __future__ import print_function

import os
import re

from System.IO import Path
from Deadline.Plugins import DeadlinePlugin, PluginType
from Deadline.Scripting import RepositoryUtils, StringUtils, FrameUtils


def GetDeadlinePlugin():
    return Husk2Deadline()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()


class Husk2Deadline(DeadlinePlugin):

    def __init__(self):
        super(Husk2Deadline, self).__init__()
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
        self.SingleFramesOnly = True          # one frame per task
        self.StdoutHandling = True
        self.PopupHandling = False

        # Progress (Alfred-style progress that husk can emit)
        self.AddStdoutHandlerCallback(
            r"ALF_PROGRESS\s+([0-9]+)%"
        ).HandleCallback += self._handle_progress

        # Fatal USD / husk errors
        self.AddStdoutHandlerCallback(
            r"(USD ERROR|Error:|Fatal error)"
        ).HandleCallback += self._handle_error

    # ------------------------------------------------------------------
    # Executable
    # ------------------------------------------------------------------
    def RenderExecutable(self):
        # Prefer the path that travelled with this specific job.
        # The submitter injects the husk belonging to the Houdini build
        # that was used to submit, so different versions just work
        # without touching Configure Plugins.
        job_exe = self.GetPluginInfoEntryWithDefault("HuskExecutable", "")
        if job_exe:
            return RepositoryUtils.CheckPathMapping(job_exe).replace("\\", "/")

        # Fallback to the global plugin config (old jobs / manual submissions)
        return self.GetConfigEntry("HuskExecutable")

    # ------------------------------------------------------------------
    # Command-line arguments
    # ------------------------------------------------------------------
    def RenderArgument(self):
        scene = self.GetPluginInfoEntryWithDefault("SceneFile", "")
        scene = RepositoryUtils.CheckPathMapping(scene).replace("\\", "/")

        frame = self.GetStartFrame()
        log_level = self.GetPluginInfoEntryWithDefault("LogLevel", "2")
        engine = self.GetPluginInfoEntryWithDefault("Engine", "karma")
        settings_prim = self.GetPluginInfoEntryWithDefault("RenderSettingsPrim", "")
        render_pass = self.GetPluginInfoEntryWithDefault("RenderPass", "")
        camera = self.GetPluginInfoEntryWithDefault("Camera", "")
        resolution = self.GetPluginInfoEntryWithDefault("Resolution", "")
        output_image = self.GetPluginInfoEntryWithDefault("OutImage", "")
        extras = self.GetPluginInfoEntryWithDefault("Extras", "")

        args = [scene]

        # Verbosity (Alfred style so progress handlers work)
        args.append("--verbose")
        args.append("a{}".format(log_level))

        # Frame
        args.append("--frame")
        args.append(str(frame))
        args.append("--frame-count")
        args.append("1")

        # Output
        if output_image:
            out = RepositoryUtils.CheckPathMapping(output_image).replace("\\", "/")
            # Replace $F / $F4 style tokens with the actual zero-padded frame
            out = self._expand_frame_token(out, frame)
            args.append("-o")
            args.append(out)
            args.append("--make-output-path")
        else:
            # Fallback: next to the USD, under a "render" folder
            usd_dir = os.path.dirname(scene)
            render_dir = os.path.join(usd_dir, "render")
            base = Path.GetFileNameWithoutExtension(scene)
            padded = StringUtils.ToZeroPaddedString(frame, 4)
            out = "{}/{}.{}.exr".format(render_dir, base, padded)
            args.append("-o")
            args.append(out)
            args.append("--make-output-path")

        # Renderer / engine
        if engine:
            args.append("--engine")
            args.append(engine)

        # Optional overrides that match common husk flags
        if settings_prim:
            args.append("--settings")
            args.append(settings_prim)
        if render_pass:
            args.append("--pass")
            args.append(render_pass)
        if camera:
            args.append("--camera")
            args.append(camera)
        if resolution:
            args.append("--res")
            # resolution is expected as "width height"
            args.extend(resolution.split())

        # Any extra user-supplied flags
        if extras:
            args.extend(extras.split())

        cmd = " ".join(args)
        self.LogInfo("Husk command: husk " + cmd)
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

    def _handle_progress(self):
        progress = float(self.GetRegexMatch(1))
        self.SetProgress(progress)
        self.SetStatusMessage("Rendering… {}%".format(int(progress)))

    def _handle_error(self):
        self.FailRender(self.GetRegexMatch(0))
