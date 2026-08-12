# Deadline Tools for Houdini / husk

**Author:** Jesse Gozo

Hey! This is a little collection of custom Deadline plugins and a Houdini HDA I made for cleaner Karma / husk workflows.

Nothing fancy or bloated — just the stuff I actually needed day-to-day.

---

## What’s inside

```
deadline/
├── otls/
│   └── lop_jesseg.husk2deadline.2.1.hda
├── plugins/
│   ├── Husk2Deadline/
│   └── HouRenderStatsOverlay/
└── README.md
```

### The tools

**Husk2Deadline**  
Deadline plugin + submitter for rendering USD stages with SideFX husk.  
Keeps things simple — one frame per task, path mapping, and it automatically uses the same husk version you’re running in Houdini.

**HouRenderStatsOverlay**  
Deadline plugin that runs Houdini’s `renderstatsoverlay` on finished EXRs so you get a nice JPG/PNG with the stats baked in (overlay or sidebar).  
Works great as a dependent job after a husk render finishes.

**lop_jesseg.husk2deadline** (the HDA)  
The actual node you drop in your LOPs network.  
It has the submitter built-in and can also kick off the overlay job automatically if you want.

Each plugin folder has its own more detailed README with install steps and all the parameters.

---

## Quick start

1. Drop the plugin folder(s) into your Deadline repository under `custom/plugins/`
2. Install the HDA in Houdini
3. Check the individual READMEs inside each plugin folder for the rest

That’s pretty much it.

---

## Changelog

### 2026-08 – First release
- Husk2Deadline plugin + husk_submit.py
- HouRenderStatsOverlay plugin
- HDA: `lop_jesseg.husk2deadline.2.1.hda`
- Icons for both plugins
- First/Mid/Last + frame increment support
- Optional dependent overlay job
- Resolution modifier options

---

Feel free to use this however you like in your studio.

**Jesse Gozo**  
2026
