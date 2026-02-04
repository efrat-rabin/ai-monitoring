#!/usr/bin/env python3
"""AI Prompts Configuration"""

# GroundCover monitor YAML structure: https://docs.groundcover.com/use-groundcover/monitors/monitor-yaml-structure
MONITOR_YAML_GENERATION_PROMPT = """Generate a single valid GroundCover monitor YAML document from the issue context below.

GroundCover monitor YAML structure (use these fields):
- title: human-readable monitor name
- display: header (short condition description), description, resourceHeaderLabels (list), contextHeaderLabels (list, e.g. cluster, namespace, workload)
- severity: S1 (Critical), S2 (High), S3 (Medium), S4 (Low)
- model.queries: list with name, dataType ("logs" or "traces"), and either sqlPipeline (selectors, groupBy, orderBy, filters, instantRollup) or expression (PromQL) with datasourceType/queryType/rollup
- model.thresholds: name, inputName (query name), operator (gt, lt, within_range, outside_range), values (list)
- executionErrorState: OK | Alerting | Error
- noDataState: OK | NoData | Alerting
- evaluationInterval: interval (e.g. 1m), pendingFor (e.g. 0s)
- measurementType: "event" (bar chart) or "state" (line chart)
- labels: optional key-value pairs

Output only the YAML document. No markdown fences, no explanation before or after.

Issue context:
{issue_context}
"""

