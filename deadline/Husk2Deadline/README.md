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

Set **Husk Executable** to the full path of `husk` on your workers, e.g.

```
C:/Program Files/Side Effects Software/Houdini 20.5.XXX/bin/husk.exe
```

or the Linux equivalent.  
You can use environment-variable style tokens if your farm already does so for other plugins.

### 2. Houdini side

Put `husk_submit.py` somewhere on the Houdini Python path (or next to your HDA).

From a Python Script button / HDA callback:

```python
import husk_submit
husk_submit.submit(kwargs["node"])
```

### Expected HDA Parameters

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

## Differences from previous scripts

- No massive dictionary of Mantra / Arnold / Redshift / V-Ray keys
- No reliance on the official Houdini Deadline submission library
- Cleaner argument construction and frame-token expansion
- Explicit, readable plugin class
- Easy to extend (add GPU affinity, multi-frame chunks, etc.)

## License

Do whatever you want with this code inside your studio.  
It is intentionally written from scratch so it does not inherit the GPL of the older public HuskStandalone submitters.
