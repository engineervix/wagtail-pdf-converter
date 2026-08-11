---
icon: lucide/file-output
---

# Creating pages from PDFs

By default the package converts a PDF to Markdown and renders that as HTML. This guide covers the **optional** alternative: turning a PDF into a real Wagtail **Page** with a StreamField body, so the content gets the full editor workflow — blocks, revisions, moderation, and previews — like any other page.

The feature is opt-in. Markdown conversion remains the default and is unaffected.

## How it works

The conversion runs through four stages:

1. **Extract** — the AI reads the PDF and returns a structured list of typed *elements* (heading, paragraph, image, quote, code, table, list) using schema-constrained JSON output, so the shape is guaranteed.
2. **Map** — a registry maps each element type to a StreamField block, producing `(block_name, value)` tuples.
3. **Resolve** — images are linked to the Wagtail Images that were already created during extraction, matched by content hash.
4. **Load** — the tuples are assembled into a StreamField value and saved as a new Page under a parent you choose.

Anything the AI emits that has no matching block is routed to a plain paragraph block, so **no content is ever silently dropped** — Wagtail's StreamField otherwise discards unrecognised block types without an error. Misclassified blocks stay editable in the page editor, so you can correct them by hand.

## 1. Enable it

```python
WAGTAIL_PDF_CONVERTER = {
    "ENABLE_PAGE_CREATION": True,
    "PAGE_CREATION_MODEL": "myapp.models.PDFPage",   # dotted path to your Page model
    "PAGE_CREATION_PARENT_ID": 3,                     # id of the parent page
}
```

| Setting                   | Default | Description                                                              |
| ------------------------- | ------- | ------------------------------------------------------------------------ |
| `ENABLE_PAGE_CREATION`    | `False` | Enables the **Create page from PDF** admin action.                       |
| `PAGE_CREATION_MODEL`     | `None`  | Dotted path to the Page model to create. Must have a `body` StreamField. |
| `PAGE_CREATION_PARENT_ID` | `None`  | Primary key of the page under which new pages are created.               |

Both `PAGE_CREATION_MODEL` and `PAGE_CREATION_PARENT_ID` are required for the admin action; if either is missing, the action shows an error and changes nothing.

## 2. Define the page model

Your page model needs a `body` StreamField whose block names match the mapper's defaults. The package ships a ready-made block kit, `PDFStreamBlock`, so the common case is a few lines:

```python
# myapp/models.py
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from wagtail_pdf_converter.blocks import PDFStreamBlock


class PDFPage(Page):
    body = StreamField(PDFStreamBlock(), blank=True, use_json_field=True)

    content_panels = Page.content_panels + [FieldPanel("body")]
```

`PDFStreamBlock` provides `heading`, `paragraph`, `image`, `quote`, `code`, `table`, and `list` blocks — one per element type the AI can emit.

## 3. Create a page

Once enabled, a **Create page** button appears on the document edit page (next to **Retry conversion**) and, for converted PDFs, in the document listing's status column. Both open a confirmation screen; confirming creates the page and takes you straight to its editor. The action is also available directly at `/admin/wagtail_pdf_converter/documents/<id>/create-page/`.

The button only appears for PDF documents, and only when `ENABLE_PAGE_CREATION`, `PAGE_CREATION_MODEL`, and `PAGE_CREATION_PARENT_ID` are all set. The page is created on form submission (POST), never from a bare link, so it can't be triggered accidentally.

### From Python

For your own views, scripts, or management commands, use the high-level orchestrator:

```python
from wagtail.models import Page
from wagtail_pdf_converter.services.page_creator import convert_pdf_to_page

document = ...                                    # a converted PDF document
parent = Page.objects.get(id=3)

page = convert_pdf_to_page(
    document,
    parent=parent,
    page_model=PDFPage,
    user=request.user,                            # optional — set as page owner
    title="Custom title",                         # optional — defaults to the document title
)
```

For finer control, `create_page_from_elements` takes a pre-built element stream directly (no AI call), which is also how the feature is tested.

## Styling the blocks

Each block in the kit renders through a template that carries a stable `pdf-page-*` class, so you can style PDF-derived content from your own stylesheet without touching the package:

| Block       | Class                  | Notes                                            |
| ----------- | ---------------------- | ------------------------------------------------ |
| `heading`   | `.pdf-page-heading`    | Also `.pdf-page-heading--1` … `--6` by level.     |
| `paragraph` | `.pdf-page-paragraph`  |                                                  |
| `image`     | `.pdf-page-image`      | Uses Wagtail's image block output.               |
| `quote`     | `.pdf-page-quote`      | Attribution in `.pdf-page-quote-attribution`.    |
| `code`      | `.pdf-page-code`       | Also `.pdf-page-code--{language}`.               |
| `table`     | `.pdf-page-table`      |                                                  |
| `list`      | `.pdf-page-list`       | Also `.pdf-page-list--ordered` for numbered lists.|

```css
.pdf-page-table { width: 100%; border-collapse: collapse; }
.pdf-page-code  { background: #f5f5f5; padding: 1em; }
```

The package ships **no styles of its own** — appearance belongs to your site. For full control over markup, override any block's template: create `templates/wagtail_pdf_converter/blocks/<name>.html` in your project and it takes precedence over the bundled one.

## Customising blocks

The default block kit covers the common cases, but every site is different. You can override how an element type maps to a block — or which block it uses — by registering your own converter.

A converter is a callable that takes an element and returns a `(block_name, value)` tuple:

```python
from wagtail_pdf_converter.mapper import MapperRegistry, StreamFieldMapper


def hero_heading(element):
    # Send top-level headings to a custom "hero" block instead of "heading".
    if element.level == 1:
        return ("hero", element.text)
    return ("heading", {"text": element.text, "level": element.level})


registry = MapperRegistry()
registry.register("heading", hero_heading)
# ... register or override others as needed

mapper = StreamFieldMapper(registry)
page = convert_pdf_to_page(document, parent=parent, page_model=PDFPage, mapper=mapper)
```

The registry always keeps a **paragraph fallback**: any element type without a registered converter (or any block name your page's StreamField doesn't define) is routed to a paragraph, so unmapped content is preserved rather than dropped. Register a custom fallback by passing it to `MapperRegistry(fallback=...)`.

!!! note
    Your page model's `body` StreamField must define a block for every name your converters emit. If a converter returns a block name the StreamField doesn't have, the loader falls back to a paragraph for that block.

## Adding a new element type

The built-in types (heading, paragraph, image, quote, code, table, list) are a baseline, not a ceiling. To support something the kit doesn't cover — a callout box, a figure with a caption, a definition list — register a custom element type. This teaches the parser *and* the AI's output schema about it, so the new type flows end-to-end: PDF → AI → element → block.

Three steps:

**1. Define the element.** Subclass `BaseElement` with a `type` literal and the fields it needs:

```python
from typing import Literal
from wagtail_pdf_converter.elements import BaseElement


class CalloutElement(BaseElement):
    type: Literal["callout"]
    text: str
    variant: str = "info"
```

**2. Register it.** Pass a one-line `description` telling the AI when to emit it:

```python
from wagtail_pdf_converter.elements import register_element_type

register_element_type(
    CalloutElement,
    description="A highlighted callout/admonition box. Provide `text` and `variant` (one of info, warning, danger).",
)
```

**3. Map it to a block** on a custom registry, and make sure your page's StreamField defines that block:

```python
registry.register("callout", lambda el: ("callout", {"text": el.text, "variant": el.variant}))
```

Anything the AI emits that has no registered converter (or no matching block on the page) still falls back to a paragraph, so experimenting with a new type is safe — content is never lost while you iterate.

## Which PDFs make good pages?

The AI classifies content probabilistically, so results vary with document quality. Well-structured, text-based PDFs (reports, guides, policies) convert cleanly; heavily designed or scanned documents may need manual tidy-up in the editor afterward. The paragraph fallback means the page is always *complete*, even when a block type is wrong — editors refine rather than reconstruct.
