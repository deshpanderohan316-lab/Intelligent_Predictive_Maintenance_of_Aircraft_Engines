"use client";

import { motion } from "framer-motion";
import { STATUS } from "@/lib/theme";
import { Counter } from "./ui";

/** Semicircular RUL gauge; the arc animates to the predicted value. */
export default function Gauge({ value, max, stage }: { value: number; max: number; stage: keyof typeof STATUS }) {
  const r = 80;
  const len = Math.PI * r;
  const frac = Math.max(0, Math.min(1, value / max));
  const color = STATUS[stage];
  return (
    <div className="relative mx-auto w-full max-w-[280px]">
      <svg viewBox="0 0 200 115" className="w-full">
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#2c2c2a" strokeWidth="14" strokeLinecap="round" />
        <motion.path
          key={`${value}-${max}`}
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={len}
          initial={{ strokeDashoffset: len }}
          animate={{ strokeDashoffset: len * (1 - frac) }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <div className="absolute inset-x-0 bottom-1 text-center">
        <p className="font-mono text-4xl font-bold text-ink">
          <Counter key={value} value={value} decimals={1} />
        </p>
        <p className="text-xs uppercase tracking-wider text-muted">cycles remaining</p>
      </div>
    </div>
  );
}
