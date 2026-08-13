from hud import Task

# Concrete HUD task row. The environment implementation lives in env.py and is
# joined at runtime by the stable environment name + template id.
tasks = [
    Task(
        env="ai-safety-paper-replication-demo",
        id="reproduce-monitoring-paper",
        args={},
        slug="replicate-monitor-paper-001",
        columns={
            "domain": "technical-ai-safety",
            "capability": "research-reproduction",
            "difficulty": "pilot",
            "source": "synthetic-unpublished-style",
        },
        # Hosted execution consumes the row-level settings. Local CLI execution
        # also reads max_steps=80 from the checked-in .hud_eval.toml.
        agent_config={"max_steps": 80, "timeout_seconds": 3600},
    )
]
