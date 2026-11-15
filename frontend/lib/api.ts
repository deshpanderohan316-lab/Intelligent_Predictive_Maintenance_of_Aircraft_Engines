"use client";

import { useEffect, useState } from "react";

// ---------------------------------------------------------------- types
export type Metrics = { MAE: number; RMSE: number; R2: number; NASA_score: number };

export type Overview = {
  datasets: string[];
  rows_1hz: number;
  rows_cycle: number;
  engines: number;
  features_engineered: number;
  features_selected: number;
  best_model: string;
  best_test: Metrics;
  pipeline_seconds: number;
};

export type PipelineStep = {
  key: string;
  title: string;
  description: string;
  seconds: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  details: Record<string, any>;
};

export type PreprocessingReport = {
  generated_at: string;
  total_seconds: number;
  config: Record<string, unknown>;
  steps: PipelineStep[];
};

export type EngineInfo = { engine_id: string; split: string; cycles: number };

export type EngineDetail = {
  engine_id: string;
  series: Record<string, (number | string)[]>;
  predictions: Record<string, (number | string)[]> | null;
};

export type ModelResult = { model: string; cv: Metrics; test: Metrics; train_seconds: number };

export type ModelsReport = {
  best_model: string;
  cv_folds: number;
  selection_metric: string;
  n_train_rows: number;
  n_test_rows: number;
  results: ModelResult[];
  feature_importance: { feature: string; importance: number }[];
};

export type EdaSummary = {
  n_engines: number;
  n_cycles: number;
  lifetimes: { engine_id: string; cycles: number; split: string; onset: number }[];
  rul_histogram: number[];
  rul_bins: number[];
  feature_rul_spearman: Record<string, number>;
  flight_class_counts: Record<string, number>;
  sensors: string[];
};

export type Prediction = {
  engine_id: string;
  cycle: number;
  split: string;
  predicted_rul: number;
  true_rul: number;
  max_cycle: number;
  model: string;
  status: { stage: "healthy" | "warning" | "critical"; label: string; action: string };
  top_inputs: Record<string, number>;
};

// ---------------------------------------------------------------- fetch helpers
export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, { cache: "no-store" });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error || `${res.status} ${res.statusText}`);
  return body as T;
}

export async function postJSON<T>(path: string, data: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error || `${res.status} ${res.statusText}`);
  return body as T;
}

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);

  useEffect(() => {
    if (!path) return;
    let alive = true;
    setLoading(true);
    setError(null);
    getJSON<T>(path)
      .then((d) => alive && setData(d))
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [path]);

  return { data, error, loading };
}

// ---------------------------------------------------------------- helpers
/** Turn a column-oriented series {a:[..], b:[..]} into recharts rows [{a,b},..]. */
export function toRows(series: Record<string, (number | string)[]>, keys: string[]) {
  const n = series[keys[0]]?.length ?? 0;
  return Array.from({ length: n }, (_, i) => {
    const row: Record<string, number | string> = {};
    keys.forEach((k) => (row[k] = series[k]?.[i]));
    return row;
  });
}

export const fmt = (n: number, d = 0) =>
  n.toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d });

export const prettyFeature = (f: string) =>
  f
    .replace(/^r_/, "")
    .replace(/_mean__/, " · ")
    .replace(/_mean$/, " residual mean")
    .replace(/_std$/, " residual std")
    .replace(/roll_mean/, "rolling mean")
    .replace(/roll_std/, "rolling std")
    .replace(/ewm/, "EWMA")
    .replace(/slope/, "slope")
    .replace(/delta/, "drift from baseline")
    .replace(/^op_/, "flight: ")
    .replace(/_/g, " ");
