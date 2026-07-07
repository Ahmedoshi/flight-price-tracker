"""Price history charts (Roadmap Phase 4) - an ASCII sparkline for
inline text, and a real PNG line chart sent as a Telegram photo.

matplotlib is used with the non-interactive "Agg" backend (set before
pyplot is ever imported) since this runs inside a headless bot process
with no display - the default backend would otherwise try to open a
GUI window and crash.
"""

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402 - must follow matplotlib.use()

# Block characters used for the ASCII sparkline, lowest to highest.
_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def ascii_sparkline(prices: list[float]) -> str:
    """A one-line sparkline like '▃▄▆█▅▂▁' scaled to the given prices'
    own min/max. Returns an empty string for fewer than 2 points (a
    single bar isn't a useful shape)."""

    if len(prices) < 2:
        return ""

    minimum = min(prices)
    maximum = max(prices)
    spread = maximum - minimum

    if spread == 0:
        # Flat line - every point is the same price.
        return _SPARK_CHARS[0] * len(prices)

    bars = []

    for price in prices:

        normalized = (price - minimum) / spread  # 0..1
        index = min(len(_SPARK_CHARS) - 1, int(normalized * (len(_SPARK_CHARS) - 1) + 0.5))
        bars.append(_SPARK_CHARS[index])

    return "".join(bars)


def render_price_chart_png(
    prices: list[float],
    labels: list[str],
    title: str,
    target_price: float | None = None,
) -> bytes:
    """Render a PNG line chart of price over time. `labels` are the
    x-axis tick labels (e.g. dates), same length as `prices`. Returns
    raw PNG bytes, ready to send via Telegram's send_photo - never
    touches disk.

    A horizontal dashed line for target_price is drawn when given, so
    it's visually obvious how the price history sits relative to the
    tracked target.
    """

    fig, ax = plt.subplots(figsize=(8, 4), dpi=150)

    ax.plot(range(len(prices)), prices, marker="o", markersize=3, linewidth=1.5, color="#2E86DE")

    if target_price is not None:
        ax.axhline(target_price, color="#E74C3C", linestyle="--", linewidth=1, label=f"Target ({target_price:.0f})")
        ax.legend(loc="upper right", fontsize=8)

    ax.set_title(title, fontsize=11)
    ax.set_ylabel("Price (SAR)")

    # Thin out x-axis labels so they don't overlap on longer histories.
    step = max(1, len(labels) // 8)
    tick_positions = list(range(0, len(labels), step))

    ax.set_xticks(tick_positions)
    ax.set_xticklabels([labels[i] for i in tick_positions], rotation=45, ha="right", fontsize=8)

    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)

    buffer.seek(0)

    return buffer.read()
