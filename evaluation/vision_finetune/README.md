# Vision Fine-tuning Pipeline

The vision fine-tuning pipeline leverages synthetic UI datasets to improve model accuracy on visual grounding tasks.

## Features

- Prepare synthetic datasets for provider-specific formats (OpenAI, Gemini, custom)
- Schedule fine-tuning jobs
- Track job status and metrics
- Download resulting model artifacts
- Register fine-tuned models in the `config_registry` for immediate use

## Workflow

1. **Generate Dataset**: Use the synthetic UI generator to export a dataset (JSONL).
2. **Prepare Dataset**: The pipeline splits data into train/validation and formats it per provider requirements.
3. **Schedule Job**: Fine-tuning jobs are simulated and tracked via the `FineTuneJobManager`.
4. **Register Model**: Upon completion, models are registered in `LLMConfigRegistry` for downstream tasks.
5. **Download Artifacts**: Retrieve the fine-tuned model artifacts for storage or deployment.

## Usage Example

```python
import asyncio

from evaluation.synthetic_ui import SyntheticUIGenerator, DatasetExporter
from evaluation.synthetic_ui.config import GenerationConfig
from evaluation.vision_finetune.config import FineTuneConfig, ProviderName
from evaluation.vision_finetune.job_manager import FineTuneJobManager
from evaluation.vision_finetune.pipeline import VisionFinetuner

# 1. Generate dataset
config = GenerationConfig(num_samples=50, include_screenshots=True)
generator = SyntheticUIGenerator(config)
layouts = generator.generate_batch()

exporter = DatasetExporter(output_dir="./datasets/finetune", include_screenshots=True)
dataset_path = exporter.export_jsonl(layouts, filename="synthetic_ui.jsonl")

# 2. Configure fine-tuning
ft_config = FineTuneConfig(
    dataset_path=dataset_path,
    output_dir="./finetune_runs",
    provider=ProviderName.OPENAI,
    base_model="gpt-4o-mini",
    job_name="ft_synthetic_demo",
    register_llm_key="OPENAI_SYNTHETIC_UI_DEMO",
)

# 3. Run pipeline
job_manager = FineTuneJobManager(storage_path="./finetune_runs/jobs.json")
finetuner = VisionFinetuner(job_manager=job_manager)

job = asyncio.run(finetuner.start_finetune(ft_config))
print("Fine-tune job:", job)
```

## Provider Support

### OpenAI
- Formats data using the Chat Completions API schema
- Registers models requiring `OPENAI_API_KEY`
- Simulated job completion with metrics reporting

### Gemini
- Uses Vertex AI-compatible payloads
- Registers models requiring `GEMINI_API_KEY`

### Custom
- Writes artifacts to local disk for bespoke model workflows

## Job Tracking

Jobs are stored in `FineTuneJobManager`, including:
- Job ID
- Provider
- Status (`scheduled`, `running`, `completed`, `failed`)
- Metrics (train/validation sample counts)
- Output artifacts

## Model Registration

Registered models are added to the `LLMConfigRegistry` allowing immediate use in Skyvern:

```python
from skyvern.forge.sdk.api.llm.config_registry import LLMConfigRegistry
from skyvern.forge.sdk.api.llm.models import LLMConfig

LLMConfigRegistry.register_config(
    "OPENAI_SYNTHETIC_UI_DEMO",
    LLMConfig(
        model_name="gpt-4o-mini-synthetic-ui",
        required_env_vars=["OPENAI_API_KEY"],
        supports_vision=True,
        add_assistant_prefix=False,
    ),
)
```
