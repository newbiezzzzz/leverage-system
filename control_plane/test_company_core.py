"""Tests for company/project lifecycle validation."""
from company_core import Project, approval_required, validate_project


def test_project_validation_accepts_intake():
    project = Project(id="demo", name="Demo", type="saas")
    assert validate_project(project) == []


def test_project_validation_rejects_invalid_stage():
    project = Project(id="demo", name="Demo", lifecycle_stage="unknown", status="intake")
    assert "invalid lifecycle stage: unknown" in validate_project(project)


def test_restricted_actions_require_approval():
    assert approval_required("move_money") is True
    assert approval_required("research") is False
