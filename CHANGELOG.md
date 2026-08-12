# Changelog

All notable changes to this project will be documented here.

## Unreleased

### Fixed

- Docs and test settings referenced `django_tasks.backends.database`, removed in django-tasks 0.12. Corrected to `django_tasks_db`.
- `django-tasks-db` is now an optional `db-backend` extra rather than a hard dependency, since it conflicts with the `django-tasks` version older supported Wagtail releases pin.
- Getting-started docs told readers to run `db_worker --queue-name pdf_conversion`, which binds to the default `ImmediateBackend` instead of the DB-backed queue. Corrected to `db_worker --backend pdf_conversion`.

### Features

#### Create Wagtail pages from PDFs

- New opt-in capability to turn a converted PDF into a real Wagtail Page with a StreamField body and the full editor workflow, alongside the existing Markdown-to-HTML output.
- The AI emits schema-constrained typed elements (heading, paragraph, image, quote, code, table, list); a pluggable registry maps them to blocks, routing anything unrecognised to a paragraph so no content is silently dropped.
- Images are resolved to already-stored Wagtail Images by content hash.
- Programmatic API: `convert_pdf_to_page()` / `create_page_from_elements()`. Admin: an opt-in **Create page** action on documents, with a confirmation step.
- Enabled via `ENABLE_PAGE_CREATION`, `PAGE_CREATION_MODEL`, and `PAGE_CREATION_PARENT_ID` settings. See the "Creating pages from PDFs" guide.

## [0.1.0rc1](https://github.com/torchbox/wagtail-pdf-converter/releases/tag/v0.1.0rc1) - 2026-04-23

### Features

#### Core Conversion Engine

- `HybridPDFConverter` for PDF-to-Markdown conversion using [PyMuPDF](https://github.com/pymupdf/pymupdf) and AI backends.
- Automatic PDF splitting for large documents (50-page chunks with overlap).
- Image extraction and processing, including support for masks and split images.
- Hallucinated link detection and repair to ensure content integrity.

#### AI Integration

- Pluggable backend system (Google Gemini via [`google-genai`](https://github.com/googleapis/python-genai) implemented as default).
- Context-aware page processing for better continuity across chunks.
- Automated image description generation for accessibility.

#### Wagtail Integration

- `PDFConversionMixin` for easy integration with existing Wagtail Document model.
- `DocumentConversion` model for efficient storage of heavy Markdown payloads.
- Integrated admin UI for monitoring conversion status and editing converted content.
- Support for background processing via [`django-tasks`](https://github.com/RealOrangeOne/django-tasks).

#### Markdown & A11y

- Custom `HeadingAnchorExtension` for accessible, linkable headings.
- Semantic HTML rendering from converted Markdown.

#### DX

- Optional Docker support for quick-start Postgres development.
- Extensive docs for configuration and customization.
- Comprehensive test suite ([pytest](https://docs.pytest.org/en/stable/)) with >90% coverage.
