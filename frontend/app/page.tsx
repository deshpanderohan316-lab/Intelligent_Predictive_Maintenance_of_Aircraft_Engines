"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Turbine from "@/components/Turbine";
import { Card, ErrorState, fadeUp, stagger, StatTile } from "@/components/ui";
import { Overview, useApi } from "@/lib/api";

const STAGES = [
  { n: "01", title: "Raw 1 Hz telemetry", text: "Flight conditions (alt, Mach, TRA, T2) and 14 engine sensors, millions of seconds per engine fleet." },
  { n: "02", title: "Preprocessing", text: "Cleaning, operating-condition normalisation, per-flight aggregation, RUL labels, causal time-series features." },
  { n: "03", title: "Model comparison", text: "Linear, kernel, neighbour, tree-ensemble, boosting and neural regressors under engine-wise cross-validation." },
  { n: "04", title: "Maintenance decision", text: "Predicted RUL → healthy / warning / critical with a recommended maintenance action." },
];

export default function Home() {
  const { data, error } = useApi<Overview>("/api/overview");

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="grid items-center gap-10 md:grid-cols-[1.2fr_1fr]">
        <motion.div initial="hidden" animate="show" variants={stagger}>
          <motion.p variants={fadeUp} className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">
            Aerospace · Predictive Maintenance
          </motion.p>
          <motion.h1 variants={fadeUp} className="mt-3 text-4xl font-bold leading-tight text-ink md:text-5xl">
            Intelligent Remaining Useful Life estimation for aircraft engines
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-5 max-w-xl text-lg text-ink2">
            A data-driven pipeline on NASA&apos;s N-CMAPSS turbofan dataset that detects degradation early and
            estimates how many flights an engine has left before failure.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-8 flex flex-wrap gap-3">
            <Link href="/preprocessing" className="rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-110">
              Explore the preprocessing pipeline →
            </Link>
            <Link href="/predict" className="rounded-full border border-line px-5 py-2.5 text-sm text-ink2 transition hover:border-accent hover:text-ink">
              Predict an engine&apos;s RUL
            </Link>
          </motion.div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className="flex justify-center"
        >
          <Turbine size={320} />
        </motion.div>
      </section>

      {/* Headline numbers */}
      {error && <ErrorState message={error} />}
      {data && (
        <motion.section initial="hidden" animate="show" variants={stagger} className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatTile label="1 Hz samples processed" value={data.rows_1hz} hint={data.datasets.join(", ")} />
          <StatTile label="Flight cycles" value={data.rows_cycle} hint={`${data.engines} run-to-failure engines`} />
          <StatTile label="Features" value={data.features_selected} hint={`selected from ${data.features_engineered} engineered`} />
          <StatTile label={`Test RMSE · ${data.best_model}`} value={data.best_test.RMSE} decimals={2} suffix=" cyc" hint={`MAE ${data.best_test.MAE} · R² ${data.best_test.R2}`} />
        </motion.section>
      )}

      {/* Workflow */}
      <section>
        <h2 className="mb-6 text-xl font-semibold text-ink">Project workflow</h2>
        <div className="grid gap-4 md:grid-cols-4">
          {STAGES.map((s, i) => (
            <Card key={s.n}>
              <motion.p
                className="font-mono text-3xl font-bold text-accent"
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.12 }}
              >
                {s.n}
              </motion.p>
              <h3 className="mt-2 font-semibold text-ink">{s.title}</h3>
              <p className="mt-2 text-sm text-ink2">{s.text}</p>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
