#!/usr/bin/env python3
"""
Demonstration of synthetic UI generation and fine-tuning pipeline integration.
"""

import asyncio
from pathlib import Path

import typer

from evaluation.synthetic_ui import DatasetExporter, SyntheticUIGenerator
from evaluation.synthetic_ui.config import GenerationConfig, UIType
from evaluation.vision_finetune.config import FineTuneConfig, ProviderName
from evaluation.vision_finetune.dataset_prep import DatasetPreparator
from evaluation.vision_finetune.job_manager import FineTuneJobManager
from evaluation.vision_finetune.pipeline import VisionFinetuner


async def run_demo(output_dir: str, num_samples: int, provider: str) -> None:
    print(f"🚀 Starting synthetic UI generation and fine-tuning demo")
    print(f"   - Samples: {num_samples}")
    print(f"   - Provider: {provider}")
    print(f"   - Output: {output_dir}\n")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("📝 Step 1: Generating synthetic UI layouts")
    config = GenerationConfig(
        num_samples=num_samples,
        ui_types=[UIType.LOGIN_FORM, UIType.SEARCH_PAGE, UIType.CHECKOUT_FORM, UIType.DATA_TABLE],
        include_screenshots=True,
        seed=42,
    )
    generator = SyntheticUIGenerator(config)
    layouts = generator.generate_batch()
    print(f"   ✓ Generated {len(layouts)} layouts\n")

    print("💾 Step 2: Exporting dataset")
    exporter = DatasetExporter(output_dir=output_path / "datasets", include_screenshots=True)
    dataset_path = exporter.export_jsonl(layouts, filename="synthetic_ui_dataset.jsonl")
    print(f"   ✓ Dataset: {dataset_path}")

    html_paths = exporter.save_html_files(layouts, prefix="demo")
    print(f"   ✓ HTML files: {len(html_paths)} saved\n")

    print("📊 Step 3: Computing dataset statistics")
    preparator = DatasetPreparator(provider=ProviderName(provider), validation_split=0.1)
    stats = preparator.compute_stats(dataset_path)
    print(f"   ✓ Total samples: {stats.total_samples}")
    print(f"   ✓ Unique layouts: {stats.unique_layouts}")
    print(f"   ✓ Avg components/layout: {stats.avg_components_per_layout:.2f}")
    print(f"   ✓ Element types: {', '.join(stats.unique_element_types)}\n")

    print("🎯 Step 4: Preparing fine-tuning dataset")
    prepared_paths = preparator.prepare(dataset_path, output_path / "prepared")
    print(f"   ✓ Train dataset: {prepared_paths['train']}")
    print(f"   ✓ Validation dataset: {prepared_paths['validation']}\n")

    print("🔧 Step 5: Starting fine-tune job")
    ft_config = FineTuneConfig(
        dataset_path=dataset_path,
        output_dir=output_path / "finetune_runs",
        provider=ProviderName(provider),
        base_model="gpt-4o-mini",
        job_name="demo_finetune_job",
        description="Demo fine-tuning job for synthetic UI",
    )

    job_manager = FineTuneJobManager(storage_path=output_path / "jobs.json")
    finetuner = VisionFinetuner(job_manager=job_manager)

    job = await finetuner.start_finetune(ft_config)
    print(f"   ✓ Job ID: {job.job_id}")
    print(f"   ✓ Status: {job.status.value}")
    print(f"   ✓ Model: {job.model_name}")
    print(f"   ✓ Metrics: {job.metrics}\n")

    print("✅ Demo completed successfully!")
    print(f"   All artifacts saved to: {output_path}")


def main(
    output_dir: str = typer.Option("./demo_output", "--output-dir", help="Output directory for demo results"),
    num_samples: int = typer.Option(20, "--num-samples", help="Number of synthetic layouts to generate"),
    provider: str = typer.Option("openai", "--provider", help="Fine-tuning provider (openai, gemini, custom)"),
) -> None:
    asyncio.run(run_demo(output_dir, num_samples, provider))


if __name__ == "__main__":
    typer.run(main)
