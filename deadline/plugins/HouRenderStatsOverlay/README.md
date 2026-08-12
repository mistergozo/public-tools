# HouRenderStatsOverlay – Deadline Plugin for SideFX renderstatsoverlay

Simple Deadline plugin that runs Houdini’s `renderstatsoverlay` utility (via **hython + the .py script**) on finished Karma EXRs so you get a JPG/PNG with the render stats baked in (overlay or sidebar).

The official `.bat` launcher is intentionally avoided – it is unreliable under Deadline.

Intended to be submitted as a dependent job after a `Husk2Deadline` (or any husk) render finishes, or as a standalone job for already-rendered EXRs.

## Features

- One frame / EXR per task
- Full path mapping support
- `$F` / `$F4` / `####` frame token expansion
- Configurable:
  - Mode (`overlay` or `sidebar`)
  - Align (`bottomleft`, `topright`, …)
  - Scale (the font/tile scale factor)
  - Stats width (`30%`, `240`, …)
  - Edge, margin, color space, custom JSON template, AOV, resize, extras
- Quiet process – only fails on obvious error patterns

## Installation

1. Copy the whole `HouRenderStatsOverlay` folder into:

```
<DeadlineRepository>/custom/plugins/HouRenderStatsOverlay/
```

2. In Deadline Monitor (super-user):

```
Tools → Configure Plugins → HouRenderStatsOverlay
```

**Important – do NOT use the .bat wrapper.**  
It frequently fails under Deadline with “The system cannot find the path specified.”

| Config key                       | Notes |
|----------------------------------|-------|
| **Hython Executable**            | Fallback only. Jobs submitted via `husk_submit.py` automatically inject the `hython` that belongs to the Houdini build you submitted from. Prefer `hython.exe` over the `.bat`. |
| **renderstatsoverlay.py Script** | Default `renderstatsoverlay.py` is fine – hython finds it the same way your local tests did. |

## Plugin Info keys (for job submission)

| Key            | Example / Default      | Notes |
|----------------|------------------------|-------|
| `InputImage`   | `.../beauty.$F4.exr`   | **Required**. Path to the EXR (supports frame tokens) |
| `OutputImage`  | `.../beauty.$F4_stats.jpg` | Optional. If empty the tool writes next to the input |
| `Mode`         | `overlay`              | `overlay` or `sidebar` |
| `Align`        | `bottomleft`           | `-A` value |
| `Scale`        | `1.0`                  | `--scale` (increase for high-res images) |
| `StatsWidth`   | `30%`                  | `-w` |
| `Edge`         |                        | optional `-e` |
| `Margin`       |                        | optional `-M` |
| `ColorSpace`   |                        | `--color-space` |
| `Template`     |                        | custom JSON tile template |
| `AOV`          |                        | `-a` |
| `Resize`       |                        | `-s` (e.g. `1280` or `50%`) |
| `Extras`       |                        | any extra flags |

## Typical settings that matched your tests

```
Mode=overlay
Align=bottomleft
Scale=1.0
StatsWidth=30%
```

At 2160p you will probably want `Scale=2.5` (or higher) so the text stays readable.  
A future improvement can auto-derive the scale from image height.

## Integration with Husk2Deadline

The companion `husk_submit.py` already supports this plugin in two ways:

1. **Dependent job** – enable the toggle `generate_renderstatsoverlay_job` on your husk HDA.  
   After the husk job is submitted a second job is created with `JobDependencies=<husk JobID>` and the same frame list. The input EXR path is automatically taken from the husk output path.

2. **Standalone** – call `husk_submit.submit_renderstats_overlay(node)` from a separate HDA when you want to generate overlays for already-rendered EXRs.

See the Husk2Deadline README for the full list of `rso_*` parameters.
