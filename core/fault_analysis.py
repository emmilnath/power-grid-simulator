"""
Fault analysis using symmetrical components and sequence networks.

Supports three-phase (3PH), single-line-to-ground (SLG),
line-to-line (LL), and double-line-to-ground (DLG) faults.
"""

import numpy as np
from dataclasses import dataclass, field
from .network import PowerNetwork
from .ybus import build_ybus, build_sequence_ybus


@dataclass
class FaultResult:
    """Results of a fault analysis."""
    fault_bus: int
    fault_type: str
    fault_current_pu: complex = 0.0 + 0.0j
    fault_current_ka: float = 0.0
    phase_currents: dict = field(default_factory=dict)
    bus_voltages_during_fault: dict = field(default_factory=dict)
    sequence_currents: dict = field(default_factory=dict)

    def summary(self, network: PowerNetwork) -> str:
        lines = [
            f"=== Fault Analysis: {self.fault_type} at Bus {self.fault_bus} ===",
            f"Fault current: {abs(self.fault_current_pu):.4f} p.u. "
            f"({self.fault_current_ka:.2f} kA)",
        ]
        if self.phase_currents:
            lines.append("Phase currents (p.u.):")
            for phase, val in self.phase_currents.items():
                lines.append(f"  I{phase} = {abs(val):.4f}∠{np.degrees(np.angle(val)):.1f}°")
        if self.bus_voltages_during_fault:
            lines.append("Bus voltages during fault (p.u.):")
            for bus_num, v in self.bus_voltages_during_fault.items():
                lines.append(f"  Bus {bus_num}: V = {abs(v):.4f}")
        return "\n".join(lines)


class FaultAnalyzer:
    """Perform short-circuit fault analysis on a power network."""

    def __init__(self, network: PowerNetwork, prefault_voltages: np.ndarray = None):
        self.network = network
        self.n = network.n_buses

        # Build sequence impedance matrices (Zbus = inv(Ybus))
        y1 = build_sequence_ybus(network, sequence=1)
        y2 = build_sequence_ybus(network, sequence=2)
        y0 = build_sequence_ybus(network, sequence=0)

        # Add generator subtransient reactances to diagonal
        for gen in network.generators:
            if gen.status:
                idx = network.get_bus_index(gen.bus)
                xd = gen.xd_pp * (network.base_mva / gen.mbase)
                y1[idx, idx] += 1.0 / (1j * xd)
                y2[idx, idx] += 1.0 / (1j * xd)
                y0[idx, idx] += 1.0 / (1j * xd * 2.5)

        self.zbus1 = np.linalg.inv(y1)
        self.zbus2 = np.linalg.inv(y2)
        self.zbus0 = np.linalg.inv(y0)

        # Pre-fault voltages (assume flat start if not provided)
        if prefault_voltages is not None:
            self.v_prefault = prefault_voltages
        else:
            self.v_prefault = np.ones(self.n, dtype=complex)

    def analyze(
        self,
        fault_bus: int,
        fault_type: str = "3PH",
        z_fault: complex = 0.0 + 0.0j,
    ) -> FaultResult:
        """
        Run fault analysis at the specified bus.

        Parameters
        ----------
        fault_bus : int
            Bus number where the fault occurs.
        fault_type : str
            "3PH" (three-phase), "SLG" (single-line-to-ground),
            "LL" (line-to-line), "DLG" (double-line-to-ground).
        z_fault : complex
            Fault impedance (default: bolted fault, z=0).

        Returns
        -------
        FaultResult
        """
        k = self.network.get_bus_index(fault_bus)
        vf = self.v_prefault[k]

        z1 = self.zbus1[k, k]
        z2 = self.zbus2[k, k]
        z0 = self.zbus0[k, k]

        # Symmetrical component transformation
        a = np.exp(1j * 2 * np.pi / 3)
        a2 = a ** 2

        if fault_type == "3PH":
            # Three-phase fault: If1 = Vf / (Z1 + Zf)
            if1 = vf / (z1 + z_fault)
            if2 = 0.0
            if0 = 0.0

        elif fault_type == "SLG":
            # Single-line-to-ground: sequence currents are equal
            i_seq = vf / (z0 + z1 + z2 + 3 * z_fault)
            if0 = i_seq
            if1 = i_seq
            if2 = i_seq

        elif fault_type == "LL":
            # Line-to-line: no zero-sequence
            if1 = vf / (z1 + z2 + z_fault)
            if2 = -if1
            if0 = 0.0

        elif fault_type == "DLG":
            # Double-line-to-ground
            z_parallel = (z2 * (z0 + 3 * z_fault)) / (z2 + z0 + 3 * z_fault)
            if1 = vf / (z1 + z_parallel)
            if2 = -if1 * (z0 + 3 * z_fault) / (z2 + z0 + 3 * z_fault)
            if0 = -if1 * z2 / (z2 + z0 + 3 * z_fault)

        else:
            raise ValueError(f"Unknown fault type: {fault_type}")

        # Convert sequence currents to phase currents
        ia = if0 + if1 + if2
        ib = if0 + a2 * if1 + a * if2
        ic = if0 + a * if1 + a2 * if2

        # Total fault current magnitude
        if fault_type == "3PH":
            i_fault = if1
        elif fault_type == "SLG":
            i_fault = 3 * if0
        elif fault_type == "LL":
            i_fault = ia  # current in faulted phases
        else:
            i_fault = ia

        # Convert to kA
        bus = self.network.get_bus(fault_bus)
        i_base = self.network.base_mva / (np.sqrt(3) * bus.base_kv)  # kA
        i_fault_ka = abs(i_fault) * i_base

        # Compute bus voltages during fault
        bus_voltages = {}
        for i, b in enumerate(self.network.buses):
            dv1 = self.zbus1[i, k] * if1
            v_during = self.v_prefault[i] - dv1
            bus_voltages[b.number] = v_during

        result = FaultResult(
            fault_bus=fault_bus,
            fault_type=fault_type,
            fault_current_pu=i_fault,
            fault_current_ka=i_fault_ka,
            phase_currents={"a": ia, "b": ib, "c": ic},
            bus_voltages_during_fault=bus_voltages,
            sequence_currents={"0": if0, "1": if1, "2": if2},
        )
        return result
