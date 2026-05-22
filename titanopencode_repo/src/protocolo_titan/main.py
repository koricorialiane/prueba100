from pathlib import Path

from .config import GSMConfig, ConvoyScenario, CampScenario, AnalyzerConfig
from .radio_access import gsm_access_summary
from .scenario_a import analyze_convoy_mobility, analyze_convoy_fading
from .scenario_b import analyze_camp_base
from .plots import (
    save_doppler_plot,
    save_coherence_plot,
    save_fading_plot,
    save_reuse_plot,
    save_noise_plot,
    save_cluster_map_plot,
    save_carrier_distribution_plot,
    save_spectrum_plot,
)
from .report import (
    build_calculation_annex_markdown,
    build_defense_brief_markdown,
    build_report_markdown,
    write_docx_document,
    write_html_document,
    write_pdf_document,
)
from .site_builder import write_static_site


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    outputs = project_root / "outputs"
    figures = outputs / "figures"
    outputs.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    gsm = GSMConfig()
    convoy = ConvoyScenario()
    camp = CampScenario()
    analyzer = AnalyzerConfig()

    access = gsm_access_summary(gsm)
    mobility = analyze_convoy_mobility(convoy, gsm)
    fading_summary, traces = analyze_convoy_fading(convoy, gsm)
    camp_results = analyze_camp_base(camp, gsm, analyzer)

    access.to_csv(outputs / "gsm_fdma_tdma_resumen.csv", index=False)
    mobility.to_csv(outputs / "escenario_a_movilidad.csv", index=False)
    fading_summary.to_csv(outputs / "escenario_a_fading_metricas.csv", index=False)
    camp_results["frequency_planning"].to_csv(outputs / "escenario_b_planificacion.csv", index=False)
    camp_results["logical_channels"].to_csv(outputs / "escenario_b_canales_logicos.csv", index=False)
    camp_results["rbw_noise"].to_csv(outputs / "certificacion_rbw.csv", index=False)
    camp_results["red_checklist"].to_csv(outputs / "certificacion_red_checklist.csv", index=False)

    save_doppler_plot(mobility, figures / "escenario_a_doppler.png")
    save_coherence_plot(mobility, figures / "escenario_a_coherencia_vs_timeslot.png")
    save_reuse_plot(camp_results["frequency_planning"], figures / "escenario_b_reutilizacion.png")
    save_noise_plot(camp_results["rbw_noise"], figures / "certificacion_rbw_ruido.png")
    save_cluster_map_plot(camp.cluster_size, camp.cell_radius_km, figures / "escenario_b_cluster_map.png")
    save_carrier_distribution_plot(
        camp_results["frequency_planning"],
        camp_results["logical_channels"],
        camp.total_carriers,
        figures / "escenario_b_distribucion_portadoras.png",
    )
    save_spectrum_plot(camp_results["logical_channels"], figures / "escenario_b_spectrum.png")

    for name, trace in traces.items():
        trace.to_csv(outputs / f"traza_{name}.csv", index=False)
        save_fading_plot(trace, figures / f"traza_{name}.png")

    report_markdown = build_report_markdown(
        mobility=mobility,
        fading_metrics=fading_summary,
        frequency_planning=camp_results["frequency_planning"],
        logical_channels=camp_results["logical_channels"],
        rbw_noise=camp_results["rbw_noise"],
        red_checklist=camp_results["red_checklist"],
    )
    annex_markdown = build_calculation_annex_markdown(
        mobility=mobility,
        fading_metrics=fading_summary,
        frequency_planning=camp_results["frequency_planning"],
        logical_channels=camp_results["logical_channels"],
        rbw_noise=camp_results["rbw_noise"],
        red_checklist=camp_results["red_checklist"],
    )
    defense_markdown = build_defense_brief_markdown(
        mobility=mobility,
        frequency_planning=camp_results["frequency_planning"],
        rbw_noise=camp_results["rbw_noise"],
    )

    (outputs / "informe_resultados.md").write_text(report_markdown, encoding="utf-8")
    (outputs / "anexo_calculos.md").write_text(annex_markdown, encoding="utf-8")
    (outputs / "guion_defensa.md").write_text(defense_markdown, encoding="utf-8")

    write_html_document(outputs / "informe_resultados.html", "Protocolo Titán — Informe técnico docente", report_markdown)
    write_html_document(outputs / "anexo_calculos.html", "Protocolo Titán — Anexo de cálculos", annex_markdown)
    write_html_document(outputs / "guion_defensa.html", "Protocolo Titán — Guion de defensa", defense_markdown)

    write_pdf_document(outputs / "informe_resultados.pdf", "Protocolo Titán — Informe técnico docente", report_markdown, outputs)
    write_pdf_document(outputs / "anexo_calculos.pdf", "Protocolo Titán — Anexo de cálculos", annex_markdown, outputs)
    write_pdf_document(outputs / "guion_defensa.pdf", "Protocolo Titán — Guion de defensa", defense_markdown, outputs)

    write_docx_document(outputs / "informe_resultados.docx", "Protocolo Titán — Informe técnico docente", report_markdown, outputs)
    write_docx_document(outputs / "anexo_calculos.docx", "Protocolo Titán — Anexo de cálculos", annex_markdown, outputs)
    write_docx_document(outputs / "guion_defensa.docx", "Protocolo Titán — Guion de defensa", defense_markdown, outputs)

    write_static_site(
        project_root=project_root,
        outputs_root=outputs,
        mobility=mobility,
        fading_metrics=fading_summary,
        frequency_planning=camp_results["frequency_planning"],
        logical_channels=camp_results["logical_channels"],
        rbw_noise=camp_results["rbw_noise"],
        red_checklist=camp_results["red_checklist"],
    )

    print("\n=== Resumen FDMA/TDMA ===")
    print(access.to_string(index=False))

    print("\n=== Escenario A: movilidad ===")
    print(mobility.to_string(index=False))

    print("\n=== Escenario A: fading ===")
    print(fading_summary.to_string(index=False))

    print("\n=== Escenario B: planificación ===")
    print(camp_results["frequency_planning"].to_string(index=False))

    print("\n=== Escenario B: canales lógicos ===")
    print(camp_results["logical_channels"].head(12).to_string(index=False))

    print("\n=== Certificación: RBW ===")
    print(camp_results["rbw_noise"].to_string(index=False))

    print(f"\nResultados exportados en: {outputs.resolve()}")
    print(f"Dashboard web listo en: {(project_root / 'docs' / 'index.html').resolve()}")


if __name__ == "__main__":
    main()
