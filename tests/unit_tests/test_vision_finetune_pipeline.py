"""
Unit tests for the vision fine-tuning pipeline.
"""

import asyncio
from tempfile import TemporaryDirectory

from evaluation.synthetic_ui import DatasetExporter, SyntheticUIGenerator
from evaluation.synthetic_ui.config import GenerationConfig, UIType
from evaluation.vision_finetune.config import FineTuneConfig, ProviderName
from evaluation.vision_finetune.dataset_prep import DatasetPreparator
from evaluation.vision_finetune.job_manager import FineTuneJobManager, FineTuneJobStatus
from evaluation.vision_finetune.pipeline import VisionFinetuner
from skyvern.forge.sdk.api.llm import config_registry


async def _run_finetune(tmpdir: str) -> tuple[str, FineTuneJobManager]:
    generation_config = GenerationConfig(num_samples=3, ui_types=[UIType.LOGIN_FORM], include_screenshots=True)
    generator = SyntheticUIGenerator(generation_config)
    layouts = generator.generate_batch(count=3)

    exporter = DatasetExporter(output_dir=tmpdir, include_screenshots=True)
    dataset_path = exporter.export_jsonl(layouts, filename="synthetic_ui.jsonl")

    ft_config = FineTuneConfig(
        dataset_path=dataset_path,
        output_dir=f"{tmpdir}/finetune",
        provider=ProviderName.OPENAI,
        base_model="gpt-4o-mini",
        job_name="ft_test_job",
        register_llm_key="OPENAI_TEST_SYNTHETIC_MODEL",
    )

    job_manager = FineTuneJobManager(storage_path=f"{tmpdir}/jobs.json")
    finetuner = VisionFinetuner(job_manager=job_manager)

    job = await finetuner.start_finetune(ft_config)
    assert job.status == FineTuneJobStatus.COMPLETED
    assert job.model_name is not None
    assert job.metrics.get("train_samples") == 2  # 90/10 split -> 2 train samples for 3 total

    registered_config = config_registry.LLMConfigRegistry.get_config("OPENAI_TEST_SYNTHETIC_MODEL")
    assert registered_config.model_name == job.model_name
    assert registered_config.supports_vision is True

    return job.job_id, job_manager


def test_dataset_preparator_stats():
    generation_config = GenerationConfig(num_samples=2, ui_types=[UIType.SEARCH_PAGE])
    generator = SyntheticUIGenerator(generation_config)
    layout = generator.generate_layout(ui_type=UIType.SEARCH_PAGE)

    with TemporaryDirectory() as tmpdir:
        exporter = DatasetExporter(output_dir=tmpdir)
        dataset_path = exporter.export_jsonl([layout], filename="single.jsonl")

        preparator = DatasetPreparator(provider=ProviderName.OPENAI)
        stats = preparator.compute_stats(dataset_path)
        assert stats.total_samples == 1
        assert stats.unique_layouts == 1
        assert stats.avg_components_per_layout > 0


def test_vision_finetune_pipeline_registers_model():
    original_configs = dict(config_registry.LLMConfigRegistry._configs)

    with TemporaryDirectory() as tmpdir:
        job_id = asyncio.run(_run_finetune(tmpdir))
        assert job_id[0] in job_id[1].jobs

    config_registry.LLMConfigRegistry._configs = original_configs
