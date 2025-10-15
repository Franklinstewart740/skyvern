import asyncio

import typer
from rich.console import Console

from skyvern.config import settings
from skyvern.forge.app import DATABASE
from skyvern.forge.sdk.api.llm.prompt_cache import PromptCacheService

console = Console()
cache_app = typer.Typer(no_args_is_help=True, help="Manage LLM prompt cache.")


@cache_app.command("evict")
def evict_expired() -> None:
    """Manually evict expired cache entries."""
    if not settings.ENABLE_PROMPT_CACHE:
        console.print("[yellow]Prompt cache is disabled in configuration.[/yellow]")
        return
    
    console.print("[cyan]Evicting expired prompt cache entries...[/cyan]")
    
    async def _evict() -> None:
        async with DATABASE.Session() as session:
            count = await PromptCacheService.evict_expired_entries(session)
            if count > 0:
                console.print(f"[green]Evicted {count} expired cache entries.[/green]")
            else:
                console.print("[yellow]No expired cache entries found.[/yellow]")
    
    asyncio.run(_evict())


@cache_app.command("info")
def cache_info() -> None:
    """Display prompt cache configuration."""
    console.print("[bold cyan]Prompt Cache Configuration[/bold cyan]")
    console.print(f"  Enabled: [green]{settings.ENABLE_PROMPT_CACHE}[/green]")
    console.print(f"  Backend: {settings.PROMPT_CACHE_BACKEND}")
    console.print(f"  TTL Hours: {settings.PROMPT_CACHE_TTL_HOURS}")
    console.print(f"  Replay Enabled: {settings.ENABLE_PROMPT_CACHE_REPLAY}")
    console.print(f"  Eviction Enabled: {settings.PROMPT_CACHE_EVICTION_ENABLED}")
    console.print(f"  Eviction Interval Hours: {settings.PROMPT_CACHE_EVICTION_INTERVAL_HOURS}")


if __name__ == "__main__":
    cache_app()
