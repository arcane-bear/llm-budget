# llm-budget

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
# Logged: 1000 tokens, $0.005400 (claude-sonnet-4)
```

When a log pushes an agent over budget, `llm-budget` prints a warning and exits with code **2** — useful for CI gates and agent harness checks:

```bash
llm-budget log my-agent --tokens 500000 --model gpt-4o || echo "over budget!"
```

### Check status

```bash
llm-budget status
```

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              LLM Budget Status                                   │
├──────────┬──────────────┬────────────┬────────┬───────────────┬────────────┬──────┤
│ Agent    │ Daily Budget │ Spent Today│Daily % │ Monthly Budget│ Spent Month│Status│
├──────────┼──────────────┼────────────┼────────┼───────────────┼────────────┼──────┤
│ my-agent │ $1.00        │ $0.0038    │ 0%     │ $20.00        │ $0.0092    │ OK   │
│ scraper  │ $0.50        │ $0.4200    │ 84%    │ $10.00        │ $3.2100    │ WARN │
│ chatbot  │ $2.00        │ $2.1500    │ 108%   │ $50.00        │ $12.4000   │ OVER │
└──────────┴──────────────┴────────────┴────────┴───────────────┴────────────┴──────┘
```

### View history

```bash
llm-budget history my-agent --days 7
```

### Reset counters

```bash
llm-budget reset my-agent --daily    # clear today's spend
llm-budget reset my-agent --monthly  # clear this month's spend
llm-budget reset my-agent --all      # delete agent + all history
```

### List supported models

```bash
llm-budget models
```

Shows all built-in models with input/output pricing per 1M tokens.

## Supported Models

GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo, o1, o1-mini, o3-mini, Claude Opus 4, Claude Sonnet 4, Claude Sonnet 3.5, Claude Haiku 3.5, Claude Haiku 3, Gemini 2.0 Flash, Gemini 1.5 Flash, Gemini 1.5 Pro, Gemini 2.5 Pro, Llama 3 (8B/70B), Llama 3.1 (8B/70B/405B), Mistral Large, Mistral Small, Mixtral 8x7B, Command R/R+, DeepSeek V3/R1.

Don't see your model? Use `--cost 0.05` to pass a manual cost override.

## How it works

- Budgets and spend logs live in `~/.llm-budget/budget.db` (SQLite)
- Costs are auto-calculated from a built-in pricing table
- Exit code 2 = over budget (daily or monthly)
- Exit code 0 = within budget
- Warning printed at >80% of any limit

## Use in agent harnesses

```bash
# Before each LLM call in your agent loop:
if ! llm-budget log my-agent --tokens "$TOKENS" --model "$MODEL"; then
    echo "Budget exceeded, stopping agent"
    exit 1
fi
```

## Python API

```python
from llm_budget.db import get_connection, set_budget, log_spend, get_daily_spend
from llm_budget.pricing import calculate_cost

conn = get_connection()
set_budget(conn, "my-agent", daily=1.00, monthly=20.00)

cost = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
log_spend(conn, "my-agent", "gpt-4o", 1000, 500, cost)

print(f"Spent today: ${get_daily_spend(conn, 'my-agent'):.4f}")
```

## License

MIT
