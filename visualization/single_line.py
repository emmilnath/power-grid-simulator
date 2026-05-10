"""Interactive single-line diagram using Plotly."""
from __future__ import annotations
import math
import plotly.graph_objects as go
from core.network import PowerNetwork, BusType


def _bus_color(bus_type: BusType) -> str:
    return {BusType.SLACK: "#e74c3c", BusType.PV: "#2ecc71", BusType.PQ: "#3498db"}[bus_type]


def _layout_buses(network: PowerNetwork):
    """Arrange buses in a circle for clean visualisation."""
    n = len(network.buses)
    positions = {}
    for i, bus in enumerate(network.buses):
        angle = 2 * math.pi * i / n - math.pi / 2
        positions[bus.number] = (math.cos(angle), math.sin(angle))
    return positions


def draw_single_line(
    network: PowerNetwork,
    voltage_magnitudes: list[float] | None = None,
    title: str = "Single-Line Diagram",
) -> go.Figure:
    pos = _layout_buses(network)

    fig = go.Figure()

    # Draw branches
    for br in network.branches:
        x0, y0 = pos[br.from_bus]
        x1, y1 = pos[br.to_bus]
        fig.add_trace(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(color="#7f8c8d", width=2),
            hoverinfo="text",
            text=f"Branch {br.from_bus}-{br.to_bus}<br>R={br.r:.4f} X={br.x:.4f}",
            showlegend=False,
        ))

    # Draw buses
    for i, bus in enumerate(network.buses):
        x, y = pos[bus.number]
        vm = voltage_magnitudes[i] if voltage_magnitudes else 1.0
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            marker=dict(size=28, color=_bus_color(bus.bus_type), line=dict(width=2, color="white")),
            text=str(bus.number),
            textposition="middle center",
            textfont=dict(color="white", size=11, family="Arial Black"),
            hoverinfo="text",
            hovertext=(
                f"Bus {bus.number} ({bus.bus_type.name})<br>"
                f"|V| = {vm:.4f} pu<br>"
                f"Base kV = {bus.base_kv}"
            ),
            showlegend=False,
        ))

    # Generator symbols
    for gen in network.generators:
        bx, by = pos[gen.bus]
        fig.add_trace(go.Scatter(
            x=[bx], y=[by + 0.12],
            mode="markers+text",
            marker=dict(size=18, symbol="circle-open", color="#e74c3c", line=dict(width=2)),
            text="G",
            textposition="middle center",
            textfont=dict(size=9, color="#e74c3c"),
            hoverinfo="text",
            hovertext=f"Gen @ Bus {gen.bus}: P={gen.p_mw} MW, Q={gen.q_mvar} Mvar",
            showlegend=False,
        ))

    # Load symbols
    for ld in network.loads:
        bx, by = pos[ld.bus]
        fig.add_trace(go.Scatter(
            x=[bx], y=[by - 0.12],
            mode="markers+text",
            marker=dict(size=14, symbol="triangle-down", color="#f39c12"),
            text="",
            hoverinfo="text",
            hovertext=f"Load @ Bus {ld.bus}: P={ld.p_mw} MW, Q={ld.q_mvar} Mvar",
            showlegend=False,
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        xaxis=dict(visible=False, range=[-1.4, 1.4]),
        yaxis=dict(visible=False, range=[-1.4, 1.4], scaleanchor="x"),
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=50, b=20),
        height=550,
    )
    return fig
