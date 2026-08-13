# Deadline Tools for Houdini / husk

**Author:** Jesse Gozo

Hey! This is a little collection of custom Deadline plugins and a Houdini HDA I made for cleaner Karma / husk workflows.

Nothing fancy or bloated — just the stuff I actually needed day-to-day.

---

## What’s inside

```
deadline/
├── otls/
│   ├── lop_jesseg.husk2deadline.2.1.hda
│   └── lop_jesseg.deadline_utilities.1.0.hda
├── plugins/
│   ├── Husk2Deadline/
│   ├── HouRenderStatsOverlay/
│   └── HouRenderStatsReport/
└── README.md
```

### The tools

**Husk2Deadline**  
Deadline plugin + submitter for rendering USD stages with SideFX husk.  
Keeps things simple — one frame per task, path mapping, and it automatically uses the same husk version you’re running in Houdini.  
Supports First/Mid/Last + frame increment, resolution modifiers, and optional dependent stats jobs.

**HouRenderStatsOverlay**  
Deadline plugin that runs Houdini’s `renderstatsoverlay` on finished EXRs so you get a nice JPG/PNG with the stats baked in (overlay or sidebar).  
Works as a dependent job after a husk render finishes, or as a standalone job on already-rendered sequences.

**HouRenderStatsReport**  
Deadline plugin that runs Houdini’s `renderstatsreport` on finished EXRs so you get a self-contained HTML render statistics report (defaults only).  
Also works as a dependent job after a husk render finishes, or as a standalone job.

**lop_jesseg.husk2deadline** (the main HDA)  
The actual node you drop in your LOPs network.  
It has the submitter built-in and can also kick off the overlay and/or HTML report jobs automatically if you want.

**lop_jesseg.deadline_utilities** (standalone utilities HDA)  
Separate HDA for submitting overlay / report jobs against already-rendered EXR sequences (no husk job required).  
Uses the same `husk_submit.py` standalone entry points (`submit_renderstats_overlay`, `submit_renderstats_report`, `submit_standalone`).

Each plugin folder has its own more detailed README with install steps and all the parameters.

---

## Quick start

1. Drop the plugin folder(s) into your Deadline repository under `custom/plugins/`
2. Install the HDAs in Houdini
3. Check the individual READMEs inside each plugin folder for the rest

That’s pretty much it.

---

## Changelog

### 2026-08-13 – Standalone support + polish
- Extended `husk_submit.py` with full standalone support:
  - `submit_renderstats_overlay()`
  - `submit_renderstats_report()`
  - `submit_standalone()` (reads generate toggles)
- Added `only_existing_frames` toggle (default on) for standalone jobs – only submits frames that actually exist on disk
- New standalone output convention:
  - Overlay → `…/extras/overlay/{stem}.$F4.jpg`
  - Report  → `…/extras/report/{stem}.$F4.html`
  - Main husk dependent path remains unchanged
- Added `lop_jesseg.deadline_utilities.1.0.hda` for standalone overlay/report submission

### 2026-08-12 – Report plugin + resolution tokens
- Added **HouRenderStatsReport** Deadline plugin (hython + `renderstatsreport.py`, defaults only)
- Added `generate_renderstatsreport_job` toggle in `husk_submit.py`
- Updated resolution modifier tokens to `preferred_height` / `preferred_width` (underscores)

### 2026-08-11 – First release
- **Husk2Deadline** plugin + `husk_submit.py`
- **HouRenderStatsOverlay** plugin
- HDA: `lop_jesseg.husk2deadline.2.1.hda`
- Minimalist icons for all plugins (clean JG monogram)
- First/Mid/Last + frame increment support (`fmlonly` + `frameinc`)
- Optional dependent overlay job (`generate_renderstatsoverlay_job`)
- Resolution modifier options (Full / Multiply / preferred height / preferred width)

---

Feel free to use this however you like in your studio.

**Jesse Gozo**  
2026
