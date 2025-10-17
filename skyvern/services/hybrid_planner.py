"""Hybrid symbolic + LLM planning engine."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from skyvern.forge.sdk.schemas.tasks import Task
from skyvern.forge.sdk.workflow.models.block import Block
from skyvern.forge.sdk.workflow.models.symbolic import (
    SymbolicActionBlueprint as SymbolicActionBlueprintModel,
    SymbolicAffordance as SymbolicAffordanceModel,
    SymbolicConstraintOperator,
    SymbolicGuard as SymbolicGuardModel,
    SymbolicPlanConfig,
    SymbolicPredicate as SymbolicPredicateModel,
    SymbolicPredicateType,
)
from skyvern.webeye.actions.action_types import ActionType
from skyvern.webeye.actions.actions import (
    Action,
    ActionStatus,
    CheckboxAction,
    ClickAction,
    CompleteAction,
    InputTextAction,
    ReloadPageAction,
    SelectOption,
    SelectOptionAction,
    TerminateAction,
    WaitAction,
)
from skyvern.webeye.scraper.scraper import ScrapedPage

LOG = structlog.get_logger()


@dataclass
class PlannerPredicate:
    """A predicate that can be evaluated on the current page state."""

    predicate_type: SymbolicPredicateType
    target: str | None = None
    expected_value: Any = None
    operator: SymbolicConstraintOperator = SymbolicConstraintOperator.AND
    metadata: dict[str, Any] = field(default_factory=dict)

    def evaluate(self, scraped_page: ScrapedPage | None, current_url: str | None = None) -> bool:
        """Evaluate the predicate against the current page state."""
        if self.predicate_type == SymbolicPredicateType.URL_PATTERN:
            if not current_url or not self.target:
                return False
            try:
                return re.match(self.target, current_url) is not None
            except re.error:
                LOG.warning("Invalid URL pattern", pattern=self.target)
                return False

        if not scraped_page or not scraped_page.elements:
            return False

        if self.predicate_type == SymbolicPredicateType.ELEMENT_EXISTS:
            return any(elem.get("id") == self.target for elem in scraped_page.elements)

        if self.predicate_type == SymbolicPredicateType.ELEMENT_VISIBLE:
            for elem in scraped_page.elements:
                if elem.get("id") == self.target:
                    attributes = elem.get("attributes", {})
                    style = attributes.get("style", "")
                    style_norm = style.replace(" ", "")
                    if "display:none" in style_norm or "visibility:hidden" in style_norm:
                        return False
                    return True
            return False

        if self.predicate_type == SymbolicPredicateType.ELEMENT_ENABLED:
            for elem in scraped_page.elements:
                if elem.get("id") == self.target:
                    attributes = elem.get("attributes", {})
                    disabled = attributes.get("disabled")
                    if disabled in {True, "true", "disabled"}:
                        return False
                    return True
            return False

        if self.predicate_type == SymbolicPredicateType.ELEMENT_COUNT:
            count = sum(1 for elem in scraped_page.elements if elem.get("id") == self.target)
            if self.expected_value is not None:
                return count == self.expected_value
            return count > 0

        if self.predicate_type == SymbolicPredicateType.ELEMENT_TEXT_CONTAINS:
            for elem in scraped_page.elements:
                if elem.get("id") == self.target:
                    text = elem.get("text", "") or ""
                    expected = self.expected_value or ""
                    return expected in text
            return False

        if self.predicate_type == SymbolicPredicateType.CUSTOM:
            # Custom predicates rely on metadata for evaluation
            expression = self.metadata.get("expression")
            if not expression:
                return False
            try:
                context = {
                    "page": scraped_page.model_dump() if hasattr(scraped_page, "model_dump") else scraped_page,
                    "url": current_url,
                }
                return bool(eval(expression, {"__builtins__": {}}, context))  # noqa: S307
            except Exception:
                LOG.warning("Failed to evaluate custom predicate", expression=expression, exc_info=True)
                return False

        LOG.debug("Unknown predicate type", predicate_type=self.predicate_type)
        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize predicate for logging."""
        return {
            "predicate_type": self.predicate_type.value,
            "target": self.target,
            "expected_value": self.expected_value,
            "operator": self.operator.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_model(cls, model: SymbolicPredicateModel) -> PlannerPredicate:
        """Create planner predicate from Pydantic model."""
        return cls(
            predicate_type=model.predicate_type,
            target=model.target,
            expected_value=model.expected_value,
            operator=model.operator,
            metadata=model.metadata,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlannerPredicate:
        """Backwards-compatible creation from dictionary."""
        return cls(
            predicate_type=SymbolicPredicateType(data.get("predicate_type", "element_exists")),
            target=data.get("target"),
            expected_value=data.get("expected_value"),
            operator=SymbolicConstraintOperator(data.get("operator", "and")),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PlannerAffordance:
    """Possible action description with pre/post conditions."""

    action_type: ActionType
    element_id: str | None = None
    preconditions: list[PlannerPredicate] = field(default_factory=list)
    postconditions: list[PlannerPredicate] = field(default_factory=list)
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_execute(self, scraped_page: ScrapedPage | None, current_url: str | None = None) -> bool:
        """Return True if all preconditions hold."""
        return all(predicate.evaluate(scraped_page, current_url) for predicate in self.preconditions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "element_id": self.element_id,
            "preconditions": [pred.to_dict() for pred in self.preconditions],
            "postconditions": [pred.to_dict() for pred in self.postconditions],
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_model(cls, model: SymbolicAffordanceModel) -> PlannerAffordance:
        return cls(
            action_type=model.action_type,
            element_id=model.element_id,
            preconditions=[PlannerPredicate.from_model(pred) for pred in model.preconditions],
            postconditions=[PlannerPredicate.from_model(pred) for pred in model.postconditions],
            priority=model.priority,
            metadata=model.metadata,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlannerAffordance:
        return cls(
            action_type=ActionType(data.get("action_type", ActionType.CLICK)),
            element_id=data.get("element_id"),
            preconditions=[PlannerPredicate.from_dict(pred) for pred in data.get("preconditions", [])],
            postconditions=[PlannerPredicate.from_dict(pred) for pred in data.get("postconditions", [])],
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PlannerGuard:
    """Guard condition preventing execution of certain actions."""

    name: str
    predicates: list[PlannerPredicate] = field(default_factory=list)
    action_types_blocked: list[ActionType] = field(default_factory=list)
    message: str | None = None

    def is_active(self, scraped_page: ScrapedPage | None, current_url: str | None = None) -> bool:
        return all(predicate.evaluate(scraped_page, current_url) for predicate in self.predicates)

    def blocks_action(self, action: Action) -> bool:
        return any(action.action_type == blocked for blocked in self.action_types_blocked)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "predicates": [pred.to_dict() for pred in self.predicates],
            "action_types_blocked": [action_type.value for action_type in self.action_types_blocked],
            "message": self.message,
        }

    @classmethod
    def from_model(cls, model: SymbolicGuardModel) -> PlannerGuard:
        return cls(
            name=model.name,
            predicates=[PlannerPredicate.from_model(pred) for pred in model.predicates],
            action_types_blocked=list(model.action_types_blocked),
            message=model.message,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlannerGuard:
        return cls(
            name=data.get("name", "guard"),
            predicates=[PlannerPredicate.from_dict(pred) for pred in data.get("predicates", [])],
            action_types_blocked=[ActionType(action_type) for action_type in data.get("action_types_blocked", [])],
            message=data.get("message"),
        )


@dataclass
class PlanValidationResult:
    """Result of hybrid plan validation."""

    valid: bool
    filtered_actions: list[Action]
    rejected_actions: list[tuple[Action, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    audit_data: dict[str, Any] = field(default_factory=dict)


class HybridPlanner:
    """Hybrid symbolic + LLM planner."""

    def __init__(self) -> None:
        self.predicates: list[PlannerPredicate] = []
        self.affordances: list[PlannerAffordance] = []
        self.guards: list[PlannerGuard] = []
        self.loop_detection_window: int = 5
        self.action_history: list[tuple[str, ActionType]] = []
        self.fallback_actions: list[Action] = []

    def register_predicate(self, predicate: PlannerPredicate) -> None:
        self.predicates.append(predicate)

    def register_affordance(self, affordance: PlannerAffordance) -> None:
        self.affordances.append(affordance)
        LOG.debug("Registered affordance", action_type=affordance.action_type, element_id=affordance.element_id)

    def register_guard(self, guard: PlannerGuard) -> None:
        self.guards.append(guard)
        LOG.debug("Registered guard", name=guard.name)

    def clear(self) -> None:
        self.predicates.clear()
        self.affordances.clear()
        self.guards.clear()
        self.fallback_actions.clear()
        self.action_history.clear()

    def validate_and_filter_actions(
        self,
        actions: list[Action],
        scraped_page: ScrapedPage | None,
        current_url: str | None = None,
        task: Task | None = None,
    ) -> PlanValidationResult:
        filtered_actions: list[Action] = []
        rejected_actions: list[tuple[Action, str]] = []
        warnings: list[str] = []

        audit_data = {
            "total_actions": len(actions),
            "affordances_checked": len(self.affordances),
            "guards_checked": len(self.guards),
            "task_id": task.task_id if task else None,
        }

        LOG.info(
            "Hybrid plan validation started",
            task_id=task.task_id if task else None,
            num_actions=len(actions),
            num_affordances=len(self.affordances),
            num_guards=len(self.guards),
        )

        for action in actions:
            rejection_reason: str | None = None

            # Evaluate guard conditions
            for guard in self.guards:
                if guard.is_active(scraped_page, current_url) and guard.blocks_action(action):
                    rejection_reason = guard.message or f"Guard '{guard.name}' blocked action"
                    LOG.warning(
                        "Action blocked by guard",
                        guard_name=guard.name,
                        action_type=action.action_type,
                        element_id=getattr(action, "element_id", None),
                    )
                    break

            if rejection_reason:
                rejected_actions.append((action, rejection_reason))
                continue

            if self.affordances:
                matching_affordances = [
                    affordance
                    for affordance in self.affordances
                    if affordance.action_type == action.action_type
                    and (affordance.element_id is None or affordance.element_id == getattr(action, "element_id", None))
                ]

                if matching_affordances:
                    matching_affordances.sort(key=lambda aff: aff.priority, reverse=True)
                    selected_affordance = matching_affordances[0]
                    if selected_affordance.can_execute(scraped_page, current_url):
                        filtered_actions.append(action)
                    else:
                        rejection_reason = (
                            selected_affordance.metadata.get("failure_reason")
                            if selected_affordance.metadata
                            else "Affordance preconditions not met"
                        )
                        rejected_actions.append((action, rejection_reason))
                        LOG.warning(
                            "Affordance preconditions failed",
                            action_type=action.action_type,
                            element_id=getattr(action, "element_id", None),
                        )
                else:
                    warnings.append(
                        f"No affordance registered for action {action.action_type.value}"
                    )
                    filtered_actions.append(action)
            else:
                filtered_actions.append(action)

        loop_warning = self._detect_loops(filtered_actions)
        if loop_warning:
            warnings.append(loop_warning)

        audit_data.update(
            {
                "filtered_actions": len(filtered_actions),
                "rejected_actions": len(rejected_actions),
                "warnings": warnings,
            }
        )

        LOG.info(
            "Hybrid plan validation completed",
            valid=bool(filtered_actions),
            filtered=len(filtered_actions),
            rejected=len(rejected_actions),
            warnings=len(warnings),
        )

        return PlanValidationResult(
            valid=bool(filtered_actions),
            filtered_actions=filtered_actions,
            rejected_actions=rejected_actions,
            warnings=warnings,
            audit_data=audit_data,
        )

    def _detect_loops(self, actions: list[Action]) -> str | None:
        if self.loop_detection_window <= 0:
            return None

        for action in actions:
            element_id = getattr(action, "element_id", "") or "global"
            self.action_history.append((element_id, action.action_type))

        max_history = self.loop_detection_window * 2
        if len(self.action_history) > max_history:
            self.action_history = self.action_history[-max_history:]

        if len(self.action_history) < self.loop_detection_window * 2:
            return None

        recent = self.action_history[-self.loop_detection_window :]
        previous = self.action_history[-self.loop_detection_window * 2 : -self.loop_detection_window]

        if recent == previous:
            LOG.warning("Potential loop detected", recent_actions=recent)
            return f"Potential loop detected: repeated sequence of {self.loop_detection_window} actions"
        return None

    def reconcile_with_fallback(
        self,
        validation_result: PlanValidationResult,
        fallback_actions: list[Action] | None = None,
    ) -> list[Action]:
        if validation_result.valid and validation_result.filtered_actions:
            LOG.info("Using validated actions", count=len(validation_result.filtered_actions))
            return validation_result.filtered_actions

        LOG.warning(
            "Plan validation failed",
            rejected=len(validation_result.rejected_actions),
            warnings=validation_result.warnings,
        )

        if fallback_actions:
            LOG.info("Using provided fallback actions", count=len(fallback_actions))
            return fallback_actions

        if self.fallback_actions:
            LOG.info("Using configured fallback actions", count=len(self.fallback_actions))
            return self.fallback_actions

        LOG.warning("No fallback actions available after hybrid planning failure")
        return []

    def extract_affordances_from_page(self, scraped_page: ScrapedPage) -> list[PlannerAffordance]:
        affordances: list[PlannerAffordance] = []
        if not scraped_page or not scraped_page.elements:
            return affordances

        for element in scraped_page.elements:
            element_id = element.get("id")
            if not element_id:
                continue

            tag_name = (element.get("tagName") or "").lower()
            attributes = element.get("attributes", {})

            if tag_name in {"button", "a"} or attributes.get("onclick"):
                affordances.append(
                    PlannerAffordance(
                        action_type=ActionType.CLICK,
                        element_id=element_id,
                        preconditions=[
                            PlannerPredicate(SymbolicPredicateType.ELEMENT_VISIBLE, element_id),
                            PlannerPredicate(SymbolicPredicateType.ELEMENT_ENABLED, element_id),
                        ],
                    )
                )

            if tag_name in {"input", "textarea"}:
                input_type = (attributes.get("type") or "text").lower()
                if input_type in {"text", "email", "password", "tel", "search", "url"}:
                    affordances.append(
                        PlannerAffordance(
                            action_type=ActionType.INPUT_TEXT,
                            element_id=element_id,
                            preconditions=[
                                PlannerPredicate(SymbolicPredicateType.ELEMENT_VISIBLE, element_id),
                                PlannerPredicate(SymbolicPredicateType.ELEMENT_ENABLED, element_id),
                            ],
                        )
                    )

            if tag_name == "select":
                affordances.append(
                    PlannerAffordance(
                        action_type=ActionType.SELECT_OPTION,
                        element_id=element_id,
                        preconditions=[
                            PlannerPredicate(SymbolicPredicateType.ELEMENT_VISIBLE, element_id),
                            PlannerPredicate(SymbolicPredicateType.ELEMENT_ENABLED, element_id),
                        ],
                    )
                )

        LOG.debug("Extracted affordances from page", count=len(affordances))
        return affordances

    def export_audit_log(self, validation_result: PlanValidationResult) -> str:
        audit_log = {
            "validation_result": {
                "valid": validation_result.valid,
                "filtered_actions_count": len(validation_result.filtered_actions),
                "rejected_actions_count": len(validation_result.rejected_actions),
                "warnings": validation_result.warnings,
            },
            "rejected_actions": [
                {
                    "action_type": action.action_type.value,
                    "element_id": getattr(action, "element_id", None),
                    "reason": reason,
                }
                for action, reason in validation_result.rejected_actions
            ],
            "audit_data": validation_result.audit_data,
            "affordances": [aff.to_dict() for aff in self.affordances],
            "guards": [guard.to_dict() for guard in self.guards],
        }
        return json.dumps(audit_log, indent=2)

    def load_from_block(self, block: Block) -> None:
        symbolic_config_data: Any | None = None
        if hasattr(block, "symbolic_config") and block.symbolic_config:
            symbolic_config_data = block.symbolic_config
        else:
            metadata = getattr(block, "metadata", {})
            if isinstance(metadata, dict):
                symbolic_config_data = metadata.get("symbolic_config")

        if symbolic_config_data is None:
            return

        if isinstance(symbolic_config_data, SymbolicPlanConfig):
            self.load_from_plan_config(symbolic_config_data)
        elif isinstance(symbolic_config_data, dict):
            # Backwards-compatible conversion
            plan_config = SymbolicPlanConfig.model_validate(symbolic_config_data)
            self.load_from_plan_config(plan_config)
        else:
            LOG.warning("Unsupported symbolic configuration type", config_type=type(symbolic_config_data))

    def load_from_plan_config(self, plan_config: SymbolicPlanConfig) -> None:
        self.clear()

        for predicate_model in plan_config.predicates:
            self.register_predicate(PlannerPredicate.from_model(predicate_model))

        for affordance_model in plan_config.affordances:
            self.register_affordance(PlannerAffordance.from_model(affordance_model))

        for guard_model in plan_config.guards:
            self.register_guard(PlannerGuard.from_model(guard_model))

        if plan_config.loop_guard_window:
            self.loop_detection_window = plan_config.loop_guard_window

        self.fallback_actions = [
            action
            for blueprint in plan_config.fallback_actions
            if (action := self._action_from_blueprint(blueprint)) is not None
        ]

    def _action_from_blueprint(self, blueprint: SymbolicActionBlueprintModel) -> Action | None:
        try:
            if blueprint.action_type == ActionType.CLICK:
                if not blueprint.element_id:
                    raise ValueError("CLICK action requires element_id")
                return ClickAction(element_id=blueprint.element_id, reasoning=blueprint.reasoning)

            if blueprint.action_type == ActionType.INPUT_TEXT:
                if not blueprint.element_id or blueprint.text is None:
                    raise ValueError("INPUT_TEXT action requires element_id and text")
                return InputTextAction(
                    element_id=blueprint.element_id,
                    text=blueprint.text,
                    reasoning=blueprint.reasoning,
                )

            if blueprint.action_type == ActionType.SELECT_OPTION:
                if not blueprint.element_id or not blueprint.option:
                    raise ValueError("SELECT_OPTION action requires element_id and option")
                option_model = blueprint.option
                option = SelectOption(
                    label=option_model.get("label"),
                    value=option_model.get("value"),
                    index=option_model.get("index"),
                )
                return SelectOptionAction(
                    element_id=blueprint.element_id,
                    option=option,
                    reasoning=blueprint.reasoning,
                )

            if blueprint.action_type == ActionType.CHECKBOX:
                if not blueprint.element_id:
                    raise ValueError("CHECKBOX action requires element_id")
                is_checked = blueprint.metadata.get("is_checked") if blueprint.metadata else None
                if is_checked is None:
                    raise ValueError("CHECKBOX action requires 'is_checked' flag in metadata")
                return CheckboxAction(
                    element_id=blueprint.element_id,
                    is_checked=bool(is_checked),
                    reasoning=blueprint.reasoning,
                )

            if blueprint.action_type == ActionType.WAIT:
                seconds = blueprint.metadata.get("seconds") if blueprint.metadata else None
                if seconds is None:
                    seconds = 5
                return WaitAction(seconds=int(seconds), reasoning=blueprint.reasoning)

            if blueprint.action_type == ActionType.TERMINATE:
                return TerminateAction(
                    reasoning=blueprint.reasoning,
                    status=ActionStatus.pending,
                )

            if blueprint.action_type == ActionType.COMPLETE:
                return CompleteAction(
                    reasoning=blueprint.reasoning,
                    status=ActionStatus.pending,
                )

            if blueprint.action_type == ActionType.RELOAD_PAGE:
                return ReloadPageAction(
                    reasoning=blueprint.reasoning,
                    status=ActionStatus.pending,
                )

            # Fallback to generic Action if type not explicitly handled
            return Action(action_type=blueprint.action_type, reasoning=blueprint.reasoning)
        except Exception as exc:
            LOG.warning(
                "Failed to convert blueprint to action",
                action_type=blueprint.action_type,
                element_id=blueprint.element_id,
                error=str(exc),
            )
            return None
