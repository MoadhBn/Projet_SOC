# Phase 3: AI engine

Status: early work started on 16 October 2026, while phase 1 waits for laptop 1. The phase itself starts after phase 2.

This file is the journal of phase 3.

## 1. Objective

Build the analysis API on the laptop 2 host: the fixed score formula, the anomaly model (Isolation Forest) and the explanation by a local language model with RAG. The language model only summarises, labels and justifies; it never computes the score and never triggers an action.

## 2. Early work: local language model

### Installation

| Item | Value |
|---|---|
| Ollama | Installed on the Windows host (official installer from ollama.com), listening on `localhost:11434` only |
| Why on the host | VMware Workstation cannot give the graphics card to a VM |
| Exposure | Ollama is not opened to the network: only the analysis API, running on the same host, will call it |
| GPU | NVIDIA GeForce RTX 2050, 4096 MiB video memory, driver 577.05 (Ollama requires 551.61 or newer) |

### First test of the candidate models (brief, section 12: "French output quality of the 3B models")

Same prompt for each model, a fictitious alert: 25 failed SSH logins in 60 seconds from 10.10.30.10 to 10.10.20.20, account root, ATT&CK T1110, asking for a two-sentence summary in French for a SOC analyst. This is a first impression, not the comparison planned on 20 to 30 lab alerts.

| Measure | Llama 3.2 3B | Qwen2.5 3B |
|---|---|---|
| French | Correct and readable | Poor: calls the attacker's IP address a "système d'exploitation", awkward phrasing, three sentences instead of two |
| Accuracy | Restates the facts correctly, but calls the attack "phishing ou brute-force": phishing is invented | Reaches the right conclusion (brute force) but invents "T1110 de l'Umbrella" |
| Generation speed | 37 tokens/s | 49.5 tokens/s |
| Load time (first call) | 11.9 s | 5.0 s |
| Total time, first call | 15.0 s (about 3 s once the model is loaded) | 7.3 s (about 2 s once loaded) |
| Placement | 20 % CPU / 80 % GPU, 2.9 GB in total | 100 % GPU, 2.2 GB in total |
| Video memory used | 2325 MiB of 4096 MiB | 2153 MiB of 4096 MiB |

Observations:

- The invented "phishing" is a small but typical error of a 3B model. It supports the design choice that the model never decides: its label can only raise the score, and the ATT&CK technique comes from the Wazuh rule, not from the model.
- The model does not fit entirely in video memory with the default context of 4096 tokens: Ollama keeps 20 % on the processor. The speed stays acceptable for a summary of about 150 tokens. Reducing the context window is the first lever if a fully GPU placement is needed; to be tested with the real prompt size (alert plus RAG passages).
- The first call includes loading the model (about 12 s). In operation the model should stay loaded, or the response time of the first alert after an idle period will be longer.

First reading of the two candidates:

- **Llama 3.2 3B** writes better French and makes one invention ("phishing"); it is slower and does not fit entirely on the graphics card.
- **Qwen2.5 3B** is faster and fits entirely on the card, but its French is clearly weaker and it invents a reference ("Umbrella").
- Neither result is final: the prompt was a single bare sentence. The real prompt will add instructions, a fixed JSON output, a low temperature and RAG passages, which usually reduce inventions. The brief also allows a 4B-class fallback (Gemma 3 4B, Phi-3.5 mini) if quality is too poor; Gemma 3 4B is worth adding to the comparison for its French.
