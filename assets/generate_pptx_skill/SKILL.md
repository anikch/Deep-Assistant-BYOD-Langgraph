---
name: generate_pptx
version: 1.0.0
description: Generates a PowerPoint (.pptx) presentation from structured content using python-pptx. Use this skill when the user asks to create, generate, or export a PowerPoint, PPTX, or slide deck.
author: Assistant PoC
tags:
  - pptx
  - powerpoint
  - presentation
  - export
triggers:
  - generate pptx
  - create powerpoint
  - make a presentation
  - export slides
  - build slide deck
---

# Skill: Generate PPTX

## Purpose
Generate a downloadable PowerPoint (.pptx) presentation from content in the session knowledge base or from user-specified data.

## When to Use
Use this skill when the user:
- Asks to "generate a pptx", "create a PowerPoint", "make a presentation", or "export to slides"
- Wants to summarise research findings as a slide deck
- Wants to turn extracted content into a presentable format

## How to Execute
Generate and run the following Python code in the code execution sandbox. Adapt the slide content based on what the user asked for and what was retrieved from the knowledge base.

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import json

# ── Configuration ────────────────────────────────────────────────────────────
OUTPUT_PATH = "/tmp/output_presentation.pptx"

# ── Slide data ────────────────────────────────────────────────────────────────
# Replace this with content derived from the user query and retrieved chunks.
# Structure: list of dicts with keys: title (str), bullets (list[str]), notes (str)
SLIDES = [
    {
        "title": "Introduction",
        "bullets": [
            "Overview of the topic",
            "Key objectives",
            "Scope of this presentation",
        ],
        "notes": "Speaker notes for the introduction slide.",
    },
    {
        "title": "Key Findings",
        "bullets": [
            "Finding 1 from the knowledge base",
            "Finding 2 with supporting evidence",
            "Finding 3 derived from uploaded documents",
        ],
        "notes": "Elaborate on each finding during the presentation.",
    },
    {
        "title": "Summary",
        "bullets": [
            "Main takeaway",
            "Recommended next steps",
            "Questions?",
        ],
        "notes": "Wrap up and invite discussion.",
    },
]

PRESENTATION_TITLE = "Generated Presentation"
PRESENTATION_SUBTITLE = "Created by Assistant PoC"

# ── Theme colours ─────────────────────────────────────────────────────────────
COLOR_HEADER_BG = RGBColor(0x1F, 0x4E, 0x79)   # dark blue
COLOR_HEADER_TEXT = RGBColor(0xFF, 0xFF, 0xFF)  # white
COLOR_BULLET_TEXT = RGBColor(0x1F, 0x1F, 0x1F) # near black
COLOR_ACCENT = RGBColor(0x2E, 0x75, 0xB6)       # mid blue


def add_title_slide(prs, title, subtitle):
    layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(layout)
    slide.shapes.title.text = title
    slide.shapes.title.text_frame.paragraphs[0].runs[0].font.color.rgb = COLOR_HEADER_TEXT
    slide.shapes.title.text_frame.paragraphs[0].runs[0].font.size = Pt(36)
    slide.shapes.title.text_frame.paragraphs[0].runs[0].font.bold = True
    ph = slide.placeholders[1]
    ph.text = subtitle
    ph.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xBF, 0xD7, 0xED)
    ph.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
    return slide


def add_content_slide(prs, title, bullets, notes=""):
    layout = prs.slide_layouts[1]  # Title and Content
    slide = prs.slides.add_slide(layout)

    # Title
    tf_title = slide.shapes.title.text_frame
    tf_title.text = title
    for para in tf_title.paragraphs:
        for run in para.runs:
            run.font.color.rgb = COLOR_HEADER_TEXT
            run.font.size = Pt(28)
            run.font.bold = True

    # Bullets
    tf = slide.placeholders[1].text_frame
    tf.clear()
    for i, bullet in enumerate(bullets):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.text = bullet
        para.level = 0
        para.alignment = PP_ALIGN.LEFT
        for run in para.runs:
            run.font.size = Pt(18)
            run.font.color.rgb = COLOR_BULLET_TEXT

    # Speaker notes
    if notes:
        slide.notes_slide.notes_text_frame.text = notes

    return slide


# ── Build presentation ────────────────────────────────────────────────────────
prs = Presentation()
prs.slide_width = Inches(13.33)
prs.slide_height = Inches(7.5)

add_title_slide(prs, PRESENTATION_TITLE, PRESENTATION_SUBTITLE)

for slide_data in SLIDES:
    add_content_slide(
        prs,
        title=slide_data.get("title", "Slide"),
        bullets=slide_data.get("bullets", []),
        notes=slide_data.get("notes", ""),
    )

prs.save(OUTPUT_PATH)

# Report output for the agent to pick up
result = {
    "status": "success",
    "output_path": OUTPUT_PATH,
    "slide_count": len(SLIDES) + 1,
    "message": f"Presentation saved to {OUTPUT_PATH} with {len(SLIDES) + 1} slides (including title slide).",
}
print(json.dumps(result))
```

## After Execution
After the code runs successfully:
1. Read the `output_path` from the printed JSON
2. Use the artifact generation API to save the file as a downloadable PPTX artifact for the session
3. Tell the user the presentation was generated and provide the download link

## Requirements
- `python-pptx` is pre-installed in the execution environment
- Output is written to `/tmp/output_presentation.pptx`
- Adapt `SLIDES`, `PRESENTATION_TITLE`, and `PRESENTATION_SUBTITLE` based on the actual user request and retrieved knowledge base content

## Slide Design Guidelines
- Title slide: use layout index 0
- Content slides: use layout index 1 (Title and Content)
- Keep bullets concise — max 6 bullets per slide
- Use speaker notes for additional detail
- Adapt colours via the COLOR_* constants if the user requests a specific theme
