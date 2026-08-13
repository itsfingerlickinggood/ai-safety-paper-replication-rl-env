# HUD AI-Safety Paper Replication Demo

A HUD 0.6.13 environment in which an agent receives a redacted synthetic
AI-safety monitoring paper, public calibration/test data, and starter code. The
agent must reproduce the experiment and leave an executable implementation that
generalizes to a held-out split.

HUD owns the model loop, SSH workspace capability, file tracking, task lifecycle,
trace, and final reward. There is no custom Anthropic loop.

## What was hardened

- `tasks.py` exposes exactly one task, so HUD task discovery has no duplicate slugs.
- Every rollout receives a unique temporary workspace, including concurrent local runs.
- Production refuses to start without bubblewrap workspace isolation.
- The held-out submission runner independently probes bubblewrap and fails closed.
- The runner has no network, verifier mount, label mount, or inherited provider/API keys.
- All grader paths are absolute, so local and hosted grading resolve the same files.
- Prediction schema, IDs, numeric values, score/threshold consistency, output size,
  held-out method fidelity, quality, baseline improvement, and FPR are checked.
- A functional gate caps non-working or non-faithful implementations at `0.35`.
- The Docker server binds `0.0.0.0:8765`, as required inside a container.
- Project dependencies are installed together; installing the standalone HUD CLI is
  not treated as installing this environment.

## Environment contents

The agent sees only a sandboxed workspace containing:

- `paper_redacted.md`
- `task.md`
- public calibration and test data
- starter monitoring and metric code

It must create:

- `submission.py`
- `results.json`
- `report.md`

The held-out data and verifier remain outside the agent workspace. The ZIP naturally
contains them for benchmark development, but a model rollout cannot access them when
the required production isolation is active.

## Install

Use Linux or WSL2 with Python 3.12, `uv`, and a host capable of creating user/PID
namespaces with bubblewrap.

```bash
cd hud_ai_safety_paper_replication_demo
uv sync --python 3.12
uv run hud version
```

Expected HUD version: `0.6.13`.

Do not use only `uv tool install hud`: that installs the CLI but omits this project's
NumPy and pandas dependencies.

## Validate before any paid model run

First run the deterministic reference and adversarial controls:

```bash
uv run python scripts/validate_reference.py
```

Then verify task discovery:

```bash
uv run hud task list --source tasks.py
```

Expected output contains exactly one row:

```text
replicate-monitor-paper-001    reproduce-monitoring-paper
```

Finally test the real HUD prompt-to-grade lifecycle:

```bash
uv run python scripts/validate_hud_lifecycle.py
```

That secure lifecycle test must report all of the following:

- `workspace_isolation: bwrap`
- `held_out_labels_from_agent_shell: blocked`
- `provider_credentials_from_agent_shell: blocked`
- `distinct_concurrent_workspaces: 3`
- `grader_mode: bubblewrap`
- `reward: 1.0`

If a restricted development container cannot create namespaces, logic can be tested
with the explicit unsafe override below:

```bash
uv run python scripts/validate_hud_lifecycle.py --allow-unisolated-local-test
```

That mode is expected to report no isolation and accessible labels. It exists only to
test HUD wiring on restricted CI hosts. **Never run a model evaluation in that mode.**

## Run Claude locally through HUD

```bash
export ANTHROPIC_API_KEY="YOUR_KEY"
uv run hud eval tasks.py claude \
  --model claude-sonnet-4-6 \
  --max-steps 80 \
  --yes
```

Five independent attempts:

```bash
uv run hud eval tasks.py claude \
  --model claude-sonnet-4-6 \
  --max-steps 80 \
  --group 5 \
  --max-concurrent 5 \
  --yes
```

The checked-in `.hud_eval.toml` also defaults local runs to 80 steps. The explicit
flag above makes the budget visible in experiment logs.

`ANTHROPIC_API_KEY` is sufficient for a local BYOK run. `HUD_API_KEY` is required
for platform tracing, deployment, HUD runtime tunnels, gateway inference, or fully
remote rollouts.

## Deploy and run on HUD

```bash
uv run hud set HUD_API_KEY=YOUR_HUD_KEY
uv run hud deploy .
uv run hud sync tasks "AI Safety Paper Replication Demo" tasks.py --yes
```

`hud deploy` performs the remote image build and links the directory to the deployed
environment. HUD 0.6.13 does not have a separate `hud build` command.

To keep the Claude agent loop local while using the deployed HUD runtime:

```bash
export ANTHROPIC_API_KEY="YOUR_KEY"
uv run hud eval "AI Safety Paper Replication Demo" claude \
  --all \
  --group 5 \
  --max-steps 80 \
  --runtime hud \
  --yes
```

For a fully platform-hosted rollout, use `--remote` after configuring the model or
HUD gateway access for your account.

## Reward

The raw weighted reward is:

- required artifact interface: 5%
- exact public baseline/proposed reproduction: 20%
- public `w=1` and `w=5` ablations: 10%
- held-out `w=3` implementation fidelity: 15%
- held-out balanced-accuracy quality: 20%
- improvement over the held-out max-step baseline: 10%
- held-out FPR constraint, gated by recall: 10%
- explicit conclusion correctness: 5%
- report completeness: 5%

If held-out TPR is below `0.20`, balanced accuracy is below `0.55`, or method
fidelity is below `0.50`, the final reward is capped at `0.35`. All components,
the pre-gate reward, cap status, grader mode, and held-out metrics are recorded in
the HUD grading result.

## Scope

This is a synthetic, unpublished-style integration demo. It demonstrates a safe,
training-ready HUD task and deterministic verifier; it is not itself the final
research sample to pitch. A production task should replace the synthetic study with
real, niche or private, expert-validated AI-safety work and should collect frontier-
model trajectories only after the environment passes the included controls.
