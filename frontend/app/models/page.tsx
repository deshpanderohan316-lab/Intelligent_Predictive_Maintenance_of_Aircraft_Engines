"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, ErrorState, Loader, PageHeader } from "@/components/ui";
import { Metrics, ModelsReport, prettyFeature, useApi } from "@/lib/api";
import { INK, SERIES, axisProps, gridProps, tooltipProps } from "@/lib/theme";

const METRICS: { key: keyof Metrics; label: string; better: "lower" | "higher" }[] = [
  { key: "RMSE", label: "RMSE", better: "lower" },
  { key: "MAE", label: "MAE", better: "lower" },
  { key: "R2", label: "R²", better: "higher" },
  { key: "NASA_score", label: "NASA score", better: "lower" },
];

export default function ModelsPage() {
  const { data, error } = useApi<ModelsReport>("/api/models");
  const [metric, setMetric] = useState<keyof Metrics>("RMSE");
  const [set, setSet] = useState<"test" | "cv">("test");

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loader label="Loading model comparison" />;

  const m = METRICS.find((x) => x.key === metric)!;
  const rows = data.results
    .map((r) => ({ model: r.model, value: r[set][metric] }))
    .sort((a, b) => (m.better === "lower" ? a.value - b.value : b.value - a.value));
  const imp = data.feature_importance.slice(0, 12).map((f) => ({ ...f, name: prettyFeature(f.feature) }));

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Model comparison" title="Which regressor estimates RUL best?">
        {data.results.length} regressors, {data.cv_folds}-fold engine-grouped cross-validation on the training engines
        for model selection, then a single evaluation on the held-out test engines. Selected model:{" "}
        <span className="font-semibold text-ink">{data.best_model}</span> (lowest {data.selection_metric}).
      </PageHeader>

      <Card>
        <div className="mb-5 flex flex-wrap items-center gap-2">
          {METRICS.map((x) => (
            <button key={x.key} onClick={() => setMetric(x.key)}
              className={`relative rounded-full px-3 py-1.5 text-sm ${metric === x.key ? "text-ink" : "text-muted hover:text-ink2"}`}>
              {metric === x.key && <motion.span layoutId="metric" className="absolute inset-0 rounded-full bg-raised ring-1 ring-line" />}
              <span className="relative">{x.label}</span>
            </button>
          ))}
          <span className="mx-2 h-5 w-px bg-line" />
          {(["test", "cv"] as const).map((s) => (
            <button key={s} onClick={() => setSet(s)}
              className={`relative rounded-full px-3 py-1.5 text-sm ${set === s ? "text-ink" : "text-muted hover:text-ink2"}`}>
              {set === s && <motion.span layoutId="set" className="absolute inset-0 rounded-full bg-raised ring-1 ring-line" />}
              <span className="relative">{s === "test" ? "Test engines" : "Cross-validation"}</span>
            </button>
          ))}
          <span className="ml-auto text-xs text-muted">{m.better} is better</span>
        </div>
        <div className="h-[380px]">
          <ResponsiveContainer>
            <BarChart data={rows} layout="vertical" margin={{ left: 20, right: 60 }}>
              <CartesianGrid {...gridProps} horizontal={false} vertical />
              <XAxis type="number" {...axisProps} />
              <YAxis type="category" dataKey="model" {...axisProps} width={180} tick={{ fill: INK.secondary, fontSize: 12 }} />
              <Tooltip {...tooltipProps} cursor={{ fill: "rgba(255,255,255,0.04)" }} formatter={(v) => [Number(v).toFixed(3), m.label]} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} animationDuration={900} key={`${metric}-${set}`}>
                {rows.map((r) => <Cell key={r.model} fill={r.model === data.best_model ? SERIES[0] : "#4a4a47"} />)}
                <LabelList dataKey="value" position="right" fill={INK.secondary} fontSize={11}
                  formatter={(v: unknown) => (metric === "R2" ? Number(v).toFixed(3) : Number(v).toFixed(2))} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <Card title="Full results" subtitle="Cross-validation (train engines) vs held-out test engines.">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-muted">
                <tr>
                  <th className="py-2 pr-3">Model</th>
                  <th className="px-2">CV RMSE</th><th className="px-2">Test RMSE</th>
                  <th className="px-2">Test MAE</th><th className="px-2">Test R²</th><th className="px-2">Fit (s)</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r, i) => (
                  <motion.tr key={r.model} initial={{ opacity: 0, x: -10 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }}
                    transition={{ delay: i * 0.05 }}
                    className={`border-t border-line font-mono text-xs ${r.model === data.best_model ? "text-ink" : "text-ink2"}`}>
                    <td className="py-2 pr-3 font-sans text-sm">{r.model === data.best_model ? "★ " : ""}{r.model}</td>
                    <td className="px-2">{r.cv.RMSE.toFixed(2)}</td>
                    <td className="px-2">{r.test.RMSE.toFixed(2)}</td>
                    <td className="px-2">{r.test.MAE.toFixed(2)}</td>
                    <td className="px-2">{r.test.R2.toFixed(3)}</td>
                    <td className="px-2">{r.train_seconds}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title={`Feature importance · ${data.best_model}`} subtitle="Normalised importance of the top features.">
          <div className="h-[360px]">
            <ResponsiveContainer>
              <BarChart data={imp} layout="vertical" margin={{ left: 10, right: 20 }}>
                <XAxis type="number" {...axisProps} hide />
                <YAxis type="category" dataKey="name" {...axisProps} width={190} tick={{ fill: INK.secondary, fontSize: 10 }} />
                <Tooltip {...tooltipProps} cursor={{ fill: "rgba(255,255,255,0.04)" }} formatter={(v) => [`${(Number(v) * 100).toFixed(1)}%`, "importance"]} />
                <Bar dataKey="importance" fill={SERIES[2]} radius={[0, 4, 4, 0]} animationDuration={1000} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}
