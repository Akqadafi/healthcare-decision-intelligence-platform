"""Deploy a digest-pinned release or test rollback; preserve evidence even on failure."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REGISTER_FIELDS = {
    "family",
    "taskRoleArn",
    "executionRoleArn",
    "networkMode",
    "containerDefinitions",
    "volumes",
    "placementConstraints",
    "requiresCompatibilities",
    "cpu",
    "memory",
    "pidMode",
    "ipcMode",
    "proxyConfiguration",
    "inferenceAccelerators",
    "ephemeralStorage",
    "runtimePlatform",
}


def revision_payload(task: dict, image: str, *, fail_health: bool = False) -> dict:
    """Keep runtime configuration, stripping DescribeTaskDefinition-only fields."""
    if not re.fullmatch(r".+@sha256:[0-9a-f]{64}", image):
        raise ValueError("An immutable image digest is required")
    payload = copy.deepcopy({key: value for key, value in task.items() if key in REGISTER_FIELDS})
    container = next(c for c in payload["containerDefinitions"] if c["name"] == "dashboard")
    previous_repository = container["image"].split("@")[0]
    if image.split("@")[0] != previous_repository:
        raise ValueError("A release must use the service's existing ECR repository")
    container["image"] = image
    if fail_health:
        container["healthCheck"]["command"] = ["CMD", "python", "-c", "raise SystemExit(1)"]
    return payload


def primary(service: dict) -> dict:
    return next(d for d in service["deployments"] if d["status"] == "PRIMARY")


def release_matches(
    service: dict,
    tasks: list[dict],
    targets: list[dict],
    expected_revision: str,
    expected_digest: str,
) -> bool:
    """A stable service after rollback must never pass as the requested new release."""
    desired = service["desiredCount"]
    deployment = primary(service)
    return (
        desired > 0
        and deployment.get("rolloutState") == "COMPLETED"
        and deployment["taskDefinition"] == expected_revision
        and service["pendingCount"] == 0
        and service["runningCount"] == desired
        and len(tasks) == desired
        and len(targets) >= desired
        and all(
            t["taskDefinitionArn"] == expected_revision
            and t.get("healthStatus") == "HEALTHY"
            and any(
                c["name"] == "dashboard" and c.get("imageDigest") == expected_digest
                for c in t["containers"]
            )
            for t in tasks
        )
        and all(t["TargetHealth"]["State"] == "healthy" for t in targets)
    )


def circuit_breaker_enabled(configuration: dict) -> bool:
    """Check required flags while tolerating additional ECS API fields."""
    return configuration.get("enable") is True and configuration.get("rollback") is True


def now() -> str:
    return datetime.now(UTC).isoformat()


class Aws:
    def __init__(self, region: str):
        self.region = region

    def run(self, *arguments: str) -> dict:
        result = subprocess.run(
            [
                "aws",
                *arguments,
                "--region",
                self.region,
                "--output",
                "json",
                "--no-cli-pager",
                "--cli-connect-timeout",
                "10",
                "--cli-read-timeout",
                "30",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout or "{}")


def collect(aws: Aws, args, start_ms: int) -> dict:
    response = aws.run(
        "ecs",
        "describe-services",
        "--cluster",
        args.cluster,
        "--services",
        args.service,
        "--include",
        "TAGS",
    )
    if response.get("failures") or not response.get("services"):
        raise RuntimeError(f"Service is unavailable: {response.get('failures')}")
    service = response["services"][0]
    arns = aws.run(
        "ecs",
        "list-tasks",
        "--cluster",
        args.cluster,
        "--service-name",
        args.service,
        "--desired-status",
        "RUNNING",
    )["taskArns"]
    tasks = (
        aws.run("ecs", "describe-tasks", "--cluster", args.cluster, "--tasks", *arns)["tasks"]
        if arns
        else []
    )
    targets = aws.run("elbv2", "describe-target-health", "--target-group-arn", args.target_group)[
        "TargetHealthDescriptions"
    ]
    events = aws.run(
        "logs",
        "filter-log-events",
        "--log-group-name",
        args.event_log,
        "--start-time",
        str(start_ms),
    )
    # Do not discard old application logs; they help explain a failed rollout after rollback.
    logs = aws.run("logs", "filter-log-events", "--log-group-name", args.application_log)
    return {
        "observed_at": now(),
        "service": service,
        "tasks": tasks,
        "targets": targets,
        "deployment_events": events,
        "application_logs": logs,
    }


def parsed_events(snapshot: dict) -> list[dict]:
    events = []
    for record in snapshot["deployment_events"].get("events", []):
        try:
            event = json.loads(record["message"])
            if event.get("detail-type") == "ECS Deployment State Change":
                events.append(event)
        except (json.JSONDecodeError, KeyError):
            continue
    return events


def check_endpoint(url: str) -> None:
    with urllib.request.urlopen(url.rstrip("/") + "/_stcore/health", timeout=15) as response:
        if response.status != 200 or response.read().strip() != b"ok":
            raise RuntimeError("Application health endpoint did not return 200/ok")


def save(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def run(args) -> None:
    aws = Aws(args.region)
    args.evidence.mkdir(parents=True, exist_ok=True)
    started = now()
    start_ms = int(time.time() * 1000)
    resume = None
    if getattr(args, "resume_evidence", None):
        if args.operation != "rollback-test":
            raise ValueError("Read-only recovery resume is only for rollback-test")
        source = args.resume_evidence
        resume = {
            "before": json.loads((source / "before.json").read_text()),
            "registered": json.loads((source / "registered.json").read_text()),
            "submitted": json.loads((source / "submitted.json").read_text()),
        }
        submitted_deployment = primary(resume["submitted"]["service"])
        start_ms = int(datetime.fromisoformat(submitted_deployment["createdAt"]).timestamp() * 1000)
    summary = {"operation": args.operation, "started_at": started, "status": "in_progress"}
    try:
        identity = aws.run("sts", "get-caller-identity")
        if identity["Account"] != args.account:
            raise RuntimeError("AWS account does not match the reviewed deployment")
        summary["identity"] = identity
        before = collect(aws, args, start_ms)
        save(args.evidence / "before.json", before)
        service = before["service"]
        circuit = service["deploymentConfiguration"].get("deploymentCircuitBreaker", {})
        if not circuit_breaker_enabled(circuit):
            raise RuntimeError("Enable the circuit breaker and rollback before deploying")
        baseline = primary(resume["before"]["service"] if resume else service)["taskDefinition"]
        task = aws.run("ecs", "describe-task-definition", "--task-definition", baseline)[
            "taskDefinition"
        ]
        image_a = next(c["image"] for c in task["containerDefinitions"] if c["name"] == "dashboard")
        digest_a = image_a.split("@")[-1]
        if resume:
            tags = {t["key"]: t["value"] for t in service.get("tags", [])}
            if tags.get("Environment") != "dev" or args.service != "healthcare-di-dev":
                raise RuntimeError("Recovery resume is restricted to the dedicated dev service")
            candidate = resume["registered"]["taskDefinition"]
            expected = revision_payload(task, image_a, fail_health=True)
            actual = {key: value for key, value in candidate.items() if key in REGISTER_FIELDS}
            if actual != expected:
                raise RuntimeError(
                    "Saved fault definition does not match baseline plus failed health command"
                )
            submitted_deployment = primary(resume["submitted"]["service"])
            revision = candidate["taskDefinitionArn"]
            if submitted_deployment["taskDefinition"] != revision:
                raise RuntimeError("Saved candidate revision does not match submitted deployment")
            image = image_a
            candidate_id = submitted_deployment["id"]
            summary.update(
                baseline_revision=baseline,
                baseline_image=image_a,
                candidate_revision=revision,
                candidate_image=image_a,
                submitted_at=submitted_deployment["createdAt"],
                submission_time_source="ECS deployment createdAt; read-only resume",
            )
        elif args.operation == "verify":
            image = image_a
            revision = baseline
            candidate_id = primary(service)["id"]
            summary.update(candidate_revision=baseline, candidate_image=image_a)
        else:
            if not release_matches(service, before["tasks"], before["targets"], baseline, digest_a):
                raise RuntimeError("A completed, healthy, digest-pinned baseline A is required")
            check_endpoint(args.url)
            if args.operation == "rollback-test":
                tags = {t["key"]: t["value"] for t in service.get("tags", [])}
                if tags.get("Environment") != "dev" or args.service != "healthcare-di-dev":
                    raise RuntimeError(
                        "Failure injection is restricted to the dedicated dev service"
                    )
                image = image_a
            else:
                image = args.image
            payload = revision_payload(task, image, fail_health=args.operation == "rollback-test")
            save(args.evidence / "candidate-task-definition.json", payload)
            registered = aws.run(
                "ecs",
                "register-task-definition",
                "--cli-input-json",
                "file://" + str((args.evidence / "candidate-task-definition.json").resolve()),
            )
            revision = registered["taskDefinition"]["taskDefinitionArn"]
            summary.update(
                baseline_revision=baseline,
                baseline_image=image_a,
                candidate_revision=revision,
                candidate_image=image,
            )
            save(args.evidence / "registered.json", registered)
            summary["submitted_at"] = now()
            update = aws.run(
                "ecs",
                "update-service",
                "--cluster",
                args.cluster,
                "--service",
                args.service,
                "--task-definition",
                revision,
            )
            save(args.evidence / "submitted.json", update)
            candidate_id = primary(update["service"])["id"]
        summary["candidate_deployment_id"] = candidate_id
        expected_revision = baseline if args.operation == "rollback-test" else revision
        expected_digest = image.split("@")[-1]
        deadline = time.monotonic() + args.timeout
        failed_event = None
        rollback_event = None
        timeline = args.evidence / "timeline.jsonl"
        while time.monotonic() < deadline:
            snapshot = collect(aws, args, start_ms)
            save(args.evidence / "latest.json", snapshot)
            with timeline.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "time": snapshot["observed_at"],
                            "deployments": snapshot["service"]["deployments"],
                        }
                    )
                    + "\n"
                )
            for event in parsed_events(snapshot):
                detail = event["detail"]
                if (
                    detail.get("eventName") == "SERVICE_DEPLOYMENT_FAILED"
                    and detail.get("deploymentId") == candidate_id
                ):
                    failed_event = event
                    save(args.evidence / "failed-deployment-event.json", event)
                if (
                    detail.get("eventName") == "SERVICE_DEPLOYMENT_IN_PROGRESS"
                    and "rolling back" in detail.get("reason", "").lower()
                ):
                    rollback_event = event
                    save(args.evidence / "rollback-event.json", event)
            matching = release_matches(
                snapshot["service"],
                snapshot["tasks"],
                snapshot["targets"],
                expected_revision,
                expected_digest,
            )
            if args.operation != "rollback-test" and (
                failed_event
                or (
                    primary(snapshot["service"]).get("rolloutState") == "COMPLETED"
                    and primary(snapshot["service"])["taskDefinition"] != revision
                )
            ):
                raise RuntimeError(
                    "Candidate failed or rolled back; this is NOT a successful release"
                )
            if matching and (
                args.operation != "rollback-test" or (failed_event and rollback_event)
            ):
                check_endpoint(args.url)
                if not snapshot["application_logs"].get("events"):
                    time.sleep(15)
                    continue
                summary.update(
                    status="passed",
                    confirmed_at=now(),
                    running_revision=expected_revision,
                    running_digest=expected_digest,
                    health_endpoint="200/ok",
                )
                if failed_event:
                    failure_time = datetime.fromisoformat(
                        failed_event["time"].replace("Z", "+00:00")
                    )
                    submitted = datetime.fromisoformat(summary["submitted_at"])
                    summary.update(
                        failed_event_at=failed_event["time"],
                        detection_seconds=(failure_time - submitted).total_seconds(),
                        recovery_confirmed_seconds=(
                            datetime.now(UTC) - failure_time
                        ).total_seconds(),
                    )
                save(args.evidence / "verified.json", snapshot)
                print(json.dumps(summary, indent=2))
                return
            time.sleep(15)
        raise TimeoutError(
            "Deployment evidence did not satisfy all acceptance checks within the timeout"
        )
    except Exception as exc:
        summary.update(status="failed", error=str(exc), finished_at=now())
        raise
    finally:
        try:
            stopped = aws.run(
                "ecs",
                "list-tasks",
                "--cluster",
                args.cluster,
                "--service-name",
                args.service,
                "--desired-status",
                "STOPPED",
            )["taskArns"]
            if stopped:
                save(
                    args.evidence / "stopped-tasks.json",
                    aws.run(
                        "ecs",
                        "describe-tasks",
                        "--cluster",
                        args.cluster,
                        "--tasks",
                        *stopped[:100],
                    ),
                )
        except Exception as exc:
            summary["stopped_task_collection_error"] = str(exc)
        save(args.evidence / "summary.json", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["verify", "deploy", "rollback-test"])
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-west-2"))
    for option in [
        "account",
        "cluster",
        "service",
        "target-group",
        "event-log",
        "application-log",
        "url",
    ]:
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--image")
    parser.add_argument(
        "--resume-evidence",
        type=Path,
        help="Read-only verification of a saved fault deployment",
    )
    parser.add_argument("--timeout", type=int, default=2400)
    parser.add_argument("--evidence", type=Path, default=Path("evidence/release"))
    arguments = parser.parse_args()
    if arguments.operation == "deploy" and not arguments.image:
        parser.error("deploy requires --image repository@sha256:digest")
    run(arguments)
