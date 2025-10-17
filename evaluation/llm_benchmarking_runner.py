"""LLM Benchmarking Runner

This script runs standardized tasks across multiple LLM providers to compare performance.
It can be used to:
1. Benchmark different providers (OpenAI, Anthropic, Gemini, etc.)
2. Compare model performance (latency, cost, accuracy)
3. Generate telemetry data for the dashboard

Usage:
    python evaluation/llm_benchmarking_runner.py --providers openai anthropic --tasks simple navigation
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

import structlog

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from skyvern.forge import app
from skyvern.forge.sdk.api.llm.api_handler_factory import LLMAPIHandlerFactory

LOG = structlog.get_logger()


# Standard test prompts for benchmarking
BENCHMARK_PROMPTS = {
    "simple": {
        "prompt": "What is 2+2?",
        "prompt_name": "benchmark_simple_math",
        "expected": "4",
    },
    "reasoning": {
        "prompt": "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
        "prompt_name": "benchmark_reasoning",
        "expected": "5 minutes",
    },
    "navigation": {
        "prompt": "Given a webpage with a login form containing username and password fields, and a 'Sign In' button, what actions would you take to log in with username 'test@example.com' and password 'password123'?",
        "prompt_name": "benchmark_navigation_planning",
        "expected": "fill username field, fill password field, click sign in button",
    },
}


async def run_benchmark_for_provider(
    llm_key: str,
    prompt: str,
    prompt_name: str,
    iterations: int = 3,
) -> dict:
    """Run a benchmark test for a specific LLM provider.
    
    Args:
        llm_key: LLM configuration key (e.g., "openai/gpt-4o", "anthropic/claude-3-5-sonnet")
        prompt: The test prompt
        prompt_name: Name identifier for the prompt
        iterations: Number of times to run the test
        
    Returns:
        Dictionary with benchmark results including latencies and success rate
    """
    try:
        handler = LLMAPIHandlerFactory.get_llm_api_handler(llm_key)
        
        latencies = []
        successes = 0
        errors = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                await handler(
                    prompt=prompt,
                    prompt_name=prompt_name,
                    organization_id="benchmark_test",
                )
                successes += 1
                latency_ms = int((time.time() - start_time) * 1000)
                latencies.append(latency_ms)
                
                LOG.info(
                    "Benchmark iteration completed",
                    llm_key=llm_key,
                    prompt_name=prompt_name,
                    iteration=i + 1,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                latencies.append(latency_ms)
                errors.append(str(e))
                LOG.error(
                    "Benchmark iteration failed",
                    llm_key=llm_key,
                    prompt_name=prompt_name,
                    iteration=i + 1,
                    error=str(e),
                )
            
            # Small delay between iterations
            await asyncio.sleep(1)
        
        results = {
            "llm_key": llm_key,
            "prompt_name": prompt_name,
            "iterations": iterations,
            "successes": successes,
            "failures": iterations - successes,
            "success_rate": successes / iterations * 100,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "min_latency_ms": min(latencies) if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
            "errors": errors,
        }
        
        LOG.info(
            "Benchmark completed for provider",
            llm_key=llm_key,
            prompt_name=prompt_name,
            results=results,
        )
        
        return results
        
    except Exception as e:
        LOG.exception("Failed to run benchmark", llm_key=llm_key, prompt_name=prompt_name)
        return {
            "llm_key": llm_key,
            "prompt_name": prompt_name,
            "error": str(e),
        }


async def run_benchmarks(
    providers: list[str],
    tasks: list[str],
    iterations: int = 3,
) -> None:
    """Run benchmarks across multiple providers and tasks.
    
    Args:
        providers: List of LLM provider keys
        tasks: List of task types to benchmark
        iterations: Number of iterations per test
    """
    all_results = []
    
    for task in tasks:
        if task not in BENCHMARK_PROMPTS:
            LOG.warning(f"Unknown task: {task}, skipping")
            continue
            
        test_config = BENCHMARK_PROMPTS[task]
        LOG.info(f"Running benchmark task: {task}")
        
        for provider in providers:
            LOG.info(f"Testing provider: {provider}")
            results = await run_benchmark_for_provider(
                llm_key=provider,
                prompt=test_config["prompt"],
                prompt_name=test_config["prompt_name"],
                iterations=iterations,
            )
            all_results.append(results)
            
            # Delay between providers
            await asyncio.sleep(2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    
    for result in all_results:
        print(f"\nProvider: {result['llm_key']}")
        print(f"Task: {result['prompt_name']}")
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  Success Rate: {result['success_rate']:.1f}%")
            print(f"  Avg Latency: {result['avg_latency_ms']:.0f}ms")
            print(f"  Min Latency: {result['min_latency_ms']:.0f}ms")
            print(f"  Max Latency: {result['max_latency_ms']:.0f}ms")
            if result['errors']:
                print(f"  Errors: {len(result['errors'])}")


def main():
    parser = argparse.ArgumentParser(description="Run LLM benchmarks across multiple providers")
    parser.add_argument(
        "--providers",
        nargs="+",
        required=True,
        help="LLM provider keys to benchmark (e.g., openai/gpt-4o anthropic/claude-3-5-sonnet)",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=["simple"],
        choices=list(BENCHMARK_PROMPTS.keys()),
        help="Task types to benchmark",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per test",
    )
    
    args = parser.parse_args()
    
    LOG.info(
        "Starting LLM benchmarking",
        providers=args.providers,
        tasks=args.tasks,
        iterations=args.iterations,
    )
    
    asyncio.run(run_benchmarks(args.providers, args.tasks, args.iterations))


if __name__ == "__main__":
    main()
