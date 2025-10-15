"""
Main fine-tuning pipeline orchestration.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import structlog

from evaluation.vision_finetune.config import FineTuneConfig, ProviderName
from evaluation.vision_finetune.dataset_prep import DatasetPreparator
from evaluation.vision_finetune.job_manager import FineTuneJob, FineTuneJobManager, FineTuneJobStatus
from evaluation.vision_finetune.providers import CustomProvider, GeminiProvider, OpenAIProvider
from evaluation.vision_finetune.providers.base import BaseProvider
from skyvern.forge.sdk.api.llm.config_registry import LLMConfigRegistry
from skyvern.forge.sdk.api.llm.models import LLMConfig

LOG = structlog.get_logger(__name__)


class VisionFinetuner:
    def __init__(self, job_manager: FineTuneJobManager | None = None):
        self.job_manager = job_manager or FineTuneJobManager()

    def _get_provider(self, config: FineTuneConfig) -> BaseProvider:
        if config.provider == ProviderName.OPENAI:
            return OpenAIProvider()
        elif config.provider == ProviderName.GEMINI:
            return GeminiProvider()
        elif config.provider == ProviderName.CUSTOM:
            return CustomProvider()
        else:
            msg = f"Unknown provider: {config.provider}"
            raise ValueError(msg)

    async def start_finetune(self, config: FineTuneConfig) -> FineTuneJob:
        LOG.info("Starting fine-tune job", provider=config.provider.value, base_model=config.base_model)

        preparator = DatasetPreparator(provider=config.provider, validation_split=0.1)
        dataset_paths = preparator.prepare(config.dataset_path, config.output_dir / "prepared")

        provider = self._get_provider(config)
        provider_job_id = await provider.start_finetune(config, dataset_paths["train"], dataset_paths["validation"])

        job = FineTuneJob(
            job_id=config.job_name or f"ft-{uuid4().hex[:12]}",
            provider=config.provider.value,
            status=FineTuneJobStatus.RUNNING,
            dataset_paths={k: str(v) for k, v in dataset_paths.items()},
            config=config.to_dict(),
        )
        job.output_artifact = provider_job_id
        self.job_manager.create_job(job)

        status = await provider.get_job_status(provider_job_id)
        if status["status"] == FineTuneJobStatus.COMPLETED.value:
            model_name = await provider.get_model_name(provider_job_id)
            self.job_manager.update_status(
                job.job_id, FineTuneJobStatus.COMPLETED, metrics=status.get("metrics", {}), model_name=model_name
            )
            LOG.info("Fine-tune job completed", job_id=job.job_id, model_name=model_name)

            if config.register_llm_key and model_name:
                self._register_model(config.register_llm_key, model_name, config)
        else:
            self.job_manager.update_status(job.job_id, FineTuneJobStatus(status["status"]))

        return self.job_manager.get_job(job.job_id) or job

    async def check_status(self, job_id: str) -> FineTuneJob | None:
        job = self.job_manager.get_job(job_id)
        if not job:
            LOG.error("Job not found", job_id=job_id)
            return None
        LOG.info("Checking job status", job_id=job_id, status=job.status.value)
        return job

    def _register_model(self, llm_key: str, model_name: str, config: FineTuneConfig) -> None:
        LOG.info("Registering fine-tuned model to config_registry", llm_key=llm_key, model_name=model_name)
        try:
            env_vars = {
                ProviderName.OPENAI: ["OPENAI_API_KEY"],
                ProviderName.GEMINI: ["GEMINI_API_KEY"],
                ProviderName.CUSTOM: [],
            }
            LLMConfigRegistry.register_config(
                llm_key,
                LLMConfig(
                    model_name=model_name,
                    required_env_vars=env_vars.get(config.provider, []),
                    supports_vision=True,
                    add_assistant_prefix=False,
                ),
            )
            LOG.info("Model registered successfully", llm_key=llm_key)
        except Exception as e:
            LOG.error("Failed to register model", llm_key=llm_key, error=str(e))

    async def download_model(self, job_id: str, output_path: Path) -> Path | None:
        job = self.job_manager.get_job(job_id)
        if not job or not job.model_name:
            LOG.error("Job or model name not found", job_id=job_id)
            return None

        config_dict = job.config
        provider_name = ProviderName(config_dict["provider"])
        config = FineTuneConfig(
            dataset_path=Path(config_dict["dataset_path"]),
            output_dir=Path(config_dict["output_dir"]),
            provider=provider_name,
            base_model=config_dict.get("base_model", "gpt-4o-mini"),
        )

        provider = self._get_provider(config)
        artifact_path = await provider.download_model(job.model_name, output_path)
        LOG.info("Model artifact downloaded", job_id=job_id, artifact_path=str(artifact_path))
        return artifact_path


__all__ = ["VisionFinetuner", "FineTuneJob"]
