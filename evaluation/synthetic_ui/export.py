"""
Export synthetic UI datasets to various formats.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from evaluation.synthetic_ui.components import SyntheticUILayout
from evaluation.synthetic_ui.labeling import UILabelingHelper
from evaluation.synthetic_ui.render import LayoutRenderer

LOG = structlog.get_logger(__name__)


@dataclass
class DatasetSample:
    layout_id: str
    html: str
    ground_truth: dict[str, Any]
    screenshot: bytes | None = None


@dataclass(slots=True)
class DatasetExporter:
    def __init__(self, output_dir: str | Path, include_screenshots: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.labeling_helper = UILabelingHelper()
        self.include_screenshots = include_screenshots
        self._renderer = LayoutRenderer() if include_screenshots else None

    def export_jsonl(self, layouts: list[SyntheticUILayout], filename: str = "dataset.jsonl") -> Path:
        output_path = self.output_dir / filename
        LOG.info("Exporting dataset to JSONL", output_path=str(output_path), num_samples=len(layouts))

        with open(output_path, "w", encoding="utf-8") as f:
            for layout in layouts:
                sample = self._layout_to_sample(layout)
                record = {
                    "layout_id": sample.layout_id,
                    "html": sample.html,
                    "ground_truth": sample.ground_truth,
                }
                if sample.screenshot:
                    record["screenshot_base64"] = base64.b64encode(sample.screenshot).decode("utf-8")
                f.write(json.dumps(record) + "\n")

        LOG.info("Export complete", output_path=str(output_path))
        return output_path

    def export_json(self, layouts: list[SyntheticUILayout], filename: str = "dataset.json") -> Path:
        output_path = self.output_dir / filename
        LOG.info("Exporting dataset to JSON", output_path=str(output_path), num_samples=len(layouts))

        samples = []
        for layout in layouts:
            sample = self._layout_to_sample(layout)
            record = {
                "layout_id": sample.layout_id,
                "html": sample.html,
                "ground_truth": sample.ground_truth,
            }
            if sample.screenshot:
                record["screenshot_base64"] = base64.b64encode(sample.screenshot).decode("utf-8")
            samples.append(record)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(samples, f, indent=2)

        LOG.info("Export complete", output_path=str(output_path))
        return output_path

    def export_vision_finetune_format(
        self, layouts: list[SyntheticUILayout], filename: str = "vision_finetune_data.jsonl", provider: str = "openai"
    ) -> Path:
        output_path = self.output_dir / filename
        LOG.info(
            "Exporting dataset for vision fine-tuning",
            output_path=str(output_path),
            num_samples=len(layouts),
            provider=provider,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            for layout in layouts:
                sample = self._layout_to_sample(layout)
                if provider == "openai":
                    record = self._format_for_openai(sample)
                elif provider == "gemini":
                    record = self._format_for_gemini(sample)
                else:
                    record = self._format_generic(sample)

                f.write(json.dumps(record) + "\n")

        LOG.info("Export complete", output_path=str(output_path))
        return output_path

    def _layout_to_sample(self, layout: SyntheticUILayout) -> DatasetSample:
        ground_truth = self.labeling_helper.to_json_serializable(layout)
        screenshot = None
        if self.include_screenshots and self._renderer:
            screenshot = self._renderer.render_to_bytes(layout)
        return DatasetSample(
            layout_id=layout.layout_id,
            html=layout.html or "",
            ground_truth=ground_truth,
            screenshot=screenshot,
        )

    def _format_for_openai(self, sample: DatasetSample) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": "You are a web element detection assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Identify all interactive elements in this UI."},
                    {"type": "image_url", "image_url": {"url": f"data:text/html;base64,{base64.b64encode(sample.html.encode()).decode()}"}},
                ],
            },
            {"role": "assistant", "content": json.dumps(sample.ground_truth)},
        ]
        return {"messages": messages}

    def _format_for_gemini(self, sample: DatasetSample) -> dict[str, Any]:
        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": "Identify all interactive elements in this UI."},
                        {"inline_data": {"mime_type": "text/html", "data": base64.b64encode(sample.html.encode()).decode()}},
                    ],
                },
                {"role": "model", "parts": [{"text": json.dumps(sample.ground_truth)}]},
            ]
        }

    def _format_generic(self, sample: DatasetSample) -> dict[str, Any]:
        return {
            "input": {
                "prompt": "Identify all interactive elements in this UI.",
                "html": sample.html,
            },
            "output": sample.ground_truth,
        }

    def save_html_files(self, layouts: list[SyntheticUILayout], prefix: str = "sample") -> list[Path]:
        html_dir = self.output_dir / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        LOG.info("Saving HTML files", output_dir=str(html_dir), num_samples=len(layouts))

        paths = []
        for idx, layout in enumerate(layouts):
            html_path = html_dir / f"{prefix}_{idx:05d}_{layout.layout_id}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(layout.html or "")
            paths.append(html_path)

        LOG.info("HTML files saved", count=len(paths))
        return paths
