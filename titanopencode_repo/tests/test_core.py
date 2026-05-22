import math
from pathlib import Path
import zipfile

from docx import Document
import pandas as pd
import pytest

from protocolo_titan.config import CampScenario
from protocolo_titan.propagation import kmh_to_ms, max_doppler_hz, coherence_time_s
from protocolo_titan.cellular_planning import assign_arfcns, carriers_per_cell, reuse_distance_km, reuse_ratio
from protocolo_titan.instrumentation import analyzer_noise_floor_dbm
from protocolo_titan.report import write_calculation_annex, write_defense_brief, write_docx_document, write_html_document, write_markdown_report, write_pdf_document
from protocolo_titan.scenario_a import analyze_convoy_fading, trace_key
from protocolo_titan.site_builder import write_static_site


def test_speed_conversion():
    assert math.isclose(kmh_to_ms(50), 13.8888888889)


def test_doppler_50_kmh_900mhz():
    v = kmh_to_ms(50)
    assert math.isclose(max_doppler_hz(v, 900e6), 41.6666666667)


def test_coherence_250_kmh():
    v = kmh_to_ms(250)
    fd = max_doppler_hz(v, 900e6)
    assert math.isclose(coherence_time_s(fd) * 1e3, 2.0304, rel_tol=1e-3)


def test_carriers_per_cell():
    assert carriers_per_cell(24, 4) == 6


def test_reuse_distance():
    assert math.isclose(reuse_ratio(4), math.sqrt(12))
    assert math.isclose(reuse_distance_km(1.5, 4), 5.1961524, rel_tol=1e-6)


def test_noise_floor():
    assert math.isclose(analyzer_noise_floor_dbm(100e3, 6), -118.0)
    assert math.isclose(analyzer_noise_floor_dbm(10e3, 6), -128.0)
    assert math.isclose(analyzer_noise_floor_dbm(1e3, 6), -138.0)


def test_trace_keys_follow_selected_speeds():
    fading_summary, traces = analyze_convoy_fading(models=("rician",), scenario=type("Scenario", (), {"cell_radius_km": 3.0, "speeds_kmh": (60.0, 125.5)})())
    assert trace_key("rician", 60.0) in traces
    assert trace_key("rician", 125.5) in traces
    assert sorted(fading_summary["speed_kmh"].tolist()) == [60.0, 125.5]


def test_report_writes_markdown_without_tabulate(tmp_path: Path):
    mobility = pd.DataFrame([
        {
            "scenario": "A_convoy_alta_velocidad",
            "cell_radius_km": 3.0,
            "speed_kmh": 50.0,
            "speed_ms": 13.8889,
            "carrier_frequency_mhz": 900.0,
            "max_doppler_hz": 41.6667,
            "coherence_time_ms": 10.152,
            "gsm_timeslot_ms": 0.577,
            "coherence_to_timeslot_ratio": 17.5945,
            "stability_class": "cuasiestatico",
        },
    ])
    fading_metrics = pd.DataFrame([
        {
            "model": "rayleigh",
            "doppler_hz": 41.6667,
            "envelope_min": 0.1,
            "envelope_max": 1.2,
            "envelope_std": 0.2,
            "relative_peak_to_peak": 1.1,
            "speed_kmh": 50.0,
            "coherence_time_ms": 10.152,
            "stability_class": "cuasiestatico",
        }
    ])
    frequency_planning = pd.DataFrame([
        {
            "scenario": "B_campamento_base",
            "cell": "A",
            "cell_radius_km": 1.5,
            "cluster_size_N": 4,
            "total_carriers": 24,
            "carriers_per_cell": 6,
            "arfcn_range": "1-6",
            "arfcn_list": "1, 2, 3, 4, 5, 6",
            "reuse_ratio_D_over_R": 3.4641,
            "reuse_distance_km": 5.1962,
        }
    ])
    logical_channels = pd.DataFrame([
        {"cell": "A", "arfcn": 1, "carrier_role": "BCCH/CCCH control", "frequency_hopping_recommended": False, "power_policy": "fixed/stable", "available_timeslots": 8, "engineering_note": "BCCH estable."},
        {"cell": "A", "arfcn": 2, "carrier_role": "TCH traffic", "frequency_hopping_recommended": True, "power_policy": "adaptive if supported", "available_timeslots": 8, "engineering_note": "TCH para tráfico."},
    ])
    rbw_noise = pd.DataFrame([
        {"rbw_hz": 100000.0, "rbw_khz": 100.0, "noise_figure_db": 6.0, "noise_floor_dbm": -118.0, "delta_vs_100khz_db": 0.0, "measurement_interpretation": "RBW ancho."},
        {"rbw_hz": 10000.0, "rbw_khz": 10.0, "noise_figure_db": 6.0, "noise_floor_dbm": -128.0, "delta_vs_100khz_db": -10.0, "measurement_interpretation": "RBW estrecho."},
    ])
    red_checklist = pd.DataFrame([
        {"area": "Uso eficiente del espectro", "evidence": "Plan ARFCN", "student_task": "Justificar protección co-canal."}
    ])
    output_path = tmp_path / "report.md"
    annex_path = tmp_path / "annex.md"
    defense_path = tmp_path / "defense.md"

    write_markdown_report(
        output_path,
        mobility=mobility,
        fading_metrics=fading_metrics,
        frequency_planning=frequency_planning,
        logical_channels=logical_channels,
        rbw_noise=rbw_noise,
        red_checklist=red_checklist,
    )
    write_calculation_annex(
        annex_path,
        mobility=mobility,
        fading_metrics=fading_metrics,
        frequency_planning=frequency_planning,
        logical_channels=logical_channels,
        rbw_noise=rbw_noise,
        red_checklist=red_checklist,
    )
    write_defense_brief(
        defense_path,
        mobility=mobility,
        frequency_planning=frequency_planning,
        rbw_noise=rbw_noise,
    )

    content = output_path.read_text(encoding="utf-8")
    annex_content = annex_path.read_text(encoding="utf-8")
    defense_content = defense_path.read_text(encoding="utf-8")
    write_html_document(tmp_path / "report.html", "Informe", content)
    write_pdf_document(tmp_path / "report.pdf", "Informe", content, tmp_path)
    write_docx_document(tmp_path / "report.docx", "Informe", content, tmp_path)
    html_content = (tmp_path / "report.html").read_text(encoding="utf-8")
    pdf_bytes = (tmp_path / "report.pdf").read_bytes()
    docx_document = Document(tmp_path / "report.docx")
    docx_text = "\n".join(paragraph.text for paragraph in docx_document.paragraphs)
    with zipfile.ZipFile(tmp_path / "report.docx") as docx_file:
        docx_entries = set(docx_file.namelist())
    assert "# Protocolo Titán — Informe técnico docente" in content
    assert "## 1. Introducción" in content
    assert "## 2. Estado del arte" in content
    assert "## 5. Pruebas, cálculos y simulaciones" in content
    assert "## 9. Referencias" in content
    assert "577" in content
    assert "Anexo de cálculos y trazabilidad" in annex_content
    assert "Guion breve de defensa" in defense_content
    assert "<html lang=\"es\">" in html_content
    assert pdf_bytes.startswith(b"%PDF")
    assert "[Content_Types].xml" in docx_entries
    assert "PLANTILLA DE ENTREGA ACADÉMICA" in docx_text
    assert "Datos de entrega y revisión final" in docx_text


def test_invalid_cluster_size_raises():
    with pytest.raises(ValueError, match="A a Z"):
        assign_arfcns(CampScenario(cluster_size=27, total_carriers=54))


def test_static_site_is_generated_with_docs_assets(tmp_path: Path):
    mobility = pd.DataFrame([
        {
            "scenario": "A_convoy_alta_velocidad",
            "cell_radius_km": 3.0,
            "speed_kmh": 50.0,
            "speed_ms": 13.8889,
            "carrier_frequency_mhz": 900.0,
            "max_doppler_hz": 41.6667,
            "coherence_time_ms": 10.152,
            "gsm_timeslot_ms": 0.577,
            "coherence_to_timeslot_ratio": 17.5945,
            "stability_class": "cuasiestatico",
        },
        {
            "scenario": "A_convoy_alta_velocidad",
            "cell_radius_km": 3.0,
            "speed_kmh": 250.0,
            "speed_ms": 69.4444,
            "carrier_frequency_mhz": 900.0,
            "max_doppler_hz": 208.3333,
            "coherence_time_ms": 2.0304,
            "gsm_timeslot_ms": 0.577,
            "coherence_to_timeslot_ratio": 3.5189,
            "stability_class": "estable_con_margen_reducido",
        },
    ])
    fading_metrics = pd.DataFrame([
        {
            "model": "rayleigh",
            "doppler_hz": 41.6667,
            "envelope_min": 0.1,
            "envelope_max": 1.2,
            "envelope_std": 0.2,
            "relative_peak_to_peak": 1.1,
            "speed_kmh": 50.0,
            "coherence_time_ms": 10.152,
            "stability_class": "cuasiestatico",
        },
        {
            "model": "rician",
            "doppler_hz": 208.3333,
            "envelope_min": 0.4,
            "envelope_max": 1.3,
            "envelope_std": 0.15,
            "relative_peak_to_peak": 0.9,
            "speed_kmh": 250.0,
            "coherence_time_ms": 2.0304,
            "stability_class": "estable_con_margen_reducido",
        },
    ])
    frequency_planning = pd.DataFrame([
        {
            "scenario": "B_campamento_base",
            "cell": "A",
            "cell_radius_km": 1.5,
            "cluster_size_N": 4,
            "total_carriers": 24,
            "carriers_per_cell": 6,
            "arfcn_range": "1-6",
            "arfcn_list": "1, 2, 3, 4, 5, 6",
            "reuse_ratio_D_over_R": 3.4641,
            "reuse_distance_km": 5.1962,
        },
        {
            "scenario": "B_campamento_base",
            "cell": "B",
            "cell_radius_km": 1.5,
            "cluster_size_N": 4,
            "total_carriers": 24,
            "carriers_per_cell": 6,
            "arfcn_range": "7-12",
            "arfcn_list": "7, 8, 9, 10, 11, 12",
            "reuse_ratio_D_over_R": 3.4641,
            "reuse_distance_km": 5.1962,
        },
    ])
    logical_channels = pd.DataFrame([
        {"cell": "A", "arfcn": 1, "carrier_role": "BCCH/CCCH control", "frequency_hopping_recommended": False, "power_policy": "fixed/stable", "available_timeslots": 8, "engineering_note": "BCCH estable."},
        {"cell": "A", "arfcn": 2, "carrier_role": "TCH traffic", "frequency_hopping_recommended": True, "power_policy": "adaptive if supported", "available_timeslots": 8, "engineering_note": "TCH para tráfico."},
        {"cell": "B", "arfcn": 7, "carrier_role": "BCCH/CCCH control", "frequency_hopping_recommended": False, "power_policy": "fixed/stable", "available_timeslots": 8, "engineering_note": "BCCH estable."},
    ])
    rbw_noise = pd.DataFrame([
        {"rbw_hz": 100000.0, "rbw_khz": 100.0, "noise_figure_db": 6.0, "noise_floor_dbm": -118.0, "delta_vs_100khz_db": 0.0, "measurement_interpretation": "RBW ancho."},
        {"rbw_hz": 10000.0, "rbw_khz": 10.0, "noise_figure_db": 6.0, "noise_floor_dbm": -128.0, "delta_vs_100khz_db": -10.0, "measurement_interpretation": "RBW estrecho."},
        {"rbw_hz": 1000.0, "rbw_khz": 1.0, "noise_figure_db": 6.0, "noise_floor_dbm": -138.0, "delta_vs_100khz_db": -20.0, "measurement_interpretation": "RBW muy estrecho."},
    ])
    red_checklist = pd.DataFrame([
        {"area": "Uso eficiente del espectro", "evidence": "Plan ARFCN", "student_task": "Justificar protección co-canal."}
    ])

    outputs = tmp_path / "outputs"
    figures = outputs / "figures"
    figures.mkdir(parents=True)
    for name in [
        "escenario_a_doppler.png",
        "escenario_a_coherencia_vs_timeslot.png",
        f"traza_{trace_key('rayleigh', 250.0)}.png",
        f"traza_{trace_key('rician', 250.0)}.png",
        "escenario_b_cluster_map.png",
        "escenario_b_distribucion_portadoras.png",
        "escenario_b_reutilizacion.png",
        "escenario_b_spectrum.png",
        "certificacion_rbw_ruido.png",
    ]:
        (figures / name).write_bytes(b"fake-png")

    for name in [
        "informe_resultados.html",
        "informe_resultados.pdf",
        "informe_resultados.docx",
        "anexo_calculos.html",
        "guion_defensa.html",
        "certificacion_rbw.csv",
    ]:
        (outputs / name).write_text("contenido", encoding="utf-8")

    write_static_site(
        project_root=tmp_path,
        outputs_root=outputs,
        mobility=mobility,
        fading_metrics=fading_metrics,
        frequency_planning=frequency_planning,
        logical_channels=logical_channels,
        rbw_noise=rbw_noise,
        red_checklist=red_checklist,
    )

    dashboard_path = tmp_path / "docs" / "index.html"
    root_index_path = tmp_path / "index.html"
    dashboard = dashboard_path.read_text(encoding="utf-8")
    root_index = root_index_path.read_text(encoding="utf-8")

    assert dashboard_path.exists()
    assert root_index_path.exists()
    assert (tmp_path / "docs" / "assets" / "figures" / "escenario_a_doppler.png").exists()
    assert (tmp_path / "docs" / "files" / "informe_resultados.html").exists()
    assert (tmp_path / "docs" / ".nojekyll").exists()
    assert "Dashboard tecnico listo para abrir y publicar en GitHub Pages" in dashboard
    assert "Escenario A · Convoy de alta velocidad" in dashboard
    assert "assets/figures/escenario_a_doppler.png" in dashboard
    assert "docs/index.html" in root_index
