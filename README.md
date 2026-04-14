# power-grid-simulator

An interactive power flow analysis and fault simulation tool built with Python. Visualize bus voltages, line flows, and fault currents in a web interface. Built for learning power systems engineering.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## What It Does

Define a power grid (buses, generators, loads, transmission lines), run Newton-Raphson power flow, and simulate faults — all through a browser interface. See results as interactive single-line diagrams with color-coded voltages and flows.

```
Define Grid → Run Power Flow → Visualize Results → Simulate Faults
```

Built as a study tool for power systems courses, but useful for anyone learning load flow analysis.

## Quick Start

```bash
git clone https://github.com/emmilnath/power-grid-simulator.git
cd power-grid-simulator
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` — load a sample grid or build your own.

## Features

**Power Flow Analysis** — Newton-Raphson and Gauss-Seidel solvers. Handles PQ buses, PV buses, and slack bus. Displays convergence history and per-bus voltage/angle results.

**Fault Simulation** — Symmetrical (3-phase) and asymmetrical (SLG, LL, DLG) fault analysis using sequence networks. Select a fault location and see fault currents at every bus.

**Interactive Visualization** — Single-line diagram with:
- Color-coded bus voltages (green = nominal, yellow = marginal, red = violation)
- Line flow arrows with MW/MVAR labels
- Clickable buses and lines for detailed data

**Sample Grids** — Pre-loaded IEEE test systems (9-bus, 14-bus, 30-bus) for quick experimentation.

**Grid Editor** — Add/remove buses, generators, loads, and lines through the UI. Export grid definitions as JSON.

## Project Structure

```
power-grid-simulator/
├── app.py                  # Streamlit entry point
├── core/
│   ├── power_flow.py       # Newton-Raphson and Gauss-Seidel solvers
│   ├── fault_analysis.py   # Symmetrical and asymmetrical faults
│   ├── network.py          # Grid data model (buses, branches, generators)
│   └── ybus.py             # Admittance matrix construction
├── visualization/
│   ├── single_line.py      # Interactive diagram (Plotly)
│   └── convergence.py      # Solver convergence plots
├── grids/
│   ├── ieee9.json          # IEEE 9-bus test system
│   ├── ieee14.json         # IEEE 14-bus test system
│   └── ieee30.json         # IEEE 30-bus test system
├── tests/
│   ├── test_power_flow.py  # Validated against textbook solutions
│   └── test_fault.py
├── requirements.txt
└── README.md
```

## Example Output

```
=== Power Flow Results (IEEE 9-bus) ===
Bus 1 (Slack):  V = 1.040∠0.0°    P = 71.6 MW   Q = 27.0 MVAR
Bus 2 (PV):     V = 1.025∠9.3°    P = 163.0 MW  Q = 6.7 MVAR
Bus 3 (PV):     V = 1.025∠4.7°    P = 85.0 MW   Q = -10.9 MVAR
...
Converged in 4 iterations (tolerance: 1e-6)
```

## Built With

- **NumPy / SciPy** — matrix operations and sparse solvers
- **Streamlit** — web interface
- **Plotly** — interactive diagrams and charts
- **NetworkX** — graph representation of the power grid
- **pytest** — testing against known textbook solutions

## What You Learn

- Newton-Raphson method applied to nonlinear power flow equations
- Admittance matrix (Ybus) construction from line parameters
- Sequence networks and symmetrical components for fault analysis
- Practical Python engineering — building a simulator, not just scripts

## Roadmap

- [ ] Optimal power flow (OPF) with economic dispatch
- [ ] Transient stability simulation
- [ ] Deploy on AWS (EC2 + S3 for grid storage)
- [ ] MATLAB/Simulink comparison validation

## License

MIT
