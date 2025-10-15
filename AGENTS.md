# Skyvern Agent Guide
This AGENTS.md file provides comprehensive guidance for AI agents working with the Skyvern codebase. Follow these guidelines to ensure consistency and quality in all contributions.

## Project Structure for Agent Navigation

### Core Python Package (`/skyvern`)

- **`/agent`**: Multi-agent system orchestration (New in Skyvern 2.0)
  - Navigator agent for planning
  - Action agents for execution
  - Extraction agents for data capture
  - Validation agents for quality assurance
  
- **`/cli`**: Command-line interface powered by Typer
  - `skyvern run` - Start services
  - `skyvern quickstart` - First-time setup
  - `skyvern init llm` - LLM configuration wizard
  
- **`/client`**: Generated Python SDK client
  - Auto-generated from OpenAPI spec
  - Type-safe API interactions
  
- **`/forge`**: Core application framework
  - `/sdk/api/llm` - LLM provider implementations
  - `/sdk/routes` - FastAPI route handlers
  - `/sdk/workflow` - Workflow engine
  - `/sdk/artifact` - Artifact storage (local/S3/Azure)
  - `/prompts` - Jinja2 prompt templates
  - `agent.py` - Main agent orchestration (5000+ lines)
  - `api_app.py` - FastAPI application factory
  
- **`/library`**: Reusable utilities and helpers
  - Skyvern SDK for programmatic access
  
- **`/schemas`**: Pydantic data models
  - Request/response validation
  - Task and workflow schemas
  
- **`/services`**: Business logic layer
  - `task_v2_service.py` - Task execution service
  - `run_service.py` - Workflow run orchestration
  - `bitwarden.py` - Credential management
  
- **`/utils`**: Common utility functions
  - String manipulation, URL validation, etc.
  
- **`/webeye`**: Browser automation engine
  - `/actions` - Browser action handlers (click, type, scroll)
  - `/scraper` - DOM scraping and element detection
  - `browser_factory.py` - Playwright browser management
  - Computer vision integration

### Frontend (`/skyvern-frontend`)
- React + TypeScript + Vite + Tailwind CSS
- Task and workflow UI
- Real-time browser livestreaming
- Artifact viewing and management

### Supporting Directories

- **`/alembic`**: Database migrations (SQLAlchemy/Alembic)
  - Version-controlled schema changes
  
- **`/integrations`**: Third-party integrations
  - `/mcp` - Model Context Protocol
  - `/langchain` - LangChain integration
  - `/llama_index` - LlamaIndex integration
  - `/n8n`, `/make` - Workflow automation platforms
  
- **`/evaluation`**: Benchmarking and evaluation
  - WebVoyager and WebBench datasets
  - Performance evaluation scripts
  
- **`/fern`**: Documentation (Fern Docs)
  - `/openapi` - OpenAPI spec
  - Markdown documentation files
  
- **`/kubernetes-deployment`**: Kubernetes manifests
  - Production deployment configurations
  
- **`/scripts`**: Utility and deployment scripts

## Coding Conventions for Agents

### Python Standards

- Use Python 3.11+ features and type hints
- Follow PEP 8 with a line length of 100 characters
- Use absolute imports for all modules
- Document all public functions and classes with Google-style docstrings
- Use `snake_case` for variables and functions, `PascalCase` for classes

### Asynchronous Programming

- Prefer async/await over callbacks
- Use `asyncio` for concurrency
- Always handle exceptions in async code
- Use context managers for resource cleanup

### Error Handling

- Use specific exception classes
- Include meaningful error messages
- Log errors with appropriate severity levels
- Never expose sensitive information in error messages

## Pull Request Process

1. **Branch Naming**
   - `feature/descriptive-name` for new features
   - `fix/issue-description` for bug fixes
   - `chore/task-description` for maintenance tasks

2. **PR Guidelines**
   - Reference related issues with `Fixes #123` or `Closes #123`
   - Include a clear description of changes
   - Update relevant documentation
   - Ensure all tests pass
   - Get at least one approval before merging

3. **Commit Message Format**
   ```
   [Component] Action: Brief description
   
   More detailed explanation if needed.
   
   - Bullet points for additional context
   - Reference issues with #123
   ```

## Skyvern 2.0 Architecture Overview

### Multi-Agent System
Skyvern 2.0 uses a swarm of specialized agents:
- **Navigator Agent**: Plans navigation paths, decides next steps
- **Action Agent**: Executes browser interactions (clicks, typing, scrolling)
- **Extraction Agent**: Captures structured data from pages
- **Validation Agent**: Verifies workflow execution and data quality

Each agent uses Vision LLMs to understand visual context without relying on brittle selectors.

### LLM Provider System
Location: `skyvern/forge/sdk/api/llm/`

Supported providers (via `LLMAPIHandler` interface):
- **OpenAI**: GPT-4o, GPT-4o-mini, O1, O3 series
- **Anthropic**: Claude 3.5/3.7 Sonnet, Claude 4 Opus/Sonnet
- **Azure OpenAI**: All GPT models via Azure
- **AWS Bedrock**: Anthropic models via Bedrock
- **Google Gemini**: Gemini 2.5 Pro/Flash
- **Ollama**: Local model support
- **OpenRouter**: Multi-provider routing
- **OpenAI-Compatible**: Custom endpoints via liteLLM

Configuration via environment variables or `skyvern init llm` CLI wizard.

### Workflow Engine
Location: `skyvern/forge/sdk/workflow/`

Workflow blocks (`models/block.py`):
- **TaskBlock**: Browser automation tasks
- **BrowserActionBlock**: Direct browser actions
- **ExtractionBlock**: Data extraction with schemas
- **ValidationBlock**: Quality assurance checks
- **ForLoopBlock**: Iteration over collections
- **CodeBlock**: Custom Python execution
- **TextPromptBlock**: LLM reasoning without browser
- **HTTPRequestBlock**: External API calls
- **FileParserBlock**: Parse PDFs, CSVs, Excel
- **EmailBlock**: Send emails via SMTP
- **UploadBlock**: Upload files to S3/Azure

### Browser Engine
Location: `skyvern/webeye/`

Playwright-based automation with:
- Visual element detection (computer vision)
- Screenshot management for LLM analysis
- Action execution (click, type, scroll, hover)
- Multi-tab/frame support
- Browser session persistence
- CDP connect mode for local Chrome

### Data Flow
1. Task/workflow submitted via UI/API/SDK
2. Navigator agent analyzes goal and creates plan
3. Browser captures screenshots
4. Vision LLM analyzes visual context
5. Action agent executes identified interactions
6. Validation agent verifies success
7. Extraction agent captures requested data
8. Results stored in PostgreSQL, artifacts in S3/local storage

## Code Quality Checks

Before submitting code, run:
```bash
# Lint and format
ruff check
ruff format

# Type checking
mypy skyvern

# Run tests
pytest tests/

# Pre-commit hooks (runs all checks)
pre-commit run --all-files
```

## Performance Considerations
- **Database**: Use connection pooling, optimize queries, add indexes
- **LLM Calls**: Cache similar requests, use secondary LLM for light tasks
- **Screenshots**: Compress images, limit screenshot frequency
- **Browser**: Reuse browser instances, clean up resources promptly
- **Async Operations**: Use asyncio properly, avoid blocking I/O
- **Memory**: Monitor browser memory usage, implement cleanup strategies

## Security Best Practices
- **Secrets**: Never commit credentials, use environment variables or secret managers
- **Input Validation**: Validate all user inputs with Pydantic schemas
- **Credentials**: Store encrypted in database (AES-256), support TOTP 2FA
- **API Keys**: Require authentication, implement rate limiting
- **Browser Security**: Sandbox browser instances, limit network access
- **Dependencies**: Keep updated, scan for vulnerabilities with `pip-audit`
- **Principle of Least Privilege**: Minimal database/AWS permissions

## Testing Guidelines
- **Unit Tests**: Test individual functions/classes in `tests/unit_tests/`
- **Integration Tests**: Test browser automation in `tests/integration_tests/`
- **Fixtures**: Use pytest fixtures for common setup
- **Async Tests**: Mark with `@pytest.mark.asyncio`
- **Mocking**: Mock external APIs (LLM providers, S3, etc.)
- **Coverage**: Aim for >80% code coverage

## Documentation Standards
- **Docstrings**: Use Google-style for all public APIs
- **Type Hints**: Required for all function signatures
- **README**: Update for new features or breaking changes
- **Fern Docs**: Add MDX files in `fern/` for user-facing features
- **CHANGELOG**: Document changes in semantic versioning format
- **API Docs**: OpenAPI spec auto-generated, regenerate after route changes

## Getting Help
- **Documentation**: Check [docs.skyvern.com](https://www.skyvern.com/docs)
- **Discord**: Join [Discord community](https://discord.gg/fG2XXEuQX3)
- **GitHub Issues**: Search existing issues before creating new ones
- **Code Examples**: Review `examples/` and `tests/` for patterns
- **Architecture Guide**: See `fern/getting-started/architecture-guide.mdx`
