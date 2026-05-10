"""Convergence plots for iterative power-flow solvers."""
from __future__ import annotations
import plotly.graph_objects as go


def plot_convergence(history: list[float], method: str = "Newton-Raphson", tol: float = 1e-6) -> go.Figure:
    """Plot mismatch vs iteration on a log-scale y-axis."""
    iters = list(range(1, len(history) + 1))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=iters, y=history,
        mode="lines+markers",
        marker=dict(size=7, color="#2980b9"),
        line=dict(width=2, color="#2980b9"),
        name="Max |mismatch|",
    ))
    fig.add_hline(y=tol, line_dash="dash", line_color="#e74c3c",
                  annotation_text=f"tol = {tol:.0e}", annotation_position="top right")

    fig.update_layout(
        title=f"{method} Convergence",
        xaxis_title="Iteration",
        yaxis_title="Max |ΔP/ΔQ| (pu)",
        yaxis_type="log",
        template="plotly_white",
        height=400,
        margin=dict(l=60, r=20, t=50, b=50),
    )
    return fig
