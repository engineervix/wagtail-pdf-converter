import io

from unittest.mock import MagicMock, patch

import fitz
import pytest

from wagtail_pdf_converter.services import PDFConversionError
from wagtail_pdf_converter.services.converter import validate_pdf


def _encrypted_pdf_bytes() -> bytes:
    doc = fitz.open()
    doc.new_page()
    buf = io.BytesIO()
    doc.save(
        buf,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner",
        user_pw="secret",
        permissions=fitz.PDF_PERM_ACCESSIBILITY,
    )
    return buf.getvalue()


class TestValidatePdf:
    def test_valid_pdf_returns_page_count(self, valid_pdf_bytes):
        assert validate_pdf(valid_pdf_bytes) == 1

    def test_rejects_non_pdf_bytes(self):
        with pytest.raises(PDFConversionError, match="could not be opened"):
            validate_pdf(b"not a pdf at all")

    def test_rejects_password_protected_pdf(self):
        with pytest.raises(PDFConversionError, match="password-protected"):
            validate_pdf(_encrypted_pdf_bytes())

    def test_rejects_zero_page_pdf(self):
        mock_doc = MagicMock()
        mock_doc.needs_pass = False
        mock_doc.page_count = 0
        with patch("wagtail_pdf_converter.services.converter.fitz") as mock_fitz:
            mock_fitz.open.return_value = mock_doc
            with pytest.raises(PDFConversionError, match="no pages"):
                validate_pdf(b"irrelevant, fitz is mocked")
