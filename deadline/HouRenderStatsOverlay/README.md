# HouRenderStatsOverlay – Deadline Plugin for SideFX renderstatsoverlay

Simple Deadline plugin that runs Houdini’s `renderstatsoverlay` utility on finished Karma EXRs so you get a JPG/PNG with the render stats baked in (overlay or sidebar).

Intended to be submitted as a dependent job after a `Husk2Deadline` (or any husk) render finishes.

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

Set **Render Stats Overlay Executable** to the launcher on your workers, e.g.

```
C:/Program Files/Side Effects Software/Houdini 20.5.XXX/bin/renderstatsoverlay.bat
```

or the Linux equivalent (`renderstatsoverlay`).  
Using the `.bat` / shell launcher is preferred because it sets up `$HFS` and the Python environment correctly.

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

## Next step

Wire this into `husk_submit.py` so that after the main husk job is submitted, a dependent `HouRenderStatsOverlay` job is created automatically (same frames, Job Dependencies = the husk JobID).
