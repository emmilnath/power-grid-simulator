# ⚡ Power Grid Simulator

Python-based power system analysis tool with interactive Streamlit UI. Implements Newton-Raphson and Gauss-Seidel power flow solvers plus symmetrical-component fault analysis on standard IEEE test systems.

## Features

- **Power Flow Analysis** — Newton-Raphson (quadratic convergence) and Gauss-Seidel solvers with configurable tolerance and iteration limits
- **Fault Analysis** — Three-phase, single-line-to-ground, line-to-line, and double-line-to-ground fault studies using sequence networks and Zbus matrices
- **IEEE Test Systems** — Pre-loaded IEEE 9-bus, 14-bus, and 30-bus networks with validated parameters
- **Interactive UI** — Streamlit dashboard with single-line diagrams (Plotly), convergence plots, and tabular results
- **Extensible Data Model** — JSON-based network format for easy custom grid definition

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Structure

```
power-grid-simulator/
├── app.py                    # Streamlit entry point
├── requirements.txt
├── core/
│   ├── __init__.py
│   ├── network.py            # Bus/Branch/Generator/Load data model
│   ├── ybus.py               # Admittance matrix construction
│   ├── power_flow.py         # NR & GS solvers
│   └── fault_analysis.py     # Symmetrical-component fault engine
├── visualization/
│   ├── __init__.py
│   ├── single_line.py        # Plotly single-line diagram
│   └── convergence.py        # Solver convergence plots
├── grids/
│   ├── ieee9.json            # WSCC 9-bus (Anderson & Fouad)
│   ├── ieee14.json           # IEEE 14-bus test case
│   └── ieee30.json           # IEEE 30-bus test case
└── tests/
    ├── test_power_flow.py    # Solver convergence & accuracy tests
    └── test_fault.py         # Fault current validation
```

## Technical Details

### Power Flow

The Newton-Raphson solver builds the full Jacobian (J1–J4 sub-matrices) at each iteration, solving the linearised mismatch equations via LU decomposition. PV bus voltage magnitudes are held constant. The Gauss-Seidel solver uses iterative complex-power balance with an acceleration factor of 1.6.

### Fault Analysis

Fault currents are computed using the bus impedance matrix (Zbus = Ybus⁻¹) for positive, negative, and zero sequence networks. Generator subtransient reactances are added to the diagonal elements. Phase currents are recovered from sequence currents via the symmetrical-component transformation matrix `[A]`.

### Validation

Solver results are validated against published IEEE test case solutions. The Newton-Raphson solver converges within 4–6 iterations on all standard test systems. Pytest tests verify convergence, PV bus voltage maintenance, and fault current positivity.

## Results

| Test System | Solver | Iterations | Max |ΔP/ΔQ| |
|------------|--------|-----------|--------------|
| IEEE 9-bus | NR     | 4         | < 1e-10      |
| IEEE 14-bus| NR     | 5         | < 1e-10      |
| IEEE 30-bus| NR     | 6         | < 1e-10      |

## License

MIT
