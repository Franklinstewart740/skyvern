"""
Unit tests for the hybrid symbolic + LLM planner.
"""
import pytest

from skyvern.forge.sdk.schemas.tasks import Task, TaskStatus
from skyvern.services.hybrid_planner import (
    ActionAffordance,
    ConstraintOperator,
    GuardCondition,
    HybridPlanner,
    PredicateType,
    SymbolicPredicate,
)
from skyvern.webeye.actions.action_types import ActionType
from skyvern.webeye.actions.actions import ClickAction, InputTextAction, TerminateAction
from skyvern.webeye.scraper.scraper import ScrapedPage


@pytest.fixture
def sample_scraped_page():
    """Create a sample scraped page for testing."""
    return ScrapedPage(
        elements=[
            {
                "id": "submit_btn",
                "tagName": "button",
                "text": "Submit",
                "attributes": {"type": "submit"},
            },
            {
                "id": "email_input",
                "tagName": "input",
                "text": "",
                "attributes": {"type": "email", "disabled": False},
            },
            {
                "id": "disabled_input",
                "tagName": "input",
                "text": "",
                "attributes": {"type": "text", "disabled": True},
            },
        ],
        html="<html><body><button id='submit_btn'>Submit</button></body></html>",
        url="https://example.com/form",
        screenshots=[],
        id_to_css_map={},
        id_to_xpath_map={},
    )


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        task_id="test_task_123",
        organization_id="test_org",
        url="https://example.com",
        status=TaskStatus.running,
    )


class TestSymbolicPredicate:
    """Test symbolic predicate evaluation."""

    def test_element_exists_predicate(self, sample_scraped_page):
        """Test ELEMENT_EXISTS predicate."""
        predicate = SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_EXISTS,
            target="submit_btn",
        )
        assert predicate.evaluate(sample_scraped_page) is True

        predicate_missing = SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_EXISTS,
            target="missing_element",
        )
        assert predicate_missing.evaluate(sample_scraped_page) is False

    def test_element_visible_predicate(self, sample_scraped_page):
        """Test ELEMENT_VISIBLE predicate."""
        predicate = SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_VISIBLE,
            target="submit_btn",
        )
        assert predicate.evaluate(sample_scraped_page) is True

    def test_element_enabled_predicate(self, sample_scraped_page):
        """Test ELEMENT_ENABLED predicate."""
        predicate_enabled = SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_ENABLED,
            target="email_input",
        )
        assert predicate_enabled.evaluate(sample_scraped_page) is True

        predicate_disabled = SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_ENABLED,
            target="disabled_input",
        )
        assert predicate_disabled.evaluate(sample_scraped_page) is False

    def test_url_pattern_predicate(self, sample_scraped_page):
        """Test URL_PATTERN predicate."""
        predicate = SymbolicPredicate(
            predicate_type=PredicateType.URL_PATTERN,
            target=r"https://example\.com/.*",
        )
        assert predicate.evaluate(sample_scraped_page, "https://example.com/form") is True
        assert predicate.evaluate(sample_scraped_page, "https://different.com/page") is False

    def test_element_text_contains_predicate(self, sample_scraped_page):
        """Test ELEMENT_TEXT_CONTAINS predicate."""
        predicate = SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_TEXT_CONTAINS,
            target="submit_btn",
            expected_value="Submit",
        )
        assert predicate.evaluate(sample_scraped_page) is True

        predicate_missing = SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_TEXT_CONTAINS,
            target="submit_btn",
            expected_value="Cancel",
        )
        assert predicate_missing.evaluate(sample_scraped_page) is False

    def test_predicate_serialization(self):
        """Test predicate to_dict and from_dict."""
        predicate = SymbolicPredicate(
            predicate_type=PredicateType.ELEMENT_EXISTS,
            target="test_element",
            expected_value=True,
            operator=ConstraintOperator.AND,
            metadata={"test": "data"},
        )

        predicate_dict = predicate.to_dict()
        assert predicate_dict["predicate_type"] == "element_exists"
        assert predicate_dict["target"] == "test_element"
        assert predicate_dict["expected_value"] is True

        restored = SymbolicPredicate.from_dict(predicate_dict)
        assert restored.predicate_type == PredicateType.ELEMENT_EXISTS
        assert restored.target == "test_element"
        assert restored.expected_value is True


class TestActionAffordance:
    """Test action affordance validation."""

    def test_affordance_preconditions(self, sample_scraped_page):
        """Test affordance precondition checking."""
        affordance = ActionAffordance(
            action_type=ActionType.CLICK,
            element_id="submit_btn",
            preconditions=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_EXISTS,
                    target="submit_btn",
                ),
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_VISIBLE,
                    target="submit_btn",
                ),
            ],
        )

        assert affordance.can_execute(sample_scraped_page) is True

    def test_affordance_failed_preconditions(self, sample_scraped_page):
        """Test affordance with failed preconditions."""
        affordance = ActionAffordance(
            action_type=ActionType.CLICK,
            element_id="missing_element",
            preconditions=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_EXISTS,
                    target="missing_element",
                ),
            ],
        )

        assert affordance.can_execute(sample_scraped_page) is False

    def test_affordance_serialization(self):
        """Test affordance to_dict and from_dict."""
        affordance = ActionAffordance(
            action_type=ActionType.CLICK,
            element_id="test_btn",
            preconditions=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_EXISTS,
                    target="test_btn",
                )
            ],
            priority=10,
            metadata={"test": "data"},
        )

        affordance_dict = affordance.to_dict()
        assert affordance_dict["action_type"] == "click"
        assert affordance_dict["element_id"] == "test_btn"
        assert len(affordance_dict["preconditions"]) == 1

        restored = ActionAffordance.from_dict(affordance_dict)
        assert restored.action_type == ActionType.CLICK
        assert restored.element_id == "test_btn"
        assert len(restored.preconditions) == 1


class TestGuardCondition:
    """Test guard condition blocking."""

    def test_guard_blocks_action(self, sample_scraped_page):
        """Test guard blocking specific actions."""
        guard = GuardCondition(
            name="login_required",
            predicates=[
                SymbolicPredicate(
                    predicate_type=PredicateType.URL_PATTERN,
                    target=r"https://example\.com/.*",
                )
            ],
            action_types_blocked=[ActionType.TERMINATE],
            message="Cannot terminate on this page",
        )

        assert guard.is_active(sample_scraped_page, "https://example.com/form") is True

        terminate_action = TerminateAction(
            action_type=ActionType.TERMINATE,
            reasoning="Test termination",
        )
        assert guard.blocks_action(terminate_action) is True

        click_action = ClickAction(
            action_type=ActionType.CLICK,
            element_id="submit_btn",
        )
        assert guard.blocks_action(click_action) is False

    def test_guard_not_active(self, sample_scraped_page):
        """Test guard that is not active."""
        guard = GuardCondition(
            name="other_page_guard",
            predicates=[
                SymbolicPredicate(
                    predicate_type=PredicateType.URL_PATTERN,
                    target=r"https://other\.com/.*",
                )
            ],
            action_types_blocked=[ActionType.CLICK],
        )

        assert guard.is_active(sample_scraped_page, "https://example.com/form") is False

    def test_guard_serialization(self):
        """Test guard to_dict and from_dict."""
        guard = GuardCondition(
            name="test_guard",
            predicates=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_EXISTS,
                    target="error_msg",
                )
            ],
            action_types_blocked=[ActionType.CLICK, ActionType.INPUT_TEXT],
            message="Error detected",
        )

        guard_dict = guard.to_dict()
        assert guard_dict["name"] == "test_guard"
        assert len(guard_dict["predicates"]) == 1
        assert len(guard_dict["action_types_blocked"]) == 2

        restored = GuardCondition.from_dict(guard_dict)
        assert restored.name == "test_guard"
        assert len(restored.predicates) == 1
        assert len(restored.action_types_blocked) == 2


class TestHybridPlanner:
    """Test the hybrid planner integration."""

    def test_planner_initialization(self):
        """Test planner initialization."""
        planner = HybridPlanner()
        assert len(planner.affordances) == 0
        assert len(planner.guards) == 0
        assert planner.loop_detection_window == 5

    def test_register_affordance(self):
        """Test registering affordances."""
        planner = HybridPlanner()
        affordance = ActionAffordance(
            action_type=ActionType.CLICK,
            element_id="test_btn",
        )
        planner.register_affordance(affordance)
        assert len(planner.affordances) == 1

    def test_register_guard(self):
        """Test registering guards."""
        planner = HybridPlanner()
        guard = GuardCondition(
            name="test_guard",
            predicates=[],
        )
        planner.register_guard(guard)
        assert len(planner.guards) == 1

    def test_validate_actions_no_constraints(self, sample_scraped_page, sample_task):
        """Test validation with no constraints (all actions pass)."""
        planner = HybridPlanner()
        actions = [
            ClickAction(action_type=ActionType.CLICK, element_id="submit_btn"),
            InputTextAction(action_type=ActionType.INPUT_TEXT, element_id="email_input", text="test@example.com"),
        ]

        result = planner.validate_and_filter_actions(
            actions=actions,
            scraped_page=sample_scraped_page,
            current_url="https://example.com/form",
            task=sample_task,
        )

        assert result.valid is True
        assert len(result.filtered_actions) == 2
        assert len(result.rejected_actions) == 0

    def test_validate_actions_with_guards(self, sample_scraped_page, sample_task):
        """Test validation with guard conditions."""
        planner = HybridPlanner()

        # Register guard that blocks terminate actions
        guard = GuardCondition(
            name="no_terminate",
            predicates=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_EXISTS,
                    target="submit_btn",
                )
            ],
            action_types_blocked=[ActionType.TERMINATE],
            message="Terminate not allowed when submit button exists",
        )
        planner.register_guard(guard)

        actions = [
            ClickAction(action_type=ActionType.CLICK, element_id="submit_btn"),
            TerminateAction(action_type=ActionType.TERMINATE, reasoning="Test"),
        ]

        result = planner.validate_and_filter_actions(
            actions=actions,
            scraped_page=sample_scraped_page,
            current_url="https://example.com/form",
            task=sample_task,
        )

        assert result.valid is True
        assert len(result.filtered_actions) == 1
        assert len(result.rejected_actions) == 1
        assert result.filtered_actions[0].action_type == ActionType.CLICK

    def test_validate_actions_with_affordances(self, sample_scraped_page, sample_task):
        """Test validation with affordances."""
        planner = HybridPlanner()

        # Register affordance for clicking submit button
        affordance = ActionAffordance(
            action_type=ActionType.CLICK,
            element_id="submit_btn",
            preconditions=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_EXISTS,
                    target="submit_btn",
                ),
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_VISIBLE,
                    target="submit_btn",
                ),
            ],
        )
        planner.register_affordance(affordance)

        actions = [
            ClickAction(action_type=ActionType.CLICK, element_id="submit_btn"),
        ]

        result = planner.validate_and_filter_actions(
            actions=actions,
            scraped_page=sample_scraped_page,
            current_url="https://example.com/form",
            task=sample_task,
        )

        assert result.valid is True
        assert len(result.filtered_actions) == 1

    def test_validate_actions_affordance_fails(self, sample_scraped_page, sample_task):
        """Test validation where affordance preconditions fail."""
        planner = HybridPlanner()

        # Register affordance with failing precondition
        affordance = ActionAffordance(
            action_type=ActionType.CLICK,
            element_id="missing_element",
            preconditions=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_EXISTS,
                    target="missing_element",
                ),
            ],
        )
        planner.register_affordance(affordance)

        actions = [
            ClickAction(action_type=ActionType.CLICK, element_id="missing_element"),
        ]

        result = planner.validate_and_filter_actions(
            actions=actions,
            scraped_page=sample_scraped_page,
            current_url="https://example.com/form",
            task=sample_task,
        )

        assert result.valid is False
        assert len(result.filtered_actions) == 0
        assert len(result.rejected_actions) == 1

    def test_loop_detection(self, sample_scraped_page, sample_task):
        """Test loop detection in action sequences."""
        planner = HybridPlanner()
        planner.loop_detection_window = 3

        # Simulate repeated actions
        for _ in range(2):
            actions = [
                ClickAction(action_type=ActionType.CLICK, element_id="btn1"),
                ClickAction(action_type=ActionType.CLICK, element_id="btn2"),
                InputTextAction(action_type=ActionType.INPUT_TEXT, element_id="input1", text="test"),
            ]
            result = planner.validate_and_filter_actions(
                actions=actions,
                scraped_page=sample_scraped_page,
                current_url="https://example.com/form",
                task=sample_task,
            )

        # Check if loop warning is present
        assert len(result.warnings) > 0
        assert any("loop" in warning.lower() for warning in result.warnings)

    def test_reconcile_with_fallback(self):
        """Test reconciliation with fallback actions."""
        planner = HybridPlanner()

        # Create validation result with no valid actions
        from skyvern.services.hybrid_planner import PlanValidationResult

        validation_result = PlanValidationResult(
            valid=False,
            filtered_actions=[],
            rejected_actions=[],
        )

        fallback_actions = [
            ClickAction(action_type=ActionType.CLICK, element_id="fallback_btn"),
        ]

        result = planner.reconcile_with_fallback(validation_result, fallback_actions)

        assert len(result) == 1
        assert result[0].action_type == ActionType.CLICK

    def test_extract_affordances_from_page(self, sample_scraped_page):
        """Test automatic affordance extraction from page."""
        planner = HybridPlanner()
        affordances = planner.extract_affordances_from_page(sample_scraped_page)

        assert len(affordances) > 0
        # Should detect button and input elements
        action_types = [aff.action_type for aff in affordances]
        assert ActionType.CLICK in action_types
        assert ActionType.INPUT_TEXT in action_types

    def test_export_audit_log(self, sample_scraped_page, sample_task):
        """Test audit log export."""
        planner = HybridPlanner()

        actions = [
            ClickAction(action_type=ActionType.CLICK, element_id="submit_btn"),
        ]

        result = planner.validate_and_filter_actions(
            actions=actions,
            scraped_page=sample_scraped_page,
            current_url="https://example.com/form",
            task=sample_task,
        )

        audit_log = planner.export_audit_log(result)

        assert isinstance(audit_log, str)
        assert "validation_result" in audit_log
        assert "audit_data" in audit_log

    def test_clear_methods(self):
        """Test clearing affordances and guards."""
        planner = HybridPlanner()

        planner.register_affordance(
            ActionAffordance(action_type=ActionType.CLICK, element_id="btn")
        )
        planner.register_guard(
            GuardCondition(name="test", predicates=[])
        )

        assert len(planner.affordances) == 1
        assert len(planner.guards) == 1

        planner.clear_affordances()
        assert len(planner.affordances) == 0

        planner.clear_guards()
        assert len(planner.guards) == 0


class TestBranchingAndFailureRecovery:
    """Test branching logic and failure recovery scenarios."""

    def test_branching_based_on_page_state(self, sample_scraped_page, sample_task):
        """Test branching based on page state using guards."""
        planner = HybridPlanner()

        # Guard for error state - blocks normal actions
        error_guard = GuardCondition(
            name="error_state",
            predicates=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_TEXT_CONTAINS,
                    target="submit_btn",
                    expected_value="Submit",
                )
            ],
            action_types_blocked=[ActionType.TERMINATE],
            message="Error detected, cannot terminate",
        )
        planner.register_guard(error_guard)

        # Actions that should be filtered based on state
        actions = [
            ClickAction(action_type=ActionType.CLICK, element_id="submit_btn"),
            TerminateAction(action_type=ActionType.TERMINATE, reasoning="Done"),
        ]

        result = planner.validate_and_filter_actions(
            actions=actions,
            scraped_page=sample_scraped_page,
            current_url="https://example.com/form",
            task=sample_task,
        )

        # Terminate should be blocked
        assert len(result.filtered_actions) == 1
        assert result.filtered_actions[0].action_type == ActionType.CLICK

    def test_failure_recovery_with_fallback(self, sample_scraped_page):
        """Test failure recovery using fallback actions."""
        planner = HybridPlanner()

        # Register strict affordances that will reject all actions
        affordance = ActionAffordance(
            action_type=ActionType.CLICK,
            element_id="missing_btn",
            preconditions=[
                SymbolicPredicate(
                    predicate_type=PredicateType.ELEMENT_EXISTS,
                    target="missing_btn",
                )
            ],
        )
        planner.register_affordance(affordance)

        actions = [
            ClickAction(action_type=ActionType.CLICK, element_id="missing_btn"),
        ]

        result = planner.validate_and_filter_actions(
            actions=actions,
            scraped_page=sample_scraped_page,
            current_url="https://example.com/form",
            task=None,
        )

        # All actions rejected
        assert len(result.filtered_actions) == 0

        # Use fallback
        fallback_actions = [
            InputTextAction(action_type=ActionType.INPUT_TEXT, element_id="email_input", text="recovery@example.com"),
        ]

        final_actions = planner.reconcile_with_fallback(result, fallback_actions)
        assert len(final_actions) == 1
        assert final_actions[0].action_type == ActionType.INPUT_TEXT
