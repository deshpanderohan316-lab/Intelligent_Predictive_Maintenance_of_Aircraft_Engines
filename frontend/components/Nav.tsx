"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/preprocessing", label: "Preprocessing" },
  { href: "/eda", label: "EDA" },
  { href: "/models", label: "Models" },
  { href: "/predict", label: "Predict RUL" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-page/80 backdrop-blur">
      <nav className="mx-auto flex max-w-7xl items-center gap-6 overflow-x-auto px-4 py-3">
        <Link href="/" className="flex shrink-0 items-center gap-2 font-semibold text-ink">
          <motion.span
            className="inline-block h-5 w-5 rounded-full border-2 border-accent border-r-transparent"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          />
          <span className="hidden sm:inline">TurboRUL</span>
        </Link>
        <ul className="flex gap-1">
          {LINKS.map((l) => {
            const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <li key={l.href} className="relative">
                <Link
                  href={l.href}
                  className={`relative z-10 block whitespace-nowrap rounded-full px-3 py-1.5 text-sm transition-colors ${
                    active ? "text-ink" : "text-muted hover:text-ink2"
                  }`}
                >
                  {l.label}
                </Link>
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 rounded-full bg-raised ring-1 ring-line"
                    transition={{ type: "spring", stiffness: 400, damping: 32 }}
                  />
                )}
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
