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


def test_document_section_service_skips_pdf_attribution_sections():
    text = (
        "[[GEMMALENS_PDF_PAGE:1]]\n"
        "The Transformer is an attention-only architecture for sequence transduction. It improves parallelization. "
        "Llion also experimented with novel model variants, was responsible for our initial codebase, and efficient inference and visualizations. "
        "Work performed while at Google Brain. 31st Conference on Neural Information Processing Systems (NIPS 2017), Long Beach, CA, USA. "
        "[[GEMMALENS_PDF_PAGE:2]]\n"
        "Recurrent neural networks have been established as sequence modeling baselines. The Transformer reduces sequential computation."
    )

    sections = DocumentSectionService().split_with_labels(text)
    joined = " ".join(section.text for section in sections)

    assert "Llion also experimented" not in joined
    assert "Conference on Neural Information Processing Systems" not in joined
    assert any("The Transformer is an attention-only architecture" in section.text for section in sections)
    assert any("Recurrent neural networks" in section.text for section in sections)
