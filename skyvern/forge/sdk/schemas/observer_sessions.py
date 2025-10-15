"""
Schema definitions for Observer Mode 2.0
"""
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ObserverSessionStatus(StrEnum):
    recording = "recording"
    completed = "completed"
    processing = "processing"
    failed = "failed"


class ObserverSession(BaseModel):
    observer_session_id: str
    organization_id: str
    browser_session_id: str | None = None
    workflow_permanent_id: str | None = None
    generated_workflow_id: str | None = None
    title: str | None = None
    description: str | None = None
    status: ObserverSessionStatus
    metadata: dict[str, Any] | None = None
    start_url: str | None = None
    created_at: datetime
    modified_at: datetime
    completed_at: datetime | None = None
    deleted_at: datetime | None = None


class ObserverRecording(BaseModel):
    observer_recording_id: str
    observer_session_id: str
    organization_id: str
    sequence_number: int
    recording_type: str
    url: str | None = None
    timestamp: datetime
    data: dict[str, Any] | None = None
    reasoning: str | None = None
    created_at: datetime


class ObserverDOMSnapshot(BaseModel):
    observer_dom_snapshot_id: str
    observer_recording_id: str
    observer_session_id: str
    organization_id: str
    url: str
    html_content: str | None = None
    screenshot_artifact_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime


class ObserverInteraction(BaseModel):
    observer_interaction_id: str
    observer_recording_id: str
    observer_session_id: str
    organization_id: str
    interaction_type: str
    element_selector: str | None = None
    element_xpath: str | None = None
    interaction_data: dict[str, Any] | None = None
    timestamp: datetime
    created_at: datetime


class CreateObserverSessionRequest(BaseModel):
    browser_session_id: str | None = None
    title: str | None = None
    description: str | None = None
    start_url: str | None = None
    metadata: dict[str, Any] | None = None


class RecordInteractionRequest(BaseModel):
    interaction_type: str
    url: str
    element_selector: str | None = None
    element_xpath: str | None = None
    interaction_data: dict[str, Any] | None = None
    reasoning: str | None = None


class GenerateWorkflowRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    auto_publish: bool = False


class ExportSessionRequest(BaseModel):
    format: str = "json"


class ImportSessionRequest(BaseModel):
    session_data: dict[str, Any]


class DiffRequest(BaseModel):
    workflow_id: str
