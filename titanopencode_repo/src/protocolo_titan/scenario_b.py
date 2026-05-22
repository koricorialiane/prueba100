import pandas as pd

from .config import CampScenario, GSMConfig, AnalyzerConfig
from .cellular_planning import frequency_planning_table, channel_logical_mapping
from .instrumentation import rbw_noise_table, red_compliance_checklist


def analyze_camp_base(
    scenario: CampScenario = CampScenario(),
    gsm: GSMConfig = GSMConfig(),
    analyzer: AnalyzerConfig = AnalyzerConfig(),
) -> dict[str, pd.DataFrame]:
    """Ejecuta el análisis completo del escenario B."""
    return {
        "frequency_planning": frequency_planning_table(scenario),
        "logical_channels": channel_logical_mapping(scenario, gsm),
        "rbw_noise": rbw_noise_table(analyzer),
        "red_checklist": red_compliance_checklist(),
    }
