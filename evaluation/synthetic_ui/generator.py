"""
Synthetic UI generator that produces randomized layouts and metadata.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from evaluation.synthetic_ui.components import SemanticAnchor, SyntheticUILayout, SyntheticUIInteraction
from evaluation.synthetic_ui.config import GenerationConfig, UIType
from evaluation.synthetic_ui.templates import (
    generate_checkout_form_html,
    generate_data_table_html,
    generate_login_form_html,
    generate_search_page_html,
    get_color_palette,
)

TemplateGenerator = Callable[[dict[str, str]], tuple[str, list, list, list]]


TEMPLATE_REGISTRY: dict[UIType, TemplateGenerator] = {
    UIType.LOGIN_FORM: generate_login_form_html,
    UIType.SEARCH_PAGE: generate_search_page_html,
    UIType.CHECKOUT_FORM: generate_checkout_form_html,
    UIType.DATA_TABLE: generate_data_table_html,
}


@dataclass(slots=True)
class SyntheticUIGenerator:
    config: GenerationConfig

    def __init__(self, config: GenerationConfig | None = None):
        self.config = config or GenerationConfig()
        self._rng = random.Random(self.config.seed)

    def _get_rng(self, seed: int | None) -> random.Random:
        if seed is None:
            seed = self._rng.randint(0, 100_000_000)
        return random.Random(seed)

    def generate_layout(self, ui_type: UIType | None = None, seed: int | None = None) -> SyntheticUILayout:
        rng = self._get_rng(seed)
        available_types = [ui for ui in self.config.ui_types if ui in TEMPLATE_REGISTRY]
        if not available_types:
            msg = "No available UI types with registered templates."
            raise ValueError(msg)
        ui_type = ui_type or rng.choice(available_types)
        template = TEMPLATE_REGISTRY[ui_type]
        colors = get_color_palette(rng)
        html, components, interactions, anchors = template(colors)

        layout = SyntheticUILayout(
            layout_id=str(uuid4()),
            width=self.config.screenshot_width,
            height=self.config.screenshot_height,
            components=components,
            interactions=[interaction for interaction in interactions if isinstance(interaction, SyntheticUIInteraction)],
            anchors=[anchor for anchor in anchors if isinstance(anchor, SemanticAnchor)],
            html=html,
        )
        return layout

    def generate_batch(self, count: int | None = None) -> list[SyntheticUILayout]:
        total = count or self.config.num_samples
        return [self.generate_layout(seed=self._rng.randint(0, 1_000_000_000)) for _ in range(total)]
