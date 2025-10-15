"""
API routes for Observer Mode 2.0
"""
import structlog
from fastapi import BackgroundTasks, Depends, HTTPException, Path, Query, status
from typing import Annotated

from skyvern.forge.sdk.routes.routers import base_router
from skyvern.forge.sdk.schemas.observer_sessions import (
    CreateObserverSessionRequest,
    DiffRequest,
    ExportSessionRequest,
    GenerateWorkflowRequest,
    ImportSessionRequest,
    RecordInteractionRequest,
)
from skyvern.forge.sdk.schemas.organizations import Organization
from skyvern.forge.sdk.services import org_auth_service
from skyvern.services import observer_mode

LOG = structlog.get_logger()


@base_router.post(
    "/observer/sessions",
    tags=["Observer Mode"],
    description="Create a new observer session for recording",
    summary="Create observer session",
    status_code=status.HTTP_201_CREATED,
)
async def create_observer_session(
    request: CreateObserverSessionRequest,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict:
    """
    Create a new observer session to start recording user interactions.
    """
    try:
        session = await observer_mode.create_observer_session(
            organization=current_org,
            browser_session_id=request.browser_session_id,
            title=request.title,
            description=request.description,
            start_url=request.start_url,
            metadata=request.metadata,
        )
        return session
    except Exception as e:
        LOG.error("Failed to create observer session", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create observer session: {str(e)}",
        )


@base_router.get(
    "/observer/sessions/{session_id}",
    tags=["Observer Mode"],
    description="Get observer session details",
    summary="Get observer session",
)
async def get_observer_session(
    session_id: Annotated[str, Path(description="Observer session ID")],
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict:
    """
    Retrieve details of a specific observer session.
    """
    try:
        # In a real implementation, fetch from database
        session = {
            "observer_session_id": session_id,
            "organization_id": current_org.organization_id,
            "status": "recording",
            "title": "Observer Session",
        }
        return session
    except Exception as e:
        LOG.error("Failed to get observer session", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Observer session not found: {session_id}",
        )


@base_router.get(
    "/observer/sessions",
    tags=["Observer Mode"],
    description="List observer sessions",
    summary="List observer sessions",
)
async def list_observer_sessions(
    current_org: Organization = Depends(org_auth_service.get_current_org),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """
    List all observer sessions for the current organization.
    """
    try:
        # In a real implementation, fetch from database with pagination
        sessions = {
            "sessions": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }
        return sessions
    except Exception as e:
        LOG.error("Failed to list observer sessions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list observer sessions: {str(e)}",
        )


@base_router.post(
    "/observer/sessions/{session_id}/interactions",
    tags=["Observer Mode"],
    description="Record an interaction in the session",
    summary="Record interaction",
    status_code=status.HTTP_201_CREATED,
)
async def record_interaction(
    session_id: Annotated[str, Path(description="Observer session ID")],
    request: RecordInteractionRequest,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict:
    """
    Record a user interaction (click, input, etc.) in the observer session.
    """
    try:
        recording = await observer_mode.record_interaction(
            observer_session_id=session_id,
            organization_id=current_org.organization_id,
            interaction_type=request.interaction_type,
            url=request.url,
            element_selector=request.element_selector,
            element_xpath=request.element_xpath,
            interaction_data=request.interaction_data,
            reasoning=request.reasoning,
        )
        return recording
    except Exception as e:
        LOG.error(
            "Failed to record interaction",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record interaction: {str(e)}",
        )


@base_router.post(
    "/observer/sessions/{session_id}/complete",
    tags=["Observer Mode"],
    description="Complete the observer session",
    summary="Complete session",
)
async def complete_session(
    session_id: Annotated[str, Path(description="Observer session ID")],
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict:
    """
    Mark the observer session as completed and ready for workflow generation.
    """
    try:
        session = await observer_mode.complete_observer_session(
            observer_session_id=session_id,
            organization_id=current_org.organization_id,
        )
        return session
    except observer_mode.ObserverSessionNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        LOG.error("Failed to complete session", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete session: {str(e)}",
        )


@base_router.post(
    "/observer/sessions/{session_id}/generate-workflow",
    tags=["Observer Mode"],
    description="Generate a workflow from the observer session",
    summary="Generate workflow",
    status_code=status.HTTP_201_CREATED,
)
async def generate_workflow(
    session_id: Annotated[str, Path(description="Observer session ID")],
    request: GenerateWorkflowRequest,
    background_tasks: BackgroundTasks,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict:
    """
    Convert the recorded session into an editable workflow using LLM.
    
    This analyzes all interactions, DOM snapshots, and reasoning to create
    a structured workflow with blocks and parameters.
    """
    try:
        workflow = await observer_mode.generate_workflow_from_recording(
            observer_session_id=session_id,
            organization_id=current_org.organization_id,
            title=request.title,
            description=request.description,
        )
        return workflow
    except observer_mode.ObserverSessionNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        LOG.error(
            "Failed to generate workflow",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate workflow: {str(e)}",
        )


@base_router.post(
    "/observer/sessions/{session_id}/export",
    tags=["Observer Mode"],
    description="Export observer session data",
    summary="Export session",
)
async def export_session(
    session_id: Annotated[str, Path(description="Observer session ID")],
    request: ExportSessionRequest,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict:
    """
    Export observer session data for sharing or backup.
    """
    try:
        export_data = await observer_mode.export_observer_session(
            observer_session_id=session_id,
            organization_id=current_org.organization_id,
            format=request.format,
        )
        return export_data
    except observer_mode.ObserverSessionNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        LOG.error("Failed to export session", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export session: {str(e)}",
        )


@base_router.post(
    "/observer/sessions/import",
    tags=["Observer Mode"],
    description="Import observer session data",
    summary="Import session",
    status_code=status.HTTP_201_CREATED,
)
async def import_session(
    request: ImportSessionRequest,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict:
    """
    Import an observer session from exported data.
    """
    try:
        session = await observer_mode.import_observer_session(
            organization_id=current_org.organization_id,
            session_data=request.session_data,
        )
        return session
    except Exception as e:
        LOG.error("Failed to import session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import session: {str(e)}",
        )


@base_router.post(
    "/observer/sessions/{session_id}/diff",
    tags=["Observer Mode"],
    description="Compare recorded steps with generated workflow",
    summary="Diff recording vs workflow",
)
async def diff_recording_workflow(
    session_id: Annotated[str, Path(description="Observer session ID")],
    request: DiffRequest,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> dict:
    """
    Generate a diff showing differences between recorded steps and the generated workflow blocks.
    
    This helps review and understand how the recording was translated into the workflow.
    """
    try:
        diff_data = await observer_mode.diff_recording_vs_workflow(
            observer_session_id=session_id,
            workflow_id=request.workflow_id,
            organization_id=current_org.organization_id,
        )
        return diff_data
    except observer_mode.ObserverSessionNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        LOG.error("Failed to generate diff", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate diff: {str(e)}",
        )


@base_router.delete(
    "/observer/sessions/{session_id}",
    tags=["Observer Mode"],
    description="Delete an observer session",
    summary="Delete session",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session_id: Annotated[str, Path(description="Observer session ID")],
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> None:
    """
    Delete an observer session and all its associated data.
    """
    try:
        # In a real implementation, soft delete from database
        LOG.info("Deleted observer session", session_id=session_id)
    except Exception as e:
        LOG.error("Failed to delete session", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )
