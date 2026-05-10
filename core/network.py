"""
Power network data model — buses, branches, generators, loads.

Stores network topology and parameters for power flow and fault analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import numpy as np


class BusType(Enum):
    SLACK = 0
    PQ = 1
    PV = 2


@dataclass
class Bus:
    """Electrical bus (node) in the power system."""
    number: int
    name: str = ""
    bus_type: BusType = BusType.PQ
    base_kv: float = 100.0
    v_mag: float = 1.0        # per-unit voltage magnitude
    v_angle: float = 0.0      # voltage angle in degrees
    v_min: float = 0.95
    v_max: float = 1.05
    # Sequence impedances for fault analysis (per-unit)
    z1: complex = 0.0 + 0.0j  # positive-sequence impedance
    z2: complex = 0.0 + 0.0j  # negative-sequence impedance
    z0: complex = 0.0 + 0.0j  # zero-sequence impedance


@dataclass
class Branch:
    """Transmission line or transformer between two buses."""
    from_bus: int
    to_bus: int
    r: float = 0.0            # resistance (per-unit)
    x: float = 0.01           # reactance (per-unit)
    b: float = 0.0            # total line charging susceptance (per-unit)
    rating_mva: float = 100.0
    tap: float = 1.0          # transformer tap ratio (1.0 for lines)
    status: bool = True

    @property
    def z(self) -> complex:
        return complex(self.r, self.x)

    @property
    def y(self) -> complex:
        if abs(self.z) < 1e-12:
            return complex(0, 0)
        return 1.0 / self.z


@dataclass
class Generator:
    """Generator connected to a bus."""
    bus: int
    p_mw: float = 0.0        # active power output (MW)
    q_mvar: float = 0.0      # reactive power output (MVAR)
    q_min: float = -999.0
    q_max: float = 999.0
    v_setpoint: float = 1.0  # voltage setpoint for PV buses
    mbase: float = 100.0     # machine base MVA
    status: bool = True
    # Subtransient reactances for fault analysis
    xd_pp: float = 0.2       # direct-axis subtransient reactance


@dataclass
class Load:
    """Load connected to a bus."""
    bus: int
    p_mw: float = 0.0
    q_mvar: float = 0.0
    status: bool = True


@dataclass
class PowerNetwork:
    """Complete power system network model."""
    name: str = "Unnamed Network"
    base_mva: float = 100.0
    buses: list = field(default_factory=list)
    branches: list = field(default_factory=list)
    generators: list = field(default_factory=list)
    loads: list = field(default_factory=list)

    @property
    def n_buses(self) -> int:
        return len(self.buses)

    def get_bus(self, number: int) -> Optional[Bus]:
        for bus in self.buses:
            if bus.number == number:
                return bus
        return None

    def get_bus_index(self, number: int) -> int:
        """Return the index of a bus by its number."""
        for i, bus in enumerate(self.buses):
            if bus.number == number:
                return i
        raise ValueError(f"Bus {number} not found")

    def get_slack_bus(self) -> Optional[Bus]:
        for bus in self.buses:
            if bus.bus_type == BusType.SLACK:
                return bus
        return None

    def get_pv_buses(self) -> list:
        return [b for b in self.buses if b.bus_type == BusType.PV]

    def get_pq_buses(self) -> list:
        return [b for b in self.buses if b.bus_type == BusType.PQ]

    def get_generators_at_bus(self, bus_number: int) -> list:
        return [g for g in self.generators if g.bus == bus_number and g.status]

    def get_loads_at_bus(self, bus_number: int) -> list:
        return [ld for ld in self.loads if ld.bus == bus_number and ld.status]

    def get_net_injection(self, bus_number: int) -> tuple:
        """Net P and Q injection at a bus (generation - load) in per-unit."""
        p_gen = sum(g.p_mw for g in self.get_generators_at_bus(bus_number))
        q_gen = sum(g.q_mvar for g in self.get_generators_at_bus(bus_number))
        p_load = sum(ld.p_mw for ld in self.get_loads_at_bus(bus_number))
        q_load = sum(ld.q_mvar for ld in self.get_loads_at_bus(bus_number))
        return ((p_gen - p_load) / self.base_mva,
                (q_gen - q_load) / self.base_mva)

    def to_dict(self) -> dict:
        """Serialize network to a dictionary."""
        return {
            "name": self.name,
            "base_mva": self.base_mva,
            "buses": [
                {
                    "number": b.number, "name": b.name,
                    "type": b.bus_type.name, "base_kv": b.base_kv,
                    "v_mag": b.v_mag, "v_angle": b.v_angle,
                    "v_min": b.v_min, "v_max": b.v_max,
                }
                for b in self.buses
            ],
            "branches": [
                {
                    "from": br.from_bus, "to": br.to_bus,
                    "r": br.r, "x": br.x, "b": br.b,
                    "rating_mva": br.rating_mva, "tap": br.tap,
                }
                for br in self.branches
            ],
            "generators": [
                {
                    "bus": g.bus, "p_mw": g.p_mw, "q_mvar": g.q_mvar,
                    "q_min": g.q_min, "q_max": g.q_max,
                    "v_setpoint": g.v_setpoint, "xd_pp": g.xd_pp,
                }
                for g in self.generators
            ],
            "loads": [
                {"bus": ld.bus, "p_mw": ld.p_mw, "q_mvar": ld.q_mvar}
                for ld in self.loads
            ],
        }

    def to_json(self, path: str):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "PowerNetwork":
        net = cls(name=data.get("name", ""), base_mva=data.get("base_mva", 100.0))
        type_map = {"SLACK": BusType.SLACK, "PQ": BusType.PQ, "PV": BusType.PV}
        for bd in data.get("buses", []):
            net.buses.append(Bus(
                number=bd["number"], name=bd.get("name", ""),
                bus_type=type_map.get(bd.get("type", "PQ"), BusType.PQ),
                base_kv=bd.get("base_kv", 100.0),
                v_mag=bd.get("v_mag", 1.0), v_angle=bd.get("v_angle", 0.0),
                v_min=bd.get("v_min", 0.95), v_max=bd.get("v_max", 1.05),
            ))
        for brd in data.get("branches", []):
            net.branches.append(Branch(
                from_bus=brd["from"], to_bus=brd["to"],
                r=brd.get("r", 0.0), x=brd.get("x", 0.01),
                b=brd.get("b", 0.0), rating_mva=brd.get("rating_mva", 100.0),
                tap=brd.get("tap", 1.0),
            ))
        for gd in data.get("generators", []):
            net.generators.append(Generator(
                bus=gd["bus"], p_mw=gd.get("p_mw", 0.0),
                q_mvar=gd.get("q_mvar", 0.0),
                q_min=gd.get("q_min", -999.0), q_max=gd.get("q_max", 999.0),
                v_setpoint=gd.get("v_setpoint", 1.0),
                xd_pp=gd.get("xd_pp", 0.2),
            ))
        for ldd in data.get("loads", []):
            net.loads.append(Load(
                bus=ldd["bus"], p_mw=ldd.get("p_mw", 0.0),
                q_mvar=ldd.get("q_mvar", 0.0),
            ))
        return net

    @classmethod
    def from_json(cls, path: str) -> "PowerNetwork":
        with open(path) as f:
            return cls.from_dict(json.load(f))
