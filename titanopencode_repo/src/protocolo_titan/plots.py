from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from .ui_charts import figure_carrier_distribution, figure_cluster_map, figure_spectrum_from_arfcns


def _style_axes(fig, ax) -> None:
    fig.patch.set_facecolor("#091426")
    ax.set_facecolor("#0F1D31")
    for spine in ax.spines.values():
        spine.set_color("#294466")
    ax.tick_params(colors="#D9E8FF")
    ax.xaxis.label.set_color("#D9E8FF")
    ax.yaxis.label.set_color("#D9E8FF")
    ax.title.set_color("#F4F8FF")
    ax.grid(True, color="#28405E", alpha=0.35, linewidth=0.8)


def save_doppler_plot(df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    _style_axes(fig, ax)
    ax.plot(df["speed_kmh"], df["max_doppler_hz"], marker="o", linewidth=2.2, color="#52D3FF")
    ax.set_xlabel("Velocidad (km/h)")
    ax.set_ylabel("Doppler máximo (Hz)")
    ax.set_title("Escenario A: efecto Doppler", loc="left", fontweight="bold")
    for row in df.itertuples(index=False):
        ax.annotate(
            f"{row.max_doppler_hz:.1f} Hz",
            (row.speed_kmh, row.max_doppler_hz),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            color="#A9DFFF",
            fontsize=9,
        )
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


def save_coherence_plot(df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    _style_axes(fig, ax)
    bars = ax.bar(df["speed_kmh"].astype(str), df["coherence_time_ms"], color=["#7EE6FF", "#2D8BFF"])
    ax.axhline(
        df["gsm_timeslot_ms"].iloc[0],
        linestyle="--",
        color="#67E8A3",
        linewidth=1.6,
        label="Timeslot GSM",
    )
    ax.set_xlabel("Velocidad (km/h)")
    ax.set_ylabel("Tiempo (ms)")
    ax.set_title("Tiempo de coherencia frente a timeslot GSM", loc="left", fontweight="bold")
    ax.legend(facecolor="#0F1D31", edgecolor="#294466", labelcolor="#D9E8FF")
    ax.grid(True, axis="y", color="#28405E", alpha=0.35, linewidth=0.8)
    for bar, coherence in zip(bars, df["coherence_time_ms"].tolist()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            coherence + 0.18,
            f"{coherence:.2f} ms",
            ha="center",
            va="bottom",
            color="#D9E8FF",
            fontsize=9,
        )
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


def save_fading_plot(df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    _style_axes(fig, ax)
    if "time_ms" in df.columns:
        x = df["time_ms"]
        xlabel = "Tiempo de observación (ms)"
    else:
        x = df["time_us"] * 1e-3
        xlabel = "Tiempo (ms)"

    ax.plot(x, df["envelope_normalized"], linewidth=1.9, color="#52D3FF")
    ax.fill_between(x, df["envelope_normalized"], color="#52D3FF", alpha=0.12)
    model = df["model"].iloc[0]
    doppler = df["doppler_hz"].iloc[0]
    duration_ms = float(x.iloc[-1] - x.iloc[0]) if len(x) > 1 else 0.0
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Envolvente normalizada")
    ax.set_title(
        f"Evolucion temporal {model} durante {duration_ms:.1f} ms - fD={doppler:.2f} Hz",
        loc="left",
        fontweight="bold",
    )
    ax.axhline(1.0, linestyle="--", linewidth=1.1, color="#67E8A3", alpha=0.7)
    if "burst_time_us" in df.columns and df["burst_time_us"].notna().any() and "time_ms" in df.columns:
        burst_window = df[df["burst_time_us"].notna()]
        burst_start = float(burst_window["time_ms"].iloc[0])
        burst_end = float(burst_window["time_ms"].iloc[-1])
        ax.axvspan(burst_start, burst_end, color="#67E8A3", alpha=0.12)
        ax.text(
            (burst_start + burst_end) / 2.0,
            float(df["envelope_normalized"].max()) * 0.92,
            "Ventana de rafaga GSM",
            ha="center",
            va="center",
            color="#C7F9D8",
            fontsize=8,
            fontweight="bold",
        )
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


def save_reuse_plot(df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    _style_axes(fig, ax)
    cells = df["cell"]
    distances = df["reuse_distance_km"]
    bars = ax.bar(cells, distances, color="#3AA8FF")
    ax.set_xlabel("Celda del clúster")
    ax.set_ylabel("Distancia de reutilización D (km)")
    ax.set_title("Escenario B: distancia de reutilización común", loc="left", fontweight="bold")
    ax.grid(True, axis="y", color="#28405E", alpha=0.35, linewidth=0.8)
    for bar, distance in zip(bars, distances.tolist()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            distance + 0.08,
            f"{distance:.2f} km",
            ha="center",
            va="bottom",
            color="#D9E8FF",
            fontsize=9,
        )
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


def save_noise_plot(df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    _style_axes(fig, ax)
    ax.plot(df["rbw_khz"], df["noise_floor_dbm"], marker="o", linewidth=2.2, color="#52D3FF", label="Ruido integrado")
    if "displayed_average_noise_dbm" in df.columns:
        ax.plot(
            df["rbw_khz"],
            df["displayed_average_noise_dbm"],
            marker="s",
            linewidth=1.8,
            color="#67E8A3",
            label="DANL mostrado",
        )
    ax.set_xscale("log")
    ax.set_xlabel("RBW (kHz)")
    ax.set_ylabel("Suelo de ruido (dBm)")
    ax.set_title("Instrumentación: ruido integrado frente a RBW", loc="left", fontweight="bold")
    for row in df.itertuples(index=False):
        ax.annotate(
            f"{row.noise_floor_dbm:.0f} dBm",
            (row.rbw_khz, row.noise_floor_dbm),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            color="#A9DFFF",
            fontsize=9,
        )
    ax.legend(facecolor="#0F1D31", edgecolor="#294466", labelcolor="#D9E8FF")
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


def save_cluster_map_plot(cluster_size: int, cell_radius_km: float, path: Path) -> None:
    fig = figure_cluster_map(cluster_size=cluster_size, cell_radius_km=cell_radius_km)
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


def save_carrier_distribution_plot(
    plan_df: pd.DataFrame,
    logical_df: pd.DataFrame,
    total_carriers: int,
    path: Path,
) -> None:
    fig = figure_carrier_distribution(plan_df, logical_df, total_carriers=total_carriers)
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)


def save_spectrum_plot(logical_df: pd.DataFrame, path: Path) -> None:
    fig = figure_spectrum_from_arfcns(logical_df)
    fig.tight_layout()
    fig.savefig(path, dpi=220, facecolor=fig.get_facecolor())
    plt.close(fig)
