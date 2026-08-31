// Typed client for the Chimera API. In dev, next.config rewrites /api -> FastAPI.
// In prod set NEXT_PUBLIC_API_BASE to the deployed backend origin.

const BASE = process.env.NEXT_PUBLIC_API_BASE || "";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}
async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

// ---- types ----
export type Technique = {
  id: string; name: string; tactic: string; rails: string[]; channels: string[];
  genai_role: string; summary: string; kill_chain: string[]; signatures: string[];
  references: string[]; simulated: boolean; severity: number;
};
export type Taxonomy = {
  tactics: Record<string, string>;
  techniques: Technique[];
  attack_ids: string[];
};
export type OperatingPoint = {
  cost_optimal: { threshold: number; alerts_per_10k: number; value_detected_rate: number; expected_cost: number };
  review_cost_per_alert: number;
  total_fraud_value: number;
  sweep: { threshold: number; alerts_per_10k: number; value_detected_rate: number; expected_cost: number }[];
};
export type Metrics = {
  n_train: number; n_test: number; test_fraud: number; test_fraud_rate: number;
  supervised: {
    roc_auc: number; pr_auc: number; precision: number; recall: number; f1: number;
    fpr: number; threshold: number; fpr_at_90_recall: number;
    alerts_per_10k?: number; value_detected_rate?: number;
    confusion: { tp: number; fp: number; fn: number; tn: number };
  };
  blended: { roc_auc: number; pr_auc: number };
  operating_point?: OperatingPoint;
  curves: { roc: [number, number][]; pr: [number, number][] };
  per_vector_recall: Record<string, { recall: number; n: number }>;
  global_importance: { feature: string; importance: number }[];
  leave_one_out?: { vector: string; supervised_recall: number; novelty_recall: number; blended_recall: number }[];
};
export type LoopReport = {
  baseline_recall: number;
  baseline_per_vector: Record<string, number>;
  rounds: {
    round: number; pre_recall: number; post_recall: number;
    pre_per_vector: Record<string, number>; post_per_vector: Record<string, number>;
    evasive_params: Record<string, Record<string, number>>;
    ideation: { attack: string; variant: string; twist: string; footprint: string[]; mode: string; sources: string[] }[];
  }[];
  hardening_curve: { round: number; pre_recall: number; post_recall: number; threshold: number }[];
  trace?: string[];
  meta: Record<string, unknown> & { orchestration?: string };
};
export type LabEvent = {
  txn_id: string; ts: number; rail: string; channel: string; amount: number; mcc: number;
  auth_method: string; entry_mode: string; counterparty_type: string; account_age_days: number;
  is_new_counterparty: boolean; ip_asn_risk: number; session_seconds: number;
  amount_to_balance_ratio: number;
  agent_id?: string; agent_attested?: number; agent_trust?: number; mandate_cap_ratio?: number;
  is_fraud: number; vector: string;
  risk: number; supervised_prob: number; novelty_score: number;
  explanation?: { feature: string; contribution: number; value: number }[];
};
export type LabResult = {
  attack_id: string; technique: Technique | null; threshold: number;
  summary: { n_fraud: number; n_legit_shown: number; recall: number; false_positives: number; fp_rate: number };
  events: LabEvent[];
};
export type GraphSnapshot = {
  nodes: { id: string; fraud_edges: number; total_edges: number; suspicious: boolean }[];
  edges: { source: string; target: string; amount: number; risk: number; is_fraud: number; vector: string }[];
  threshold: number;
};
export type Ideation = {
  variant_name: string; technique_id: string; novel_twist: string;
  param_directions: Record<string, unknown>; observable_footprint: string[];
  rationale: string; sources: string[]; mode: string;
};

export const api = {
  health: () => get<{ status: string; detector_loaded: boolean }>("/api/health"),
  taxonomy: () => get<Taxonomy>("/api/taxonomy"),
  metrics: () => get<Metrics>("/api/metrics"),
  loop: () => get<LoopReport>("/api/loop"),
  simMeta: () => get<any>("/api/sim-meta"),
  attackParams: () => get<Record<string, Record<string, { min: number; max: number; default: number; desc: string }>>>("/api/attack-params"),
  attackLab: (attack_id: string, intensity = 1, params?: Record<string, number>) =>
    post<LabResult>("/api/attack-lab", { attack_id, intensity, params }),
  ideation: (attack_id: string, params?: Record<string, number>) =>
    post<Ideation>("/api/ideation", { attack_id, params }),
  graph: () => get<GraphSnapshot>("/api/graph"),
  validation: () => get<Validation>("/api/validation"),
};

export type Validation = {
  external?: {
    dataset: string; n: number; n_fraud: number; fraud_rate: number;
    supervised: { roc_auc: number; pr_auc: number };
    ensemble: { roc_auc: number; pr_auc: number };
    best_single_feature_auc: number;
    fidelity_vs_synthetic?: { synthetic_best_single_feature_auc: number };
  };
  gnn?: {
    gradient_boosting: { roc_auc: number; pr_auc: number };
    graphsage_gnn: { roc_auc: number; pr_auc: number };
    graphsage_inductive?: { roc_auc: number; pr_auc: number };
    pr_auc_lift: number; pr_auc_lift_inductive?: number;
    n_nodes: number; n_fraud_nodes: number;
  };
  point_in_time?: {
    batch: { pr_auc: number; recall: number };
    causal: { pr_auc: number; recall: number };
  };
  rigor?: {
    stability_across_seeds?: {
      seeds: number[];
      roc_auc: { mean: number; std: number };
      recall: { mean: number; std: number };
    };
    component_ablation?: Record<string, { pr_auc: number }>;
    latency?: { generation_events_per_sec: number; feature_build_events_per_sec: number; inference_events_per_sec: number };
  };
  benchmark?: {
    baselines: Record<string, { roc_auc: number; pr_auc: number }>;
    closed_loop_on_real: { baseline_recall: number; under_evasion: number; after_retrain: number };
  };
  attack_chains?: {
    note?: string;
    finding?: string;
    single_stage_cold: { supervised_only: number; full_ensemble: number };
    chained: { supervised_only: number; full_ensemble: number };
    chained_after_retrain: { supervised_only: number; full_ensemble: number };
  };
};
