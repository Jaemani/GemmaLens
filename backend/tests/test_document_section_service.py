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


def test_document_section_service_merges_short_page_footer_orphans():
    text = (
        "[[GEMMALENS_PDF_PAGE:3]]\n"
        "Network Architectures. We have tested various plain and residual nets. "
        "The plain baseline is inspired by VGG nets and uses lower complexity than VGG. "
        "Our 34-layer baseline has 3.6 billion FLOPs, which is only 18% of VGG-19. 3 "
        "[[GEMMALENS_PDF_PAGE:4]]\n"
        "Based on the above plain network, we insert shortcut connections that turn the network into a residual version."
    )

    sections = DocumentSectionService().split_with_labels(text)

    assert len(sections) == 2
    assert "Our 34-layer baseline" in sections[0].text
    assert not sections[1].text.startswith("Our 34-layer baseline")


def test_document_section_service_skips_conv_table_artifacts():
    table = " ".join(
        [
            "7x7 conv, 64, /2 pool, /2",
            "3x3 conv, 64 3x3 conv, 64 3x3 conv, 128, /2",
            "3x3 conv, 256 3x3 conv, 256 3x3 conv, 512, /2 pool",
            "3x3 conv, 512 3x3 conv, 512 avg pool fc 1000",
        ]
        * 5
    )
    text = (
        "[[GEMMALENS_PDF_PAGE:4]]\n"
        f"{table} "
        "[[GEMMALENS_PDF_PAGE:5]]\n"
        "Based on the above plain network, we insert shortcut connections that turn the network into a residual version. "
        "Projection shortcuts are used when dimensions need to match."
    )

    sections = DocumentSectionService().split_with_labels(text)
    joined = " ".join(section.text for section in sections)

    assert "7x7 conv" not in joined
    assert "Based on the above plain network" in joined


def test_document_section_service_skips_imagenet_architecture_table_artifacts():
    table = (
        "layer nameoutput size 18-layer 34-layer 50-layer 101-layer 152-layer conv1 112×112 7×7, 64, stride 2 "
        "conv2x 56×56 3×3 max pool, stride 2 [ 3×3, 64 3×3, 64 ] ×2 "
        "conv3x 28×28 [ 3×3, 128 3×3, 128 ] ×4 conv4x 14×14 [ 3×3, 256 3×3, 256 ] ×6 "
        "conv5x 7×7 [ 3×3, 512 3×3, 512 ] ×3 average pool, 1000-d fc, softmax "
        "FLOPs 1.8×109 3.6×109 3.8×109 7.6×109 11.3×109 Table 1. Architectures for ImageNet."
    )
    text = (
        "[[GEMMALENS_PDF_PAGE:6]]\n"
        f"{table} "
        "[[GEMMALENS_PDF_PAGE:7]]\n"
        "Experiments on ImageNet compare plain networks and residual networks by top-1 and top-5 error."
    )

    sections = DocumentSectionService().split_with_labels(text)
    joined = " ".join(section.text for section in sections)

    assert "layer nameoutput size" not in joined
    assert "Experiments on ImageNet" in joined
