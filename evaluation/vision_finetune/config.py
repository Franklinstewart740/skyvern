"""
Fine-tuning configuration models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ProviderName(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    CUSTOM = "custom"


@dataclass(slots=True)
class FineTuneHyperparameters:
    learning_rate: float = 1e-4
    batch_size: int = 8
    num_epochs: int = 3
    weight_decay: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "num_epochs": self.num_epochs,
            "weight_decay": self.weight_decay,
        }


@dataclass(slots=True)
class FineTuneConfig:
    dataset_path: Path
    output_dir: Path
    provider: ProviderName = ProviderName.OPENAI
    base_model: str = "gpt-4o-mini"
    vision_feature: str = "object-detection"
    job_name: str | None = None
    description: str | None = None
    hyperparameters: FineTuneHyperparameters = field(default_factory=FineTuneHyperparameters)
    metadata: dict[str, Any] = field(default_factory=dict)
    register_llm_key: str | None = None

    def __post_init__(self) -> None:
        self.dataset_path = Path(self.dataset_path)
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "dataset_path": str(self.dataset_path),
            "output_dir": str(self.output_dir),
            "provider": self.provider.value,
            "base_model": self.base_model,
            "vision_feature": self.vision_feature,
            "hyperparameters": self.hyperparameters.to_dict(),
            "metadata": self.metadata,
        }
        if self.job_name:
            data["job_name"] = self.job_name
        if self.description:
            data["description"] = self.description
        if self.register_llm_key:
            data["register_llm_key"] = self.register_llm_key
        return data
