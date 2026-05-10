"""Power Grid Simulator — Streamlit UI.

Run with:  streamlit run app.py
"""
from __future__ import annotations
import json, pathlib
import streamlit as st
from core.network import PowerNetwork
from core.power_flow import PowerFlowSolver
from core.fault_analysis import FaultAnalyzer
from visualization.single_line import draw_single_line
from visualization.convergence import plot_convergence

GRID_DIR = pathlib.Path(__file__).parent / "grids"

st.set_page_config(page_title="Power Grid Simulator", layout="wide")
st.title("⚡ Power Grid Simulator")
st.caption("Newton-Raphson / Gauss-Seidel power flow  •  Symmetrical-component fault analysis")

# ── Sidebar: grid selection ──────────────────────────────────────────
with st.sidebar:
    st.header("Network")
    grid_files = sorted(GRID_DIR.glob("*.json"))
    grid_name = st.selectbox("Test system", [f.stem for f in grid_files])
    network = PowerNetwork.from_json(GRID_DIR / f"{grid_name}.json")
    st.metric("Buses", len(network.buses))
    st.metric("Branches", len(network.branches))
    st.metric("Generators", len(network.generators))

    st.divider()
    st.header("Power Flow")
    method = st.radio("Solver", ["Newton-Raphson", "Gauss-Seidel"])
    tol = st.select_slider("Tolerance", options=[1e-4, 1e-6, 1e-8, 1e-10], value=1e-6)
    max_iter = st.number_input("Max iterations", 5, 2000, value=50 if method == "Newton-Raphson" else 500)
    run_pf = st.button("Run Power Flow", use_container_width=True, type="primary")

    st.divider()
    st.header("Fault Analysis")
    fault_bus = st.selectbox("Fault bus", [b.number for b in network.buses])
    fault_type = st.selectbox("Fault type", ["3PH", "SLG", "LL", "DLG"])
    run_fault = st.button("Run Fault Study", use_container_width=True)

# ── Main area ────────────────────────────────────────────────────────
tab_pf, tab_fault, tab_diagram = st.tabs(["Power Flow", "Fault Analysis", "Network Diagram"])

with tab_pf:
    if run_pf:
        solver = PowerFlowSolver(network)
        with st.spinner("Solving..."):
            if method == "Newton-Raphson":
                result = solver.solve_newton_raphson(tol=tol, max_iter=int(max_iter))
            else:
                result = solver.solve_gauss_seidel(tol=tol, max_iter=int(max_iter))

        if result.converged:
            st.success(f"Converged in {result.iterations} iterations")
        else:
            st.error(f"Did NOT converge after {result.iterations} iterations")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Bus Voltages")
            rows = []
            for i, bus in enumerate(network.buses):
                rows.append({
                    "Bus": bus.number,
                    "Type": bus.bus_type.name,
                    "|V| (pu)": round(result.v_mag[i], 5),
                    "δ (deg)": round(result.v_angle[i], 4),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

        with col2:
            st.subheader("Line Flows")
            lf_rows = []
            for f in result.line_flows:
                lf_rows.append({
                    "From": f.from_bus,
                    "To": f.to_bus,
                    "P_from (pu)": round(f.p_from, 5),
                    "Q_from (pu)": round(f.q_from, 5),
                    "P_loss (pu)": round(f.p_loss, 6),
                    "Q_loss (pu)": round(f.q_loss, 6),
                })
            st.dataframe(lf_rows, use_container_width=True, hide_index=True)

        st.subheader("Convergence")
        st.plotly_chart(plot_convergence(result.convergence_history, method, tol), use_container_width=True)
    else:
        st.info("Configure settings in the sidebar and click **Run Power Flow**.")

with tab_fault:
    if run_fault:
        analyzer = FaultAnalyzer(network)
        with st.spinner("Computing fault currents..."):
            fresult = analyzer.analyze(bus=fault_bus, fault_type=fault_type)

        st.subheader(f"{fault_type} Fault at Bus {fault_bus}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Fault Current", f"{fresult.fault_current_ka:.3f} kA")
        col2.metric("Base Current", f"{fresult.base_current_a:.1f} A")
        col3.metric("Fault Current (pu)", f"{fresult.fault_current_pu:.4f}")

        st.subheader("Sequence Currents at Fault (pu)")
        st.write({
            "I₀ (zero)": f"{abs(fresult.I0):.4f}",
            "I₁ (positive)": f"{abs(fresult.I1):.4f}",
            "I₂ (negative)": f"{abs(fresult.I2):.4f}",
        })

        st.subheader("Phase Currents at Fault (pu)")
        st.write({
            "Iₐ": f"{abs(fresult.Ia):.4f} ∠ {fresult.Ia_angle:.1f}°",
            "I_b": f"{abs(fresult.Ib):.4f} ∠ {fresult.Ib_angle:.1f}°",
            "I_c": f"{abs(fresult.Ic):.4f} ∠ {fresult.Ic_angle:.1f}°",
        })

        st.subheader("Bus Voltages During Fault (pu)")
        v_rows = []
        for i, bus in enumerate(network.buses):
            v_rows.append({"Bus": bus.number, "|V|": round(abs(fresult.bus_voltages[i]), 4)})
        st.dataframe(v_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Select a fault bus and type in the sidebar, then click **Run Fault Study**.")

with tab_diagram:
    st.plotly_chart(draw_single_line(network, title=f"{grid_name} — Single-Line Diagram"), use_container_width=True)
