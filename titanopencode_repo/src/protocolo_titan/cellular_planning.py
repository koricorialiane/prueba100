import math
from typing import Dict, List
import pandas as pd

from .config import CampScenario, GSMConfig


def carriers_per_cell(total_carriers: int, cluster_size: int) -> int:
    if total_carriers <= 0 or cluster_size <= 0:
        raise ValueError("total_carriers y cluster_size deben ser positivos.")
    if total_carriers % cluster_size != 0:
        raise ValueError("El reparto exacto exige que total_carriers sea divisible por cluster_size.")
    return total_carriers // cluster_size


def reuse_ratio(cluster_size: int) -> float:
    if cluster_size <= 0:
        raise ValueError("cluster_size debe ser positivo.")
    return math.sqrt(3 * cluster_size)


def reuse_distance_km(cell_radius_km: float, cluster_size: int) -> float:
    if cell_radius_km <= 0:
        raise ValueError("cell_radius_km debe ser positivo.")
    return cell_radius_km * reuse_ratio(cluster_size)


def arfcn_to_uplink_mhz(arfcn: int) -> float:
    if not 1 <= arfcn <= 124:
        raise ValueError("arfcn debe estar en el rango GSM-900 (1-124).")
    return 890.0 + 0.2 * arfcn


def arfcn_to_downlink_mhz(arfcn: int) -> float:
    return arfcn_to_uplink_mhz(arfcn) + 45.0


def estimate_cir_db(
    cluster_size: int,
    path_loss_exponent: float,
    cochannel_tier_size: int = 6,
) -> float:
    if path_loss_exponent <= 0:
        raise ValueError("path_loss_exponent debe ser positivo.")
    if cochannel_tier_size <= 0:
        raise ValueError("cochannel_tier_size debe ser positivo.")

    cir_linear = (reuse_ratio(cluster_size) ** path_loss_exponent) / cochannel_tier_size
    return 10.0 * math.log10(cir_linear)


def traffic_timeslots_per_cell(carriers_in_cell: int, bcch_timeslots_reserved: int = 1) -> int:
    if carriers_in_cell <= 0:
        raise ValueError("carriers_in_cell debe ser positivo.")
    if bcch_timeslots_reserved < 0:
        raise ValueError("bcch_timeslots_reserved no puede ser negativo.")
    return max(carriers_in_cell * 8 - bcch_timeslots_reserved, 0)


def assign_arfcns(
    scenario: CampScenario = CampScenario(),
) -> Dict[str, List[int]]:
    """Asigna ARFCNs consecutivos a las celdas del clúster.

    Para docencia se usa una asignación consecutiva. En ingeniería real se
    contrastaría con drive tests, coordinación espectral y medidas de campo.
    """
    if scenario.cluster_size > 26:
        raise ValueError("cluster_size debe ser <= 26 para etiquetar celdas de A a Z.")
    if scenario.first_arfcn <= 0:
        raise ValueError("first_arfcn debe ser positivo.")
    if scenario.first_arfcn + scenario.total_carriers - 1 > 124:
        raise ValueError("El rango ARFCN debe permanecer dentro de GSM-900 (1-124).")

    n = carriers_per_cell(scenario.total_carriers, scenario.cluster_size)
    assignments: Dict[str, List[int]] = {}

    current = scenario.first_arfcn
    for idx in range(scenario.cluster_size):
        cell = chr(ord("A") + idx)
        assignments[cell] = list(range(current, current + n))
        current += n

    return assignments


def channel_logical_mapping(
    scenario: CampScenario = CampScenario(),
    config: GSMConfig = GSMConfig(),
) -> pd.DataFrame:
    """Propone una asignación didáctica BCCH/TCH por celda.

    - El primer ARFCN de cada celda se reserva como portadora BCCH.
    - El resto de portadoras se asignan preferentemente a TCH.
    - Se marca BCCH como potencia estable y sin frequency hopping.
    """
    assignments = assign_arfcns(scenario)
    rows = []
    traffic_slots = traffic_timeslots_per_cell(
        carriers_per_cell(scenario.total_carriers, scenario.cluster_size),
        bcch_timeslots_reserved=scenario.bcch_timeslots_reserved,
    )

    for cell, arfcns in assignments.items():
        for idx, arfcn in enumerate(arfcns):
            is_bcch = idx == 0
            rows.append(
                {
                    "cell": cell,
                    "arfcn": arfcn,
                    "uplink_mhz": arfcn_to_uplink_mhz(arfcn),
                    "downlink_mhz": arfcn_to_downlink_mhz(arfcn),
                    "carrier_role": "BCCH/CCCH control" if is_bcch else "TCH traffic",
                    "frequency_hopping_recommended": False if is_bcch else True,
                    "power_policy": "fixed/stable" if is_bcch else "adaptive if supported",
                    "available_timeslots": config.timeslots_per_frame,
                    "traffic_timeslots_available": config.timeslots_per_frame - 1 if is_bcch else config.timeslots_per_frame,
                    "control_timeslots_reserved": 1 if is_bcch else 0,
                    "cell_total_traffic_timeslots": traffic_slots,
                    "estimated_user_bitrate_kbps": traffic_slots * scenario.tch_user_bitrate_kbps,
                    "engineering_note": (
                        "BCCH debe ser detectable y estable para camping, sincronización y control."
                        if is_bcch
                        else "TCH transporta tráfico; puede beneficiarse de hopping y control de potencia."
                    ),
                }
            )

    return pd.DataFrame(rows)


def frequency_planning_table(
    scenario: CampScenario = CampScenario(),
) -> pd.DataFrame:
    assignments = assign_arfcns(scenario)
    d = reuse_distance_km(scenario.cell_radius_km, scenario.cluster_size)
    d_over_r = reuse_ratio(scenario.cluster_size)
    per_cell = carriers_per_cell(scenario.total_carriers, scenario.cluster_size)
    cir_db = estimate_cir_db(scenario.cluster_size, scenario.path_loss_exponent, scenario.cochannel_tier_size)
    traffic_slots = traffic_timeslots_per_cell(per_cell, scenario.bcch_timeslots_reserved)
    voice_circuits = traffic_slots
    bitrate_kbps = traffic_slots * scenario.tch_user_bitrate_kbps

    rows = []
    for cell, arfcns in assignments.items():
        rows.append(
            {
                "scenario": "B_campamento_base",
                "cell": cell,
                "cell_radius_km": scenario.cell_radius_km,
                "cluster_size_N": scenario.cluster_size,
                "total_carriers": scenario.total_carriers,
                "carriers_per_cell": per_cell,
                "arfcn_range": f"{arfcns[0]}-{arfcns[-1]}",
                "arfcn_list": ", ".join(map(str, arfcns)),
                "uplink_start_mhz": arfcn_to_uplink_mhz(arfcns[0]),
                "uplink_end_mhz": arfcn_to_uplink_mhz(arfcns[-1]),
                "downlink_start_mhz": arfcn_to_downlink_mhz(arfcns[0]),
                "downlink_end_mhz": arfcn_to_downlink_mhz(arfcns[-1]),
                "reuse_ratio_D_over_R": d_over_r,
                "reuse_distance_km": d,
                "path_loss_exponent": scenario.path_loss_exponent,
                "estimated_cir_db": cir_db,
                "cir_margin_db": cir_db - scenario.target_cir_db,
                "traffic_timeslots_per_cell": traffic_slots,
                "gross_voice_circuits_per_cell": voice_circuits,
                "estimated_user_bitrate_kbps": bitrate_kbps,
            }
        )

    return pd.DataFrame(rows)
