from __future__ import annotations

import shutil
from datetime import datetime
from html import escape as html_escape
from pathlib import Path

import pandas as pd

from .scenario_a import trace_key


def _format_number(value: float, digits: int = 2) -> str:
    if digits == 0:
        return str(int(round(value)))
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _format_cell(value: object) -> str:
    if pd.isna(value):
        return "-"
    if isinstance(value, bool):
        return "Si" if value else "No"
    if isinstance(value, float):
        return _format_number(value, 3)
    return str(value).replace("_", " ")


def _select_and_rename_columns(df: pd.DataFrame, columns: list[tuple[str, str]]) -> pd.DataFrame:
    selected = [(source, target) for source, target in columns if source in df.columns]
    if not selected:
        return df.copy()
    return df[[source for source, _ in selected]].rename(columns={source: target for source, target in selected})


def _render_metric(label: str, value: str, caption: str) -> str:
    return f"""
    <article class="metric-card">
      <span class="metric-label">{html_escape(label)}</span>
      <strong class="metric-value">{html_escape(value)}</strong>
      <p class="metric-caption">{html_escape(caption)}</p>
    </article>
    """


def _render_kpi_strip(items: list[tuple[str, str]]) -> str:
    chips = []
    for label, value in items:
        chips.append(
            f'<div class="kpi-chip"><span>{html_escape(label)}</span><strong>{html_escape(value)}</strong></div>'
        )
    return "\n".join(chips)


def _render_bullet_list(items: list[str]) -> str:
    bullets = "".join(f"<li>{html_escape(item)}</li>" for item in items if item)
    return f'<ul class="insight-list">{bullets}</ul>'


def _render_table(df: pd.DataFrame, title: str, subtitle: str) -> str:
    headers = "".join(f"<th>{html_escape(str(column))}</th>" for column in df.columns)
    rows = []
    for row in df.itertuples(index=False, name=None):
        cells = "".join(f"<td>{html_escape(_format_cell(value))}</td>" for value in row)
        rows.append(f"<tr>{cells}</tr>")

    return f"""
    <article class="table-card">
      <div class="section-heading">
        <h3>{html_escape(title)}</h3>
        <p>{html_escape(subtitle)}</p>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>{headers}</tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>
    </article>
    """


def _render_figure_card(image_path: str, title: str, subtitle: str) -> str:
    return f"""
    <article class="figure-card">
      <div class="section-heading compact">
        <h3>{html_escape(title)}</h3>
        <p>{html_escape(subtitle)}</p>
      </div>
      <img src="{html_escape(image_path)}" alt="{html_escape(title)}" loading="lazy">
    </article>
    """


def _render_download_card(href: str, label: str, file_type: str, description: str) -> str:
    return f"""
    <a class="download-card" href="{html_escape(href)}">
      <span class="download-type">{html_escape(file_type)}</span>
      <strong>{html_escape(label)}</strong>
      <p>{html_escape(description)}</p>
      <span class="download-link">Abrir archivo</span>
    </a>
    """


def _copy_output_assets(outputs_root: Path, site_root: Path) -> None:
    figures_src = outputs_root / "figures"
    figures_dst = site_root / "assets" / "figures"
    files_dst = site_root / "files"
    figures_dst.mkdir(parents=True, exist_ok=True)
    files_dst.mkdir(parents=True, exist_ok=True)

    if figures_src.exists():
        for figure_path in figures_src.glob("*.png"):
            shutil.copy2(figure_path, figures_dst / figure_path.name)

    for pattern in ("*.html", "*.pdf", "*.docx", "*.md", "*.csv"):
        for file_path in outputs_root.glob(pattern):
            shutil.copy2(file_path, files_dst / file_path.name)

    (site_root / ".nojekyll").write_text("", encoding="utf-8")


def build_root_redirect_html() -> str:
    return """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=docs/index.html">
  <title>Protocolo Titan</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #07111f;
      color: #e5eefc;
      font-family: Arial, Helvetica, sans-serif;
    }
    a {
      color: #7dd3fc;
    }
    main {
      max-width: 640px;
      padding: 32px;
      text-align: center;
    }
  </style>
</head>
<body>
  <main>
    <h1>Redirigiendo al dashboard de Protocolo Titan...</h1>
    <p>Si tu navegador no abre la web automaticamente, entra en <a href="docs/index.html">docs/index.html</a>.</p>
  </main>
</body>
</html>
"""


def build_static_dashboard_html(
    mobility: pd.DataFrame,
    fading_metrics: pd.DataFrame,
    frequency_planning: pd.DataFrame,
    logical_channels: pd.DataFrame,
    rbw_noise: pd.DataFrame,
    red_checklist: pd.DataFrame,
) -> str:
    mobility_sorted = mobility.sort_values("speed_kmh").reset_index(drop=True)
    fading_sorted = fading_metrics.sort_values(["speed_kmh", "model"]).reset_index(drop=True)
    plan_sorted = frequency_planning.sort_values("cell").reset_index(drop=True)
    logical_sorted = logical_channels.sort_values(["cell", "arfcn"]).reset_index(drop=True)
    rbw_sorted = rbw_noise.sort_values("rbw_hz", ascending=False).reset_index(drop=True)

    low_case = mobility_sorted.iloc[0]
    high_case = mobility_sorted.iloc[-1]
    plan_reference = plan_sorted.iloc[0]
    best_noise = rbw_sorted.loc[rbw_sorted["noise_floor_dbm"].idxmin()]
    noise_drop_db = float(rbw_sorted["noise_floor_dbm"].iloc[0] - best_noise["noise_floor_dbm"])
    worst_fading = fading_sorted.loc[fading_sorted["relative_peak_to_peak"].idxmax()]
    bcch_count = int(logical_sorted[logical_sorted["carrier_role"].str.contains("BCCH")]["cell"].nunique())
    coherence_bw_khz = float(low_case["coherence_bandwidth_khz"]) if "coherence_bandwidth_khz" in low_case.index else None
    estimated_cir_db = float(plan_reference["estimated_cir_db"]) if "estimated_cir_db" in plan_reference.index else None
    voice_circuits = int(plan_reference["gross_voice_circuits_per_cell"]) if "gross_voice_circuits_per_cell" in plan_reference.index else None
    displayed_noise_dbm = float(best_noise["displayed_average_noise_dbm"]) if "displayed_average_noise_dbm" in best_noise.index else None
    fade_lcr = float(worst_fading["fade_lcr_per_s"]) if "fade_lcr_per_s" in worst_fading.index else None
    fade_afd_ms = float(worst_fading["avg_fade_duration_ms"]) if "avg_fade_duration_ms" in worst_fading.index else None

    low_speed = float(low_case["speed_kmh"])
    high_speed = float(high_case["speed_kmh"])
    high_trace_rayleigh = f"assets/figures/traza_{trace_key('rayleigh', high_speed)}.png"
    high_trace_rician = f"assets/figures/traza_{trace_key('rician', high_speed)}.png"

    hero_metrics = "\n".join(
        [
            _render_metric("Frecuencia central", f"{_format_number(float(low_case['carrier_frequency_mhz']), 0)} MHz", "Banda GSM-900 del reto"),
            _render_metric("Timeslot GSM", f"{_format_number(float(low_case['gsm_timeslot_ms']) * 1000.0, 0)} us", "Duracion de la rafaga analizada"),
            _render_metric("Cluster de campamento", f"N={int(plan_reference['cluster_size_N'])}", "Patron de reutilizacion del escenario B"),
            _render_metric(
                "Portadoras por celda",
                f"{int(plan_reference['carriers_per_cell'])}",
                "Reparto exacto con 24 ARFCNs" if voice_circuits is None else f"{voice_circuits} circuitos de trafico por celda",
            ),
        ]
    )

    mobility_table = _select_and_rename_columns(
        mobility_sorted,
        [
            ("speed_kmh", "Velocidad (km/h)"),
            ("speed_ms", "Velocidad (m/s)"),
            ("max_doppler_hz", "Doppler maximo (Hz)"),
            ("doppler_spread_hz", "Espectro Doppler (Hz)"),
            ("coherence_time_ms", "Tiempo de coherencia (ms)"),
            ("coherence_bandwidth_khz", "Ancho de coherencia (kHz)"),
            ("gsm_timeslot_ms", "Timeslot GSM (ms)"),
            ("coherence_to_timeslot_ratio", "Relacion Tc/Tslot"),
            ("normalized_doppler", "Doppler normalizado"),
            ("channel_selectivity", "Selectividad estimada"),
            ("stability_class", "Lectura ingenieril"),
        ],
    )

    fading_table = _select_and_rename_columns(
        fading_sorted,
        [
            ("speed_kmh", "Velocidad (km/h)"),
            ("model", "Modelo de fading"),
            ("envelope_min", "Envolvente minima"),
            ("envelope_max", "Envolvente maxima"),
            ("envelope_std", "Desviacion estandar"),
            ("relative_peak_to_peak", "Pico a pico relativo"),
            ("fade_lcr_per_s", "LCR a -10 dB (1/s)"),
            ("avg_fade_duration_ms", "AFD media (ms)"),
            ("outage_probability_pct", "Outage (%)"),
            ("stability_class", "Lectura ingenieril"),
        ],
    )

    planning_table = _select_and_rename_columns(
        plan_sorted,
        [
            ("cell", "Celda"),
            ("carriers_per_cell", "Portadoras/celda"),
            ("arfcn_range", "Rango ARFCN"),
            ("reuse_ratio_D_over_R", "Relacion D/R"),
            ("reuse_distance_km", "Distancia de reutilizacion (km)"),
            ("estimated_cir_db", "C/I estimada (dB)"),
            ("cir_margin_db", "Margen sobre objetivo (dB)"),
            ("gross_voice_circuits_per_cell", "Circuitos de voz/celda"),
            ("estimated_user_bitrate_kbps", "Bitrate util estimado (kbps)"),
        ],
    )

    logical_table = _select_and_rename_columns(
        logical_sorted,
        [
            ("cell", "Celda"),
            ("arfcn", "ARFCN"),
            ("uplink_mhz", "Uplink (MHz)"),
            ("downlink_mhz", "Downlink (MHz)"),
            ("carrier_role", "Rol de la portadora"),
            ("frequency_hopping_recommended", "Hopping recomendado"),
            ("traffic_timeslots_available", "TS utiles"),
            ("power_policy", "Politica de potencia"),
        ],
    )

    noise_table = _select_and_rename_columns(
        rbw_sorted,
        [
            ("rbw_khz", "RBW (kHz)"),
            ("noise_floor_dbm", "Ruido integrado (dBm)"),
            ("displayed_average_noise_dbm", "DANL mostrado (dBm)"),
            ("delta_vs_100khz_db", "Delta vs 100 kHz (dB)"),
            ("estimated_sweep_time_ms", "Barrido estimado (ms)"),
            ("visibility_margin_db", "Margen para señal debil (dB)"),
            ("measurement_interpretation", "Interpretacion de medida"),
        ],
    )

    checklist_table = red_checklist.rename(
        columns={
            "area": "Area de control",
            "evidence": "Evidencia",
            "student_task": "Argumento que debe aparecer en la memoria",
        }
    )

    scenario_a_figures = [
        (
            "assets/figures/escenario_a_doppler.png",
            "Curva de Doppler",
            "Relacion directa entre velocidad y desplazamiento Doppler en GSM-900.",
        ),
        (
            "assets/figures/escenario_a_coherencia_vs_timeslot.png",
            "Coherencia frente a timeslot",
            "Comparativa entre tiempo de coherencia del canal y la ventana util de transmision.",
        ),
        (
            high_trace_rayleigh,
            f"Fading Rayleigh a {high_speed:g} km/h",
            "Caso sin componente dominante de linea de vista en la velocidad mas exigente.",
        ),
        (
            high_trace_rician,
            f"Fading Rician a {high_speed:g} km/h",
            "Caso con componente LOS dominante para comparar estabilidad de la envolvente.",
        ),
    ]

    scenario_b_figures = [
        (
            "assets/figures/escenario_b_cluster_map.png",
            "Topologia del cluster N=4",
            "Mapa del patron celular y de las celdas reutilizadas en el campamento.",
        ),
        (
            "assets/figures/escenario_b_distribucion_portadoras.png",
            "Reparto BCCH y TCH",
            "Distribucion de portadoras de control y trafico por celda.",
        ),
        (
            "assets/figures/escenario_b_reutilizacion.png",
            "Distancia de proteccion co-canal",
            "Lectura rapida de la distancia D exigida por la reutilizacion celular.",
        ),
        (
            "assets/figures/escenario_b_spectrum.png",
            "Huella espectral del despliegue",
            "Visualizacion del reparto de ARFCNs y del entorno co-canal en GSM-900.",
        ),
        (
            "assets/figures/certificacion_rbw_ruido.png",
            "RBW frente a ruido integrado",
            "El estrechamiento de la RBW mejora la visibilidad de senales debiles pero alarga la medida.",
        ),
    ]

    scenario_a_cards = "\n".join(
        _render_figure_card(image_path, title, subtitle)
        for image_path, title, subtitle in scenario_a_figures
    )
    scenario_b_cards = "\n".join(
        _render_figure_card(image_path, title, subtitle)
        for image_path, title, subtitle in scenario_b_figures
    )

    downloads = [
        ("files/informe_resultados.html", "Informe tecnico web", "HTML", "Documento principal navegable para revisar conclusiones y tablas."),
        ("files/informe_resultados.pdf", "Informe tecnico listo para entrega", "PDF", "Version formal para imprimir o subir al campus virtual."),
        ("files/informe_resultados.docx", "Informe editable", "DOCX", "Archivo Word para rematar portada, autores o referencias."),
        ("files/anexo_calculos.html", "Anexo de calculos", "HTML", "Trazabilidad matematica paso a paso con todas las ecuaciones."),
        ("files/guion_defensa.html", "Guion de defensa", "HTML", "Resumen corto para presentar el reto en clase o en exposicion."),
        ("files/certificacion_rbw.csv", "Tabla RBW y ruido", "CSV", "Datos listos para reutilizar en hojas de calculo o analisis adicional."),
    ]
    download_cards = "\n".join(
        _render_download_card(href, label, file_type, description) for href, label, file_type, description in downloads
    )

    executive_chips = _render_kpi_strip(
        [
            ("Doppler a baja velocidad", f"{_format_number(float(low_case['max_doppler_hz']), 1)} Hz"),
            ("Doppler a velocidad extrema", f"{_format_number(float(high_case['max_doppler_hz']), 1)} Hz"),
            (
                "Mejor suelo de ruido",
                f"{_format_number(displayed_noise_dbm if displayed_noise_dbm is not None else float(best_noise['noise_floor_dbm']), 1)} dBm",
            ),
            ("BCCH dedicadas", f"{bcch_count} celdas" if estimated_cir_db is None else f"C/I {estimated_cir_db:.1f} dB"),
        ]
    )

    scenario_a_notes = _render_bullet_list(
        [
            f"A {low_speed:g} km/h el Doppler queda en {_format_number(float(low_case['max_doppler_hz']), 1)} Hz y el tiempo de coherencia en {_format_number(float(low_case['coherence_time_ms']), 2)} ms.",
            f"A {high_speed:g} km/h el canal sigue superando el timeslot GSM con una relacion Tc/Tslot de {_format_number(float(high_case['coherence_to_timeslot_ratio']), 2)}.",
            (
                f"El peor caso de variacion de envolvente en las simulaciones es {str(worst_fading['model']).upper()} con pico a pico relativo {_format_number(float(worst_fading['relative_peak_to_peak']), 2)}."
                if fade_lcr is None
                else f"El peor caso presenta LCR de {_format_number(fade_lcr, 2)} cruces/s y AFD media de {_format_number(fade_afd_ms if fade_afd_ms is not None else 0.0, 3)} ms."
            ),
            (
                f"El ancho de coherencia estimado ronda {_format_number(coherence_bw_khz, 1)} kHz, util para justificar si el canal se comporta casi plano o ya entra en transicion selectiva."
                if coherence_bw_khz is not None
                else ""
            ),
        ]
    )

    scenario_b_notes = _render_bullet_list(
        [
            f"Cada celda recibe {int(plan_reference['carriers_per_cell'])} portadoras y la distancia de reutilizacion alcanza {_format_number(float(plan_reference['reuse_distance_km']), 2)} km.",
            (
                f"La relacion D/R vale {_format_number(float(plan_reference['reuse_ratio_D_over_R']), 2)} y la C/I estimada se situa en {_format_number(estimated_cir_db, 2)} dB."
                if estimated_cir_db is not None
                else f"La relacion D/R vale {_format_number(float(plan_reference['reuse_ratio_D_over_R']), 2)}, suficiente para explicar la proteccion co-canal del reto."
            ),
            f"Pasar de 100 kHz a 1 kHz reduce el ruido integrado mostrado en {abs(noise_drop_db):.0f} dB, pero ralentiza el barrido instrumental.",
        ]
    )

    build_time = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Protocolo Titan | Dashboard Tecnico</title>
  <meta name="description" content="Panel web listo para abrir y publicar del proyecto Protocolo Titan.">
  <style>
    :root {{
      color-scheme: dark;
      --bg: #07111f;
      --bg-soft: #0d1a2d;
      --panel: rgba(10, 24, 43, 0.92);
      --panel-border: rgba(122, 162, 255, 0.18);
      --text: #e8efff;
      --muted: #9db2cf;
      --accent: #7dd3fc;
      --accent-strong: #38bdf8;
      --ok: #67e8a3;
      --shadow: 0 30px 60px rgba(0, 0, 0, 0.28);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background:
        radial-gradient(circle at top right, rgba(59, 130, 246, 0.22), transparent 30%),
        radial-gradient(circle at top left, rgba(34, 197, 94, 0.10), transparent 25%),
        linear-gradient(180deg, #050b16 0%, var(--bg) 48%, #081424 100%);
      color: var(--text);
      line-height: 1.6;
    }}
    a {{ color: inherit; text-decoration: none; }}
    img {{ width: 100%; display: block; border-radius: 18px; }}
    .page {{ max-width: 1440px; margin: 0 auto; padding: 28px; }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 20;
      margin-bottom: 24px;
      backdrop-filter: blur(16px);
      background: rgba(5, 11, 22, 0.72);
      border: 1px solid rgba(125, 211, 252, 0.12);
      border-radius: 18px;
      padding: 16px 22px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 18px;
      box-shadow: var(--shadow);
    }}
    .brand strong {{ display: block; font-size: 1.02rem; letter-spacing: 0.08em; text-transform: uppercase; }}
    .brand span {{ color: var(--muted); font-size: 0.92rem; }}
    .topbar nav {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .topbar nav a {{
      color: var(--muted);
      border: 1px solid rgba(157, 178, 207, 0.18);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 0.92rem;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 24px;
      padding: 34px;
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(11, 25, 45, 0.97), rgba(7, 17, 31, 0.94));
      border: 1px solid var(--panel-border);
      box-shadow: var(--shadow);
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 0.78rem;
      color: var(--accent);
      margin-bottom: 14px;
    }}
    .eyebrow::before {{
      content: "";
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--ok);
      box-shadow: 0 0 18px rgba(103, 232, 163, 0.8);
    }}
    h1 {{
      margin: 0 0 14px;
      font-size: clamp(2.3rem, 4vw, 4.2rem);
      line-height: 1.02;
    }}
    .hero p {{ margin: 0 0 16px; color: var(--muted); max-width: 70ch; }}
    .hero-summary {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 20px;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      align-content: start;
    }}
    .metric-card, .panel, .figure-card, .table-card, .download-card {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }}
    .metric-card {{ padding: 20px; }}
    .metric-label {{
      display: block;
      margin-bottom: 10px;
      font-size: 0.78rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}
    .metric-value {{ display: block; font-size: clamp(1.55rem, 2vw, 2.2rem); margin-bottom: 8px; }}
    .metric-caption {{ margin: 0; color: var(--muted); font-size: 0.94rem; }}
    .hero-summary .panel, .section-grid > .panel {{ padding: 22px; }}
    .section-grid {{
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 22px;
      margin-top: 26px;
    }}
    .span-4 {{ grid-column: span 4; }}
    .span-5 {{ grid-column: span 5; }}
    .span-6 {{ grid-column: span 6; }}
    .span-7 {{ grid-column: span 7; }}
    .span-8 {{ grid-column: span 8; }}
    .span-12 {{ grid-column: span 12; }}
    .section-heading {{ margin-bottom: 16px; }}
    .section-heading.compact {{ margin-bottom: 14px; }}
    .section-heading h2, .section-heading h3 {{ margin: 0 0 8px; }}
    .section-heading p {{ margin: 0; color: var(--muted); }}
    .section-heading h2 {{ font-size: 1.55rem; }}
    .section-heading h3 {{ font-size: 1.1rem; }}
    .kpi-strip {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
    .kpi-chip {{
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(10, 24, 43, 0.8);
      border: 1px solid rgba(125, 211, 252, 0.14);
    }}
    .kpi-chip span {{ display: block; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.11em; color: var(--muted); margin-bottom: 8px; }}
    .kpi-chip strong {{ font-size: 1.14rem; }}
    .insight-list {{ margin: 0; padding-left: 18px; color: var(--text); }}
    .insight-list li + li {{ margin-top: 10px; }}
    .figure-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .figure-card {{ padding: 16px; }}
    .table-card {{ padding: 22px; }}
    .table-wrapper {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 720px; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid rgba(157, 178, 207, 0.12); text-align: left; vertical-align: top; }}
    th {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); }}
    td {{ color: #d9e6ff; font-size: 0.95rem; }}
    tbody tr:hover {{ background: rgba(125, 211, 252, 0.05); }}
    .download-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }}
    .download-card {{ padding: 22px; transition: transform 0.18s ease, border-color 0.18s ease; }}
    .download-card:hover {{ transform: translateY(-3px); border-color: rgba(125, 211, 252, 0.35); }}
    .download-type {{ display: inline-block; margin-bottom: 12px; padding: 6px 10px; border-radius: 999px; background: rgba(56, 189, 248, 0.16); color: var(--accent); font-size: 0.78rem; letter-spacing: 0.1em; text-transform: uppercase; }}
    .download-card strong {{ display: block; margin-bottom: 8px; font-size: 1.04rem; }}
    .download-card p {{ margin: 0 0 12px; color: var(--muted); }}
    .download-link {{ color: var(--ok); font-weight: bold; }}
    .footer-note {{ color: var(--muted); font-size: 0.92rem; text-align: center; margin-top: 28px; }}
    @media (max-width: 1180px) {{
      .hero {{ grid-template-columns: 1fr; }}
      .span-4, .span-5, .span-6, .span-7, .span-8 {{ grid-column: span 12; }}
      .download-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 760px) {{
      .page {{ padding: 16px; }}
      .topbar {{ position: static; flex-direction: column; align-items: flex-start; }}
      .metric-grid, .hero-summary, .kpi-strip, .figure-grid, .download-grid {{ grid-template-columns: 1fr; }}
      .hero {{ padding: 24px; }}
      table {{ min-width: 640px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header class="topbar">
      <div class="brand">
        <strong>Protocolo Titan</strong>
        <span>Dashboard tecnico listo para abrir y publicar en GitHub Pages</span>
      </div>
      <nav>
        <a href="#resumen">Resumen</a>
        <a href="#escenario-a">Escenario A</a>
        <a href="#escenario-b">Escenario B</a>
        <a href="#entregables">Entregables</a>
      </nav>
    </header>

    <section class="hero">
      <div>
        <div class="eyebrow">Estado del proyecto: listo para demo</div>
        <h1>Red GSM/EDGE tactica con analitica web profesional</h1>
        <p>
          Esta pagina sintetiza el reto docente Protocolo Titan como si fuera un panel de ingenieria listo para defensa,
          revision tecnica y publicacion estatica. Integra movilidad extrema, planificacion espectral, reutilizacion celular
          y criterio instrumental de certificacion en una unica experiencia navegable.
        </p>
        <p>
          La web es estatica, se puede abrir directamente desde el archivo HTML y tambien queda preparada para publicarse en GitHub Pages sin backend.
        </p>
        <div class="hero-summary">
          <section class="panel">
            <div class="section-heading compact">
              <h3>Que domina en cada escenario</h3>
              <p>Lectura ejecutiva de los resultados mas importantes.</p>
            </div>
            {_render_bullet_list([
                'Escenario A: domina la variacion temporal del canal y el impacto del Doppler sobre la estabilidad intra-rafaga.',
                'Escenario B: dominan la disciplina espectral, la proteccion co-canal y la correcta interpretacion de las medidas de laboratorio.',
                'El proyecto ya deja informe, anexo, guion de defensa y tablas exportables para entrega o GitHub.'
            ])}
          </section>
          <section class="panel">
            <div class="section-heading compact">
              <h3>Ventajas de esta version</h3>
              <p>Orientada a memoria seria y presentacion profesional.</p>
            </div>
            {_render_bullet_list([
                'HTML principal con secciones, tablas y graficas listas para abrir en local.',
                'Carpeta docs preparada para GitHub Pages y archivos auxiliares copiados automaticamente.',
                'Salida documental paralela en HTML, PDF, DOCX, Markdown y CSV para reutilizar en la entrega.'
            ])}
          </section>
        </div>
      </div>
      <div class="metric-grid">
        {hero_metrics}
      </div>
    </section>

    <section class="section-grid" id="resumen">
      <article class="panel span-12">
        <div class="section-heading">
          <h2>Resumen ejecutivo</h2>
          <p>Valores clave del despliegue base y mensajes que deben sostener la memoria final.</p>
        </div>
        <div class="kpi-strip">
          {executive_chips}
        </div>
      </article>
    </section>

    <section class="section-grid" id="escenario-a">
      <article class="panel span-4">
        <div class="section-heading">
          <h2>Escenario A · Convoy de alta velocidad</h2>
          <p>Analisis de Doppler, tiempo de coherencia y comportamiento del canal durante el timeslot GSM.</p>
        </div>
        {scenario_a_notes}
      </article>
      <article class="panel span-8">
        <div class="section-heading">
          <h2>Galeria de graficas de movilidad</h2>
          <p>Curvas y trazas que sostienen la interpretacion radio del escenario ferroviario.</p>
        </div>
        <div class="figure-grid">
          {scenario_a_cards}
        </div>
      </article>
      <div class="span-6">
        {_render_table(mobility_table, 'Tabla de movilidad', 'Comparativa de velocidades, Doppler y estabilidad del canal.')}
      </div>
      <div class="span-6">
        {_render_table(fading_table, 'Tabla de fading', 'Metricas de variacion de envolvente para Rayleigh y Rician.')}
      </div>
    </section>

    <section class="section-grid" id="escenario-b">
      <article class="panel span-4">
        <div class="section-heading">
          <h2>Escenario B · Campamento base</h2>
          <p>Planificacion de ARFCNs, BCCH/TCH, reutilizacion celular y criterio de certificacion.</p>
        </div>
        {scenario_b_notes}
      </article>
      <article class="panel span-8">
        <div class="section-heading">
          <h2>Galeria de graficas espectrales</h2>
          <p>Visualizaciones para defender la asignacion de canales y el ajuste del analizador.</p>
        </div>
        <div class="figure-grid">
          {scenario_b_cards}
        </div>
      </article>
      <div class="span-6">
        {_render_table(planning_table, 'Planificacion celular', 'Reparto por celda del cluster N=4 y distancia de proteccion.')}
      </div>
      <div class="span-6">
        {_render_table(noise_table, 'Tabla RBW y ruido', 'Base numerica para explicar el compromiso entre ruido integrado y tiempo de barrido.')}
      </div>
      <div class="span-7">
        {_render_table(logical_table, 'Canales logicos y fisicos', 'Asignacion de roles BCCH/TCH y politicas de hopping o potencia por portadora.')}
      </div>
      <div class="span-5">
        {_render_table(checklist_table, 'Checklist RED', 'Puntos que conviene dejar expresos en la memoria tecnica final.')}
      </div>
    </section>

    <section class="section-grid" id="entregables">
      <article class="panel span-12">
        <div class="section-heading">
          <h2>Entregables y publicacion</h2>
          <p>Archivos listos para abrir, revisar y subir al repositorio sin depender de un servidor Python.</p>
        </div>
        <div class="download-grid">
          {download_cards}
        </div>
      </article>
    </section>

    <p class="footer-note">
      Build generado el {html_escape(build_time)}. Para publicarlo en GitHub Pages basta con subir el proyecto y usar la carpeta <code>docs/</code> como origen.
    </p>
  </div>
</body>
</html>
"""


def write_static_site(
    project_root: Path,
    outputs_root: Path,
    mobility: pd.DataFrame,
    fading_metrics: pd.DataFrame,
    frequency_planning: pd.DataFrame,
    logical_channels: pd.DataFrame,
    rbw_noise: pd.DataFrame,
    red_checklist: pd.DataFrame,
) -> None:
    site_root = project_root / "docs"
    site_root.mkdir(parents=True, exist_ok=True)
    _copy_output_assets(outputs_root, site_root)

    dashboard_html = build_static_dashboard_html(
        mobility=mobility,
        fading_metrics=fading_metrics,
        frequency_planning=frequency_planning,
        logical_channels=logical_channels,
        rbw_noise=rbw_noise,
        red_checklist=red_checklist,
    )
    (site_root / "index.html").write_text(dashboard_html, encoding="utf-8")
    (project_root / "index.html").write_text(build_root_redirect_html(), encoding="utf-8")
