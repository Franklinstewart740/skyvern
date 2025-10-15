# Synthetic UI Generator

This module generates randomized web layouts, forms, and interactions for training and evaluation purposes.

## Overview

The Synthetic UI Generator creates HTML-based user interfaces with randomized:
- Login forms
- Search pages
- Checkout forms
- Data tables
- Navigation menus
- Form wizards

Each generated UI comes with ground truth labels for:
- Element bounding boxes
- Interactive elements
- Semantic roles
- Action targets
- XPath/CSS selectors

## Usage

### Basic Generation

```python
from evaluation.synthetic_ui import SyntheticUIGenerator, DatasetExporter
from evaluation.synthetic_ui.config import GenerationConfig, UIType

# Configure generation
config = GenerationConfig(
    ui_types=[UIType.LOGIN_FORM, UIType.SEARCH_PAGE],
    num_samples=100,
    randomize_styles=True,
    screenshot_width=1280,
    screenshot_height=720,
)

# Generate layouts
generator = SyntheticUIGenerator(config)
layouts = generator.generate_batch(count=50)

# Export dataset
exporter = DatasetExporter(output_dir="./datasets/synthetic_ui")
exporter.export_jsonl(layouts, filename="ui_dataset.jsonl")
exporter.save_html_files(layouts, prefix="ui_sample")
```

### Generate for Vision Fine-tuning

```python
from evaluation.synthetic_ui import SyntheticUIGenerator, DatasetExporter
from evaluation.synthetic_ui.config import GenerationConfig

config = GenerationConfig(num_samples=500, include_screenshots=True)
generator = SyntheticUIGenerator(config)
layouts = generator.generate_batch()

exporter = DatasetExporter(output_dir="./datasets/vision_finetune", include_screenshots=True)
exporter.export_vision_finetune_format(
    layouts,
    filename="openai_finetune.jsonl",
    provider="openai"
)
```

### Custom UI Types

You can extend the generator by adding custom template functions:

```python
from evaluation.synthetic_ui.generator import TEMPLATE_REGISTRY
from evaluation.synthetic_ui.config import UIType

def generate_custom_ui(colors):
    # Your custom UI generation logic
    return html, components, interactions, anchors

# Register the template
TEMPLATE_REGISTRY[UIType.CUSTOM] = generate_custom_ui
```

## Dataset Format

### JSONL Format

Each line contains:
```json
{
  "layout_id": "uuid",
  "html": "<html>...</html>",
  "ground_truth": {
    "components": [
      {
        "component_id": "uuid",
        "element_type": "button",
        "text": "Submit",
        "bbox": {"x": 100, "y": 200, "width": 120, "height": 40},
        "interactive": true,
        "action": "click",
        "semantic_role": "submit_button"
      }
    ],
    "interactions": [...],
    "anchors": [...]
  }
}
```

## Configuration Options

- `ui_types`: List of UI types to generate
- `num_samples`: Number of layouts to generate
- `min_elements`: Minimum elements per layout
- `max_elements`: Maximum elements per layout
- `randomize_styles`: Randomize colors and styling
- `randomize_layout`: Randomize element positions
- `screenshot_width`: Width of screenshots
- `screenshot_height`: Height of screenshots
- `include_screenshots`: Generate screenshot images
- `seed`: Random seed for reproducibility

## Ground Truth Labels

The labeling system captures:
- **Bounding boxes**: Precise element coordinates
- **Element types**: Button, input, select, etc.
- **Semantic roles**: Purpose of each element (login button, email field)
- **Interactions**: Expected user actions
- **Anchors**: Text hints for element identification
- **XPath/CSS selectors**: DOM traversal paths
