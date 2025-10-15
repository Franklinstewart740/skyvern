"""
Render synthetic layouts to images.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from evaluation.synthetic_ui.components import SyntheticUILayout
from evaluation.synthetic_ui.config import ElementType


COLOR_MAP: dict[ElementType, tuple[int, int, int]] = {
    ElementType.BUTTON: (59, 130, 246),
    ElementType.INPUT: (16, 185, 129),
    ElementType.SELECT: (236, 72, 153),
    ElementType.CHECKBOX: (99, 102, 241),
    ElementType.RADIO: (249, 115, 22),
    ElementType.LINK: (129, 140, 248),
    ElementType.TEXT: (75, 85, 99),
    ElementType.IMAGE: (163, 163, 163),
    ElementType.TABLE: (37, 99, 235),
    ElementType.LIST: (168, 85, 247),
    ElementType.TEXTAREA: (16, 185, 129),
}


@dataclass(slots=True)
class LayoutRenderer:
    background_color: tuple[int, int, int] = (250, 250, 250)

    def render(self, layout: SyntheticUILayout) -> Image.Image:
        image = Image.new("RGB", (layout.width, layout.height), self.background_color)
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.load_default(size=12)
        except TypeError:
            font = ImageFont.load_default()

        for component in layout.components:
            bbox = component.bounding_box
            color = COLOR_MAP.get(component.element_type, (107, 114, 128))
            draw.rectangle(
                [bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height],
                fill=(color[0], color[1], color[2], 120),
                outline=(55, 65, 81),
                width=2,
            )
            text = component.text or component.element_type.value
            text_position = (bbox.x + 5, bbox.y + 5)
            draw.text(text_position, text, fill=(17, 24, 39), font=font)

        return image

    def render_to_bytes(self, layout: SyntheticUILayout, format: str = "PNG") -> bytes:
        image = self.render(layout)
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()
