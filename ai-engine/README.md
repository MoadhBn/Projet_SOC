# Analysis API

FastAPI service running on the laptop 2 host: the single entry point of the AI engine (score, anomaly detection, explanation by the local language model).

Current state: phase 3 skeleton. Only the score formula is implemented; the anomaly score and the language model label are given by the caller.

## Score

| Component | Source | Maximum |
|---|---|---|
| Severity | Wazuh rule level (0 to 15), proportional | 50 |
| Threat intelligence | Indicator found in MISP | 25 |
| Anomaly | Isolation Forest score (0 to 1), proportional | 15 |
| Language model label | malicious = 10, suspicious = 5, benign = 0 | 10 |

- The base score (first three components) is available before the language model answers. The answer has two flags: `respond` (final level high: an automatic response is executed) and `respond_before_llm` (the base score alone is high: the response fires without waiting for the model). When only `respond` is true, the response fires once the model has answered.
- The label can only add points; "benign" removes nothing.
- Thresholds are placeholders (medium 25, high 40) until calibration on the test scenarios. The half weight for "suspicious" is an assumption of this implementation.

## Run

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Then `http://localhost:8000/docs` shows the interactive documentation.

Example:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/score -ContentType "application/json" -Body '{"rule_level": 10, "misp_match": false, "anomaly_score": 0.2, "llm_label": "malicious"}'
```
