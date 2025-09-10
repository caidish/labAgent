# labAgent — Experiment Lab Framework (v1)

A pragmatic, lab‑ready architecture for a condensed‑matter **experiment** lab with MCP‑connected instruments (instrMCP, arXivDaily, etc.).

---

## 1) System Overview

**Control Plane**
- **Planner (Main Chatbot):** single entrypoint; converts intents/events into a **Task Graph** (DAG). Owns decomposition, routing, approvals.
- **Agent Pods (role‑scoped):**
  - **Workers:** instrument workflows via instrMCP/QCoDeS/RedPitaya/Nikon.
  - **Assistants:** admin ops (receipts, emails, onboarding/offboarding, calendar, travel).
  - **Science Consultants:** literature triage + wiki maintenance with citations.
  - **Information Center:** rolling briefs; “state of the experiment.”
- **Shared Services:** Event Bus, Memory Layer, Policy/Safety, Observability, Q‑DevBench.

**Data Plane**
- Structured logs, datasets, plots, reports, and wiki diffs flow through a content‑addressed artifact store with traceable lineage.

---

## 2) Planner Responsibilities
- Parse request → **TaskSpec** → expand to **TaskGraph**.
- For each node: select **Agent Pod** + **Tool Contract** (+ memory namespace) and set **runlevel**: `dry-run` → `sim` → `live`.
- Enforce gates: safety checks, human approvals, time windows, resource/budget caps.
- Emit **meeting packets** (daily, weekly, 1‑1) and action registers.

**TaskSpec (JSON) — minimal**
```json
{
  "task_id": "tg_2025-09-10_1532Z_001",
  "goal": "Cooldown device D14, then 2D gate map at 20 mK",
  "constraints": ["runlevel:live", "window:21:00-07:00", "max_power=2mW"],
  "artifacts": ["device_map/D14.json"],
  "owner": "jiaqi",
  "sla": "P1D",
  "tags": ["experiment", "cooldown", "gate-scan"]
}
```

**TaskGraph Node (JSON)**
```json
{
  "node_id": "cooldown_D14",
  "agent": "worker.cooldown",
  "tools": ["instrMCP.qcodes", "instrMCP.cryostat"],
  "params": {"target_T": "20 mK", "rate": "<=5 mK/min"},
  "guards": ["interlock.cryostat_ok", "shift=night"],
  "on_success": ["scan_gatemap_D14"],
  "on_fail": ["notify_owner", "attach_logs"]
}
```

---

## 3) Agent Pods (Role Design)

### 3.1 Workers (Instrument)
- **Inputs:** Task node + MCP tool contracts.
- **Execution model:** workflow state machine; emits structured logs + raw data pointers.
- **Safety:** hardware interlocks, rate limits, dry‑run/sim, SOS halt.

**Workflow States (YAML)**
```yaml
states:
  - name: PRECHECK
    guards: [interlock.cryostat_ok, power_ok]
    next: CONFIG
  - name: CONFIG
    action: instrMCP.configure_lockin
    next: RUN
  - name: RUN
    action: instrMCP.sweep
    next: SUMMARIZE
  - name: SUMMARIZE
    action: info_center.summarize_scan
    next: DONE
```

### 3.2 Assistants (Ops)
- **Receipts:** OCR → schema → policy check → export to finance; generate reimbursement packet.
- **Email:** templates (onboarding, seminar); label/assign; draft with review gates; SLA tracking.

### 3.3 Science Consultants (Knowledge Curation)
- Consume arXivDaily, lab notes, internal wiki; produce **diff‑based** updates with citations; maintain topic briefs tied to devices/phenomena.

### 3.4 Information Center (Rolling Intelligence)
- Generates **living docs**: Device status pages, gate‑instability memos, “This week in FCI/FQAH/WS₂‑2M,” and **morning briefs**.

---

## 4) Memory Design (Robust & Audit‑Friendly)

**Layers (namespaced):**
1. **Episodic (TTL):** run logs, chat turns, task graphs. KV + retention (30–90 days).
2. **Semantic (Vector/RAG):** papers, wiki pages, lab notes, schematics; chunked with signed citations.
3. **Procedural (State):** resumable checkpoints for workflows/instruments.
4. **Artifacts:** datasets, plots, reports, invoices, email threads — content‑addressed URIs.

**Namespace Convention**
```
ns = devices/<ID>/experiments/<YYYY-MM-DD>
ns = admin/receipts/<YYYY>/<MM>
ns = labwiki/<topic>
ns = papers/<arxiv_id>
```

**Memory Write Contract (JSON)**
```json
{
  "who": "worker.gatemap",
  "when": "2025-09-10T15:42:12Z",
  "ns": "devices/D14/experiments/2025-09-10",
  "type": "artifact.pointer",
  "keys": ["dataset", "plot", "logbook_entry"],
  "data": {
    "dataset": "s3://lab/D14/2025-09-10/gatemap.h5",
    "log": "obs://runs/tg_.../cooldown_D14.log",
    "summary_md": "obs://runs/tg_.../summary.md"
  },
  "lineage": {"task_id": "tg_...", "parents": ["cooldown_D14"]},
  "visibility": "lab"
}
```

**Retrieval Policy**
- Role‑scoped RAG by default; surfaced facts carry source links + hashes.
- Planner can demand **evidence** for any claim (“show citations”).

---

## 5) Meetings as Automation

**Daily Standup (auto‑compiled)**
- Inputs: last 24h task graphs, metric deltas, anomalies, PRs, inbox triage.
- Outputs: 1‑page brief + action items (owner, due date).

**Brief Schema (JSON)**
```json
{
  "brief_id": "brief_2025-09-10_lab",
  "sections": [
    {"title": "Experiment status", "bullets": ["..."]},
    {"title": "New results", "links": ["..."]},
    {"title": "Blockers/risks", "bullets": ["..."]},
    {"title": "ArXiv to read", "citations": ["..."]},
    {"title": "Admin", "bullets": ["..."]}
  ]
}
```

**1‑1 Brief**
```json
{
  "for": "jiaqi",
  "period": "2025-09-08..2025-09-10",
  "my_tasks": ["tg_..."],
  "blockers": ["cryostat valve leak investigation"],
  "approvals_needed": ["elevate runlevel for magnet ramp"],
  "suggestions": ["add drift compensation to next scan"]
}
```

---

## 6) Safety & Governance
- **Runlevels:** `dry-run` (default) → `sim` → `live` (explicit elevation + approval).
- **Capability Tokens:** fine‑grained permissions per MCP tool (e.g., DAC ≤ 50 mV; read‑only magnet).
- **Interlocks:** enforce bounds (ramp rates, pressures, power); 2‑person rule for risky ops.
- **Audit:** immutable event log (trace IDs), printable runbooks, post‑mortem bundles.

**Policy Snippets (YAML)**
```yaml
approvals:
  live_magnet_ramp: [pi, safety_officer]
limits:
  dac_vmax: 0.05   # Volts
  temp_cool_rate: 5e-3  # K/s
windows:
  night_ops: "21:00-07:00"
```

---

## 7) Inter‑Agent Protocol
```json
{
  "msg_id": "evt_2025-09-10_1602Z_42",
  "type": "task.dispatch|status.update|artifact.new|alert",
  "sender": "planner|worker.cooldown|assistant.finance|consultant.lit",
  "task_id": "tg_...|null",
  "ns": "devices/D14|admin/receipts",
  "payload": {"...": "..."},
  "requires_ack": true,
  "priority": "low|normal|high",
  "visibility": "lab|owner|pi-only"
}
```

---

## 8) Deployment & Repos
```
labAgent/
  planner/
  agents/
    worker/
    assistant/
    consultant/
    info-center/
  mcp/
  memory/
    episodic/
    semantic/
    artifacts/
  safety/
  ui/
  ops/
    eval/
    observability/
```

**.env.example**
```
ARTIFACT_S3_ENDPOINT=...
ARTIFACT_S3_BUCKET=lab
VECTOR_DB_URL=...
EVENT_BUS_URL=redis://...
```

---

## 9) Metrics & Evaluation
- **Experiment:** uptime, success rate, scan throughput, SNR, drift, % dry‑run vs live, incidents.
- **Knowledge:** citation coverage, hallucination rate, brief freshness, time‑to‑insight.
- **Admin:** receipt cycle time, email SLA, error rate.
- **Cost:** tokens, storage, instrument time, consumables.

---

## 10) M0→M4 Rollout
- **M0 — Baseline wiring:** planner stub; 1 Worker (sim), 1 Assistant, 1 Consultant; episodic memory; daily brief v0.
- **M1 — Safety & live:** interlocks + runlevels; first live overnight scan; artifact store; morning brief v1 with plots.
- **M2 — Knowledge & ops:** Science Consultant auto‑updates wiki with citations; Assistants complete receipts/email drafts E2E.
- **M3 — Reliability:** retries, checkpoint resume, SLA alerts, anomaly detection, approvals dashboard.
- **M4 — Scale & polish:** multi‑device scheduling, conflict resolution, budgets, full Q‑DevBench eval loop.

---

## 11) Ready‑to‑Use Prompts (Starter)

**Planner → Worker (gate map)**
```
Goal: 2D gate map on D14 at 20 mK.
Constraints: window 21:00–07:00, DAC ≤ 50 mV, lock‑in freq 73 Hz.
Deliverables: dataset + summary.md + PNG plot.
Runlevel: start in sim; elevate to live after interlocks pass.
```

**Assistant → Finance (receipt)**
```
Input: image/pdf of receipt.
Steps: OCR → normalize → policy check → fill reimbursement form → draft email → attach packet → await approval.
```

**Consultant → Wiki (paper digest)**
```
Input: arXiv:YYMM.NNNNN
Output: 200‑word summary + key equations + relevance to D14 + citations; propose wiki diff block.
```

---

### Notes
- Keep **evidence mode** on for Science Consultants (citations mandatory).
- Prefer **dry‑run** first for any Worker pipeline; Planner owns elevation.
- Use **namespaces** rigorously to make retrieval/policy simple.

