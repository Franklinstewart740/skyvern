"""
Prepare datasets for vision fine-tuning.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from evaluation.vision_finetune.config import ProviderName

LOG = structlog.get_logger(__name__)


@dataclass
class DatasetStats:
    total_samples: int
    unique_layouts: int
    avg_components_per_layout: float
    unique_element_types: set[str]


@dataclass(slots=True)
class DatasetPreparator:
    provider: ProviderName
    validation_split: float = 0.1

    def prepare(self, input_path: Path, output_dir: Path) -> dict[str, Path]:
        LOG.info("Preparing dataset for fine-tuning", input_path=str(input_path), provider=self.provider.value)

        if not input_path.exists():
            msg = f"Input dataset not found: {input_path}"
            raise FileNotFoundError(msg)

        output_dir.mkdir(parents=True, exist_ok=True)
        samples = self._load_samples(input_path)
        LOG.info(f"Loaded {len(samples)} samples from dataset")

        split_idx = int(len(samples) * (1 - self.validation_split))
        train_samples = samples[:split_idx]
        val_samples = samples[split_idx:]

        train_path = output_dir / "train.jsonl"
        val_path = output_dir / "validation.jsonl"

        if self.provider == ProviderName.OPENAI:
            self._write_openai_format(train_samples, train_path)
            self._write_openai_format(val_samples, val_path)
        elif self.provider == ProviderName.GEMINI:
            self._write_gemini_format(train_samples, train_path)
            self._write_gemini_format(val_samples, val_path)
        else:
            self._write_generic_format(train_samples, train_path)
            self._write_generic_format(val_samples, val_path)

        LOG.info(
            "Dataset preparation complete",
            train_samples=len(train_samples),
            val_samples=len(val_samples),
            train_path=str(train_path),
            val_path=str(val_path),
        )

        return {"train": train_path, "validation": val_path}

    def _load_samples(self, input_path: Path) -> list[dict[str, Any]]:
        samples = []
        with open(input_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
        return samples

    def _write_openai_format(self, samples: list[dict[str, Any]], output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                messages = [
                    {"role": "system", "content": "You are a web element detection assistant."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Identify all interactive elements in this UI."},
                        ],
                    },
                    {"role": "assistant", "content": json.dumps(sample.get("ground_truth", {}))},
                ]
                if "screenshot_base64" in sample:
                    messages[1]["content"].append(
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{sample['screenshot_base64']}"}}
                    )
                record = {"messages": messages}
                f.write(json.dumps(record) + "\n")

    def _write_gemini_format(self, samples: list[dict[str, Any]], output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                user_parts = [{"text": "Identify all interactive elements in this UI."}]
                if "screenshot_base64" in sample:
                    user_parts.append({"inline_data": {"mime_type": "image/png", "data": sample["screenshot_base64"]}})

                record = {
                    "contents": [
                        {"role": "user", "parts": user_parts},
                        {"role": "model", "parts": [{"text": json.dumps(sample.get("ground_truth", {}))}]},
                    ]
                }
                f.write(json.dumps(record) + "\n")

    def _write_generic_format(self, samples: list[dict[str, Any]], output_path: Path) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in samples:
                record = {
                    "input": {"prompt": "Identify all interactive elements in this UI.", "html": sample.get("html", "")},
                    "output": sample.get("ground_truth", {}),
                }
                if "screenshot_base64" in sample:
                    record["input"]["screenshot_base64"] = sample["screenshot_base64"]
                f.write(json.dumps(record) + "\n")

    def compute_stats(self, dataset_path: Path) -> DatasetStats:
        samples = self._load_samples(dataset_path)
        total_samples = len(samples)
        unique_layouts = len(set(s.get("layout_id", "") for s in samples))
        total_components = 0
        element_types = set()

        for sample in samples:
            gt = sample.get("ground_truth", {})
            components = gt.get("components", [])
            total_components += len(components)
            for comp in components:
                element_types.add(comp.get("element_type", "unknown"))

        avg_components = total_components / total_samples if total_samples > 0 else 0.0

        return DatasetStats(
            total_samples=total_samples,
            unique_layouts=unique_layouts,
            avg_components_per_layout=avg_components,
            unique_element_types=element_types,
        )
