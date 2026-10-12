import copy
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "aws_release", Path(__file__).parents[1] / "scripts/aws_release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
IMAGE = "123456789012.dkr.ecr.us-west-2.amazonaws.com/healthcare-di-dev@sha256:" + "a" * 64


def test_fault_revision_only_changes_container_health_command():
    task = {
        "family": "healthcare-di-dev",
        "taskDefinitionArn": "old:1",
        "revision": 1,
        "executionRoleArn": "execution",
        "containerDefinitions": [
            {
                "name": "dashboard",
                "image": IMAGE,
                "portMappings": [{"containerPort": 8501}],
                "healthCheck": {"command": ["CMD", "python", "health.py"], "interval": 30},
                "logConfiguration": {"logDriver": "awslogs"},
            }
        ],
    }
    original = copy.deepcopy(task)
    result = release.revision_payload(task, IMAGE, fail_health=True)
    assert task == original
    assert "revision" not in result and "taskDefinitionArn" not in result
    result["containerDefinitions"][0]["healthCheck"]["command"] = ["CMD", "python", "health.py"]
    assert result == {key: value for key, value in task.items() if key in release.REGISTER_FIELDS}


def test_mutable_image_and_other_repository_are_rejected():
    task = {"containerDefinitions": [{"name": "dashboard", "image": IMAGE}]}
    with pytest.raises(ValueError, match="immutable"):
        release.revision_payload(task, "repo:latest")
    with pytest.raises(ValueError, match="existing ECR"):
        release.revision_payload(task, IMAGE.replace("healthcare-di-dev", "other"))


def test_healthy_rollback_cannot_pass_as_new_release():
    service = {
        "desiredCount": 1,
        "runningCount": 1,
        "pendingCount": 0,
        "deployments": [{"status": "PRIMARY", "rolloutState": "COMPLETED", "taskDefinition": "A"}],
    }
    tasks = [
        {
            "taskDefinitionArn": "A",
            "healthStatus": "HEALTHY",
            "containers": [{"name": "dashboard", "imageDigest": "sha256:" + "a" * 64}],
        }
    ]
    targets = [{"TargetHealth": {"State": "healthy"}}]
    assert release.release_matches(service, tasks, targets, "A", "sha256:" + "a" * 64)
    assert not release.release_matches(service, tasks, targets, "B", "sha256:" + "a" * 64)
    assert not release.release_matches(service, tasks, targets, "A", "sha256:" + "b" * 64)
    tasks[0]["healthStatus"] = "UNHEALTHY"
    assert not release.release_matches(service, tasks, targets, "A", "sha256:" + "a" * 64)


def test_circuit_breaker_accepts_new_aws_fields_without_relaxing_required_flags():
    configuration = {
        "enable": True,
        "rollback": True,
        "resetOnHealthyTask": True,
        "thresholdConfiguration": {"type": "BOUNDED_PERCENT", "value": 50},
    }
    assert release.circuit_breaker_enabled(configuration)
    assert not release.circuit_breaker_enabled({**configuration, "enable": False})
    assert not release.circuit_breaker_enabled({**configuration, "rollback": False})
    assert not release.circuit_breaker_enabled({"enable": True})
