"""
Admittance matrix (Ybus) construction from network branch data.

Builds the bus admittance matrix used in power flow and fault analysis.
"""

import numpy as np
from .network import PowerNetwork


def build_ybus(network: PowerNetwork) -> np.ndarray:
    """
    Build the bus admittance matrix (Ybus) for the given network.

    For each branch with series admittance y = 1/(r + jx) and shunt
    susceptance b, the contributions to Ybus are:

        Y[i,i] += y / tap^2 + j*b/2
        Y[j,j] += y + j*b/2
        Y[i,j] -= y / tap
        Y[j,i] -= y / tap

    Parameters
    ----------
    network : PowerNetwork
        The power system network.

    Returns
    -------
    np.ndarray
        Complex Ybus matrix of shape (n_buses, n_buses).
    """
    n = network.n_buses
    ybus = np.zeros((n, n), dtype=complex)

    for branch in network.branches:
        if not branch.status:
            continue

        i = network.get_bus_index(branch.from_bus)
        j = network.get_bus_index(branch.to_bus)

        y_series = branch.y
        b_shunt = branch.b
        tap = branch.tap

        # Diagonal elements
        ybus[i, i] += y_series / (tap ** 2) + 1j * b_shunt / 2
        ybus[j, j] += y_series + 1j * b_shunt / 2

        # Off-diagonal elements
        ybus[i, j] -= y_series / tap
        ybus[j, i] -= y_series / tap

    return ybus


def build_sequence_ybus(network: PowerNetwork, sequence: int = 1) -> np.ndarray:
    """
    Build sequence admittance matrices for fault analysis.

    Parameters
    ----------
    network : PowerNetwork
    sequence : int
        1 = positive, 2 = negative, 0 = zero sequence.

    Returns
    -------
    np.ndarray
        Sequence Ybus matrix.
    """
    # For simplified fault analysis, we use the same Ybus structure
    # with sequence impedances where applicable.
    # Positive-sequence Ybus is the standard Ybus.
    if sequence == 1:
        return build_ybus(network)

    n = network.n_buses
    ybus = np.zeros((n, n), dtype=complex)

    for branch in network.branches:
        if not branch.status:
            continue

        i = network.get_bus_index(branch.from_bus)
        j = network.get_bus_index(branch.to_bus)

        # For negative and zero sequence, use same line parameters
        # (simplified: neg-seq = pos-seq for transmission lines)
        if sequence == 2:
            y_series = branch.y
            b_shunt = branch.b
        else:  # zero sequence
            # Zero-sequence reactance is typically 2-3x positive-sequence
            z0 = complex(branch.r, branch.x * 2.5)
            y_series = 1.0 / z0 if abs(z0) > 1e-12 else 0.0
            b_shunt = branch.b / 3.0

        tap = branch.tap
        ybus[i, i] += y_series / (tap ** 2) + 1j * b_shunt / 2
        ybus[j, j] += y_series + 1j * b_shunt / 2
        ybus[i, j] -= y_series / tap
        ybus[j, i] -= y_series / tap

    return ybus
