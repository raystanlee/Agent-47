# memory/usage.py
# ─────────────────────────────────────────────────────────
# CONCEPT: Token tracking and cost estimation.
#
# Every Claude API response includes a usage object:
#   response.usage.input_tokens   — tokens we sent
#   response.usage.output_tokens  — tokens Claude generated
#
# Input is cheap, output is expensive. But in practice the
# biggest cost driver for Agent 47 is INPUT — because we
# send the full history + all tool schemas on every turn.
#
# Tracking this tells you:
#   - Where your money is going
#   - When history is getting too large
#   - How many turns a session actually used
# ─────────────────────────────────────────────────────────

from dataclasses import dataclass, field
from datetime import datetime

# Claude Sonnet 4.6 pricing (per million tokens)
# Update these if Anthropic changes pricing
INPUT_COST_PER_M  = 3.00   # $3.00 per 1M input tokens
OUTPUT_COST_PER_M = 15.00  # $15.00 per 1M output tokens


@dataclass
class UsageTracker:
    """
    Tracks token usage and cost across an entire session.
    One instance lives for the duration of a main.py run.
    """
    session_start: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    total_input_tokens:  int = 0
    total_output_tokens: int = 0
    total_api_calls:     int = 0
    turns: list = field(default_factory=list)  # per-turn breakdown

    def record(self, input_tokens: int, output_tokens: int, label: str = ""):
        """
        Record usage from one API call.
        Called after every client.messages.create() in loop.py.
        """
        self.total_input_tokens  += input_tokens
        self.total_output_tokens += output_tokens
        self.total_api_calls     += 1

        self.turns.append({
            "label":   label or f"call_{self.total_api_calls}",
            "input":   input_tokens,
            "output":  output_tokens,
            "cost":    _cost(input_tokens, output_tokens),
        })

    @property
    def total_cost(self) -> float:
        return _cost(self.total_input_tokens, self.total_output_tokens)

    def print_summary(self):
        """Print a clean session summary when the user quits."""
        print("\n" + "─" * 50)
        print("📊 SESSION SUMMARY")
        print("─" * 50)
        print(f"  Started:        {self.session_start}")
        print(f"  API calls:      {self.total_api_calls}")
        print(f"  Input tokens:   {self.total_input_tokens:,}")
        print(f"  Output tokens:  {self.total_output_tokens:,}")
        print(f"  Total tokens:   {self.total_input_tokens + self.total_output_tokens:,}")
        print(f"  Estimated cost: ${self.total_cost:.4f}")
        print("─" * 50)

        if self.turns:
            # Show the most expensive turns so you know where cost went
            expensive = sorted(self.turns, key=lambda t: t["cost"], reverse=True)[:3]
            print("  Most expensive turns:")
            for t in expensive:
                print(f"    {t['label']}: {t['input']:,} in / {t['output']:,} out — ${t['cost']:.4f}")

        # Warn if input tokens are unusually high (history getting large)
        avg_input = self.total_input_tokens / max(self.total_api_calls, 1)
        if avg_input > 5000:
            print(f"\n  ⚠️  Avg input/call: {avg_input:,.0f} tokens — history may be growing large.")
            print("     Run 'clear history' to reset if costs keep rising.")

        print("─" * 50 + "\n")


def _cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given token count."""
    return (
        (input_tokens  / 1_000_000) * INPUT_COST_PER_M +
        (output_tokens / 1_000_000) * OUTPUT_COST_PER_M
    )