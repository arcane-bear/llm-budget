"""CLI commands for llm-budget."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table

from llm_budget import __version__
from llm_budget.db import (
    delete_agent,
    get_budget,
    get_connection,
    get_daily_spend,
    get_history,
    get_monthly_spend,
    list_agents,
    log_spend,
    reset_daily,
    reset_monthly,
    set_budget,
)
from llm_budget.pricing import MODEL_PRICING, calculate_cost, list_models

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="llm-budget")
def cli():
    """Per-agent LLM spend tracking and budget enforcement."""
    pass


@cli.command()
@click.argument("agent")
@click.option("--daily", type=float, help="Daily budget in USD")
@click.option("--monthly", type=float, help="Monthly budget in USD")
def set(agent: str, daily: float | None, monthly: float | None):
    """Set budget limits for an agent."""
    if daily is None and monthly is None:
        click.echo("Error: provide at least one of --daily or --monthly", err=True)
        sys.exit(1)
    conn = get_connection()
    result = set_budget(conn, agent, daily=daily, monthly=monthly)
    click.echo(
        f"Budget set for '{agent}': "
        f"daily=${result['daily_usd']:.2f}, monthly=${result['monthly_usd']:.2f}"
    )


@cli.command()
@click.argument("agent")
@click.option("--tokens", type=int, default=0, help="Total tokens (split as input if --input/--output not given)")
@click.option("--input-tokens", "input_tokens", type=int, default=0, help="Input tokens")
@click.option("--output-tokens", "output_tokens", type=int, default=0, help="Output tokens")
@click.option("--model", required=True, help="Model name (e.g. gpt-4o, claude-sonnet-4)")
@click.option("--cost", type=float, default=None, help="Override cost in USD (skip auto-calc)")
def log(agent: str, tokens: int, input_tokens: int, output_tokens: int, model: str, cost: float | None):
    """Log a spend event for an agent."""
    conn = get_connection()

    # Resolve token counts
    if input_tokens == 0 and output_tokens == 0 and tokens > 0:
        input_tokens = tokens  # assume all input if not split

    # Calculate cost
    if cost is not None:
        final_cost = cost
    else:
        final_cost = calculate_cost(model, input_tokens, output_tokens)
        if final_cost == 0 and (input_tokens > 0 or output_tokens > 0):
            if model not in MODEL_PRICING:
                click.echo(f"Warning: unknown model '{model}', cost recorded as $0.00", err=True)

    entry = log_spend(conn, agent, model, input_tokens, output_tokens, final_cost)
    click.echo(f"Logged: {entry['total_tokens']} tokens, ${final_cost:.6f} ({model})")

    # Check budget
    budget = get_budget(conn, agent)
    if budget:
        exit_code = 0
        daily = get_daily_spend(conn, agent)
        monthly = get_monthly_spend(conn, agent)

        if budget["daily_usd"] > 0 and daily > budget["daily_usd"]:
            click.echo(
                f"OVER BUDGET (daily): ${daily:.4f} / ${budget['daily_usd']:.2f}",
                err=True,
            )
            exit_code = 2
        elif budget["daily_usd"] > 0 and daily > budget["daily_usd"] * 0.8:
            click.echo(
                f"Warning (daily): ${daily:.4f} / ${budget['daily_usd']:.2f} (>80%)",
                err=True,
            )

        if budget["monthly_usd"] > 0 and monthly > budget["monthly_usd"]:
            click.echo(
                f"OVER BUDGET (monthly): ${monthly:.4f} / ${budget['monthly_usd']:.2f}",
                err=True,
            )
            exit_code = 2
        elif budget["monthly_usd"] > 0 and monthly > budget["monthly_usd"] * 0.8:
            click.echo(
                f"Warning (monthly): ${monthly:.4f} / ${budget['monthly_usd']:.2f} (>80%)",
                err=True,
            )

        if exit_code:
            sys.exit(exit_code)


@cli.command()
@click.argument("agent", required=False)
def status(agent: str | None):
    """Show budget status for all agents (or one agent)."""
    conn = get_connection()

    if agent:
        agents = [get_budget(conn, agent)]
        if agents[0] is None:
            click.echo(f"No budget found for '{agent}'", err=True)
            sys.exit(1)
    else:
        agents = list_agents(conn)
        if not agents:
            click.echo("No agents configured. Use 'llm-budget set <agent> --daily N' to start.")
            return

    table = Table(title="LLM Budget Status")
    table.add_column("Agent", style="cyan")
    table.add_column("Daily Budget", justify="right")
    table.add_column("Spent Today", justify="right")
    table.add_column("Daily %", justify="right")
    table.add_column("Monthly Budget", justify="right")
    table.add_column("Spent Month", justify="right")
    table.add_column("Monthly %", justify="right")
    table.add_column("Status", justify="center")

    any_over = False
    for a in agents:
        name = a["agent"]
        daily_budget = a["daily_usd"]
        monthly_budget = a["monthly_usd"]
        daily_spent = get_daily_spend(conn, name)
        monthly_spent = get_monthly_spend(conn, name)

        daily_pct = (daily_spent / daily_budget * 100) if daily_budget > 0 else 0
        monthly_pct = (monthly_spent / monthly_budget * 100) if monthly_budget > 0 else 0

        if daily_pct > 100 or monthly_pct > 100:
            status_str = "[red bold]OVER[/red bold]"
            any_over = True
        elif daily_pct > 80 or monthly_pct > 80:
            status_str = "[yellow]WARNING[/yellow]"
        else:
            status_str = "[green]OK[/green]"

        table.add_row(
            name,
            f"${daily_budget:.2f}" if daily_budget > 0 else "-",
            f"${daily_spent:.4f}",
            f"{daily_pct:.0f}%" if daily_budget > 0 else "-",
            f"${monthly_budget:.2f}" if monthly_budget > 0 else "-",
            f"${monthly_spent:.4f}",
            f"{monthly_pct:.0f}%" if monthly_budget > 0 else "-",
            status_str,
        )

    console.print(table)
    if any_over:
        sys.exit(2)


@cli.command()
@click.argument("agent")
@click.option("--days", default=7, help="Number of days to look back")
def history(agent: str, days: int):
    """Show spend history for an agent."""
    conn = get_connection()
    entries = get_history(conn, agent, days=days)

    if not entries:
        click.echo(f"No spend history for '{agent}' in the last {days} days.")
        return

    table = Table(title=f"Spend History: {agent} (last {days} days)")
    table.add_column("Time", style="dim")
    table.add_column("Model", style="cyan")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Cost", justify="right", style="green")

    total_cost = 0.0
    for e in entries:
        total_cost += e["cost_usd"]
        table.add_row(
            e["logged_at"],
            e["model"],
            f"{e['input_tokens']:,}",
            f"{e['output_tokens']:,}",
            f"{e['total_tokens']:,}",
            f"${e['cost_usd']:.6f}",
        )

    console.print(table)
    click.echo(f"Total: ${total_cost:.4f} across {len(entries)} events")


@cli.command()
@click.argument("agent")
@click.option("--daily", is_flag=True, help="Reset daily spend")
@click.option("--monthly", is_flag=True, help="Reset monthly spend")
@click.option("--all", "reset_all", is_flag=True, help="Delete agent and all history")
def reset(agent: str, daily: bool, monthly: bool, reset_all: bool):
    """Reset spend counters for an agent."""
    conn = get_connection()

    if reset_all:
        if delete_agent(conn, agent):
            click.echo(f"Deleted agent '{agent}' and all history.")
        else:
            click.echo(f"Agent '{agent}' not found.", err=True)
            sys.exit(1)
        return

    if not daily and not monthly:
        click.echo("Specify --daily, --monthly, or --all", err=True)
        sys.exit(1)

    if daily:
        n = reset_daily(conn, agent)
        click.echo(f"Reset daily spend for '{agent}' ({n} entries removed)")

    if monthly:
        n = reset_monthly(conn, agent)
        click.echo(f"Reset monthly spend for '{agent}' ({n} entries removed)")


@cli.command()
def models():
    """List all supported models and their pricing."""
    table = Table(title="Supported Models")
    table.add_column("Model", style="cyan")
    table.add_column("Input $/1M", justify="right")
    table.add_column("Output $/1M", justify="right")

    for model in list_models():
        inp, out = MODEL_PRICING[model]
        table.add_row(model, f"${inp:.3f}", f"${out:.3f}")

    console.print(table)
