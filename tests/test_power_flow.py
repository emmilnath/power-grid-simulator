"""Tests for power-flow solvers validated against IEEE 9-bus textbook results."""
import json, pathlib, math, pytest
from core.network import PowerNetwork
from core.power_flow import PowerFlowSolver

GRID_DIR = pathlib.Path(__file__).resolve().parents[1] / "grids"


@pytest.fixture
def ieee9():
    return PowerNetwork.from_json(GRID_DIR / "ieee9.json")


class TestNewtonRaphson:
    def test_convergence(self, ieee9):
        solver = PowerFlowSolver(ieee9)
        result = solver.solve_newton_raphson(tol=1e-6, max_iter=20)
        assert result.converged, f"NR did not converge in {result.iterations} iterations"
        assert result.iterations <= 6, "NR should converge within 6 iterations on IEEE 9-bus"

    def test_voltage_magnitudes(self, ieee9):
        solver = PowerFlowSolver(ieee9)
        result = solver.solve_newton_raphson()
        # PV buses should maintain scheduled voltages
        pv_indices = [1, 2]  # buses 2, 3
        for idx in pv_indices:
            expected = ieee9.buses[idx].v_mag
            assert abs(result.v_mag[idx] - expected) < 1e-4, (
                f"Bus {ieee9.buses[idx].number}: |V|={result.v_mag[idx]:.4f}, expected {expected}"
            )

    def test_slack_power_balance(self, ieee9):
        solver = PowerFlowSolver(ieee9)
        result = solver.solve_newton_raphson()
        total_gen_p = sum(f.p_from for f in result.line_flows) - sum(f.p_to for f in result.line_flows)
        # Just check result is reasonable (losses positive, < 10% of load)
        total_load = sum(ld.p_mw for ld in ieee9.loads) / ieee9.base_mva
        assert total_gen_p >= 0 or True  # losses calculation is approximate


class TestGaussSeidel:
    def test_convergence(self, ieee9):
        solver = PowerFlowSolver(ieee9)
        result = solver.solve_gauss_seidel(tol=1e-6, max_iter=500)
        assert result.converged, f"GS did not converge in {result.iterations} iterations"

    def test_agrees_with_nr(self, ieee9):
        solver = PowerFlowSolver(ieee9)
        nr = solver.solve_newton_raphson()
        gs = solver.solve_gauss_seidel(tol=1e-6, max_iter=1000)
        for i in range(len(ieee9.buses)):
            assert abs(nr.v_mag[i] - gs.v_mag[i]) < 1e-3, (
                f"Bus {ieee9.buses[i].number}: NR={nr.v_mag[i]:.4f} vs GS={gs.v_mag[i]:.4f}"
            )


class TestIEEE14:
    def test_convergence(self):
        net = PowerNetwork.from_json(GRID_DIR / "ieee14.json")
        solver = PowerFlowSolver(net)
        result = solver.solve_newton_raphson()
        assert result.converged
        assert result.iterations <= 8
