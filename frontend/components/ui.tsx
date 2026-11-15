"use client";

import { animate, motion, useInView, useMotionValue, useTransform, type Variants } from "framer-motion";
import { ReactNode, useEffect, useRef } from "react";

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

export const stagger: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } };

export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return (
    <motion.header initial="hidden" animate="show" variants={stagger} className="mb-10">
      <motion.p variants={fadeUp} className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">
        {eyebrow}
      </motion.p>
      <motion.h1 variants={fadeUp} className="mt-2 text-3xl font-bold text-ink md:text-4xl">
        {title}
      </motion.h1>
      {children && (
        <motion.p variants={fadeUp} className="mt-3 max-w-3xl text-ink2">
          {children}
        </motion.p>
      )}
    </motion.header>
  );
}

export function Card({ children, className = "", title, subtitle }: {
  children: ReactNode; className?: string; title?: string; subtitle?: string;
}) {
  return (
    <motion.section
      variants={fadeUp}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-60px" }}
      className={`rounded-2xl border border-line bg-surface p-5 md:p-6 ${className}`}
    >
      {title && <h2 className="text-base font-semibold text-ink">{title}</h2>}
      {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      <div className={title || subtitle ? "mt-4" : ""}>{children}</div>
    </motion.section>
  );
}

export function Counter({ value, decimals = 0, suffix = "" }: { value: number; decimals?: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const mv = useMotionValue(0);
  const text = useTransform(mv, (v) =>
    v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + suffix,
  );
  useEffect(() => {
    if (!inView) return;
    const controls = animate(mv, value, { duration: 1.6, ease: "easeOut" });
    return () => controls.stop();
  }, [inView, value, mv]);
  return <motion.span ref={ref}>{text}</motion.span>;
}

export function StatTile({ label, value, decimals = 0, suffix = "", hint }: {
  label: string; value: number; decimals?: number; suffix?: string; hint?: string;
}) {
  return (
    <motion.div
      variants={fadeUp}
      whileHover={{ y: -4 }}
      className="rounded-2xl border border-line bg-surface p-5"
    >
      <p className="text-xs uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-2 font-mono text-3xl font-semibold text-ink">
        <Counter value={value} decimals={decimals} suffix={suffix} />
      </p>
      {hint && <p className="mt-1 text-xs text-ink2">{hint}</p>}
    </motion.div>
  );
}

export function Loader({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-16 text-muted">
      <motion.span
        className="h-4 w-4 rounded-full border-2 border-accent border-t-transparent"
        animate={{ rotate: 360 }}
        transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
      />
      {label}…
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-critical/40 bg-critical/10 p-5 text-sm text-ink">
      <p className="font-semibold">Could not reach the Flask API</p>
      <p className="mt-1 text-ink2">{message}</p>
      <p className="mt-3 font-mono text-xs text-muted">
        Start it from the project root: python -m backend.app
      </p>
    </div>
  );
}

export function Pill({ children, color }: { children: ReactNode; color?: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-line bg-raised px-2.5 py-1 text-xs text-ink2"
    >
      {color && <span className="h-2 w-2 rounded-full" style={{ background: color }} />}
      {children}
    </span>
  );
}

export function Select({ value, onChange, options, label }: {
  value: string; onChange: (v: string) => void; options: { value: string; label: string }[]; label: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-line bg-raised px-3 py-2 text-sm text-ink outline-none focus:border-accent"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}
