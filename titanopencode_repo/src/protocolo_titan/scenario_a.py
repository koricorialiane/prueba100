import pandas as pd

from .config import GSMConfig, ConvoyScenario
from .propagation import (
    kmh_to_ms,
    max_doppler_hz,
    doppler_spread_hz,
    coherence_time_s,
    coherence_bandwidth_hz,
    rms_delay_spread_s,
    normalized_doppler,
    classify_timeslot_stability,
    classify_frequency_selectivity,
    simulate_flat_fading,
    fading_metrics,
    TYPICAL_URBAN_DELAYS_US,
    TYPICAL_URBAN_POWERS_DB,
)


def trace_key(model: str, speed_kmh: float) -> str:
    speed_token = format(float(speed_kmh), "g").replace("-", "m").replace(".", "_")
    return f"{model.lower()}_{speed_token}_kmh"


def analyze_convoy_mobility(
    scenario: ConvoyScenario = ConvoyScenario(),
    config: GSMConfig = GSMConfig(),
) -> pd.DataFrame:
    """Calcula Doppler, coherencia y estabilidad del canal para el convoy."""
    rows = []
    default_scenario = ConvoyScenario()
    cell_radius_km = getattr(scenario, "cell_radius_km", default_scenario.cell_radius_km)
    rms_delay_spread_us = getattr(scenario, "rms_delay_spread_us", default_scenario.rms_delay_spread_us)
    delay_spread_s = max(rms_delay_spread_us * 1e-6, rms_delay_spread_s(TYPICAL_URBAN_DELAYS_US, TYPICAL_URBAN_POWERS_DB))
    coherence_bw_hz = coherence_bandwidth_hz(delay_spread_s)
    selectivity = classify_frequency_selectivity(coherence_bw_hz, config.channel_bandwidth_hz)

    for speed_kmh in scenario.speeds_kmh:
        speed_ms = kmh_to_ms(speed_kmh)
        fd = max_doppler_hz(speed_ms, config.carrier_frequency_hz, config.speed_of_light_ms)
        tc = coherence_time_s(fd)
        doppler_span = doppler_spread_hz(fd)
        ratio = tc / config.timeslot_duration_s
        norm_doppler = normalized_doppler(fd, config.timeslot_duration_s)
        stability = classify_timeslot_stability(tc, config.timeslot_duration_s)

        rows.append(
            {
                "scenario": "A_convoy_alta_velocidad",
                "cell_radius_km": cell_radius_km,
                "speed_kmh": speed_kmh,
                "speed_ms": speed_ms,
                "carrier_frequency_mhz": config.carrier_frequency_hz / 1e6,
                "max_doppler_hz": fd,
                "doppler_spread_hz": doppler_span,
                "coherence_time_ms": tc * 1e3,
                "gsm_timeslot_ms": config.timeslot_duration_s * 1e3,
                "coherence_to_timeslot_ratio": ratio,
                "normalized_doppler": norm_doppler,
                "rms_delay_spread_us": rms_delay_spread_us,
                "coherence_bandwidth_khz": coherence_bw_hz / 1e3,
                "channel_selectivity": selectivity,
                "phase_rotation_deg_over_timeslot": 360.0 * fd * config.timeslot_duration_s,
                "stability_class": stability,
            }
        )

    return pd.DataFrame(rows)


def analyze_convoy_fading(
    scenario: ConvoyScenario = ConvoyScenario(),
    config: GSMConfig = GSMConfig(),
    models: tuple[str, ...] = ("rayleigh", "rician"),
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Simula Rayleigh/Rician para cada velocidad y resume métricas."""
    mobility = analyze_convoy_mobility(scenario, config)
    metrics_rows = []
    traces = {}
    default_scenario = ConvoyScenario()
    analysis_window_ms = getattr(scenario, "analysis_window_ms", default_scenario.analysis_window_ms)
    jakes_sinusoids = getattr(scenario, "jakes_sinusoids", default_scenario.jakes_sinusoids)
    rician_k_factor_db = getattr(scenario, "rician_k_factor_db", default_scenario.rician_k_factor_db)
    fade_threshold_db = getattr(scenario, "fade_threshold_db", default_scenario.fade_threshold_db)

    for _, row in mobility.iterrows():
        for model in models:
            trace = simulate_flat_fading(
                doppler_hz=float(row["max_doppler_hz"]),
                config=config,
                model=model,
                k_factor_db=rician_k_factor_db,
                samples=max(2048, jakes_sinusoids * 96),
                seed=int(row["speed_kmh"]) + (0 if model == "rayleigh" else 1000),
                observation_time_s=analysis_window_ms * 1e-3,
                sinusoids=jakes_sinusoids,
            )
            trace["analysis_window_ms"] = analysis_window_ms
            trace["fade_threshold_db"] = fade_threshold_db
            key = trace_key(model, float(row["speed_kmh"]))
            traces[key] = trace

            m = fading_metrics(trace)
            m.update(
                {
                    "speed_kmh": row["speed_kmh"],
                    "coherence_time_ms": row["coherence_time_ms"],
                    "coherence_bandwidth_khz": row["coherence_bandwidth_khz"],
                    "doppler_spread_hz": row["doppler_spread_hz"],
                    "normalized_doppler": row["normalized_doppler"],
                    "rms_delay_spread_us": row["rms_delay_spread_us"],
                    "channel_selectivity": row["channel_selectivity"],
                    "analysis_window_ms": analysis_window_ms,
                    "fade_threshold_db": fade_threshold_db,
                    "stability_class": row["stability_class"],
                }
            )
            metrics_rows.append(m)

    return pd.DataFrame(metrics_rows), traces
