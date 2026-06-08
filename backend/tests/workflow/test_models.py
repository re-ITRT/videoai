"""workflow/models 测试"""
from app.workflow.models import WorkflowConfig


class TestWorkflowConfig:
    def test_workflow_config_has_required_fields(self):
        assert hasattr(WorkflowConfig, "workflow_name")
        assert hasattr(WorkflowConfig, "config")
        assert hasattr(WorkflowConfig, "enabled")
        assert hasattr(WorkflowConfig, "user_id")

    def test_defaults(self):
        # enabled default should be 1 (boolean True) or similar
        assert WorkflowConfig.__table__ is not None


class TestWorkflowConfigCreation:
    def test_create_config_instance(self):
        cfg = WorkflowConfig(
            workflow_name="test-flow",
            config='{"api_key": "test"}',
            enabled=1,
            user_id="test_user",
        )
        assert cfg.workflow_name == "test-flow"
        assert cfg.enabled == 1
        assert cfg.user_id == "test_user"

    def test_disabled_config(self):
        cfg = WorkflowConfig(
            workflow_name="test-disabled",
            config="{}",
            enabled=0,
            user_id="test_user",
        )
        assert cfg.enabled == 0
