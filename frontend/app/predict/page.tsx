"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import Gauge from "@/components/Gauge";
import Turbine from "@/components/Turbine";
import { Card, ErrorState, Loader, PageHeader, Select } from "@/components/ui";
import { EngineDetail, EngineInfo, Prediction, postJSON, prettyFeature, toRows, useApi } from "@/lib/api";
import { INK, SERIES, STATUS, axisProps, gridProps, tooltipProps } from "@/lib/theme";

const ICON = { healthy: "✓", warning: "!", critical: "✕" } as const;

export default function PredictPage() {
  const { data: engines, error } = useApi<EngineInfo[]>("/api/engines");
  const [engine, setEngine] = useState("");
  const [cycle, setCycle] = useState(1);
  const [pred, setPred] = useState<Prediction | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const testEngines = useMemo(() => (engines ?? []).filter((e) => e.split === "test"), [engines]);
  const info = engines?.find((e) => e.engine_id === engine);

  useEffect(() => {
    if (testEngines.length && !engine) {
      setEngine(testEngines[0].engine_id);
      setCycle(Math.round(testEngines[0].cycles * 0.6));
    }
  }, [testEngines, engine]);

  const { data: detail } = useApi<EngineDetail>(engine ? `/api/engines/${engine}` : null);

  // debounce prediction calls while dragging the slider
  useEffect(() => {
    if (!engine) return;
    const t = setTimeout(() => {
      postJSON<Prediction>("/api/predict", { engine_id: engine, cycle })
        .then((p) => { setPred(p); setErr(null); })
        .catch((e: Error) => setErr(e.message));
    }, 180);
    return () => clearTimeout(t);
  }, [engine, cycle]);

  const chart = useMemo(() => (detail?.predictions ? toRows(detail.predictions, ["cycle", "RUL_raw", "pred"]) : []), [detail]);

  if (error) return <ErrorState message={error} />;
  if (!engines) return <Loader label="Loading engines" />;

  const stage = pred?.status.stage ?? "healthy";
  const color = STATUS[stage];
  const maxRul = Math.max(...chart.map((r) => Number(r.RUL_raw)), 1);

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Inference" title="Predict Remaining Useful Life">
        Pick a held-out test engine and scrub through its life. The Flask API looks up the preprocessed
        features of that flight and returns the model&apos;s RUL estimate and a maintenance recommendation.
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <Card>
          <div className="flex flex-wrap items-end gap-4">
            <div className="w-56">
              <Select label="Engine" value={engine}
                onChange={(v) => { setEngine(v); const e = engines.find((x) => x.engine_id === v); if (e) setCycle(Math.min(cycle, e.cycles)); }}
                options={engines.map((e) => ({ value: e.engine_id, label: `${e.engine_id} · ${e.split === "test" ? "test" : "train"}` }))} />
            </div>
            <div className="text-xs text-muted">{info ? `${info.cycles} cycles recorded` : ""}</div>
          </div>
          <label className="mt-6 block text-xs text-muted">
            Flight cycle: <span className="font-mono text-base text-ink">{cycle}</span>
            <input type="range" min={1} max={info?.cycles ?? 100} value={cycle}
              onChange={(e) => setCycle(Number(e.target.value))} className="mt-2 w-full" />
          </label>

          <div className="mt-6 flex items-center justify-center gap-6">
            <div className="hidden sm:block">
              {/* engine spins slower as it degrades */}
              <Turbine size={110} speed={pred ? 0.8 + (1 - Math.min(pred.predicted_rul, 80) / 80) * 4 : 2} />
            </div>
            {pred && <Gauge value={pred.predicted_rul} max={Math.max(maxRul, pred.predicted_rul)} stage={stage} />}
          </div>

          {err && <p className="mt-4 text-sm" style={{ color: STATUS.critical }}>{err}</p>}

          <AnimatePresence mode="wait">
            {pred && (
              <motion.div key={stage} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
                className="mt-6 rounded-xl border p-4" style={{ borderColor: `${color}66`, background: `${color}14` }}>
                <div className="flex items-center gap-3">
                  <motion.span className="flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold"
                    style={{ background: color, color: stage === "warning" ? "#0b0b0b" : "#fff" }}
                    animate={stage === "critical" ? { scale: [1, 1.15, 1] } : {}} transition={{ repeat: Infinity, duration: 1 }}>
                    {ICON[stage]}
                  </motion.span>
                  <div>
                    <p className="font-semibold text-ink">{pred.status.label}</p>
                    <p className="text-sm text-ink2">{pred.status.action}</p>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-lg bg-raised p-2"><p className="text-muted">Predicted</p><p className="font-mono text-base text-ink">{pred.predicted_rul}</p></div>
                  <div className="rounded-lg bg-raised p-2"><p className="text-muted">Actual</p><p className="font-mono text-base text-ink">{pred.true_rul}</p></div>
                  <div className="rounded-lg bg-raised p-2"><p className="text-muted">Error</p><p className="font-mono text-base text-ink">{(pred.predicted_rul - pred.true_rul).toFixed(1)}</p></div>
                </div>
                <p className="mt-3 text-xs text-muted">Model: {pred.model}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>

        <div className="space-y-6">
          <Card title="Predicted vs actual RUL over the engine's life"
            subtitle={detail?.predictions ? "Shaded bands: warning (≤ 30) and critical (≤ 10) zones. Vertical line: selected cycle." : "Prediction trajectories are available for test engines."}>
            {detail?.predictions ? (
              <div className="h-80">
                <ResponsiveContainer>
                  <LineChart data={chart}>
                    <CartesianGrid {...gridProps} />
                    <ReferenceArea y1={0} y2={10} fill={STATUS.critical} fillOpacity={0.08} />
                    <ReferenceArea y1={10} y2={30} fill={STATUS.warning} fillOpacity={0.06} />
                    <XAxis dataKey="cycle" {...axisProps} />
                    <YAxis {...axisProps} width={40} />
                    <Tooltip {...tooltipProps} formatter={(v, n) => [Number(v).toFixed(1), String(n)]} labelFormatter={(l) => `cycle ${l}`} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <ReferenceLine x={cycle} stroke={INK.secondary} strokeDasharray="4 4" />
                    <Line dataKey="RUL_raw" name="Actual RUL" stroke={SERIES[1]} dot={false} strokeWidth={2} animationDuration={1200} />
                    <Line dataKey="pred" name="Predicted RUL" stroke={SERIES[0]} dot={false} strokeWidth={2} animationDuration={1500} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="py-10 text-center text-sm text-muted">Select a test engine to see its full trajectory.</p>
            )}
          </Card>

          {pred && (
            <Card title="Model inputs at this cycle" subtitle="Standardised values (z-scores) of the top-ranked features.">
              <div className="space-y-2">
                {Object.entries(pred.top_inputs).map(([f, v]) => (
                  <div key={f} className="grid grid-cols-[1fr_2fr_auto] items-center gap-3 text-xs">
                    <span className="truncate text-ink2">{prettyFeature(f)}</span>
                    <div className="relative h-2 rounded-full bg-raised">
                      <span className="absolute left-1/2 top-0 h-2 w-px bg-axis" />
                      <motion.span className="absolute top-0 h-2 rounded-full"
                        style={{ background: SERIES[0], left: v >= 0 ? "50%" : undefined, right: v < 0 ? "50%" : undefined }}
                        animate={{ width: `${Math.min(Math.abs(v), 3) / 3 * 50}%` }} transition={{ duration: 0.5 }} />
                    </div>
                    <span className="w-12 text-right font-mono text-ink">{v.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
