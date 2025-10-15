"""
Configuration for synthetic UI generation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class UIType(str, Enum):
    LOGIN_FORM = "login_form"
    SEARCH_PAGE = "search_page"
    CHECKOUT_FORM = "checkout_form"
    DATA_TABLE = "data_table"
    NAVIGATION_MENU = "navigation_menu"
    FORM_WIZARD = "form_wizard"
    CARD_GRID = "card_grid"
    SETTINGS_PANEL = "settings_panel"


class ElementType(str, Enum):
    BUTTON = "button"
    INPUT = "input"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    LINK = "link"
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    LIST = "list"
    TEXTAREA = "textarea"


@dataclass
class GenerationConfig:
    """Configuration for UI generation."""

    ui_types: list[UIType] = field(
        default_factory=lambda: [
            UIType.LOGIN_FORM,
            UIType.SEARCH_PAGE,
            UIType.CHECKOUT_FORM,
            UIType.DATA_TABLE,
        ]
    )
    num_samples: int = 100
    min_elements: int = 5
    max_elements: int = 20
    randomize_styles: bool = True
    randomize_layout: bool = True
    add_noise: bool = True
    screenshot_width: int = 1280
    screenshot_height: int = 720
    output_format: str = "jsonl"
    include_screenshots: bool = True
    seed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ui_types": [ui_type.value for ui_type in self.ui_types],
            "num_samples": self.num_samples,
            "min_elements": self.min_elements,
            "max_elements": self.max_elements,
            "randomize_styles": self.randomize_styles,
            "randomize_layout": self.randomize_layout,
            "add_noise": self.add_noise,
            "screenshot_width": self.screenshot_width,
            "screenshot_height": self.screenshot_height,
            "output_format": self.output_format,
            "include_screenshots": self.include_screenshots,
            "seed": self.seed,
        }


@dataclass
class LabelConfig:
    """Configuration for ground truth labeling."""

    include_bbox: bool = True
    include_element_type: bool = True
    include_semantic_role: bool = True
    include_visibility: bool = True
    include_interactivity: bool = True
    include_xpath: bool = True
    include_selector: bool = True
