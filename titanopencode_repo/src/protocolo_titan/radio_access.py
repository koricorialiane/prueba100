from dataclasses import asdict
import pandas as pd

from .config import GSMConfig


def gsm_access_summary(config: GSMConfig = GSMConfig()) -> pd.DataFrame:
    """Resume los parámetros FDMA/TDMA básicos de GSM usados en la práctica."""
    frame_duration_s = config.timeslot_duration_s * config.timeslots_per_frame
    gross_channel_structure = {
        "carrier_frequency_mhz": config.carrier_frequency_hz / 1e6,
        "fdma_carrier_bandwidth_khz": config.channel_bandwidth_hz / 1e3,
        "tdma_timeslots_per_frame": config.timeslots_per_frame,
        "timeslot_duration_us": config.timeslot_duration_s * 1e6,
        "frame_duration_ms": frame_duration_s * 1e3,
    }
    return pd.DataFrame([gross_channel_structure])


def theoretical_voice_circuits_per_carrier(config: GSMConfig = GSMConfig()) -> int:
    """Devuelve el número ideal de timeslots por portadora.

    En GSM una portadora tiene 8 timeslots. En una red real algunos se reservan
    para control, señalización, BCCH/CCCH/SDCCH, etc.
    """
    return config.timeslots_per_frame
