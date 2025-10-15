#!/usr/bin/env python3
"""
Smoke test for synthetic UI generator and vision fine-tuning pipeline.
This script runs end-to-end generation, export, and fine-tuning steps.
"""

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import structlog
import typer

from evaluation.synthetic_ui import DatasetExporter, SyntheticUIGenerator
from evaluation.synthetic_ui.config import GenerationConfig, UIType
from evaluation.vision_finetune.config import FineTuneConfig, ProviderName
from evaluation.vision_finetune.dataset_prep import DatasetPreparator
from evaluation.vision_finetune.job_manager import FineTuneJobManager
from evaluation.vision_finetune.pipeline import VisionFinetuner

LOG = structlog.get_logger(__name__)


async def run_smoke_test(output_dir: str, num_samples: int = 10) -> None:
    LOG.info("Starting smoke test for synthetic UI generation and fine-tuning pipeline", num_samples=num_samples)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config = GenerationConfig(
        num_samples=num_samples,
        ui_types=[UIType.LOGIN_FORM, UIType.SEARCH_PAGE, UIType.CHECKOUT_FORM],
        include_screenshots=True,
        seed=42,
    )
    generator = SyntheticUIGenerator(config)
    LOG.info("Generating synthetic UI layouts")
    layouts = generator.generate_batch()
    LOG.info(f"Generated {len(layouts)} layouts")

    exporter = DatasetExporter(output_dir=output_path / "datasets", include_screenshots=True)
    dataset_path = exporter.export_jsonl(layouts, filename="synthetic_ui_dataset.jsonl")
    LOG.info(f"Exported dataset to {dataset_path}")

    html_paths = exporter.save_html_files(layouts, prefix="smoke_test")
    LOG.info(f"Saved {len(html_paths)} HTML files")

    preparator = DatasetPreparator(provider=ProviderName.OPENAI, validation_split=0.1)
    stats = preparator.compute_stats(dataset_path)
    LOG.info(
        "Dataset statistics",
        total_samples=stats.total_samples,
        unique_layouts=stats.unique_layouts,
        avg_components=stats.avg_components_per_layout,
        element_types=list(stats.unique_element_types),
    )

    ft_config = FineTuneConfig(
        dataset_path=dataset_path,
        output_dir=output_path / "finetune_runs",
        provider=ProviderName.OPENAI,
        base_model="gpt-4o-mini",
        job_name="smoke_test_job",
        description="Smoke test fine-tuning job",
    )
    LOG.info("Starting fine-tune job")

    job_manager = FineTuneJobManager(storage_path=output_path / "jobs.json")
    finetuner = VisionFinetuner(job_manager=job_manager)

    job = await finetuner.start_finetune(ft_config)
    LOG.info("Fine-tune job completed", job_id=job.job_id, status=job.status.value, model_name=job.model_name)

    summary = {
        "generated_layouts": len(layouts),
        "dataset_path": str(dataset_path),
        "html_files": len(html_paths),
        "stats": {
            "total_samples": stats.total_samples,
            "unique_layouts": stats.unique_layouts,
            "avg_components": stats.avg_components_per_layout,
            "element_types": list(stats.unique_element_types),
        },
        "finetune_job": {
            "job_id": job.job_id,
            "status": job.status.value,
            "model_name": job.model_name,
            "metrics": job.metrics,
        },
    }

    summary_path = output_path / "smoke_test_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    LOG.info("Smoke test completed successfully", summary_path=str(summary_path))
    print(f"\n✅ Smoke test completed! Summary written to: {summary_path}")


def main(
    output_dir: str = typer.Option("./smoke_test_output", "--output-dir", help="Output directory for smoke test results"),
    num_samples: int = typer.Option(10, "--num-samples", help="Number of synthetic layouts to generate"),
) -> None:
    asyncio.run(run_smoke_test(output_dir, num_samples))


if __name__ == "__main__":
    typer.run(main)
