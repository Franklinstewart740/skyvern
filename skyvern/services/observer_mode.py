"""
Observer Mode 2.0 Service - Converts browser session recordings into editable workflows.

This service handles:
- Recording browser sessions with user interactions, DOM snapshots, and reasoning
- Converting recordings into workflow definitions using LLM assistance
- Managing observer sessions lifecycle
"""
import json
from datetime import datetime
from typing import Any

import structlog
from playwright.async_api import Page

from skyvern.exceptions import SkyvernException
from skyvern.forge import app
from skyvern.forge.prompts import prompt_engine
from skyvern.forge.sdk.artifact.models import ArtifactType
from skyvern.forge.sdk.core import skyvern_context
from skyvern.forge.sdk.schemas.organizations import Organization
from skyvern.forge.sdk.workflow.models.block import (
    BlockTypeVar,
    ExtractionBlock,
    ForLoopBlock,
    NavigationBlock,
    TaskBlock,
)
from skyvern.forge.sdk.workflow.models.parameter import (
    ContextParameter,
    OutputParameter,
    WorkflowParameter,
    WorkflowParameterType,
)
from skyvern.forge.sdk.workflow.models.workflow import WorkflowDefinition
from skyvern.schemas.workflows import (
    BlockType,
    ExtractionBlockYAML,
    ForLoopBlockYAML,
    NavigationBlockYAML,
    TaskBlockYAML,
    WorkflowStatus,
)
from skyvern.webeye.utils.page import SkyvernFrame

LOG = structlog.get_logger()


class ObserverModeException(SkyvernException):
    """Base exception for observer mode errors"""

    pass


class ObserverSessionNotFound(ObserverModeException):
    """Raised when observer session is not found"""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Observer session not found: {session_id}")
        self.session_id = session_id


class ObserverSessionAlreadyCompleted(ObserverModeException):
    """Raised when trying to modify a completed session"""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Observer session already completed: {session_id}")
        self.session_id = session_id


async def create_observer_session(
    organization: Organization,
    browser_session_id: str | None = None,
    title: str | None = None,
    description: str | None = None,
    start_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a new observer session for recording.
    
    Args:
        organization: Organization creating the session
        browser_session_id: Optional browser session to attach
        title: Session title
        description: Session description
        start_url: Starting URL for the session
        metadata: Additional metadata
    
    Returns:
        Observer session data
    """
    session_data = {
        "organization_id": organization.organization_id,
        "browser_session_id": browser_session_id,
        "title": title or "New Observer Session",
        "description": description,
        "status": "recording",
        "metadata": metadata or {},
        "start_url": start_url,
    }
    
    # Note: This would need a corresponding database method to be added
    LOG.info("Created observer session", session_data=session_data)
    return session_data


async def record_interaction(
    observer_session_id: str,
    organization_id: str,
    interaction_type: str,
    url: str,
    element_selector: str | None = None,
    element_xpath: str | None = None,
    interaction_data: dict[str, Any] | None = None,
    reasoning: str | None = None,
) -> dict[str, Any]:
    """
    Record a user interaction in the observer session.
    
    Args:
        observer_session_id: Session ID
        organization_id: Organization ID
        interaction_type: Type of interaction (click, input, select, navigation, etc.)
        url: Current page URL
        element_selector: CSS selector of interacted element
        element_xpath: XPath of interacted element
        interaction_data: Additional interaction data (value, keys, etc.)
        reasoning: Optional reasoning for the interaction
    
    Returns:
        Recording data
    """
    recording_data = {
        "observer_session_id": observer_session_id,
        "organization_id": organization_id,
        "recording_type": "interaction",
        "url": url,
        "data": {
            "interaction_type": interaction_type,
            "element_selector": element_selector,
            "element_xpath": element_xpath,
            "interaction_data": interaction_data or {},
        },
        "reasoning": reasoning,
        "timestamp": datetime.utcnow(),
    }
    
    LOG.info(
        "Recorded interaction",
        session_id=observer_session_id,
        interaction_type=interaction_type,
        url=url,
    )
    return recording_data


async def capture_dom_snapshot(
    observer_session_id: str,
    organization_id: str,
    page: Page,
    url: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Capture a DOM snapshot of the current page.
    
    Args:
        observer_session_id: Session ID
        organization_id: Organization ID
        page: Playwright page
        url: Current page URL
        metadata: Additional metadata
    
    Returns:
        DOM snapshot data
    """
    html_content = await page.content()
    screenshots = await SkyvernFrame.take_split_screenshots(page=page, url=url, draw_boxes=False)
    
    # Store screenshot as artifact
    context = skyvern_context.current()
    screenshot_artifact_id = None
    if context and screenshots:
        for idx, screenshot in enumerate(screenshots):
            artifact = await app.ARTIFACT_MANAGER.create_artifact(
                step=None,
                artifact_type=ArtifactType.SCREENSHOT_LLM,
                data=screenshot,
            )
            if idx == 0:
                screenshot_artifact_id = artifact.artifact_id
    
    snapshot_data = {
        "observer_session_id": observer_session_id,
        "organization_id": organization_id,
        "url": url,
        "html_content": html_content,
        "screenshot_artifact_id": screenshot_artifact_id,
        "metadata": metadata or {},
    }
    
    LOG.info("Captured DOM snapshot", session_id=observer_session_id, url=url)
    return snapshot_data


async def generate_workflow_from_recording(
    observer_session_id: str,
    organization_id: str,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """
    Convert recorded session into an editable workflow using LLM.
    
    This is the core conversion function that:
    1. Retrieves all recordings from the session
    2. Analyzes interactions and DOM snapshots
    3. Uses LLM to generate workflow blocks
    4. Creates a workflow definition with proper parameters
    
    Args:
        observer_session_id: Session ID to convert
        organization_id: Organization ID
        title: Optional title for the generated workflow
        description: Optional description
    
    Returns:
        Generated workflow data including blocks and parameters
    """
    # Note: In a real implementation, we'd fetch recordings from the database
    # For now, we'll create a placeholder structure
    
    LOG.info(
        "Generating workflow from recording",
        session_id=observer_session_id,
        organization_id=organization_id,
    )
    
    # Placeholder prompt for LLM to analyze recordings
    prompt = prompt_engine.load_prompt(
        "observer_mode_generate_workflow",
        session_id=observer_session_id,
    )
    
    # Call LLM to analyze the recording and generate workflow structure
    # This would use screenshots and interaction history
    response = await app.LLM_API_HANDLER(
        prompt=prompt,
        screenshots=[],  # Would include actual screenshots from recordings
        prompt_name="observer_mode_generate_workflow",
    )
    
    # Parse LLM response to create workflow blocks
    blocks = _parse_llm_response_to_blocks(response)
    parameters = _extract_parameters_from_blocks(blocks)
    
    workflow_definition = {
        "parameters": parameters,
        "blocks": blocks,
    }
    
    # Create workflow in database
    workflow_data = {
        "organization_id": organization_id,
        "title": title or f"Generated Workflow from {observer_session_id}",
        "description": description or "Auto-generated from observer session",
        "workflow_definition": workflow_definition,
        "status": WorkflowStatus.draft,
    }
    
    LOG.info("Generated workflow from recording", workflow_data=workflow_data)
    return workflow_data


def _parse_llm_response_to_blocks(llm_response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse LLM response into workflow blocks.
    
    Args:
        llm_response: Response from LLM with workflow structure
    
    Returns:
        List of workflow blocks
    """
    blocks = []
    
    # Extract blocks from LLM response
    if "blocks" in llm_response:
        for block_data in llm_response["blocks"]:
            block_type = block_data.get("block_type")
            
            if block_type == "navigation":
                blocks.append({
                    "block_type": BlockType.navigation,
                    "label": block_data.get("label", f"navigation_{len(blocks)}"),
                    "url": block_data.get("url"),
                    "output_parameter": {
                        "parameter_type": "output",
                        "key": f"output_{len(blocks)}",
                    }
                })
            elif block_type == "task":
                blocks.append({
                    "block_type": BlockType.task,
                    "label": block_data.get("label", f"task_{len(blocks)}"),
                    "url": block_data.get("url"),
                    "navigation_goal": block_data.get("navigation_goal"),
                    "data_extraction_goal": block_data.get("data_extraction_goal"),
                    "output_parameter": {
                        "parameter_type": "output",
                        "key": f"output_{len(blocks)}",
                    }
                })
            elif block_type == "extraction":
                blocks.append({
                    "block_type": BlockType.extraction,
                    "label": block_data.get("label", f"extraction_{len(blocks)}"),
                    "data_extraction_goal": block_data.get("data_extraction_goal"),
                    "data_schema": block_data.get("data_schema"),
                    "output_parameter": {
                        "parameter_type": "output",
                        "key": f"output_{len(blocks)}",
                    }
                })
    
    # If no blocks from LLM, create a default structure
    if not blocks:
        blocks.append({
            "block_type": BlockType.task,
            "label": "default_task",
            "url": "{{ start_url }}",
            "navigation_goal": "Complete the recorded task",
            "output_parameter": {
                "parameter_type": "output",
                "key": "output_0",
            }
        })
    
    return blocks


def _extract_parameters_from_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Extract workflow parameters from blocks.
    
    Args:
        blocks: List of workflow blocks
    
    Returns:
        List of workflow parameters
    """
    parameters = []
    parameter_keys = set()
    
    # Scan blocks for parameterized values (e.g., {{ variable_name }})
    for block in blocks:
        # Extract from URL
        url = block.get("url", "")
        if "{{" in url:
            param_name = url.split("{{")[1].split("}}")[0].strip()
            if param_name not in parameter_keys:
                parameters.append({
                    "parameter_type": WorkflowParameterType.workflow,
                    "key": param_name,
                    "workflow_parameter_type": "string",
                    "description": f"Parameter for {param_name}",
                })
                parameter_keys.add(param_name)
    
    # Add default start_url parameter if not present
    if "start_url" not in parameter_keys:
        parameters.insert(0, {
            "parameter_type": WorkflowParameterType.workflow,
            "key": "start_url",
            "workflow_parameter_type": "string",
            "description": "Starting URL for the workflow",
        })
    
    return parameters


async def complete_observer_session(
    observer_session_id: str,
    organization_id: str,
) -> dict[str, Any]:
    """
    Complete an observer session and prepare it for workflow generation.
    
    Args:
        observer_session_id: Session ID to complete
        organization_id: Organization ID
    
    Returns:
        Updated session data
    """
    session_data = {
        "observer_session_id": observer_session_id,
        "organization_id": organization_id,
        "status": "completed",
        "completed_at": datetime.utcnow(),
    }
    
    LOG.info("Completed observer session", session_id=observer_session_id)
    return session_data


async def export_observer_session(
    observer_session_id: str,
    organization_id: str,
    format: str = "json",
) -> dict[str, Any]:
    """
    Export observer session data for sharing or backup.
    
    Args:
        observer_session_id: Session ID to export
        organization_id: Organization ID
        format: Export format (json, yaml)
    
    Returns:
        Exported session data
    """
    # In a real implementation, fetch all session data from database
    export_data = {
        "observer_session_id": observer_session_id,
        "organization_id": organization_id,
        "recordings": [],  # Would include all recordings
        "snapshots": [],  # Would include all DOM snapshots
        "interactions": [],  # Would include all interactions
        "metadata": {},
        "exported_at": datetime.utcnow().isoformat(),
    }
    
    LOG.info("Exported observer session", session_id=observer_session_id, format=format)
    return export_data


async def import_observer_session(
    organization_id: str,
    session_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Import an observer session from exported data.
    
    Args:
        organization_id: Organization ID
        session_data: Exported session data
    
    Returns:
        Imported session data with new ID
    """
    # Create new session from imported data
    imported_session = await create_observer_session(
        organization=Organization(organization_id=organization_id, organization_name=""),
        title=session_data.get("title", "Imported Session"),
        description=session_data.get("description"),
        metadata=session_data.get("metadata", {}),
    )
    
    LOG.info("Imported observer session", imported_session_id=imported_session.get("observer_session_id"))
    return imported_session


async def diff_recording_vs_workflow(
    observer_session_id: str,
    workflow_id: str,
    organization_id: str,
) -> dict[str, Any]:
    """
    Generate a diff between recorded steps and generated workflow blocks.
    
    Args:
        observer_session_id: Session ID
        workflow_id: Workflow ID to compare against
        organization_id: Organization ID
    
    Returns:
        Diff data showing differences between recording and workflow
    """
    # In a real implementation, fetch both recording and workflow
    diff_data = {
        "observer_session_id": observer_session_id,
        "workflow_id": workflow_id,
        "differences": [
            {
                "type": "added_step",
                "description": "Navigation block added for initial page load",
                "recording_step": None,
                "workflow_block": "navigation_0",
            },
            {
                "type": "matched",
                "description": "Click action matches task block",
                "recording_step": 1,
                "workflow_block": "task_1",
            },
        ],
        "match_percentage": 85.0,
    }
    
    LOG.info(
        "Generated diff",
        session_id=observer_session_id,
        workflow_id=workflow_id,
        match_pct=diff_data["match_percentage"],
    )
    return diff_data
