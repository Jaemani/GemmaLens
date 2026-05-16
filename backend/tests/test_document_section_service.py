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


def test_document_section_service_skips_short_equation_fragments():
    text = (
        "[[GEMMALENS_PDF_PAGE:1]]\n"
        "The output is computed as a weighted sum 3. "
        "Scaled Dot-Product Attention uses queries, keys, and values to compute attention weights. "
        "The softmax function turns query-key scores into weights that combine the values."
    )

    sections = DocumentSectionService().split_with_labels(text)
    joined = " ".join(section.text for section in sections)

    assert "weighted sum 3" not in joined
    assert "Scaled Dot-Product Attention" in joined


def test_document_section_service_merges_dangling_pdf_hyphen_page_breaks():
    text = (
        "[[GEMMALENS_PDF_PAGE:2]]\n"
        "On the contrary, our formulation always learns residual functions; our identity shortcuts are never closed, "
        "and all information is always passed through, with additional residual functions to be learned. In addition, high- 2 "
        "[[GEMMALENS_PDF_PAGE:3]]\n"
        "way networks have not demonstrated accuracy gains with extremely increased depth. "
        "Residual Learning Let us consider H(x) as an underlying mapping to be fit by a few stacked layers."
    )

    sections = DocumentSectionService().split_with_labels(text)

    assert len(sections) == 1
    assert "highway networks" in sections[0].text
    assert "high- 2" not in sections[0].text
    assert sections[0].source_label == "PDF page 2"
