"""
Dataclasses describing synthetic UI components and layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from evaluation.synthetic_ui.config import ElementType


@dataclass(slots=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    def as_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    def intersects(self, other: "BoundingBox") -> bool:
        if self.x + self.width <= other.x:
            return False
        if other.x + other.width <= self.x:
            return False
        if self.y + self.height <= other.y:
            return False
        if other.y + other.height <= self.y:
            return False
        return True

    def contains_point(self, x: int, y: int) -> bool:
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height


@dataclass(slots=True)
class SyntheticUIComponent:
    component_id: str
    element_type: ElementType
    text: str
    bounding_box: BoundingBox
    interactive: bool = False
    action: Literal["click", "type", "select", "toggle", "hover"] | None = None
    semantic_role: str | None = None
    anchor_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        element_type: ElementType,
        text: str,
        bounding_box: BoundingBox,
        interactive: bool,
        action: Literal["click", "type", "select", "toggle", "hover"] | None,
        semantic_role: str | None,
        anchor_text: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> "SyntheticUIComponent":
        return cls(
            component_id=str(uuid4()),
            element_type=element_type,
            text=text,
            bounding_box=bounding_box,
            interactive=interactive,
            action=action,
            semantic_role=semantic_role,
            anchor_text=anchor_text,
            metadata=metadata or {},
        )

    def to_label(self) -> dict[str, Any]:
        label = {
            "component_id": self.component_id,
            "element_type": self.element_type.value,
            "text": self.text,
            "bbox": self.bounding_box.as_dict(),
            "interactive": self.interactive,
        }
        if self.action:
            label["action"] = self.action
        if self.semantic_role:
            label["semantic_role"] = self.semantic_role
        if self.anchor_text:
            label["anchor_text"] = self.anchor_text
        if self.metadata:
            label["metadata"] = self.metadata
        return label


@dataclass(slots=True)
class SyntheticUIInteraction:
    component_id: str
    description: str
    expected_action: Literal["click", "type", "select", "toggle", "hover"]
    anchor_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "description": self.description,
            "expected_action": self.expected_action,
            "anchor_text": self.anchor_text,
        }


@dataclass(slots=True)
class SemanticAnchor:
    component_id: str
    label: str
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "label": self.label,
            "hints": self.hints,
        }


@dataclass
class SyntheticUILayout:
    layout_id: str
    width: int
    height: int
    components: list[SyntheticUIComponent]
    interactions: list[SyntheticUIInteraction] = field(default_factory=list)
    anchors: list[SemanticAnchor] = field(default_factory=list)
    html: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "width": self.width,
            "height": self.height,
            "components": [component.to_label() for component in self.components],
            "interactions": [interaction.to_dict() for interaction in self.interactions],
            "anchors": [anchor.to_dict() for anchor in self.anchors],
            "html": self.html,
        }
