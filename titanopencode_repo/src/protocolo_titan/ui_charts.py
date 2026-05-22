from __future__ import annotations

import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon
import pandas as pd


def _dark_axes(fig, ax):
    fig.patch.set_facecolor('#091426')
    ax.set_facecolor('#0E1B2E')
    for spine in ax.spines.values():
        spine.set_color('#2D4060')
    ax.tick_params(colors='#C7D5F2')
    ax.xaxis.label.set_color('#C7D5F2')
    ax.yaxis.label.set_color('#C7D5F2')
    ax.title.set_color('#F2F7FF')
    ax.grid(True, color='#1D3352', alpha=0.45, linewidth=0.8)
    return fig, ax


def figure_timeslot_signal(trace: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    _dark_axes(fig, ax)
    if 'burst_time_us' in trace.columns and trace['burst_time_us'].notna().any():
        burst_trace = trace[trace['burst_time_us'].notna()].copy()
        x = burst_trace['burst_time_us'].to_numpy()
        y = burst_trace['envelope_normalized'].to_numpy()
    else:
        x = trace['time_us'].to_numpy()
        y = trace['envelope_normalized'].to_numpy()
    burst_duration_us = float(x.max())
    burst_data_end = burst_duration_us * (300.0 / 577.0)
    training_end = burst_duration_us * (540.0 / 577.0)
    label_y = y.max() * 0.96
    ax.plot(x, y, color='#46C6FF', linewidth=1.8)
    ax.axvspan(0, burst_data_end, color='#123A5E', alpha=0.25)
    ax.axvspan(burst_data_end, training_end, color='#1B5D74', alpha=0.20)
    ax.axvspan(training_end, burst_duration_us, color='#2E4E6F', alpha=0.22)
    ax.text(burst_data_end * 0.25, label_y, 'BURST DATA', color='#AFC4E8', fontsize=8, fontweight='bold')
    ax.text((burst_data_end + training_end) * 0.5, label_y, 'TRAINING SEQUENCE', color='#AFC4E8', fontsize=8, fontweight='bold')
    ax.text((training_end + burst_duration_us) * 0.5, label_y, 'GUARD', color='#AFC4E8', fontsize=8, fontweight='bold')
    ax.set_title('ANÁLISIS TEMPORAL DE LA VARIACIÓN DE SEÑAL', loc='left', fontsize=13, fontweight='bold')
    ax.set_xlabel('TIME (µs)')
    ax.set_ylabel('AMP. NORM.')
    ax.set_xlim(0, burst_duration_us)
    ax.axhline(1.0, linestyle='--', color='#7ED7FF', alpha=0.5)
    return fig


def figure_noise(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    _dark_axes(fig, ax)
    ax.plot(df['rbw_khz'], df['noise_floor_dbm'], color='#46C6FF', marker='o', linewidth=2, label='Ruido integrado')
    if 'displayed_average_noise_dbm' in df.columns:
        ax.plot(
            df['rbw_khz'],
            df['displayed_average_noise_dbm'],
            color='#67E8A3',
            marker='s',
            linewidth=1.8,
            label='DANL mostrado',
        )
    ax.set_xscale('log')
    ax.set_title('ANÁLISIS DE ESPECTRO Y RUIDO', loc='left', fontsize=13, fontweight='bold')
    ax.set_xlabel('RBW (kHz)')
    ax.set_ylabel('NOISE FLOOR (dBm)')
    ax.legend(facecolor='#0E1B2E', edgecolor='#2D4060', labelcolor='#DDE9FF')
    return fig


def figure_cluster_map(cluster_size: int = 4, cell_radius_km: float = 1.5):
    fig, ax = plt.subplots(figsize=(8, 7))
    _dark_axes(fig, ax)
    ax.set_title(f'MAPEO DE CLÚSTER (N={cluster_size})', loc='left', fontsize=13, fontweight='bold')

    cell_colors = {
        'A': '#35E1E8',
        'B': '#2B8CFF',
        'C': '#3F6ED8',
        'D': '#6BB7D8',
    }

    if cluster_size == 4:
        labels = [
            (-1, 1, 'A'), (0, 1, 'B'), (1, 1, 'D'),
            (-1.5, 0, 'C'), (-0.5, 0, 'A'), (0.5, 0, 'B'), (1.5, 0, 'D'),
            (-1, -1, 'C'), (0, -1, 'D'), (1, -1, 'B'),
            (-0.5, 2, 'D'), (0.5, 2, 'C'),
            (-0.5, -2, 'B'), (0.5, -2, 'A')
        ]

        r = 0.55
        for x, y, lab in labels:
            hexagon = RegularPolygon((x, y), numVertices=6, radius=r, orientation=np.radians(30),
                                     facecolor=cell_colors[lab], edgecolor='#A6F7FF', alpha=0.85, linewidth=1.2)
            ax.add_patch(hexagon)
            ax.text(x, y, f'Cell {lab}', ha='center', va='center', color='#08213A', fontsize=9, fontweight='bold')

        ax.text(1.95, 1.95, f'Cell Radius\nR={cell_radius_km:g} km', color='#C7D5F2', fontsize=9)
        ax.text(1.95, -1.9, f'Reuse pattern\nN={cluster_size}', color='#C7D5F2', fontsize=9)
        ax.set_xlim(-2.4, 2.8)
        ax.set_ylim(-2.6, 2.6)
    else:
        palette = ['#35E1E8', '#2B8CFF', '#3F6ED8', '#6BB7D8', '#7EE6FF', '#94D8FF']
        radius = 0.42 if cluster_size > 12 else 0.5
        orbit = 1.65 if cluster_size > 1 else 0.0
        angles = np.linspace(0.0, 2.0 * np.pi, cluster_size, endpoint=False)

        for idx, angle in enumerate(angles):
            x = orbit * math.cos(angle)
            y = orbit * math.sin(angle)
            label = chr(ord('A') + idx)
            hexagon = RegularPolygon(
                (x, y),
                numVertices=6,
                radius=radius,
                orientation=np.radians(30),
                facecolor=palette[idx % len(palette)],
                edgecolor='#A6F7FF',
                alpha=0.85,
                linewidth=1.2,
            )
            ax.add_patch(hexagon)
            ax.text(x, y, f'Cell {label}', ha='center', va='center', color='#08213A', fontsize=8, fontweight='bold')

        ax.text(2.2, 1.95, f'Cell Radius\nR={cell_radius_km:g} km', color='#C7D5F2', fontsize=9)
        ax.text(2.2, -1.9, f'Reuse pattern\nN={cluster_size}', color='#C7D5F2', fontsize=9)
        ax.set_xlim(-2.6, 3.0)
        ax.set_ylim(-2.5, 2.5)

    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    return fig


def figure_carrier_distribution(plan_df: pd.DataFrame, logical_df: pd.DataFrame, total_carriers: int | None = None):
    bcch = logical_df[logical_df['carrier_role'].str.contains('BCCH')].groupby('cell').size()
    tch = logical_df[logical_df['carrier_role'].str.contains('TCH')].groupby('cell').size()
    cells = plan_df['cell'].tolist()
    bcch_vals = [int(bcch.get(c, 0)) for c in cells]
    tch_vals = [int(tch.get(c, 0)) for c in cells]

    fig, ax = plt.subplots(figsize=(6.3, 3.3))
    _dark_axes(fig, ax)
    ax.bar(cells, bcch_vals, label='BCCH', color='#7EE6FF')
    ax.bar(cells, tch_vals, bottom=bcch_vals, label='TCH', color='#278DFF')
    carriers = total_carriers if total_carriers is not None else int(logical_df['arfcn'].nunique())
    ax.set_title(f'DISTRIBUCIÓN DE PORTADORAS ({carriers} CH)', loc='left', fontsize=12, fontweight='bold')
    ax.set_xlabel('Cell ID')
    ax.set_ylabel('Número de canales')
    ax.legend(facecolor='#0E1B2E', edgecolor='#2D4060', labelcolor='#DDE9FF')
    return fig


def figure_spectrum_from_arfcns(logical_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    _dark_axes(fig, ax)

    if 'uplink_mhz' in logical_df.columns:
        freqs = logical_df['uplink_mhz'].to_numpy(dtype=float)
    else:
        arfcns = logical_df['arfcn'].to_numpy(dtype=float)
        freqs = 890.0 + arfcns * 0.2

    x = np.linspace(freqs.min() - 1.2, freqs.max() + 1.2, 2400)
    baseline_dbm = -118.0
    spectrum_linear = np.full_like(x, 10 ** (baseline_dbm / 10.0), dtype=float)

    for idx, row in enumerate(logical_df.itertuples(index=False)):
        center_mhz = float(getattr(row, 'uplink_mhz', 890.0 + getattr(row, 'arfcn') * 0.2))
        is_bcch = 'BCCH' in str(getattr(row, 'carrier_role', ''))
        peak_dbm = -55.0 if is_bcch else -60.0 - 1.5 * (idx % 3)
        peak_linear = 10 ** (peak_dbm / 10.0)
        offset = x - center_mhz
        main_lobe = np.sinc(offset / 0.11) ** 2
        side_lobes = 0.18 * (np.sinc(offset / 0.28) ** 2)
        spectrum_linear += peak_linear * (main_lobe + side_lobes)

    y = 10.0 * np.log10(np.clip(spectrum_linear, 1e-12, None))
    ax.plot(x, y, color='#46C6FF', linewidth=1.4)
    ax.fill_between(x, y, baseline_dbm - 4.0, color='#46C6FF', alpha=0.08)
    ax.set_ylim(baseline_dbm - 4.0, -20)
    ax.set_xlabel('Frequency (MHz)')
    ax.set_ylabel('Power / Amplitude (dBm)')
    ax.set_title('ESPECTRO GSM-900 UPLINK — DISTRIBUCIÓN Y CO-CANAL', loc='left', fontsize=12, fontweight='bold')
    return fig


def figure_small_camera_placeholder():
    # self-contained synthetic view resembling a live RF corridor panel
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    fig.patch.set_facecolor('#091426')
    ax.set_facecolor('#10243B')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    # sky and terrain
    ax.fill_between([0, 10], 10, 6.7, color='#92BFE6')
    ax.fill_between([0, 2.3, 4.8, 6.8, 10], [6.1, 6.8, 6.0, 6.5, 6.2], 0, color='#7FA772')
    # viaduct
    ax.plot([0.8, 9.2], [2.0, 3.3], color='#B7C7D9', linewidth=12, solid_capstyle='round')
    for p in [1.7, 3.2, 4.7, 6.2, 7.7, 9.0]:
        y = 1.8 + (p-0.8)*(1.3/8.4)
        ax.plot([p, p], [0.4, y], color='#CBD8E8', linewidth=3)
    # mast
    ax.plot([5.3, 5.3], [3.8, 7.1], color='#9AA9BA', linewidth=4)
    ax.plot([5.1, 5.5], [5.9, 5.9], color='#9AA9BA', linewidth=3)
    ax.plot([5.0, 5.6], [6.3, 6.3], color='#9AA9BA', linewidth=3)
    for r in [0.7, 1.2, 1.8]:
        circ = plt.Circle((5.3, 5.0), r, color='#55C8FF', fill=False, alpha=0.22, linewidth=1.4)
        ax.add_patch(circ)
    # train
    ax.plot([7.0, 8.8], [2.8, 3.05], color='#16324F', linewidth=16, solid_capstyle='round')
    ax.plot([7.1, 8.7], [2.95, 3.18], color='#E5F2FF', linewidth=2.2)
    return fig
