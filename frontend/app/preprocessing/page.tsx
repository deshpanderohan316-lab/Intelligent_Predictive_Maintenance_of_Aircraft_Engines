"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Card, Counter, ErrorState, Loader, PageHeader, Pill, Select } from "@/components/ui";
import {
  EngineDetail, EngineInfo, PipelineStep, PreprocessingReport, fmt, prettyFeature, toRows, useApi,
} from "@/lib/api";
import { INK, SERIES, STATUS, axisProps, gridProps, tooltipProps } from "@/lib/theme";

// ============================================================== page
export default function PreprocessingPage() {
  const { data: report, error } = useApi<PreprocessingReport>("/api/preprocessing");
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing || !report) return;
    const id = setInterval(() => {
      setActive((a) => {
        if (a >= report.steps.length - 1) {
          setPlaying(false);
          return a;
        }
        return a + 1;
      });
    }, 3200);
    return () => clearInterval(id);
  }, [playing, report]);

  if (error) return <ErrorState message={error} />;
  if (!report) return <Loader label="Loading preprocessing report" />;

  const step = report.steps[active];
  const agg = report.steps.find((s) => s.key === "clean_residual_aggregate")!.details;
  const feat = report.steps.find((s) => s.key === "features")!.details;
  const sel = report.steps.find((s) => s.key === "selection")!.details;

  return (
    <div className="space-y-10">
      <PageHeader eyebrow="Core of the project" title="Data preprocessing pipeline">
        N-CMAPSS records every engine second-by-second across whole flights. Before any model can learn
        degradation we must clean it, remove the effect of flight conditions, compress it per flight, label it and
        engineer time-series features — all while fitting every transform on training engines only.
      </PageHeader>

      <DataFunnel
        stages={[
          { label: "1 Hz samples", value: agg.rows_1hz_in },
          { label: "flight cycles", value: agg.rows_cycle_out },
          { label: "engineered features", value: feat.n_features },
          { label: "selected features", value: sel.n_selected },
        ]}
      />

      {/* -------------------------------------------- stepper */}
      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <div className="lg:sticky lg:top-20 lg:self-start">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs uppercase tracking-wider text-muted">{report.steps.length} steps · {report.total_seconds}s total</p>
            <button
              onClick={() => {
                if (!playing && active === report.steps.length - 1) setActive(0);
                setPlaying((p) => !p);
              }}
              className="rounded-full border border-line px-3 py-1 text-xs text-ink2 transition hover:border-accent hover:text-ink"
            >
              {playing ? "❚❚ Pause" : "▶ Play pipeline"}
            </button>
          </div>
          <ol className="relative flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:gap-1 lg:overflow-visible">
            {report.steps.map((s, i) => (
              <li key={s.key} className="relative shrink-0">
                <button
                  onClick={() => { setActive(i); setPlaying(false); }}
                  className={`relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                    i === active ? "text-ink" : i < active ? "text-ink2" : "text-muted hover:text-ink2"
                  }`}
                >
                  {i === active && (
                    <motion.span layoutId="step-bg" className="absolute inset-0 rounded-xl border border-accent/50 bg-accent/10"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }} />
                  )}
                  <span className={`relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono text-xs ${
                    i <= active ? "bg-accent text-white" : "bg-raised text-muted"}`}>
                    {i < active ? "✓" : i + 1}
                  </span>
                  <span className="relative z-10 whitespace-nowrap lg:whitespace-normal">{s.title}</span>
                </button>
              </li>
            ))}
          </ol>
          <div className="mt-3 hidden h-1 overflow-hidden rounded-full bg-raised lg:block">
            <motion.div className="h-full bg-accent" animate={{ width: `${((active + 1) / report.steps.length) * 100}%` }} />
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step.key}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="rounded-2xl border border-line bg-surface p-6"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-xl font-semibold text-ink">
                <span className="mr-2 font-mono text-accent">{String(active + 1).padStart(2, "0")}</span>
                {step.title}
              </h2>
              <Pill>{step.seconds}s</Pill>
            </div>
            <p className="mt-2 text-ink2">{step.description}</p>
            <div className="mt-6">
              <StepDetail step={step} />
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      <BeforeAfter />
    </div>
  );
}

// ============================================================== funnel
function DataFunnel({ stages }: { stages: { label: string; value: number }[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {stages.map((s, i) => (
        <motion.div
          key={s.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.15 }}
          className="relative rounded-2xl border border-line bg-surface p-5"
        >
          <p className="font-mono text-2xl font-bold text-ink md:text-3xl"><Counter value={s.value} /></p>
          <p className="text-xs uppercase tracking-wider text-muted">{s.label}</p>
          {i < stages.length - 1 && (
            <div className="absolute -right-3 top-1/2 z-10 hidden -translate-y-1/2 md:block">
              <motion.span
                className="block h-2 w-2 rounded-full bg-accent"
                animate={{ x: [-6, 10], opacity: [0, 1, 0] }}
                transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.3 }}
              />
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}

// ============================================================== per-step views
function KV({ items }: { items: [string, string | number][] }) {
  return (
    <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {items.map(([k, v]) => (
        <div key={k} className="rounded-xl bg-raised p-3">
          <dt className="text-xs text-muted">{k}</dt>
          <dd className="mt-1 font-mono text-lg text-ink">{typeof v === "number" ? fmt(v, Number.isInteger(v) ? 0 : 2) : v}</dd>
        </div>
      ))}
    </dl>
  );
}

function PreviewTable({ preview }: { preview?: { columns: string[]; rows: (string | number | null)[][] } }) {
  if (!preview) return null;
  return (
    <div className="mt-5 overflow-x-auto rounded-xl border border-line">
      <table className="w-full text-left font-mono text-xs">
        <thead className="bg-raised text-muted">
          <tr>{preview.columns.map((c) => <th key={c} className="px-3 py-2 font-medium">{c}</th>)}</tr>
        </thead>
        <tbody>
          {preview.rows.map((r, i) => (
            <motion.tr key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 * i }}
              className="border-t border-line text-ink2">
              {r.map((v, j) => <td key={j} className="whitespace-nowrap px-3 py-2">{v ?? "—"}</td>)}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StepDetail({ step }: { step: PipelineStep }) {
  const d = step.details;
  switch (step.key) {
    case "inventory":
      return (
        <div className="space-y-5">
          <div className="grid gap-2 md:grid-cols-2">
            {(d.files as { name: string; size_gb: number; ok: boolean; rows_dev?: number; rows_test?: number }[]).map((f, i) => (
              <motion.div key={f.name} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                  d.selected.includes(f.name) ? "border-accent/60 bg-accent/10" : "border-line bg-raised"}`}>
                <span className="font-mono text-ink">{f.name}</span>
                <span className="flex items-center gap-2 text-xs text-muted">
                  {f.size_gb} GB
                  {f.ok ? (
                    <span style={{ color: STATUS.healthy }}>● {fmt((f.rows_dev ?? 0) + (f.rows_test ?? 0))} rows</span>
                  ) : (
                    <span style={{ color: STATUS.critical }}>✕ corrupt / truncated</span>
                  )}
                </span>
              </motion.div>
            ))}
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {Object.entries(d.variables as Record<string, string[]>).map(([group, vars]) => (
              <div key={group} className="rounded-xl bg-raised p-3">
                <p className="text-xs text-muted">{group}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">{vars.map((v) => <Pill key={v}>{v}</Pill>)}</div>
              </div>
            ))}
          </div>
        </div>
      );

    case "baseline_fit": {
      const r2 = d.r2_healthy_holdout as Record<string, number>;
      return (
        <div className="space-y-5">
          <KV items={[["Healthy seconds used", d.healthy_samples_used], ["Inputs", (d.inputs as string[]).join(", ")],
            ["Polynomial degree", 3], ["Outputs", (d.outputs as string[]).length]]} />
          <p className="text-sm text-ink2">
            Variance of each sensor explained by flight condition alone on held-out <em>healthy</em> data. Almost
            all of the raw signal is flight condition — the residual that is left is where degradation lives.
          </p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 md:grid-cols-7">
            {Object.entries(r2).map(([s, v], i) => (
              <motion.div key={s} initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: i * 0.05, type: "spring" }} className="rounded-xl bg-raised p-3 text-center">
                <p className="text-xs text-muted">{s}</p>
                <p className="font-mono text-sm text-ink">{(v * 100).toFixed(3)}%</p>
              </motion.div>
            ))}
          </div>
          <p className="rounded-xl border border-line p-3 font-mono text-xs text-ink2">
            r = (sensor − f(alt, Mach, TRA, T2)) / σ<sub>healthy</sub>
          </p>
        </div>
      );
    }

    case "clean_residual_aggregate": {
      const q = Object.entries(d.quality as Record<string, Record<string, number>>);
      return (
        <div className="space-y-5">
          <KV items={[["1 Hz rows in", d.rows_1hz_in], ["Cycle rows out", d.rows_cycle_out],
            ["Compression", `${fmt(d.compression_ratio)}×`], ["Duplicate keys", d.duplicate_cycle_keys]]} />
          <div className="grid gap-3 md:grid-cols-2">
            {q.map(([k, v]) => (
              <div key={k} className="rounded-xl bg-raised p-3 text-sm">
                <p className="font-mono text-ink">{k}</p>
                <p className="mt-1 text-xs text-muted">
                  NaN {v.nan_rows} · Inf {v.inf_rows} · non-physical {v.non_physical_rows} · removed {v.removed_pct}%
                </p>
              </div>
            ))}
          </div>
          <FlightTrace />
          <PreviewTable preview={d.preview} />
        </div>
      );
    }

    case "labels": {
      const counts = d.health_stage_counts as Record<string, number>;
      const rows = ["healthy", "warning", "critical"].map((k) => ({ stage: k, count: counts[k] ?? 0 }));
      return (
        <div className="space-y-5">
          <KV items={[["Engines", d.engines], ["RUL range", `${d.rul_min} – ${d.rul_max}`], ["Mean RUL", d.rul_mean],
            ["Label mismatches", d.label_mismatch_rows]]} />
          <div className="h-48">
            <ResponsiveContainer>
              <BarChart data={rows} layout="vertical" margin={{ left: 10, right: 30 }}>
                <XAxis type="number" {...axisProps} />
                <YAxis type="category" dataKey="stage" {...axisProps} width={70} />
                <Tooltip {...tooltipProps} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} animationDuration={900}>
                  {rows.map((r) => <Cell key={r.stage} fill={STATUS[r.stage as keyof typeof STATUS]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-muted">Health stage: healthy &gt; 30 cycles · warning 11–30 · critical ≤ 10.</p>
        </div>
      );
    }

    case "features": {
      const g = d.groups as { operating_condition: string[]; residual_mean: string[]; residual_std: string[]; temporal: number };
      const blocks = [
        { label: "Flight profile", n: g.operating_condition.length, eg: "duration, max altitude, mean Mach…" },
        { label: "Residual means", n: g.residual_mean.length, eg: "per-sensor health residual per flight" },
        { label: "Residual std", n: g.residual_std.length, eg: "within-flight instability" },
        { label: "Temporal", n: g.temporal, eg: "rolling mean/std, EWMA, slope, drift" },
      ];
      return (
        <div className="space-y-5">
          <div className="grid gap-3 md:grid-cols-4">
            {blocks.map((b, i) => (
              <motion.div key={b.label} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                className="rounded-xl bg-raised p-4">
                <p className="font-mono text-3xl text-ink"><Counter value={b.n} /></p>
                <p className="mt-1 text-sm text-ink">{b.label}</p>
                <p className="text-xs text-muted">{b.eg}</p>
              </motion.div>
            ))}
          </div>
          <p className="text-sm text-ink2">
            Total: <span className="font-mono text-ink">{d.n_features}</span> features (+ age in cycles). Every window
            looks backwards only, so a deployed model never peeks at future flights.
          </p>
        </div>
      );
    }

    case "split":
      return (
        <div className="grid gap-4 md:grid-cols-2">
          {[["Train (development) engines", d.train_engines, d.train_rows, SERIES[0]],
            ["Test engines (held out)", d.test_engines, d.test_rows, SERIES[1]]].map(([label, engines, rows, color]) => (
            <div key={label as string} className="rounded-xl bg-raised p-4">
              <p className="text-sm text-ink">{label as string}</p>
              <p className="text-xs text-muted">{fmt(rows as number)} cycle rows</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {(engines as string[]).map((e, i) => (
                  <motion.span key={e} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.06, type: "spring" }}>
                    <Pill color={color as string}>{e}</Pill>
                  </motion.span>
                ))}
              </div>
            </div>
          ))}
        </div>
      );

    case "winsorize":
      return <KV items={[["Values clipped (train)", d.values_clipped_train], ["Values clipped (test)", d.values_clipped_test]]} />;

    case "selection": {
      const dc = d.dropped_counts as Record<string, number>;
      const top = (d.selected as { feature: string; abs_spearman: number }[]).slice(0, 15);
      return (
        <div className="space-y-5">
          <KV items={[["Low variance", dc.low_variance], ["Redundant (|r| > 0.95)", dc.redundant], ["Over cap", dc.over_cap], ["Selected", d.n_selected]]} />
          <div className="h-[420px]">
            <ResponsiveContainer>
              <BarChart data={top.map((t) => ({ ...t, name: prettyFeature(t.feature) }))} layout="vertical" margin={{ left: 20, right: 30 }}>
                <CartesianGrid {...gridProps} horizontal={false} vertical />
                <XAxis type="number" domain={[0, 1]} {...axisProps} />
                <YAxis type="category" dataKey="name" {...axisProps} width={210} tick={{ fill: INK.secondary, fontSize: 11 }} />
                <Tooltip {...tooltipProps} cursor={{ fill: "rgba(255,255,255,0.04)" }} formatter={(v) => [Number(v).toFixed(3), "|Spearman ρ| with RUL"]} />
                <Bar dataKey="abs_spearman" fill={SERIES[0]} radius={[0, 4, 4, 0]} animationDuration={1000} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      );
    }

    case "scaling": {
      const rows = Object.keys(d.mean_before).map((k) => ({ feature: prettyFeature(k), mean: d.mean_before[k], std: d.std_before[k] }));
      return (
        <div className="space-y-5">
          <div className="overflow-x-auto rounded-xl border border-line">
            <table className="w-full text-left text-sm">
              <thead className="bg-raised text-xs text-muted">
                <tr><th className="px-3 py-2">Feature</th><th className="px-3 py-2">mean → 0</th><th className="px-3 py-2">std → 1</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.feature} className="border-t border-line text-ink2">
                    <td className="px-3 py-2">{r.feature}</td>
                    <td className="px-3 py-2 font-mono">{r.mean}</td>
                    <td className="px-3 py-2 font-mono">{r.std}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <PreviewTable preview={d.preview} />
        </div>
      );
    }
    default:
      return <pre className="overflow-x-auto text-xs text-ink2">{JSON.stringify(d, null, 2)}</pre>;
  }
}

// ============================================================== 1 Hz flight trace
function FlightTrace() {
  const { data } = useApi<Record<string, number>[]>("/api/preprocessing/flight-trace");
  if (!data) return null;
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {[
        { key: "alt", title: "Altitude (ft) — flight profile", color: SERIES[2] },
        { key: "T48", title: "Raw T48 (°R) — follows the profile", color: SERIES[1] },
        { key: "r_T48", title: "T48 residual (σ) — flat when healthy", color: SERIES[0] },
      ].map((c) => (
        <div key={c.key} className="rounded-xl bg-raised p-3">
          <p className="mb-2 text-xs text-ink2">{c.title}</p>
          <div className="h-36">
            <ResponsiveContainer>
              <LineChart data={data}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="t" {...axisProps} tickFormatter={(t) => `${Math.round(t / 60)}m`} minTickGap={30} />
                <YAxis {...axisProps} width={45} domain={["auto", "auto"]} />
                <Tooltip {...tooltipProps} labelFormatter={(t) => `t = ${t}s`} />
                <Line dataKey={c.key} stroke={c.color} dot={false} strokeWidth={2} animationDuration={1500} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================== before / after
function BeforeAfter() {
  const { data: engines } = useApi<EngineInfo[]>("/api/engines");
  const [selected, setSelected] = useState<string[]>([]);
  const [sensor, setSensor] = useState("T48");
  const [details, setDetails] = useState<Record<string, EngineDetail>>({});

  useEffect(() => {
    if (engines && !selected.length) setSelected(engines.filter((e) => e.split === "dev").slice(0, 3).map((e) => e.engine_id));
  }, [engines, selected.length]);

  useEffect(() => {
    selected.filter((id) => !details[id]).forEach((id) =>
      fetch(`/api/engines/${id}`).then((r) => r.json()).then((d: EngineDetail) => setDetails((p) => ({ ...p, [id]: d }))));
  }, [selected, details]);

  const merged = useMemo(() => {
    const byCycle = new Map<number, Record<string, number>>();
    selected.forEach((id) => {
      const s = details[id]?.series;
      if (!s) return;
      toRows(s, ["cycle", `raw_${sensor}_mean`, `r_${sensor}_mean`]).forEach((r) => {
        const c = r.cycle as number;
        const row = byCycle.get(c) ?? { cycle: c };
        row[`raw:${id}`] = r[`raw_${sensor}_mean`] as number;
        row[`res:${id}`] = r[`r_${sensor}_mean`] as number;
        byCycle.set(c, row);
      });
    });
    return Array.from(byCycle.values()).sort((a, b) => a.cycle - b.cycle);
  }, [selected, details, sensor]);

  if (!engines) return null;
  const sensors = ["T24", "T30", "T48", "T50", "P15", "P2", "P21", "P24", "Ps30", "P40", "P50", "Nf", "Nc", "Wf"];

  return (
    <Card title="Why operating-condition normalisation matters"
      subtitle="Per-flight mean of a sensor over each engine's life. Left: raw values swing with altitude, Mach and throttle. Right: healthy-baseline residuals reveal a clean, monotonic degradation trend.">
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <Select label="Sensor" value={sensor} onChange={setSensor} options={sensors.map((s) => ({ value: s, label: s }))} />
        <div className="flex flex-wrap gap-2">
          {engines.map((e) => {
            const on = selected.includes(e.engine_id);
            const idx = selected.indexOf(e.engine_id);
            return (
              <button key={e.engine_id}
                onClick={() => setSelected((s) => on ? s.filter((x) => x !== e.engine_id) : s.length < 4 ? [...s, e.engine_id] : s)}
                className={`rounded-full border px-3 py-1 text-xs transition ${on ? "border-ink2 text-ink" : "border-line text-muted hover:text-ink2"}`}>
                {on && <span className="mr-1.5 inline-block h-2 w-2 rounded-full" style={{ background: SERIES[idx] }} />}
                {e.engine_id}
              </button>
            );
          })}
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {(["raw", "res"] as const).map((kind) => (
          <div key={kind} className="rounded-xl bg-raised p-3">
            <p className="mb-2 text-sm text-ink2">{kind === "raw" ? `Raw ${sensor} (flight mean)` : `${sensor} residual (σ from healthy baseline)`}</p>
            <div className="h-64">
              <ResponsiveContainer>
                <LineChart data={merged}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="cycle" {...axisProps} label={{ value: "flight cycle", fill: INK.muted, fontSize: 11, position: "insideBottom", offset: -2 }} />
                  <YAxis {...axisProps} width={50} domain={["auto", "auto"]} />
                  <Tooltip {...tooltipProps} formatter={(v, n) => [Number(v).toFixed(3), String(n).split(":")[1]]} />
                  <Legend formatter={(v: string) => v.split(":")[1]} wrapperStyle={{ fontSize: 11 }} />
                  {selected.map((id, i) => (
                    <Line key={id} dataKey={`${kind}:${id}`} stroke={SERIES[i]} dot={false} strokeWidth={2} connectNulls animationDuration={1200} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
