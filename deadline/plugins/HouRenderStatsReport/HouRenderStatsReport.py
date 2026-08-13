# HouRenderStatsReport – Deadline Plugin for SideFX renderstatsreport

Simple Deadline plugin that runs Houdini’s `renderstatsreport` utility (via **hython + the .py script**) on finished Karma EXRs so you get a self-contained HTML render statistics report.

The official `.bat` launcher is intentionally avoided – it is unreliable under Deadline.

Intended to be submitted as a dependent job after a `Husk2Deadline` (or any husk) render finishes, or as a standalone job for already-rendered EXRs.

## Features

- One frame / EXR per task
- Full path mapping support
- `$F` / `$F4` / `####` frame token expansion
- **Defaults only** – no extra parameters for thumbnails, heatmaps, titles, etc.
- Quiet process – only fails on obvious error patterns

## Installation

1. Copy the whole `HouRenderStatsReport` folder into:

```
<DeadlineRepository>/custom/plugins/HouRenderStatsReport/
```

2. In Deadline Monitor (super-user):

```
Tools → Configure Plugins → HouRenderStatsReport
```

**Important – do NOT use the .bat wrapper.**  
It frequently fails under Deadline with “The system cannot find the path specified.”

| Config key                       | Notes |
|----------------------------------|-------|
| **Hython Executable**            | Fallback only. Jobs submitted via `husk_submit.py` automatically inject the `hython` that belongs to the Houdini build you submitted from. Prefer `hython.exe` over the `.bat`. |
| **renderstatsreport.py Script**  | Default `renderstatsreport.py` is fine – hython finds it the same way your local tests did. |

## Plugin Info keys (for job submission)

| Key            | Example / Default      | Notes |
|----------------|------------------------|-------|
| `InputImage`   | `.../beauty.$F4.exr`   | **Required**. Path to the EXR (supports frame tokens) |
| `OutputHTML`   | `.../beauty.$F4.html`  | Optional. If empty the tool writes next to the input (same basename + `.html`) |
| `HythonExecutable` | (injected by submitter) | Path to the matching hython |

## Integration with Husk2Deadline

The companion `husk_submit.py` already supports this plugin:

1. **Dependent job** – enable the toggle `generate_renderstatsreport_job` on your husk HDA.  
   After the husk job is submitted a second job is created with `JobDependencies=<husk JobID>` and the same frame list. The input EXR path is automatically taken from the husk output path. `OutputHTML` is left empty so the report lands next to the EXR.

2. Future: a standalone submitter can be added later if needed (same pattern as the overlay).

## Notes

- The generated HTML is self-contained (`--single` is the tool default) and includes AOV thumbnails, performance tables, heatmaps where available, scene/lighting/materials breakdown, etc.
- File size per frame is typically a few hundred KB (depends on resolution and number of AOVs).
- Combining an entire sequence into one giant HTML is possible as a post-process step but is not part of this plugin (keeps things simple and reliable).
