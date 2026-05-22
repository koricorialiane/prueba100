import math
import numpy as np
import pandas as pd

from .config import GSMConfig


TYPICAL_URBAN_DELAYS_US = np.array([0.0, 0.2, 0.5, 1.6, 2.3, 5.0])
TYPICAL_URBAN_POWERS_DB = np.array([0.0, -2.0, -4.0, -6.0, -8.0, -10.0])


def kmh_to_ms(speed_kmh: float) -> float:
    if speed_kmh < 0:
        raise ValueError("La velocidad no puede ser negativa.")
    return speed_kmh / 3.6


def max_doppler_hz(speed_ms: float, carrier_frequency_hz: float, speed_of_light_ms: float = 3e8) -> float:
    if carrier_frequency_hz <= 0:
        raise ValueError("La frecuencia debe ser positiva.")
    if speed_of_light_ms <= 0:
        raise ValueError("La velocidad de propagación debe ser positiva.")
    return speed_ms * carrier_frequency_hz / speed_of_light_ms


def coherence_time_s(doppler_hz: float) -> float:
    if doppler_hz <= 0:
        return math.inf
    return 0.423 / doppler_hz


def doppler_spread_hz(max_doppler_hz_value: float) -> float:
    if max_doppler_hz_value < 0:
        raise ValueError("max_doppler_hz_value no puede ser negativo.")
    return 2.0 * max_doppler_hz_value


def normalized_doppler(max_doppler_hz_value: float, timeslot_s: float) -> float:
    if timeslot_s <= 0:
        raise ValueError("timeslot_s debe ser positivo.")
    return max_doppler_hz_value * timeslot_s


def rms_delay_spread_s(delays_us: np.ndarray, powers_db: np.ndarray) -> float:
    delays_s = np.asarray(delays_us, dtype=float) * 1e-6
    powers_linear = 10 ** (np.asarray(powers_db, dtype=float) / 10.0)
    if delays_s.size == 0 or delays_s.size != powers_linear.size:
        raise ValueError("delays_us y powers_db deben tener la misma longitud y no estar vacíos.")

    weights = powers_linear / powers_linear.sum()
    mean_delay = np.sum(weights * delays_s)
    mean_square_delay = np.sum(weights * delays_s**2)
    variance = max(mean_square_delay - mean_delay**2, 0.0)
    return math.sqrt(variance)


def coherence_bandwidth_hz(rms_delay_spread_value_s: float, correlation_level: float = 0.5) -> float:
    if rms_delay_spread_value_s <= 0:
        return math.inf
    if not 0.0 < correlation_level < 1.0:
        raise ValueError("correlation_level debe estar entre 0 y 1.")

    factor = 5.0 if correlation_level >= 0.5 else 50.0
    return 1.0 / (factor * rms_delay_spread_value_s)


def classify_timeslot_stability(coherence_s: float, timeslot_s: float) -> str:
    """Clasifica la estabilidad del canal durante una ráfaga GSM."""
    ratio = coherence_s / timeslot_s

    if ratio >= 10:
        return "cuasiestatico"
    if ratio >= 3:
        return "estable_con_margen_reducido"
    if ratio >= 1:
        return "estable_pero_critico"
    return "variable_durante_timeslot"


def classify_frequency_selectivity(coherence_bandwidth_value_hz: float, signal_bandwidth_hz: float) -> str:
    if signal_bandwidth_hz <= 0:
        raise ValueError("signal_bandwidth_hz debe ser positivo.")
    if coherence_bandwidth_value_hz >= signal_bandwidth_hz:
        return "plano_predominante"
    if coherence_bandwidth_value_hz >= signal_bandwidth_hz / 4.0:
        return "transicion_plano_selectivo"
    return "selectivo_en_frecuencia"


def _jakes_complex_process(
    time_s: np.ndarray,
    doppler_hz: float,
    sinusoids: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if sinusoids < 8:
        raise ValueError("sinusoids debe ser >= 8.")
    if doppler_hz < 0:
        raise ValueError("doppler_hz no puede ser negativo.")
    if doppler_hz == 0:
        return np.ones_like(time_s, dtype=complex)

    n = np.arange(1, sinusoids + 1, dtype=float)
    arrival_angles = np.pi * n / (sinusoids + 1.0)
    doppler_angular = 2.0 * np.pi * doppler_hz * np.cos(arrival_angles)
    phase_i = rng.uniform(0.0, 2.0 * np.pi, sinusoids)
    phase_q = rng.uniform(0.0, 2.0 * np.pi, sinusoids)

    phase_matrix = np.outer(time_s, doppler_angular)
    i_component = np.sqrt(2.0 / sinusoids) * np.sum(np.cos(phase_matrix + phase_i), axis=1)
    q_component = np.sqrt(2.0 / sinusoids) * np.sum(np.sin(phase_matrix + phase_q), axis=1)
    process = (i_component + 1j * q_component) / np.sqrt(2.0)

    power = np.mean(np.abs(process) ** 2)
    return process / np.sqrt(power)


def simulate_time_variant_channel(
    doppler_hz: float,
    config: GSMConfig = GSMConfig(),
    model: str = "rayleigh",
    k_factor_db: float = 7.0,
    observation_time_s: float = 40e-3,
    samples: int = 4096,
    sinusoids: int = 32,
    seed: int = 7,
    tap_delays_us: np.ndarray | None = None,
    tap_powers_db: np.ndarray | None = None,
) -> pd.DataFrame:
    """Simula un canal temporalmente variante mediante multitrayecto y Jakes.

    El objetivo es acercarse más a un canal radio móvil realista que una simple
    envolvente suavizada aleatoria. Se modelan varias trayectorias con potencias
    desiguales y evolución temporal correlacionada por el Doppler.
    """
    if samples < 256:
        raise ValueError("samples debe ser >= 256.")
    if observation_time_s <= 0:
        raise ValueError("observation_time_s debe ser positivo.")

    delays_us = np.asarray(tap_delays_us if tap_delays_us is not None else TYPICAL_URBAN_DELAYS_US, dtype=float)
    powers_db = np.asarray(tap_powers_db if tap_powers_db is not None else TYPICAL_URBAN_POWERS_DB, dtype=float)
    if delays_us.size != powers_db.size:
        raise ValueError("tap_delays_us y tap_powers_db deben tener la misma longitud.")

    rng = np.random.default_rng(seed)
    time_s = np.linspace(0.0, observation_time_s, samples)
    powers_linear = 10 ** (powers_db / 10.0)
    powers_linear = powers_linear / powers_linear.sum()

    channel = np.zeros_like(time_s, dtype=complex)
    model_lower = model.lower()

    for tap_index, tap_power in enumerate(powers_linear):
        diffuse = np.sqrt(tap_power) * _jakes_complex_process(time_s, doppler_hz, sinusoids, rng)
        static_delay_phase = np.exp(-1j * 2.0 * np.pi * config.carrier_frequency_hz * delays_us[tap_index] * 1e-6)

        if model_lower == "rayleigh":
            tap_response = diffuse * static_delay_phase
        elif model_lower == "rician":
            if tap_index == 0:
                k_linear = 10 ** (k_factor_db / 10.0)
                los_angle = rng.uniform(0.0, 2.0 * np.pi)
                los = np.sqrt(tap_power * (k_linear / (k_linear + 1.0))) * np.exp(
                    1j * (2.0 * np.pi * doppler_hz * time_s * np.cos(los_angle) + los_angle)
                )
                diffuse = diffuse * np.sqrt(1.0 / (k_linear + 1.0))
                tap_response = (los + diffuse) * static_delay_phase
            else:
                tap_response = diffuse * static_delay_phase
        else:
            raise ValueError("model debe ser 'rayleigh' o 'rician'.")

        channel += tap_response

    envelope = np.abs(channel)
    envelope = envelope / envelope.mean()
    instant_power_db = 20.0 * np.log10(np.clip(envelope, 1e-9, None))
    local_slope_db_per_ms = np.gradient(instant_power_db, time_s * 1e3)

    burst_center_s = observation_time_s / 2.0
    burst_start_s = burst_center_s - config.timeslot_duration_s / 2.0
    burst_end_s = burst_center_s + config.timeslot_duration_s / 2.0
    burst_mask = (time_s >= burst_start_s) & (time_s <= burst_end_s)
    burst_time_us = np.full(time_s.shape, np.nan, dtype=float)
    burst_time_us[burst_mask] = (time_s[burst_mask] - burst_start_s) * 1e6

    return pd.DataFrame(
        {
            "time_s": time_s,
            "time_ms": time_s * 1e3,
            "burst_time_us": burst_time_us,
            "envelope_normalized": envelope,
            "instant_power_db": instant_power_db,
            "local_slope_db_per_ms": local_slope_db_per_ms,
            "real": np.real(channel),
            "imag": np.imag(channel),
            "doppler_hz": doppler_hz,
            "model": model_lower,
        }
    )


def simulate_flat_fading(
    doppler_hz: float,
    config: GSMConfig = GSMConfig(),
    model: str = "rayleigh",
    k_factor_db: float = 6.0,
    samples: int = 512,
    seed: int = 7,
    observation_time_s: float | None = None,
    sinusoids: int = 32,
) -> pd.DataFrame:
    """Mantiene compatibilidad y devuelve la ventana completa con una ráfaga marcada."""
    observation_time_s = observation_time_s if observation_time_s is not None else max(config.timeslot_duration_s * 40.0, 12e-3)
    adjusted_samples = max(samples * 8, 2048)
    return simulate_time_variant_channel(
        doppler_hz=doppler_hz,
        config=config,
        model=model,
        k_factor_db=k_factor_db,
        observation_time_s=observation_time_s,
        samples=adjusted_samples,
        sinusoids=sinusoids,
        seed=seed,
    )


def fading_metrics(df: pd.DataFrame) -> dict:
    """Calcula métricas simples de variación de envolvente durante la ráfaga."""
    env = df["envelope_normalized"].to_numpy()
    if "time_s" in df.columns:
        time_axis_s = df["time_s"].to_numpy(dtype=float)
    elif "time_us" in df.columns:
        time_axis_s = df["time_us"].to_numpy(dtype=float) * 1e-6
    else:
        time_axis_s = np.linspace(0.0, 1.0, len(env))

    if len(time_axis_s) > 1:
        dt_s = float(np.median(np.diff(time_axis_s)))
        total_time_s = max(float(time_axis_s[-1] - time_axis_s[0]), dt_s)
    else:
        dt_s = 0.0
        total_time_s = 1.0

    power_db = 20.0 * np.log10(np.clip(env, 1e-9, None))
    threshold_db = float(df["fade_threshold_db"].iloc[0]) if "fade_threshold_db" in df.columns else -10.0
    below_threshold = power_db <= threshold_db
    fade_starts = np.count_nonzero(~below_threshold[:-1] & below_threshold[1:]) if len(env) > 1 else 0

    fade_durations_ms = []
    if dt_s > 0:
        start_idx = None
        for idx, in_fade in enumerate(below_threshold):
            if in_fade and start_idx is None:
                start_idx = idx
            if not in_fade and start_idx is not None:
                fade_durations_ms.append((idx - start_idx) * dt_s * 1e3)
                start_idx = None
        if start_idx is not None:
            fade_durations_ms.append((len(below_threshold) - start_idx) * dt_s * 1e3)

    return {
        "model": df["model"].iloc[0],
        "doppler_hz": float(df["doppler_hz"].iloc[0]),
        "envelope_min": float(env.min()),
        "envelope_max": float(env.max()),
        "envelope_std": float(env.std()),
        "relative_peak_to_peak": float(env.max() - env.min()),
        "fade_threshold_db": threshold_db,
        "fade_lcr_per_s": float(fade_starts / total_time_s),
        "avg_fade_duration_ms": float(np.mean(fade_durations_ms)) if fade_durations_ms else 0.0,
        "max_fade_duration_ms": float(np.max(fade_durations_ms)) if fade_durations_ms else 0.0,
        "outage_probability_pct": float(np.mean(below_threshold) * 100.0),
        "rms_slope_db_per_ms": float(np.sqrt(np.mean(np.gradient(power_db, time_axis_s * 1e3) ** 2))) if len(env) > 2 else 0.0,
    }
