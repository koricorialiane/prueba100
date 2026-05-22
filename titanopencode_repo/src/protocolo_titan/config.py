from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class GSMConfig:
    """Parámetros de capa física GSM/EDGE empleados en el reto."""

    carrier_frequency_hz: float = 900e6
    channel_bandwidth_hz: float = 200e3
    speed_of_light_ms: float = 3e8
    timeslot_duration_s: float = 577e-6
    timeslots_per_frame: int = 8


@dataclass(frozen=True)
class ConvoyScenario:
    """Escenario A: convoy de alta velocidad en vía férrea."""

    cell_radius_km: float = 3.0
    speeds_kmh: Sequence[float] = (50.0, 250.0)
    rms_delay_spread_us: float = 1.8
    analysis_window_ms: float = 40.0
    jakes_sinusoids: int = 32
    rician_k_factor_db: float = 7.0
    fade_threshold_db: float = -10.0


@dataclass(frozen=True)
class CampScenario:
    """Escenario B: campamento base con alta densidad operativa."""

    cell_radius_km: float = 1.5
    total_carriers: int = 24
    cluster_size: int = 4
    first_arfcn: int = 1
    path_loss_exponent: float = 3.6
    cochannel_tier_size: int = 6
    target_cir_db: float = 9.0
    bcch_timeslots_reserved: int = 1
    tch_user_bitrate_kbps: float = 13.0


@dataclass(frozen=True)
class AnalyzerConfig:
    """Parámetros de instrumentación para certificación y medidas."""

    noise_figure_db: float = 6.0
    rbw_values_hz: Sequence[float] = (100e3, 10e3, 1e3)
    span_hz: float = 5e6
    enbw_factor: float = 1.05
    detector_bias_db: float = 2.51
    weak_signal_reference_dbm: float = -120.0
