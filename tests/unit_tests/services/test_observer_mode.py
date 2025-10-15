"""
Unit tests for Observer Mode 2.0 service
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from skyvern.forge.sdk.schemas.organizations import Organization
from skyvern.services import observer_mode


@pytest.mark.asyncio
async def test_create_observer_session():
    """Test creating a new observer session"""
    org = Organization(
        organization_id="test_org",
        organization_name="Test Org",
        created_at=datetime.utcnow(),
        modified_at=datetime.utcnow(),
    )
    
    session = await observer_mode.create_observer_session(
        organization=org,
        title="Test Session",
        description="Test Description",
        start_url="https://example.com",
    )
    
    assert session["organization_id"] == "test_org"
    assert session["title"] == "Test Session"
    assert session["status"] == "recording"
    assert session["start_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_record_interaction():
    """Test recording a user interaction"""
    recording = await observer_mode.record_interaction(
        observer_session_id="test_session",
        organization_id="test_org",
        interaction_type="click",
        url="https://example.com",
        element_selector="button.submit",
        reasoning="Click submit button to proceed",
    )
    
    assert recording["observer_session_id"] == "test_session"
    assert recording["recording_type"] == "interaction"
    assert recording["data"]["interaction_type"] == "click"
    assert recording["data"]["element_selector"] == "button.submit"
    assert recording["reasoning"] == "Click submit button to proceed"


@pytest.mark.asyncio
async def test_generate_workflow_from_recording():
    """Test generating a workflow from recorded session"""
    with patch("skyvern.services.observer_mode.app.LLM_API_HANDLER", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {
            "blocks": [
                {
                    "block_type": "navigation",
                    "label": "navigate_to_page",
                    "url": "https://example.com",
                },
                {
                    "block_type": "task",
                    "label": "complete_form",
                    "navigation_goal": "Fill out the form",
                },
            ]
        }
        
        workflow = await observer_mode.generate_workflow_from_recording(
            observer_session_id="test_session",
            organization_id="test_org",
            title="Generated Workflow",
        )
        
        assert workflow["organization_id"] == "test_org"
        assert workflow["title"] == "Generated Workflow"
        assert "workflow_definition" in workflow
        assert "blocks" in workflow["workflow_definition"]
        assert "parameters" in workflow["workflow_definition"]
        assert len(workflow["workflow_definition"]["blocks"]) == 2


@pytest.mark.asyncio
async def test_complete_observer_session():
    """Test completing an observer session"""
    session = await observer_mode.complete_observer_session(
        observer_session_id="test_session",
        organization_id="test_org",
    )
    
    assert session["observer_session_id"] == "test_session"
    assert session["status"] == "completed"
    assert session["completed_at"] is not None


@pytest.mark.asyncio
async def test_export_observer_session():
    """Test exporting observer session data"""
    export_data = await observer_mode.export_observer_session(
        observer_session_id="test_session",
        organization_id="test_org",
        format="json",
    )
    
    assert export_data["observer_session_id"] == "test_session"
    assert "recordings" in export_data
    assert "snapshots" in export_data
    assert "interactions" in export_data
    assert "exported_at" in export_data


@pytest.mark.asyncio
async def test_import_observer_session():
    """Test importing observer session data"""
    session_data = {
        "title": "Imported Session",
        "description": "Imported from backup",
        "metadata": {"source": "export"},
    }
    
    imported_session = await observer_mode.import_observer_session(
        organization_id="test_org",
        session_data=session_data,
    )
    
    assert imported_session["organization_id"] == "test_org"
    assert imported_session["title"] == "Imported Session"


@pytest.mark.asyncio
async def test_diff_recording_vs_workflow():
    """Test diffing recorded steps vs workflow blocks"""
    diff_data = await observer_mode.diff_recording_vs_workflow(
        observer_session_id="test_session",
        workflow_id="test_workflow",
        organization_id="test_org",
    )
    
    assert diff_data["observer_session_id"] == "test_session"
    assert diff_data["workflow_id"] == "test_workflow"
    assert "differences" in diff_data
    assert "match_percentage" in diff_data


def test_parse_llm_response_to_blocks():
    """Test parsing LLM response into blocks"""
    llm_response = {
        "blocks": [
            {
                "block_type": "navigation",
                "label": "nav_1",
                "url": "https://example.com",
            },
            {
                "block_type": "task",
                "label": "task_1",
                "navigation_goal": "Complete task",
            },
        ]
    }
    
    blocks = observer_mode._parse_llm_response_to_blocks(llm_response)
    
    assert len(blocks) == 2
    assert blocks[0]["block_type"] == "navigation"
    assert blocks[0]["label"] == "nav_1"
    assert blocks[1]["block_type"] == "task"
    assert blocks[1]["label"] == "task_1"


def test_extract_parameters_from_blocks():
    """Test extracting parameters from blocks"""
    blocks = [
        {
            "block_type": "navigation",
            "label": "nav_1",
            "url": "{{ base_url }}/page",
        },
        {
            "block_type": "task",
            "label": "task_1",
            "url": "{{ target_url }}",
        },
    ]
    
    parameters = observer_mode._extract_parameters_from_blocks(blocks)
    
    # Should have start_url (default) + base_url + target_url
    assert len(parameters) >= 2
    param_keys = [p["key"] for p in parameters]
    assert "start_url" in param_keys
    assert "base_url" in param_keys or "target_url" in param_keys
