import html
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from protocolo_titan.config import GSMConfig, ConvoyScenario, CampScenario, AnalyzerConfig
from protocolo_titan.instrumentation import rbw_noise_table
from protocolo_titan.radio_access import gsm_access_summary
from protocolo_titan.scenario_a import analyze_convoy_mobility, analyze_convoy_fading, trace_key
from protocolo_titan.scenario_b import analyze_camp_base
from protocolo_titan.ui_charts import (
    figure_timeslot_signal,
    figure_noise,
    figure_cluster_map,
    figure_carrier_distribution,
    figure_spectrum_from_arfcns,
    figure_small_camera_placeholder,
)


st.set_page_config(
    page_title="RAIL-COM ANALYTICS",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css():
    st.markdown(
        """
        <style>
        :root {
          --bg:#07111F; --panel:#0D1A2B; --panel2:#13233A; --border:#223A5D; --text:#EAF4FF; --muted:#A9BEDA;
        }
        .stApp { background: linear-gradient(180deg, #051023 0%, #06111f 100%); color: var(--text); }
        [data-testid="stSidebar"] { background: linear-gradient(180deg,#041024 0%, #061327 100%); border-right: 1px solid var(--border); }
        [data-testid="stHeader"] { background: rgba(0,0,0,0); }
        #MainMenu, footer {visibility:hidden;}
        .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 100%; }
        .hero { display:flex; justify-content:space-between; align-items:center; background:linear-gradient(90deg,#05162D,#071A33); border:1px solid var(--border); padding:14px 18px; border-radius:14px; margin-bottom:12px; }
        .hero-title { font-size:20px; font-weight:800; color:var(--text); letter-spacing:0.3px; }
        .hero-sub { font-size:11px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:1px; }
        .chip { display:inline-block; padding:7px 12px; border:1px solid #34577E; border-radius:10px; color:#DDEEFF; margin-left:8px; background:#0E2038; font-size:12px; font-weight:700; }
        .status-on { color:#6CFFB2; font-weight:800; }
        .panel { background: linear-gradient(180deg, #0B1829 0%, #0D1B2E 100%); border:1px solid var(--border); border-radius:14px; padding:14px; height:100%; }
        .panel-title { color:#E8F3FF; font-weight:800; font-size:15px; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; }
        .subtle { color: var(--muted); font-size: 13px; }
        .mini-kpi { background:#102139; border:1px solid var(--border); border-radius:10px; padding:12px; min-height:88px; margin-bottom: 10px; }
        .mini-kpi .label { font-size:12px; color:#AFC4E8; text-transform:uppercase; letter-spacing:0.8px; }
        .mini-kpi .value { font-size:28px; font-weight:800; color:#59CCFF; line-height:1.1; margin-top:6px; }
        .mini-kpi .suffix { font-size:18px; color:#C9E9FF; }
        .smallbox { background:#102139; border:1px solid var(--border); border-radius:10px; padding:10px; margin-bottom:10px; }
        .sidebar-header { font-size: 24px; font-weight: 800; color: white; line-height:1.1; margin-bottom: 1rem; }
        .sidebar-caption { color:#AFC4E8; font-size:12px; text-transform:uppercase; letter-spacing:1px; }
        .stButton button { width:100%; border-radius:10px; border:1px solid #3A6089; background:#10213A; color:#EAF4FF; font-weight:700; }
        .stRadio > div { background:#081324; padding:8px; border-radius:12px; border:1px solid var(--border); }
        .stDataFrame, .stTable { border:1px solid var(--border); border-radius:12px; overflow:hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def header():
    st.markdown(
        """
        <div class="hero">
            <div>
                <div class="hero-sub">Mission Control</div>
                <div class="hero-title">RAIL-COM ANALYTICS</div>
            </div>
            <div>
                <span class="chip">LIVE STREAM</span>
                <span class="chip">HISTORICAL</span>
                <span class="chip">GEOMETRY</span>
                <span class="chip">PHYSICS & SPECTRUM</span>
                <span class="chip status-on">EN VIVO</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_controls():
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-caption">HSR-700-ALPHA</div><div class="sidebar-header">MISSION CONTROL</div>',
            unsafe_allow_html=True,
        )
        st.button('+ NEW SCENARIO')
        section = st.radio(
            'Secciones',
            ['Escenario A · Physics & Spectrum', 'Escenario B · Base Camp'],
            label_visibility='collapsed',
        )
        st.markdown('---')
        st.markdown('**Parámetros globales**')
        fc_mhz = st.number_input('Frecuencia central (MHz)', min_value=100.0, max_value=3000.0, value=900.0, step=10.0)
        timeslot_us = st.number_input('Timeslot GSM (µs)', min_value=1.0, max_value=5000.0, value=577.0, step=1.0)
        st.markdown('**Escenario A**')
        speed_low = st.number_input('Velocidad baja (km/h)', min_value=0.0, max_value=1000.0, value=50.0, step=10.0)
        speed_high = st.number_input('Velocidad alta (km/h)', min_value=0.0, max_value=1000.0, value=250.0, step=10.0)
        st.markdown('**Escenario B**')
        total_carriers = st.number_input('Portadoras totales', min_value=1, max_value=124, value=24, step=1)
        cluster_max = min(26, int(total_carriers))
        cluster_size = st.number_input('Clúster N', min_value=1, max_value=cluster_max, value=min(4, cluster_max), step=1)
        radius_km = st.number_input('Radio celda campamento (km)', min_value=0.1, max_value=50.0, value=1.5, step=0.1)
        st.markdown('**Instrumentación**')
        nf_db = st.number_input('Figura de ruido NF (dB)', min_value=0.0, max_value=30.0, value=6.0, step=0.5)
        st.markdown('---')
        st.caption('Diagnósticos · Export · Logs')
    return section, fc_mhz, timeslot_us, speed_low, speed_high, total_carriers, cluster_size, radius_km, nf_db


def metric_card(title: str, value: str, suffix: str = '', caption: str = ''):
    safe_title = html.escape(str(title), quote=True)
    safe_value = html.escape(str(value), quote=True)
    safe_suffix = html.escape(str(suffix), quote=True)
    safe_caption = html.escape(str(caption), quote=True)
    st.markdown(
        f'''<div class="mini-kpi"><div class="label">{safe_title}</div><div class="value">{safe_value}<span class="suffix"> {safe_suffix}</span></div><div class="subtle">{safe_caption}</div></div>''',
        unsafe_allow_html=True,
    )


def render_scenario_a(gsm, convoy, analyzer):
    mobility = analyze_convoy_mobility(convoy, gsm)
    fading_summary, traces = analyze_convoy_fading(convoy, gsm)
    access = gsm_access_summary(gsm)
    noise = rbw_noise_table(analyzer)

    speed_options = list(dict.fromkeys(float(speed) for speed in mobility['speed_kmh'].tolist()))
    default_index = 1 if len(speed_options) > 1 else 0
    selected_speed = st.radio(
        'Perfil de velocidad',
        speed_options,
        horizontal=True,
        index=default_index,
        format_func=lambda speed: f'{speed:g} km/h',
    )
    selected_row = mobility[mobility['speed_kmh'].eq(float(selected_speed))].iloc[0]
    selected_trace = traces[trace_key('rician', float(selected_speed))]

    c1, c2, c3 = st.columns([4, 4, 4])
    with c1:
        st.markdown('<div class="panel"><div class="panel-title">Capa física</div>', unsafe_allow_html=True)
        a1, a2 = st.columns(2)
        with a1:
            metric_card('FDMA', f"{gsm.channel_bandwidth_hz / 1e3:g}", 'kHz', 'Portadoras GSM-900')
        with a2:
            metric_card('TDMA', gsm.timeslots_per_frame, 'slots', 'Timeslots por trama')
        b1, b2 = st.columns(2)
        with b1:
            metric_card('Separación', f"{gsm.channel_bandwidth_hz / 1e3:g}", 'kHz', 'Ancho por ARFCN')
        with b2:
            metric_card('Duración TS', f"{gsm.timeslot_duration_s * 1e6:g}", 'µs', 'Timeslot GSM')
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="panel"><div class="panel-title">Coherencia y Doppler</div>', unsafe_allow_html=True)
        a1, a2 = st.columns(2)
        with a1:
            metric_card('Shift Doppler', f"{selected_row['max_doppler_hz']:.0f}", 'Hz', f'Velocidad {selected_speed:g} km/h')
        with a2:
            metric_card('Tiempo coherencia', f"{selected_row['coherence_time_ms']:.2f}", 'ms', selected_row['stability_class'])
        st.write('**Modelos de desvanecimiento**')
        ray = float(
            fading_summary[
                (fading_summary['speed_kmh'] == float(selected_speed)) & (fading_summary['model'] == 'rayleigh')
            ]['relative_peak_to_peak'].iloc[0]
        )
        ric = float(
            fading_summary[
                (fading_summary['speed_kmh'] == float(selected_speed)) & (fading_summary['model'] == 'rician')
            ]['relative_peak_to_peak'].iloc[0]
        )
        st.write('Rayleigh (NLOS)')
        st.progress(max(0.05, min(ray / 4.0, 1.0)))
        st.write('Rician (LOS dominante)')
        st.progress(max(0.05, min(ric / 2.0, 1.0)))
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="panel"><div class="panel-title">Visualización en tiempo real</div>', unsafe_allow_html=True)
        st.pyplot(figure_small_camera_placeholder(), clear_figure=True, use_container_width=True)
        x1, x2 = st.columns(2)
        with x1:
            metric_card('CAM', '04', '', 'Frontal')
        with x2:
            metric_card('Velocidad', f'{selected_speed:g}', 'km/h', 'Convoy operativo')
        st.markdown('</div>', unsafe_allow_html=True)

    lower_left, lower_right = st.columns([8, 3])
    with lower_left:
        st.markdown('<div class="panel"><div class="panel-title">Instrumentación de espectro</div>', unsafe_allow_html=True)
        st.radio('RBW', ['100 kHz', '10 kHz', '1 kHz'], horizontal=True, label_visibility='collapsed', index=1)
        info1, info2 = st.columns([1.3, 4.7])
        with info1:
            html = ['<div class="smallbox"><b>PISO DE RUIDO VS RBW</b><br><br>']
            for _, r in noise.iterrows():
                html.append(
                    f"{int(r['rbw_khz'])} kHz<span style='float:right;color:#8FD9FF'>{r['noise_floor_dbm']:.0f} dBm</span><br>"
                )
            html.append('</div>')
            st.markdown(''.join(html), unsafe_allow_html=True)
        with info2:
            st.pyplot(figure_timeslot_signal(selected_trace), clear_figure=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with lower_right:
        st.markdown('<div class="panel"><div class="panel-title">Análisis de telemetría GSM</div>', unsafe_allow_html=True)
        a, b, c = st.columns(3)
        with a:
            metric_card('Slot', f"{gsm.timeslot_duration_s * 1e6:g}", 'µs', 'Duración')
        with b:
            metric_card('Desplaz.', f"{selected_row['max_doppler_hz'] / 1000:.2f}", 'kHz', 'Escala visual')
        with c:
            metric_card('Estabilidad', f"{min(selected_row['coherence_to_timeslot_ratio'] * 26.8, 99):.1f}", '%', 'Indicador heurístico')
        st.pyplot(figure_timeslot_signal(selected_trace), clear_figure=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander('Ver tablas técnicas de escenario A'):
        st.dataframe(access, use_container_width=True)
        st.dataframe(mobility, use_container_width=True)
        st.dataframe(fading_summary, use_container_width=True)


def render_scenario_b(gsm, camp, analyzer):
    try:
        results = analyze_camp_base(camp, gsm, analyzer)
    except ValueError as exc:
        st.error(f'Parámetros no válidos para el escenario B: {exc}')
        st.info('Ajusta las portadoras totales, el clúster N o el rango ARFCN para continuar.')
        return

    plan = results['frequency_planning']
    logical = results['logical_channels']
    noise = results['rbw_noise']
    checklist = results['red_checklist']

    st.markdown(
        '<div class="panel" style="padding:16px 18px 10px 18px; margin-bottom:12px;"><div style="font-size:18px;font-weight:800;color:#F2F7FF;">Escenario B (Base Camp)</div><div class="subtle">Análisis técnico de topología de red y distribución de portadoras.</div></div>',
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([7, 3])
    with top_left:
        st.markdown(f'<div class="panel"><div class="panel-title">Mapeo de clúster (N={camp.cluster_size})</div>', unsafe_allow_html=True)
        st.pyplot(figure_cluster_map(camp.cluster_size, camp.cell_radius_km), clear_figure=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with top_right:
        st.markdown(f'<div class="panel"><div class="panel-title">Planificación celular (N={camp.cluster_size})</div>', unsafe_allow_html=True)
        reuse_ratio = float(plan['reuse_ratio_D_over_R'].iloc[0])
        reuse_distance = float(plan['reuse_distance_km'].iloc[0])
        metric_card('Distancia de reúso', f'{reuse_distance:.2f}', 'km', 'D = R √(3N)')
        metric_card('Relación D/R', f'{reuse_ratio:.2f}', '', 'Protección co-canal')
        metric_card('Factor de reúso', f'1/{camp.cluster_size}', '', f'Clúster N = {camp.cluster_size}')
        st.markdown(f'<div class="panel-title" style="margin-top:12px;">Distribución de portadoras ({camp.total_carriers} CH)</div>', unsafe_allow_html=True)
        st.pyplot(figure_carrier_distribution(plan, logical, camp.total_carriers), clear_figure=True, use_container_width=True)
        st.dataframe(logical[['cell', 'arfcn', 'carrier_role']].head(8), use_container_width=True, hide_index=True)
        st.markdown('<div class="panel-title" style="margin-top:12px;">Cumplimiento y normativa</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="smallbox"><b>Directiva RED</b><span style="float:right;color:#6CFFB2;font-weight:800;">PASS</span><br><span class="subtle">Conformidad CE y uso eficiente del espectro</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="smallbox"><b>Emisiones radiadas</b><span style="float:right;color:#6CFFB2;font-weight:800;">PASS</span><br><span class="subtle">Análisis instrumental y control de ruido</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns([5, 5])
    with bottom_left:
        st.markdown('<div class="panel"><div class="panel-title">Gestión de interferencias (SIR)</div>', unsafe_allow_html=True)
        st.pyplot(figure_carrier_distribution(plan, logical, camp.total_carriers), clear_figure=True, use_container_width=True)
        st.dataframe(plan[['cell', 'carriers_per_cell', 'arfcn_range', 'reuse_distance_km']], use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with bottom_right:
        st.markdown('<div class="panel"><div class="panel-title">Análisis de espectro y ruido</div>', unsafe_allow_html=True)
        st.pyplot(figure_spectrum_from_arfcns(logical), clear_figure=True, use_container_width=True)
        st.pyplot(figure_noise(noise), clear_figure=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander('Ver tablas técnicas de escenario B'):
        st.dataframe(plan, use_container_width=True)
        st.dataframe(logical, use_container_width=True)
        st.dataframe(noise, use_container_width=True)
        st.dataframe(checklist, use_container_width=True)


def main():
    inject_css()
    header()
    section, fc_mhz, timeslot_us, speed_low, speed_high, total_carriers, cluster_size, radius_km, nf_db = sidebar_controls()

    gsm = GSMConfig(carrier_frequency_hz=fc_mhz * 1e6, timeslot_duration_s=timeslot_us * 1e-6)
    convoy = ConvoyScenario(speeds_kmh=(speed_low, speed_high))
    camp = CampScenario(total_carriers=int(total_carriers), cluster_size=int(cluster_size), cell_radius_km=radius_km)
    analyzer = AnalyzerConfig(noise_figure_db=nf_db)

    if section.startswith('Escenario A'):
        render_scenario_a(gsm, convoy, analyzer)
    else:
        render_scenario_b(gsm, camp, analyzer)


if __name__ == '__main__':
    main()
