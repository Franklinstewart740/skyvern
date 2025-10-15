"""Example script demonstrating the Skyvern plugin framework."""

import asyncio

from skyvern.services.plugins import auto_load_plugins, get_plugin_registry
from skyvern.services.plugins.base import PluginExecutionRequest


async def main():
    """Demonstrate plugin framework usage."""
    print("=== Skyvern Plugin Framework Demo ===\n")

    # 1. Auto-load plugins
    print("1. Loading plugins...")
    plugin_count = auto_load_plugins()
    print(f"   Loaded {plugin_count} plugins\n")

    # 2. Get registry and list available plugins
    registry = get_plugin_registry()
    plugins = registry.list_plugins()
    print("2. Available plugins:")
    for name, plugin_class in plugins.items():
        manifest = plugin_class.manifest
        print(f"   - {name} (v{manifest.version}): {manifest.description}")
    print()

    # 3. Execute HTTP request plugin
    print("3. Testing HTTP Request Plugin...")
    http_request = PluginExecutionRequest(
        payload={
            "url": "https://api.github.com/repos/Skyvern-AI/skyvern",
            "method": "GET",
            "headers": {"Accept": "application/vnd.github.v3+json"},
        }
    )

    try:
        result = await registry.execute_plugin("http_request", http_request)
        print(f"   Status Code: {result.output.get('status_code')}")
        print(f"   Success: {result.metadata.get('success')}")
        print()
    except Exception as e:
        print(f"   Error: {e}\n")

    # 4. Execute data validator plugin
    print("4. Testing Data Validator Plugin...")
    from skyvern.services.plugins.builtin.validators import DataValidatorPluginConfig, ValidationRule

    validator_config = DataValidatorPluginConfig(
        rules=[
            ValidationRule(field="name", required=True, allow_empty=False),
            ValidationRule(field="email", required=True),
        ]
    )

    await registry.instantiate_plugin("data_validator", validator_config)

    # Valid data
    valid_request = PluginExecutionRequest(
        payload={"data": {"name": "John Doe", "email": "john@example.com"}}
    )
    valid_result = await registry.execute_plugin("data_validator", valid_request)
    print(f"   Valid data: {valid_result.output['valid']}")

    # Invalid data
    invalid_request = PluginExecutionRequest(payload={"data": {"name": "", "email": "john@example.com"}})
    invalid_result = await registry.execute_plugin("data_validator", invalid_request)
    print(f"   Invalid data: {invalid_result.output['valid']}")
    print(f"   Errors: {invalid_result.output['errors']}")
    print()

    # 5. List connectors
    from skyvern.services.plugins.types import PluginType

    connectors = registry.list_plugins(plugin_type=PluginType.CONNECTOR)
    print("5. Available connectors:")
    for name in connectors:
        print(f"   - {name}")
    print()

    # 6. Set up stream listener
    print("6. Setting up stream listener...")

    async def log_stream_event(event):
        print(f"   [STREAM] Plugin: {event.plugin_name}, Event: {event.event}")

    registry.add_stream_listener(log_stream_event)

    # Execute a plugin to trigger stream events
    print("   Executing plugin to trigger stream events...")
    request = PluginExecutionRequest(payload={"url": "https://httpbin.org/get", "method": "GET"})
    await registry.execute_plugin("http_request", request)
    print()

    print("=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
