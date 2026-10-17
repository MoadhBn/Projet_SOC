# Phase 3: AI engine

Status: early work started on 16 October 2026, while phase 1 waits for laptop 1. The phase itself starts after phase 2.

This file is the journal of phase 3.

## 1. Objective

Build the analysis API on the laptop 2 host: the fixed score formula, the anomaly model (Isolation Forest) and the explanation by a local language model with RAG. The language model only summarises, labels and justifies; it never computes the score and never triggers an action.

## 2. Early work: analysis API skeleton and score formula

The score formula of the brief is implemented in `ai-engine/app/scoring.py` and exposed by a FastAPI service (`ai-engine/app/main.py`).

| Component | Computation | Maximum |
|---|---|---|
| Severity | 50 × Wazuh rule level / 15 | 50 |
| Threat intelligence | 25 if an indicator is known in MISP | 25 |
| Anomaly | 15 × Isolation Forest score (0 to 1) | 15 |
| LLM label | malicious 10, suspicious 5, benign 0 | 10 |

Design rules enforced by the code:

- The **base score** (severity + MISP + anomaly) is available before the language model answers; when it alone reaches the high threshold, `respond_before_llm` is true and the response fires without waiting for the model (BNF-01). A second flag, `respond`, is true whenever the final level (after the model's label) is high: in that case the response fires once the model has answered.
- The label can only **add** points; "benign" removes nothing.
- Every response returns the detail of each component, so any decision can be justified (BNF-05).
- Inputs are validated: a rule level outside 0 to 15 or an anomaly score outside 0 to 1 is rejected.

Assumptions of this implementation, to revisit: the thresholds are placeholders (medium 25, high 40) until calibration on the test scenarios, and "suspicious" is given half the LLM weight (the brief only fixes "malicious" and "benign").

Calibration note: an SSH brute force has no MISP match (lab addresses are private), so its score comes from the rule level and the anomaly only (65 at most). The high threshold will have to be set accordingly for T-01 to end "high".

Tests (`ai-engine/tests/test_scoring.py`, pytest): 11 tests pass, covering the maximum score, the base score without the model, "benign never lowers", "malicious can raise the level", the immediate response on a high base score, the delayed response when the label raises the level, input validation, and the HTTP endpoint. Libraries pinned in `requirements.txt` (FastAPI 0.143.3, Pydantic 2.14.1, Uvicorn 0.54.0, pytest 9.1.1, httpx 0.28.1; Python 3.13).

## 3. Early work: local language model

### Installation

| Item | Value |
|---|---|
| Ollama | Installed on the Windows host (official installer from ollama.com), listening on `localhost:11434` only |
| Why on the host | VMware Workstation cannot give the graphics card to a VM |
| Exposure | Ollama is not opened to the network: only the analysis API, running on the same host, will call it |
| GPU | NVIDIA GeForce RTX 2050, 4096 MiB video memory, driver 577.05 (Ollama requires 551.61 or newer) |

### First test of the candidate models (brief, section 12: "French output quality of the 3B models")

Same prompt for each model, a fictitious alert: 25 failed SSH logins in 60 seconds from 10.10.30.10 to 10.10.20.20, account root, ATT&CK T1110, asking for a two-sentence summary in French for a SOC analyst. This is a first impression, not the comparison planned on 20 to 30 lab alerts.

| Measure | Llama 3.2 3B | Qwen2.5 3B | Gemma 3 4B |
|---|---|---|---|
| French | Correct and readable | Poor: calls the attacker's IP address a "système d'exploitation", awkward phrasing, three sentences instead of two | Best of the three: natural, precise, two sentences |
| Accuracy | Restates the facts correctly, but calls the attack "phishing ou brute-force": phishing is invented | Reaches the right conclusion (brute force) but invents "T1110 de l'Umbrella" | Accurate, nothing invented; adds a useful recommendation (immediate investigation) |
| Generation speed | 37 tokens/s | 49.5 tokens/s | 18.4 tokens/s |
| Load time (first call) | 11.9 s | 5.0 s | 11.4 s |
| Total time, first call | 15.0 s (about 3 s once the model is loaded) | 7.3 s (about 2 s once loaded) | 18.3 s (about 7 s once loaded) |
| Placement | 20 % CPU / 80 % GPU, 2.9 GB in total | 100 % GPU, 2.2 GB in total | 54 % CPU / 46 % GPU, 3.5 GB in total |
| Video memory used | 2325 MiB of 4096 MiB | 2153 MiB of 4096 MiB | 2465 MiB of 4096 MiB |

Observations:

- The invented "phishing" is a small but typical error of a 3B model. It supports the design choice that the model never decides: its label can only raise the score, and the ATT&CK technique comes from the Wazuh rule, not from the model.
- The model does not fit entirely in video memory with the default context of 4096 tokens: Ollama keeps 20 % on the processor. The speed stays acceptable for a summary of about 150 tokens. Reducing the context window is the first lever if a fully GPU placement is needed; to be tested with the real prompt size (alert plus RAG passages).
- The first call includes loading the model (about 12 s). In operation the model should stay loaded, or the response time of the first alert after an idle period will be longer.

First reading of the three models:

- **Llama 3.2 3B** writes better French and makes one invention ("phishing"); it is slower and does not fit entirely on the graphics card.
- **Qwen2.5 3B** is faster and fits entirely on the card, but its French is clearly weaker and it invents a reference ("Umbrella").
- Neither result is final: the prompt was a single bare sentence. The real prompt will add instructions, a fixed JSON output, a low temperature and RAG passages, which usually reduce inventions. The brief also allows a 4B-class fallback (Gemma 3 4B, Phi-3.5 mini) if quality is too poor; Gemma 3 4B is worth adding to the comparison for its French.
- **Gemma 3 4B** (the brief's 4B fallback) gives the best answer by far: correct French, accurate facts, no invention. Its cost is speed: more than half of the model runs on the processor because it does not fit in 4 GB of video memory, so it generates at 18 tokens/s, about 7 s for a short explanation once loaded.

Provisional conclusion: quality ranks Gemma 3 4B, then Llama 3.2 3B, then Qwen2.5 3B; speed ranks them in the opposite order. Since the response never waits for the language model (BNF-01 applies to the response, not to the explanation), a few seconds more for a reliable explanation is acceptable. Gemma 3 4B is the provisional favourite, to be confirmed by the planned comparison on 20 to 30 lab alerts with the real prompt, and by measuring host memory with the lab VMs running, since 3.5 GB partly sits in system memory.
