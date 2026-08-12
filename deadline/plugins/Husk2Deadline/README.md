# Husk2Deadline – Clean Deadline Plugin for Houdini / husk

A minimal, self-contained Deadline plugin + Houdini submitter for rendering USD stages with SideFX `husk`.

Written to replace the older HuskStandalone / customised official Deadline Houdini scripts with something shorter, clearer and free of unused renderer-specific baggage.

## Features

- Direct husk rendering (no Hython / Houdini Engine license required for the render itself)
- One frame per task (standard for progressive / checkpoint-friendly workflows)
- Configurable:
  - Engine (karma, karmaxpu, …)
  - Render Settings prim
  - Render Pass
  - Camera
  - Resolution override
  - Output path (supports `$F4` / `####` tokens)
  - Extra command-line flags
  - Log / verbosity level
  - Flexible First/Mid/Last + frame increment controls (`fmlonly` + `frameinc`)
- Path mapping support via Deadline
- Progress reporting via Alfred-style stdout
- No dependency on the large official `SubmitHoudiniToDeadlineFunctions.py`

## Installation

### 1. Deadline Plugin

Copy the whole `Husk2Deadline` folder (the one that contains `Husk2Deadline.py` and `Husk2Deadline.param`) into:

```
<DeadlineRepository>/custom/plugins/Husk2Deadline/
```

In Deadline Monitor (super-user mode):

```
Tools → Configure Plugins → Husk2Deadline
```

**Husk Executable** is now only a *fallback*.  
Jobs submitted via `husk_submit.py` automatically inject the `husk` that belongs to the Houdini build you submitted from (so 21.0.671 / 22.0.512 / etc. just work).  
You only need the global path for old jobs or manual submissions. You can leave a sensible default or even leave it blank.

### 2. Houdini side

Put `husk_submit.py` somewhere on the Houdini Python path (or next to your HDA).

**Main husk submit (with optional dependent overlay):**

```python
import husk_submit
husk_submit.submit(kwargs["node"])
```

**Standalone RenderStats Overlay** (for already-rendered EXRs):

```python
import husk_submit
husk_submit.submit_renderstats_overlay(kwargs["node"])
```

### Expected HDA Parameters (Husk2Deadline)

| Parameter name   | Type     | Purpose                          | Example                  |
|------------------|----------|----------------------------------|--------------------------|
| `jobname`        | string   | Deadline job name                | `shot010_beauty`         |
| `usdfile`        | string   | Path to the .usd / .usda         | `$HIP/export/shot.usd`   |
| `frangex`        | int      | Start frame                      | 1001                     |
| `frangey`        | int      | End frame                        | 1100                     |
| `fmlonly`        | toggle   | Enable First/Mid/Last behaviour  | off                      |
| `frameinc`       | int      | Increment (0 / 1 / >1 – see notes) | 1                      |
| `framespertask`  | int      | Chunk size                       | 1                        |
| `engine`         | string   | husk `--engine`                  | `karma` / `karmaxpu`     |
| `primpath`       | string   | `--settings` prim                | `/Render/rendersettings` |
| `renderpass`     | string   | `--pass` (optional)              |                          |
| `camera`         | string   | `--camera`                       | `/cameras/cam1`          |
| `resolutionx`    | string   | base width                       | `1920`                   |
| `resolutiony`    | string   | base height                      | `1080`                   |
| `resmodifier`    | ordered menu | Full / Multiply (x) / Preferred Height / Preferred Width | `Full` |
| `resvalue`       | float    | multiplier or target height/width | `0.5` / `1080`         |
| `reslabel`       | string (disabled) | live effective resolution label | (auto)              |
| `outdir`         | string   | output root                      | `$HIP/render`            |
| `imgname`        | string   | image name stem                  | `beauty`                 |
| `ver`            | int      | version folder                   | `1` → `v01`              |
| `extras`         | string   | extra husk flags                 | `--ocio 1`               |
| `usdloglevel`    | int      | verbosity (0-9)                  | `2`                      |
| `pool`           | string   | Deadline pool                    |                          |
| `priority`       | int      | 0-100                            | `50`                     |
| **`generate_renderstatsoverlay_job`** | **toggle** | **Create dependent overlay job after husk** | **off** |
| `rso_mode`        | string   | overlay / sidebar                | `overlay`                |
| `rso_align`       | string   | alignment                        | `bottomleft`             |
| `rso_scale`       | string   | stats graphic scale              | `1.0` (use ~2.5 for 4K)  |
| `rso_width`       | string   | stats width                      | `30%`                    |
| `rso_outputimage` | string   | optional override for overlay output | (empty = tool default) |

**Frame logic (`fmlonly` + `frameinc`):**

| fmlonly | frameinc | Result |
|---------|----------|--------|
| on      | 0        | only First / Mid / Last |
| on      | 1        | full continuous range |
| on      | >1       | stepped + force F/M/L |
| off     | 0 or 1   | full continuous range (`frangex`-`frangey`) |
| off     | >1       | pure stepped (`start-endxinc`) – no forced F/M/L |

**Resolution modifier (non-destructive):**

`resolutionx` / `resolutiony` are the base values (what you pull from the USD or type by hand).  
`resmodifier` + `resvalue` compute the *effective* resolution that is actually sent to husk:

| resmodifier       | What `resvalue` means          | Result |
|-------------------|--------------------------------|--------|
| Full              | ignored                        | base resolution |
| Multiply (x)      | scale factor (e.g. 0.5)        | base × value (rounded to nearest even) |
| Preferred Height  | target height in pixels        | height = value, width from aspect |
| Preferred Width   | target width in pixels         | width = value, height from aspect |

The live label (`reslabel`) shows the effective resolution + pixel count + aspect ratio.

You can rename parameters in the HDA; just update the `_parm(...)` calls in `husk_submit.py`.

---

## Dependent Render Stats Overlay

When `generate_renderstatsoverlay_job` is enabled, after the main husk job is successfully submitted a second job using the **HouRenderStatsOverlay** plugin is created with:

- Same frame range / FML logic
- `JobDependencies = <husk JobID>`
- `InputImage` automatically derived from `outdir / imgname / vXX / imgname.$F4.exr`
- Appearance controlled by the `rso_*` parameters (or plugin defaults if the parms are missing)

This means the overlay tasks only start once the corresponding husk frame has finished.

---

## Standalone Overlay HDA

For EXRs that already exist on disk you can use a separate HDA that calls:

```python
husk_submit.submit_renderstats_overlay(kwargs["node"])
```

**Minimum required parameter:**

| Parameter     | Type   | Purpose                          |
|---------------|--------|----------------------------------|
| `inputimage`  | string | EXR path with `$F4` / `####` tokens |

Useful optional parameters (same names as above):

- `outputimage`, `rso_mode`, `rso_align`, `rso_scale`, `rso_width`, …
- Standard job controls: `jobname`, `pool`, `priority`, `frangex`/`frangey`, `fmlonly`, `frameinc`, etc.

---

## License

Do whatever you want with this code inside your studio.  
It is intentionally written from scratch so it does not inherit the GPL of the older public HuskStandalone submitters.
