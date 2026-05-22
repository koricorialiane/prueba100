import math
import pandas as pd

from .config import AnalyzerConfig


def analyzer_noise_floor_dbm(rbw_hz: float, noise_figure_db: float = 6.0) -> float:
    """Calcula el suelo de ruido integrado en el RBW del analizador."""
    if rbw_hz <= 0:
        raise ValueError("RBW debe ser positivo.")
    return -174.0 + 10.0 * math.log10(rbw_hz) + noise_figure_db


def displayed_average_noise_level_dbm(
    rbw_hz: float,
    noise_figure_db: float = 6.0,
    enbw_factor: float = 1.05,
    detector_bias_db: float = 2.51,
) -> float:
    if enbw_factor <= 0:
        raise ValueError("enbw_factor debe ser positivo.")
    enbw_corrected_noise = analyzer_noise_floor_dbm(rbw_hz * enbw_factor, noise_figure_db)
    return enbw_corrected_noise - detector_bias_db


def estimated_sweep_time_ms(span_hz: float, rbw_hz: float, shape_factor: float = 2.5) -> float:
    if span_hz <= 0 or rbw_hz <= 0:
        raise ValueError("span_hz y rbw_hz deben ser positivos.")
    return shape_factor * span_hz / (rbw_hz**2) * 1e3


def rbw_noise_table(config: AnalyzerConfig = AnalyzerConfig()) -> pd.DataFrame:
    rows = []
    reference = None

    for rbw in config.rbw_values_hz:
        noise = analyzer_noise_floor_dbm(rbw, config.noise_figure_db)
        displayed_noise = displayed_average_noise_level_dbm(
            rbw_hz=rbw,
            noise_figure_db=config.noise_figure_db,
            enbw_factor=config.enbw_factor,
            detector_bias_db=config.detector_bias_db,
        )
        sweep_time_ms = estimated_sweep_time_ms(config.span_hz, rbw)

        if reference is None:
            reference = noise

        rows.append(
            {
                "rbw_hz": rbw,
                "rbw_khz": rbw / 1e3,
                "noise_figure_db": config.noise_figure_db,
                "noise_floor_dbm": noise,
                "displayed_average_noise_dbm": displayed_noise,
                "enbw_factor": config.enbw_factor,
                "detector_bias_db": config.detector_bias_db,
                "delta_vs_100khz_db": noise - reference,
                "estimated_sweep_time_ms": sweep_time_ms,
                "visibility_margin_db": config.weak_signal_reference_dbm - displayed_noise,
                "measurement_interpretation": (
                    "RBW ancho: barrido rápido, menor sensibilidad de señales débiles."
                    if rbw >= 100e3
                    else "RBW estrecho: mejor visibilidad de señales débiles, barrido más lento."
                ),
            }
        )

    return pd.DataFrame(rows)


def red_compliance_checklist() -> pd.DataFrame:
    """Checklist teórico de conformidad RED para el informe del alumno."""
    rows = [
        {
            "area": "Uso eficiente del espectro",
            "evidence": "planificación ARFCN, clúster N=4, distancia de reutilización y control de co-canal",
            "student_task": "Justificar que la asignación espectral reduce interferencias y evita solapamientos.",
        },
        {
            "area": "Emisiones no deseadas",
            "evidence": "medida con analizador de espectro y ajuste de RBW",
            "student_task": "Explicar cómo se distinguirían señales débiles de ruido instrumental.",
        },
        {
            "area": "Estabilidad de canal",
            "evidence": "Doppler, tiempo de coherencia y comparación con timeslot GSM",
            "student_task": "Defender si el enlace es viable durante la ráfaga en movilidad.",
        },
        {
            "area": "Documentación técnica",
            "evidence": "tablas, gráficas, hipótesis y trazabilidad de cálculos",
            "student_task": "Incluir ecuaciones, unidades y discusión ingenieril.",
        },
    ]
    return pd.DataFrame(rows)
