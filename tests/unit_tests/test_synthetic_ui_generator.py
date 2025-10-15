"""
Unit tests for the synthetic UI generator.
"""

from tempfile import TemporaryDirectory

from evaluation.synthetic_ui import DatasetExporter, SyntheticUIGenerator, UILabelingHelper
from evaluation.synthetic_ui.components import BoundingBox, SyntheticUIComponent
from evaluation.synthetic_ui.config import ElementType, GenerationConfig, LabelConfig, UIType


def test_generation_config_defaults():
    config = GenerationConfig()
    assert config.num_samples == 100
    assert config.min_elements == 5
    assert config.max_elements == 20
    assert config.randomize_styles is True


def test_bounding_box():
    bbox = BoundingBox(x=10, y=20, width=100, height=50)
    assert bbox.as_tuple() == (10, 20, 100, 50)
    assert bbox.as_dict() == {"x": 10, "y": 20, "width": 100, "height": 50}


def test_bounding_box_intersects():
    bbox1 = BoundingBox(0, 0, 100, 100)
    bbox2 = BoundingBox(50, 50, 100, 100)
    bbox3 = BoundingBox(200, 200, 50, 50)
    assert bbox1.intersects(bbox2)
    assert not bbox1.intersects(bbox3)


def test_bounding_box_contains_point():
    bbox = BoundingBox(10, 20, 100, 50)
    assert bbox.contains_point(50, 40)
    assert not bbox.contains_point(200, 200)


def test_synthetic_component_creation():
    comp = SyntheticUIComponent.create(
        element_type=ElementType.BUTTON,
        text="Submit",
        bounding_box=BoundingBox(100, 200, 80, 40),
        interactive=True,
        action="click",
        semantic_role="submit_button",
        anchor_text="Submit",
    )
    assert comp.element_type == ElementType.BUTTON
    assert comp.text == "Submit"
    assert comp.interactive is True
    assert comp.action == "click"


def test_generator_creates_layout():
    config = GenerationConfig(num_samples=1, ui_types=[UIType.LOGIN_FORM])
    generator = SyntheticUIGenerator(config)
    layout = generator.generate_layout(ui_type=UIType.LOGIN_FORM)
    assert layout.layout_id is not None
    assert layout.width == config.screenshot_width
    assert layout.height == config.screenshot_height
    assert len(layout.components) > 0


def test_generator_batch():
    config = GenerationConfig(num_samples=5, ui_types=[UIType.LOGIN_FORM, UIType.SEARCH_PAGE])
    generator = SyntheticUIGenerator(config)
    layouts = generator.generate_batch(count=3)
    assert len(layouts) == 3


def test_labeling_helper():
    config = GenerationConfig(ui_types=[UIType.LOGIN_FORM])
    generator = SyntheticUIGenerator(config)
    layout = generator.generate_layout(ui_type=UIType.LOGIN_FORM)
    helper = UILabelingHelper(LabelConfig())
    ground_truth = helper.build_ground_truth(layout)
    assert "layout_id" in ground_truth
    assert "components" in ground_truth
    assert isinstance(ground_truth["components"], list)


def test_exporter_jsonl():
    config = GenerationConfig(num_samples=2, ui_types=[UIType.LOGIN_FORM])
    generator = SyntheticUIGenerator(config)
    layouts = generator.generate_batch(count=2)

    with TemporaryDirectory() as tmpdir:
        exporter = DatasetExporter(output_dir=tmpdir)
        output_path = exporter.export_jsonl(layouts, filename="test_dataset.jsonl")
        assert output_path.exists()

        with open(output_path, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 2


def test_exporter_json():
    config = GenerationConfig(num_samples=2, ui_types=[UIType.SEARCH_PAGE])
    generator = SyntheticUIGenerator(config)
    layouts = generator.generate_batch(count=2)

    with TemporaryDirectory() as tmpdir:
        exporter = DatasetExporter(output_dir=tmpdir)
        output_path = exporter.export_json(layouts, filename="test_dataset.json")
        assert output_path.exists()


def test_exporter_vision_finetune_format():
    config = GenerationConfig(num_samples=1, ui_types=[UIType.CHECKOUT_FORM])
    generator = SyntheticUIGenerator(config)
    layouts = generator.generate_batch(count=1)

    with TemporaryDirectory() as tmpdir:
        exporter = DatasetExporter(output_dir=tmpdir)
        output_path = exporter.export_vision_finetune_format(layouts, provider="openai")
        assert output_path.exists()


def test_html_files_export():
    config = GenerationConfig(num_samples=2, ui_types=[UIType.DATA_TABLE])
    generator = SyntheticUIGenerator(config)
    layouts = generator.generate_batch(count=2)

    with TemporaryDirectory() as tmpdir:
        exporter = DatasetExporter(output_dir=tmpdir)
        html_paths = exporter.save_html_files(layouts, prefix="test")
        assert len(html_paths) == 2
        for path in html_paths:
            assert path.exists()
            assert path.suffix == ".html"
