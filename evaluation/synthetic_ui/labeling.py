"""
Helpers for generating ground truth labels for synthetic UIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evaluation.synthetic_ui.components import SyntheticUILayout
from evaluation.synthetic_ui.config import LabelConfig


@dataclass(slots=True)
class UILabelingHelper:
    config: LabelConfig

    def __init__(self, config: LabelConfig | None = None):
        self.config = config or LabelConfig()

    def build_ground_truth(self, layout: SyntheticUILayout) -> dict[str, Any]:
        component_labels: list[dict[str, Any]] = []
        for component in layout.components:
            label = component.to_label()
            if not self.config.include_bbox:
                label.pop("bbox", None)
            if not self.config.include_element_type:
                label.pop("element_type", None)
            if not self.config.include_interactivity:
                label.pop("interactive", None)
                label.pop("action", None)
            if not self.config.include_semantic_role:
                label.pop("semantic_role", None)
            if not self.config.include_selector:
                label.pop("anchor_text", None)
            if not self.config.include_visibility:
                label.pop("metadata", None)
            component_labels.append(label)

        interactions = [interaction.to_dict() for interaction in layout.interactions]
        anchors = [anchor.to_dict() for anchor in layout.anchors]

        ground_truth = {
            "layout_id": layout.layout_id,
            "components": component_labels,
            "interactions": interactions,
            "anchors": anchors,
        }

        if self.config.include_xpath:
            for component_label in ground_truth["components"]:
                component_id = component_label.get("component_id", "")
                component_label["xpath"] = f"//*[@id='{component_id}']"

        return ground_truth

    def to_json_serializable(self, layout: SyntheticUILayout) -> dict[str, Any]:
        ground_truth = self.build_ground_truth(layout)
        ground_truth["width"] = layout.width
        ground_truth["height"] = layout.height
        return ground_truth
