# llm-budget

> Built by [Rapid Claw](https://rapidclaw.dev) — [production agent infrastructure](https://rapidclaw.dev) for teams shipping AI.

Per-agent LLM spend tracking and budget enforcement. SQLite-backed. CLI-first.

Set a budget, log usage, get warned (or hard-blocked) when limits are hit.

## Install

```bash
pip install git+https://github.com/arcane-bear/llm-budget.git
```

Or clone and install locally:

```bash
git clone https://github.com/arcane-bear/llm-budget.git
cd llm-budget
pip install -e .
```

## Usage

### Set a budget

```bash
llm-budget set my-agent --daily 1.00 --monthly 20.00
# Budget set for 'my-agent': daily=$1.00, monthly=$20.00
```

### Log spend events

```bash
llm-budget log my-agent --tokens 1500 --model gpt-4o
# Logged: 1500 tokens, $0.003750 (gpt-4o)

llm-budget log my-agent --input-tokens 800 --output-tokens 200 --model claude-sonnet-4
```

## Learn More

- [Managing LLM Costs Across Agent Fleets](https://rapidclaw.dev/blog/managing-llm-costs-across-agent-fleets) — budget guardrails for autonomous AI systems
- [Deploying Cost-Aware Agents](https://rapidclaw.dev/blog/deploying-cost-aware-agents) — how the [Rapid Claw platform](https://rapidclaw.dev) handles spend enforcement at scale
- [RapidClaw Docs](https://rapidclaw.dev/docs) — full documentation for agent deployment and cost management

## License

MIT
