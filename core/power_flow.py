"""
Power flow solvers: Newton-Raphson and Gauss-Seidel.

Solves the nonlinear power flow equations to find bus voltages and angles.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from .network import PowerNetwork, BusType
from .ybus import build_ybus


@dataclass
class PowerFlowResult:
    """Results of a power flow computation."""
    converged: bool = False
    iterations: int = 0
    tolerance: float = 1e-6
    max_mismatch: float = float("inf")
    v_mag: np.ndarray = field(default_factory=lambda: np.array([]))
    v_angle: np.ndarray = field(default_factory=lambda: np.array([]))
    p_inject: np.ndarray = field(default_factory=lambda: np.array([]))
    q_inject: np.ndarray = field(default_factory=lambda: np.array([]))
    convergence_history: list = field(default_factory=list)
    line_flows: list = field(default_factory=list)

    def bus_voltage(self, idx: int) -> complex:
        return self.v_mag[idx] * np.exp(1j * self.v_angle[idx])

    def summary(self, network: PowerNetwork) -> str:
        lines = [f"=== Power Flow Results ({network.name}) ==="]
        for i, bus in enumerate(network.buses):
            angle_deg = np.degrees(self.v_angle[i])
            p_mw = self.p_inject[i] * network.base_mva
            q_mvar = self.q_inject[i] * network.base_mva
            lines.append(
                f"Bus {bus.number} ({bus.bus_type.name:5s}): "
                f"V = {self.v_mag[i]:.3f}∠{angle_deg:.1f}°  "
                f"P = {p_mw:.1f} MW  Q = {q_mvar:.1f} MVAR"
            )
        status = "Converged" if self.converged else "DID NOT CONVERGE"
        lines.append(
            f"{status} in {self.iterations} iterations "
            f"(tolerance: {self.tolerance:.0e})"
        )
        return "\n".join(lines)


class PowerFlowSolver:
    """Newton-Raphson and Gauss-Seidel power flow solver."""

    def __init__(self, network: PowerNetwork):
        self.network = network
        self.ybus = build_ybus(network)

    def solve_newton_raphson(
        self,
        max_iter: int = 50,
        tolerance: float = 1e-6,
    ) -> PowerFlowResult:
        """
        Solve power flow using the Newton-Raphson method.

        Iteratively solves:
            [dP]   [J1  J2] [dTheta]
            [dQ] = [J3  J4] [dV/V  ]

        until the mismatch vector is below tolerance.
        """
        net = self.network
        n = net.n_buses
        ybus = self.ybus

        # Initialise voltage vector
        v_mag = np.array([bus.v_mag for bus in net.buses], dtype=float)
        v_angle = np.zeros(n, dtype=float)

        # Set PV bus voltage magnitudes
        for bus in net.buses:
            if bus.bus_type == BusType.PV:
                idx = net.get_bus_index(bus.number)
                gens = net.get_generators_at_bus(bus.number)
                if gens:
                    v_mag[idx] = gens[0].v_setpoint

        # Scheduled injections (per-unit)
        p_sched = np.zeros(n)
        q_sched = np.zeros(n)
        for i, bus in enumerate(net.buses):
            p_pu, q_pu = net.get_net_injection(bus.number)
            p_sched[i] = p_pu
            q_sched[i] = q_pu

        # Identify bus types for indexing
        slack_idx = [net.get_bus_index(b.number) for b in net.buses
                     if b.bus_type == BusType.SLACK]
        pv_idx = [net.get_bus_index(b.number) for b in net.buses
                  if b.bus_type == BusType.PV]
        pq_idx = [net.get_bus_index(b.number) for b in net.buses
                  if b.bus_type == BusType.PQ]

        # Indices where P and Q equations are active
        p_buses = sorted(pv_idx + pq_idx)  # all non-slack
        q_buses = sorted(pq_idx)           # PQ buses only

        history = []
        converged = False

        for iteration in range(max_iter):
            # Compute complex voltages
            v_complex = v_mag * np.exp(1j * v_angle)

            # Compute injected power
            s_calc = v_complex * np.conj(ybus @ v_complex)
            p_calc = s_calc.real
            q_calc = s_calc.imag

            # Mismatch vectors
            dp = p_sched[p_buses] - p_calc[p_buses]
            dq = q_sched[q_buses] - q_calc[q_buses]
            mismatch = np.concatenate([dp, dq])

            max_mis = np.max(np.abs(mismatch))
            history.append(max_mis)

            if max_mis < tolerance:
                converged = True
                break

            # Build Jacobian
            n_p = len(p_buses)
            n_q = len(q_buses)
            n_j = n_p + n_q
            jacobian = np.zeros((n_j, n_j))

            # J1: dP/dTheta
            for ii, i in enumerate(p_buses):
                for jj, j in enumerate(p_buses):
                    if i == j:
                        jacobian[ii, jj] = -q_calc[i] - ybus[i, i].imag * v_mag[i] ** 2
                    else:
                        vi = v_mag[i]
                        vj = v_mag[j]
                        gij = ybus[i, j].real
                        bij = ybus[i, j].imag
                        tij = v_angle[i] - v_angle[j]
                        jacobian[ii, jj] = vi * vj * (gij * np.sin(tij) - bij * np.cos(tij))

            # J2: dP/dV
            for ii, i in enumerate(p_buses):
                for jj, j in enumerate(q_buses):
                    if i == j:
                        jacobian[ii, n_p + jj] = p_calc[i] / v_mag[i] + ybus[i, i].real * v_mag[i]
                    else:
                        vi = v_mag[i]
                        vj = v_mag[j]
                        gij = ybus[i, j].real
                        bij = ybus[i, j].imag
                        tij = v_angle[i] - v_angle[j]
                        jacobian[ii, n_p + jj] = vi * (gij * np.cos(tij) + bij * np.sin(tij))

            # J3: dQ/dTheta
            for ii, i in enumerate(q_buses):
                for jj, j in enumerate(p_buses):
                    if i == j:
                        jacobian[n_p + ii, jj] = p_calc[i] - ybus[i, i].real * v_mag[i] ** 2
                    else:
                        vi = v_mag[i]
                        vj = v_mag[j]
                        gij = ybus[i, j].real
                        bij = ybus[i, j].imag
                        tij = v_angle[i] - v_angle[j]
                        jacobian[n_p + ii, jj] = -vi * vj * (gij * np.cos(tij) + bij * np.sin(tij))

            # J4: dQ/dV
            for ii, i in enumerate(q_buses):
                for jj, j in enumerate(q_buses):
                    if i == j:
                        jacobian[n_p + ii, n_p + jj] = q_calc[i] / v_mag[i] - ybus[i, i].imag * v_mag[i]
                    else:
                        vi = v_mag[i]
                        vj = v_mag[j]
                        gij = ybus[i, j].real
                        bij = ybus[i, j].imag
                        tij = v_angle[i] - v_angle[j]
                        jacobian[n_p + ii, n_p + jj] = vi * (gij * np.sin(tij) - bij * np.cos(tij))

            # Solve correction vector
            try:
                correction = np.linalg.solve(jacobian, mismatch)
            except np.linalg.LinAlgError:
                break

            # Apply corrections
            d_theta = correction[:n_p]
            d_v = correction[n_p:]

            for ii, i in enumerate(p_buses):
                v_angle[i] += d_theta[ii]
            for ii, i in enumerate(q_buses):
                v_mag[i] += d_v[ii] * v_mag[i]  # dV/V correction

        # Compute final power injections
        v_complex = v_mag * np.exp(1j * v_angle)
        s_calc = v_complex * np.conj(ybus @ v_complex)

        # Compute line flows
        line_flows = self._compute_line_flows(v_complex)

        result = PowerFlowResult(
            converged=converged,
            iterations=iteration + 1 if not converged else iteration + 1,
            tolerance=tolerance,
            max_mismatch=history[-1] if history else float("inf"),
            v_mag=v_mag,
            v_angle=v_angle,
            p_inject=s_calc.real,
            q_inject=s_calc.imag,
            convergence_history=history,
            line_flows=line_flows,
        )
        return result

    def solve_gauss_seidel(
        self,
        max_iter: int = 500,
        tolerance: float = 1e-6,
        acceleration: float = 1.4,
    ) -> PowerFlowResult:
        """
        Solve power flow using the Gauss-Seidel method.

        Simpler but slower convergence than Newton-Raphson.
        Uses acceleration factor to speed up convergence.
        """
        net = self.network
        n = net.n_buses
        ybus = self.ybus

        v = np.array(
            [bus.v_mag * np.exp(1j * np.radians(bus.v_angle)) for bus in net.buses],
            dtype=complex,
        )

        p_sched = np.zeros(n)
        q_sched = np.zeros(n)
        for i, bus in enumerate(net.buses):
            p_pu, q_pu = net.get_net_injection(bus.number)
            p_sched[i] = p_pu
            q_sched[i] = q_pu

        history = []
        converged = False

        for iteration in range(max_iter):
            v_old = v.copy()

            for i, bus in enumerate(net.buses):
                if bus.bus_type == BusType.SLACK:
                    continue

                # Sum of Y[i,j] * V[j] for j != i
                s = sum(ybus[i, j] * v[j] for j in range(n) if j != i)

                # Compute new voltage
                s_sched = complex(p_sched[i], -q_sched[i])
                if abs(v[i]) > 1e-12:
                    v_new = (1.0 / ybus[i, i]) * (s_sched / np.conj(v[i]) - s)
                else:
                    v_new = v[i]

                # Apply acceleration
                v_new = v_old[i] + acceleration * (v_new - v_old[i])

                # For PV buses, keep voltage magnitude fixed
                if bus.bus_type == BusType.PV:
                    gens = net.get_generators_at_bus(bus.number)
                    v_set = gens[0].v_setpoint if gens else bus.v_mag
                    v_new = v_set * v_new / abs(v_new)

                v[i] = v_new

            # Check convergence
            max_mis = np.max(np.abs(v - v_old))
            history.append(max_mis)

            if max_mis < tolerance:
                converged = True
                break

        v_mag = np.abs(v)
        v_angle = np.angle(v)
        s_calc = v * np.conj(ybus @ v)
        line_flows = self._compute_line_flows(v)

        return PowerFlowResult(
            converged=converged,
            iterations=iteration + 1,
            tolerance=tolerance,
            max_mismatch=history[-1] if history else float("inf"),
            v_mag=v_mag,
            v_angle=v_angle,
            p_inject=s_calc.real,
            q_inject=s_calc.imag,
            convergence_history=history,
            line_flows=line_flows,
        )

    def _compute_line_flows(self, v: np.ndarray) -> list:
        """Compute active and reactive power flow on each branch."""
        net = self.network
        flows = []
        for branch in net.branches:
            if not branch.status:
                continue
            i = net.get_bus_index(branch.from_bus)
            j = net.get_bus_index(branch.to_bus)

            y = branch.y
            tap = branch.tap
            b_half = 1j * branch.b / 2

            # Current from i to j
            i_ij = (v[i] / tap - v[j]) * y + v[i] / tap * b_half
            s_ij = v[i] / tap * np.conj(i_ij)

            # Current from j to i
            i_ji = (v[j] - v[i] / tap) * y + v[j] * b_half
            s_ji = v[j] * np.conj(i_ji)

            # Losses
            s_loss = s_ij + s_ji

            flows.append({
                "from": branch.from_bus,
                "to": branch.to_bus,
                "p_from_mw": s_ij.real * net.base_mva,
                "q_from_mvar": s_ij.imag * net.base_mva,
                "p_to_mw": s_ji.real * net.base_mva,
                "q_to_mvar": s_ji.imag * net.base_mva,
                "p_loss_mw": s_loss.real * net.base_mva,
                "q_loss_mvar": s_loss.imag * net.base_mva,
            })
        return flows
