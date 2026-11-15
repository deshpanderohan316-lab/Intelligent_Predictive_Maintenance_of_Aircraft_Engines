"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { Card, ErrorState, Loader, PageHeader, Select, stagger, StatTile } from "@/components/ui";
import { EdaSummary, EngineDetail, EngineInfo, prettyFeature, toRows, useApi } from "@/lib/api";
import { INK, SERIES, axisProps, gridProps, tooltipProps } from "@/lib/theme";

export default function EdaPage() {
  const { data, error } = useApi<EdaSummary>("/api/eda");
  const { data: envelope } = useApi<Record<string, number>[]>("/api/eda/envelope");

  if (error) return <ErrorState message={error} />;
  if (!data) return <Loader label="Loading exploratory analysis" />;

  const hist = data.rul_histogram.map((c, i) => ({ bin: `${Math.round(data.rul_bins[i])}`, count: c }));
  const corr = Object.entries(data.feature_rul_spearman).slice(0, 12)
    .map(([f, v]) => ({ name: prettyFeature(f), rho: v }));
  const classes = Array.from(new Set((envelope ?? []).map((r) => r.Fc))).sort();
  const lifetimes = [...data.lifetimes].sort((a, b) => a.engine_id.localeCompare(b.engine_id));

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Exploratory data analysis" title="Understanding the fleet">
        Flight envelopes, engine lifetimes, label distribution and which engineered signals track degradation.
      </PageHeader>

      <motion.div initial="hidden" animate="show" variants={stagger} className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatTile label="Engines" value={data.n_engines} />
        <StatTile label="Flight cycles" value={data.n_cycles} />
        <StatTile label="Sensors" value={data.sensors.length} />
        <StatTile label="Flight classes" value={Object.keys(data.flight_class_counts).length} hint="1 short · 2 medium · 3 long haul" />
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Flight envelope" subtitle="Altitude vs Mach for sampled seconds, coloured by flight class.">
          <div className="h-72">
            <ResponsiveContainer>
              <ScatterChart margin={{ right: 10 }}>
                <CartesianGrid {...gridProps} />
                <XAxis type="number" dataKey="Mach" name="Mach" {...axisProps} domain={["auto", "auto"]} />
                <YAxis type="number" dataKey="alt" name="Altitude" {...axisProps} width={55} />
                <ZAxis range={[10, 10]} />
                <Tooltip {...tooltipProps} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {classes.map((fc, i) => (
                  <Scatter key={fc} name={`Flight class ${fc}`} data={(envelope ?? []).filter((r) => r.Fc === fc)}
                    fill={SERIES[i]} fillOpacity={0.6} animationDuration={1200} />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Engine lifetimes" subtitle="Cycles to failure per engine. Blue: training engines · orange: test engines.">
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={lifetimes} margin={{ right: 10 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="engine_id" {...axisProps} tickFormatter={(v: string) => v.split("_")[1]} />
                <YAxis {...axisProps} width={40} />
                <Tooltip {...tooltipProps} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="cycles" name="cycles to failure" radius={[4, 4, 0, 0]} animationDuration={1000}>
                  {lifetimes.map((l) => <Cell key={l.engine_id} fill={l.split === "dev" ? SERIES[0] : SERIES[1]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="RUL label distribution" subtitle="Number of flight cycles per RUL bin (all engines).">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={hist}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="bin" {...axisProps} />
                <YAxis {...axisProps} width={40} />
                <Tooltip {...tooltipProps} cursor={{ fill: "rgba(255,255,255,0.04)" }} labelFormatter={(l) => `RUL ≥ ${l}`} />
                <Bar dataKey="count" fill={SERIES[0]} radius={[4, 4, 0, 0]} animationDuration={1000} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Strongest signals" subtitle="Spearman ρ between selected features and RUL (training engines).">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={corr} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid {...gridProps} horizontal={false} vertical />
                <XAxis type="number" domain={[-1, 1]} {...axisProps} />
                <YAxis type="category" dataKey="name" {...axisProps} width={190} tick={{ fill: INK.secondary, fontSize: 10 }} />
                <Tooltip {...tooltipProps} cursor={{ fill: "rgba(255,255,255,0.04)" }} formatter={(v) => [Number(v).toFixed(3), "ρ"]} />
                <Bar dataKey="rho" radius={4} animationDuration={1000}>
                  {corr.map((c) => <Cell key={c.name} fill={c.rho < 0 ? SERIES[1] : SERIES[0]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <HealthParameters />
    </div>
  );
}

function HealthParameters() {
  const { data: engines } = useApi<EngineInfo[]>("/api/engines");
  const [engine, setEngine] = useState<string>("");
  useEffect(() => { if (engines && !engine) setEngine(engines[0].engine_id); }, [engines, engine]);
  const { data } = useApi<EngineDetail>(engine ? `/api/engines/${engine}` : null);
  if (!engines || !data) return null;

  const keys = Object.keys(data.series).filter((k) => k.startsWith("theta_") &&
    new Set(data.series[k]).size > 1);
  const rows = toRows(data.series, ["cycle", ...keys]);

  return (
    <Card title="Ground-truth component degradation (EDA only)"
      subtitle="Simulated health parameters θ (efficiency / flow modifiers). These are never used as model inputs — they would leak the answer — but they show which components degrade and when.">
      <div className="mb-4 w-48">
        <Select label="Engine" value={engine} onChange={setEngine} options={engines.map((e) => ({ value: e.engine_id, label: `${e.engine_id} (${e.split})` }))} />
      </div>
      <div className="h-72">
        <ResponsiveContainer>
          <LineChart data={rows}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="cycle" {...axisProps} />
            <YAxis {...axisProps} width={55} domain={["auto", "auto"]} />
            <Tooltip {...tooltipProps} formatter={(v, n) => [Number(v).toFixed(4), String(n).replace("theta_", "")]} />
            <Legend formatter={(v: string) => v.replace("theta_", "")} wrapperStyle={{ fontSize: 11 }} />
            {keys.slice(0, 8).map((k, i) => (
              <Line key={k} dataKey={k} stroke={SERIES[i]} dot={false} strokeWidth={2} animationDuration={1200} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
