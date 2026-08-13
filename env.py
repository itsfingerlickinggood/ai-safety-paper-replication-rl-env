from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from hud.environment import Environment
from hud.graders import EvaluationResult, SubScore

from verifier import score_workspace

BASE_DIR = Path(__file__).resolve().parent
SEED = BASE_DIR / "workspace_seed"

# A unique host directory prevents concurrent local rollouts from sharing state.
# Inside an isolated HUD workspace the agent still sees it as /workspace.
WORKSPACE_TEMP = tempfile.TemporaryDirectory(prefix="hud-paper-replication-")
ROOT = Path(WORKSPACE_TEMP.name).resolve()
ALLOW_UNISOLATED_TEST = os.environ.get("HUD_ALLOW_UNISOLATED_WORKSPACE") == "1"
SANITIZED_AGENT_ENV = {
    "ANTHROPIC_API_KEY": "",
    "OPENAI_API_KEY": "",
    "GEMINI_API_KEY": "",
    "GOOGLE_API_KEY": "",
    "AZURE_OPENAI_API_KEY": "",
    "AWS_ACCESS_KEY_ID": "",
    "AWS_SECRET_ACCESS_KEY": "",
    "AWS_SESSION_TOKEN": "",
    "HUD_API_KEY": "",
}

env = Environment(name="ai-safety-paper-replication-demo")


@env.initialize
async def _seed_workspace() -> None:
    """Seed before HUD starts file tracking, so starter files are the baseline."""
    for child in ROOT.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)
    shutil.copytree(SEED, ROOT, dirs_exist_ok=True)
    if not ALLOW_UNISOLATED_TEST and hasattr(os, "geteuid") and os.geteuid() == 0:
        os.chown(ROOT, 65534, 65534)
        for path in ROOT.rglob("*"):
            os.chown(path, 65534, 65534)


@env.shutdown
async def _remove_workspace() -> None:
    WORKSPACE_TEMP.cleanup()


# Hidden labels and verifier code share the environment image but must never be
# reachable from the agent shell. Production therefore fails closed when HUD
# cannot create a bubblewrap namespace. The override is only for package tests.
env.workspace(
    ROOT,
    network=False,
    track_files=True,
    require_isolation=not ALLOW_UNISOLATED_TEST,
    env=SANITIZED_AGENT_ENV,
    # The official container runs as root; dropping the SSH shell to nobody
    # prevents host-process credentials from entering even before bwrap mounts.
    shell_uid=None if ALLOW_UNISOLATED_TEST else 65534,
    shell_gid=None if ALLOW_UNISOLATED_TEST else 65534,
)


@env.template(
    id="reproduce-monitoring-paper",
    description=(
        "Reproduce a redacted AI-safety monitoring study from its methods, repository, "
        "and public data; leave executable artifacts that generalize to a hidden split."
    ),
)
async def reproduce_monitoring_paper() -> object:
    prompt = (ROOT / "task.md").read_text()
    answer = yield prompt

    scored = score_workspace(ROOT)
    subscores = [
        SubScore(
            name=name,
            value=float(value),
            weight=float(scored["weights"].get(name, 0.0)),
        )
        for name, value in scored["components"].items()
        if name in scored["weights"]
    ]
    yield EvaluationResult(
        reward=float(scored["reward"]),
        subscores=subscores,
        info={
            "hidden_metrics": scored["hidden_metrics"],
            "hidden_baseline_metrics": scored["hidden_baseline_metrics"],
            "grader_mode": scored["grader_mode"],
            "pre_gate_reward": scored["pre_gate_reward"],
            "functional_cap": scored["functional_cap"],
            "notes": scored["notes"],
            "agent_final_answer": answer,
        },
        content="Deterministic reproduction score with hidden held-out evaluation.",
    )
