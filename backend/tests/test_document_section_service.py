from app.services.document_section_service import DocumentSectionService


def test_document_section_service_preserves_pdf_page_labels():
    text = (
        "[[GEMMALENS_PDF_PAGE:1]]\n"
        "Abstract\n"
        "Batch Normalization reduces internal covariate shift. It improves optimization. "
        "[[GEMMALENS_PDF_PAGE:2]]\n"
        "The method estimates mini-batch statistics. This page explains learned scale and shift parameters."
    )

    sections = DocumentSectionService().split_with_labels(text)

    assert [section.source_label for section in sections] == ["PDF page 1", "PDF page 2"]
    assert " ".join(sections[0].text.split()).startswith("Abstract Batch Normalization")
    assert "GEMMALENS_PDF_PAGE" not in sections[0].text
    assert sections[1].text.startswith("The method estimates")
