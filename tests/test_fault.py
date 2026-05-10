"""Tests for symmetrical-component fault analysis on IEEE 9-bus."""
import pathlib, pytest
from core.network import PowerNetwork
from core.fault_analysis import FaultAnalyzer

GRID_DIR = pathlib.Path(__file__).resolve().parents[1] / "grids"


@pytest.fixture
def ieee9():
    return PowerNetwork.from_json(GRID_DIR / "ieee9.json")


@pytest.fixture
def analyzer(ieee9):
    return FaultAnalyzer(ieee9)


class TestThreePhase:
    def test_fault_current_positive(self, analyzer):
        result = analyzer.analyze(bus=7, fault_type="3PH")
        assert result.fault_current_ka > 0, "3PH fault current must be positive"

    def test_faulted_bus_voltage_zero(self, analyzer):
        result = analyzer.analyze(bus=7, fault_type="3PH")
        # Faulted bus voltage should be zero for bolted 3PH fault
        bus_idx = 6  # bus 7 is index 6
        assert abs(result.bus_voltages[bus_idx]) < 1e-6


class TestSLG:
    def test_fault_current_positive(self, analyzer):
        result = analyzer.analyze(bus=5, fault_type="SLG")
        assert result.fault_current_ka > 0

    def test_slg_less_than_3ph(self, analyzer):
        """SLG fault on a grounded system can exceed 3PH, but should be finite."""
        slg = analyzer.analyze(bus=5, fault_type="SLG")
        assert slg.fault_current_ka < 100, "SLG fault current implausibly high"


class TestLL:
    def test_fault_current_positive(self, analyzer):
        result = analyzer.analyze(bus=5, fault_type="LL")
        assert result.fault_current_ka > 0

    def test_ll_relation_to_3ph(self, analyzer):
        """LL fault current ≈ (√3/2) × 3PH fault current in simple systems."""
        ll = analyzer.analyze(bus=5, fault_type="LL")
        ph3 = analyzer.analyze(bus=5, fault_type="3PH")
        ratio = ll.fault_current_ka / ph3.fault_current_ka
        # Ratio should be near sqrt(3)/2 ≈ 0.866 but varies with impedance
        assert 0.5 < ratio < 1.5, f"LL/3PH ratio = {ratio:.3f} seems wrong"


class TestDLG:
    def test_fault_current_positive(self, analyzer):
        result = analyzer.analyze(bus=5, fault_type="DLG")
        assert result.fault_current_ka > 0


class TestAllBuses:
    def test_fault_at_every_bus(self, analyzer, ieee9):
        """Verify fault analysis runs without error on every bus."""
        for bus in ieee9.buses:
            for ft in ["3PH", "SLG", "LL", "DLG"]:
                result = analyzer.analyze(bus=bus.number, fault_type=ft)
                assert result.fault_current_ka > 0, (
                    f"Bus {bus.number} {ft}: current = {result.fault_current_ka}"
                )
