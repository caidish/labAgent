Got it—here are inline visualizations (no canvas).

### 1) Example Task DAG — Overnight Gate-Map (Device D14)

```mermaid
graph LR
  A[Intake\nRequest→TaskSpec]
  B[Prechecks\nresources, window, budget]
  C{Approval Gate\nElevate runlevel?}
  D[Cooldown D14\nworker.cooldown]
  E[Lock-in Config\nworker.lockin_config]
  F[2D Gate Sweep\nworker.sweep]
  G[Upload Artifacts\nartifact.store]
  H[Summarize Scan\ninfo_center.summarize]
  I[Wiki Diff Proposal\nconsultant.wiki_update]
  J[Morning Brief\ninfo_center.brief]

  A --> B --> C
  C -->|approved| D --> E --> F --> G --> H --> J
  H --> I

  %% Guards / Interlocks
  GI1[interlock.cryostat_ok]
  GI2[shift: night_ops]
  GI3[capability: DAC ≤ 50 mV]

  D -.requires.-> GI1
  E -.requires.-> GI3
  A -.requires.-> GI2
```

### 2) Generic Planner DAG Template

```mermaid
graph TD
  subgraph Intake
    T0[Intake]
    T1[Parse → TaskSpec]
  end

  subgraph Planning
    P0[Expand → TaskGraph]
    P1[Resolve deps]
    P2[Assign agents/tools]
    P3[Set runlevels]
  end

  subgraph Execution
    X1[Node: PRECHECK]
    X2[Node: CONFIG]
    X3[Node: RUN]
    X4[Node: POST]
  end

  subgraph Outputs
    O1[Artifacts]
    O2[Briefs]
    O3[Wiki Diffs]
  end

  T0-->T1-->P0-->P1-->P2-->P3
  P3-->X1-->X2-->X3-->X4
  X4-->O1 & O2 & O3
```

### 3) Conditional Branches & Retries

```mermaid
graph LR
  A[Start] --> B{Interlocks pass?}
  B -- no --> R1[Auto-remediate]\n--retry--> B
  B -- yes --> C[Configure Instruments]
  C --> D{SNR ≥ threshold?}
  D -- no --> H1[Adjust params]\n--retry--> C
  D -- yes --> E[Run Sweep]
  E --> F[Upload + Index]
  F --> G[Summarize + Notify]
```

### 4) Multi-Device Scheduling with Resource Locks

```mermaid
graph TD
  subgraph Device D14
    d1[Cooldown] --> d2[Sweep A]
  end
  subgraph Device D22
    e1[Anneal] --> e2[Sweep B]
  end

  classDef lock fill:#eee,stroke:#999,stroke-width:1px
  L1[[Cryostat Slot]]:::lock
  L2[[Lock-in #1]]:::lock

  d1 --> L1 --> d2
  e1 --> L1 --> e2
  d2 --> L2
  e2 --> L2
```