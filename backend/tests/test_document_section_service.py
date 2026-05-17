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


def test_document_section_service_uses_inline_headings_as_boundaries():
    text = (
        "[[GEMMALENS_PDF_PAGE:151]]\n"
        "4.2 Convex optimization The objective function must be convex. "
        "Abstract form convex optimization problem It is important to note a subtlety in our definition of convex optimization problem. "
        "This problem is not a convex optimization problem in standard form since the equality constraint is not affine. "
        "Concave maximization problems With a slight abuse of notation, we also refer to concave maximization problems."
    )

    sections = DocumentSectionService().split_with_labels(text)

    assert len(sections) >= 3
    assert sections[0].text.startswith("4.2 Convex optimization")
    assert any(section.text.startswith("Abstract form convex optimization problem") for section in sections)
    assert any(section.text.startswith("Concave maximization problems") for section in sections)
    assert all(section.source_label == "PDF page 151" for section in sections)


def test_document_section_service_never_splits_decimal_archive_references_as_sections():
    text = (
        "[[GEMMALENS_PDF_PAGE:28]]\n"
        "The dataset is available from public archives 28.\n"
        "4 and includes metadata collected across multiple releases. "
        "This paragraph explains the source and should remain one learning section, not a numbered heading. "
        "The following sentence continues the same discussion with enough content for analysis."
    )

    sections = DocumentSectionService().split_with_labels(text)
    joined = " ".join(section.text for section in sections)

    assert len(sections) == 1
    assert "archives 28.4" in joined
    assert sections[0].title is None


def test_document_section_service_keeps_real_numbered_headings_after_decimal_guard():
    text = (
        "[[GEMMALENS_PDF_PAGE:4]]\n"
        "4 Why Self-Attention In this section we compare aspects of self-attention layers to recurrent and convolutional layers. "
        "The goal is to understand long-range dependencies and computational complexity."
    )

    sections = DocumentSectionService().split_with_labels(text)

    assert len(sections) == 1
    assert sections[0].title == "4 Why Self-Attention"


def test_document_section_service_tracks_logical_titles_across_pages():
    text = (
        "[[GEMMALENS_PDF_PAGE:1]]\n"
        "Abstract The Transformer is an attention-only architecture for sequence transduction. "
        "It improves parallelization and translation quality. "
        "1 Introduction Recurrent models process tokens sequentially and limit parallelization. "
        "[[GEMMALENS_PDF_PAGE:2]]\n"
        "This inherently sequential nature precludes parallelization within training examples. "
        "2 Background The goal of reducing sequential computation also forms the foundation of ByteNet and ConvS2S. "
        "3 Model Architecture Most competitive neural sequence transduction models have an encoder-decoder structure. "
        "3.1 Encoder and Decoder Stacks Encoder: The encoder is composed of a stack of layers."
    )

    sections = DocumentSectionService().split_with_labels(text)

    titles = [section.title for section in sections]
    assert titles[:2] == ["Abstract", "1 Introduction"]
    introduction = next(section for section in sections if section.title == "1 Introduction")
    assert "precludes parallelization within training examples" in introduction.text
    assert "2 Background" in titles
    assert "3 Model Architecture" in titles
    assert "3.1 Encoder and Decoder Stacks" in titles


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


def test_document_section_service_skips_imagenet_result_table_artifacts():
    table = (
        "model top-1 err. top-5 err. VGG-16 28.07 9.33 GoogLeNet 9.15 PReLU-net 24.27 7.38 "
        "plain-34 28.54 10.02 ResNet-34 A 25.03 7.76 ResNet-34 B 24.52 7.46 ResNet-50 22.85 6.71 "
        "Error rates (%, 10-crop testing) on ImageNet validation. method top-1 err. top-5 err. "
        "VGG 24.4 7.1 ResNet-152 19.38 4.49 Error rates (%) of single-model results on the ImageNet validation set."
    )
    text = (
        "[[GEMMALENS_PDF_PAGE:7]]\n"
        f"{table} "
        "[[GEMMALENS_PDF_PAGE:8]]\n"
        "Next we investigate projection shortcuts and compare options A, B, and C."
    )

    sections = DocumentSectionService().split_with_labels(text)
    joined = " ".join(section.text for section in sections)

    assert "model top-1 err" not in joined
    assert "Next we investigate projection shortcuts" in joined


def test_document_section_service_skips_resnet_cifar_figure_artifacts():
    figure = (
        "0 1 2 3 4 5 60 5 10 20 iter. (1e4) error (%) plain-20 plain-32 plain-44 plain-56 "
        "ResNet-20 ResNet-32 ResNet-44 ResNet-56 ResNet-110 Figure 6. Training on CIFAR-10. "
        "Dashed lines denote training error, and bold lines denote testing error. Left: plain networks. Middle: ResNets. "
        "Standard deviations (std) of layer responses on CIFAR-10. plain-20 plain-56 ResNet-20 ResNet-56 ResNet-110."
    )
    text = (
        "[[GEMMALENS_PDF_PAGE:8]]\n"
        f"{figure} "
        "[[GEMMALENS_PDF_PAGE:9]]\n"
        "The 1202-layer network is unnecessarily deep and starts to expose optimization issues."
    )

    sections = DocumentSectionService().split_with_labels(text)
    joined = " ".join(section.text for section in sections)

    assert "iter. (1e4)" not in joined
    assert "Dashed lines denote training error" not in joined
    assert "The 1202-layer network" in joined


def test_document_section_service_skips_bibliography_artifacts_but_keeps_appendix():
    references = (
        "References [1] Y. Bengio, P. Simard, and P. Frasconi. Learning long-term dependencies with gradient descent is difficult. "
        "IEEE Transactions on Neural Networks, 1994. [2] C. M. Bishop. Neural networks for pattern recognition. Oxford university press, 1995. "
        "[3] S. Ioffe and C. Szegedy. Batch normalization. In ICML, 2015. [4] S. Ren et al. Faster R-CNN. In NIPS, 2015."
    )
    appendix = (
        "A. Object Detection Baselines In this section we introduce our detection method based on the baseline Faster R-CNN system. "
        "The models are initialized by the ImageNet classification models, and then fine-tuned on the object detection data."
    )
    text = (
        "[[GEMMALENS_PDF_PAGE:9]]\n"
        f"{references} "
        "[[GEMMALENS_PDF_PAGE:10]]\n"
        f"{appendix}"
    )

    sections = DocumentSectionService().split_with_labels(text)
    joined = " ".join(section.text for section in sections)

    assert "References [1]" not in joined
    assert "IEEE Transactions" not in joined
    assert "Object Detection Baselines" in joined
