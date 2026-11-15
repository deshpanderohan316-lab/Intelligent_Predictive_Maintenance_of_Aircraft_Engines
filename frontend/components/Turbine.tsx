"use client";

import { motion } from "framer-motion";

/** Animated turbofan front view: spinning fan blades, pulsing hub, intake glow. */
export default function Turbine({ size = 320, speed = 2.4 }: { size?: number; speed?: number }) {
  const blades = Array.from({ length: 18 });
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{ background: "radial-gradient(circle, rgba(57,135,229,0.35) 0%, rgba(57,135,229,0) 70%)" }}
        animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      />
      <svg viewBox="-100 -100 200 200" width={size} height={size} className="relative">
        <circle r="96" fill="#141413" stroke="#383835" strokeWidth="3" />
        <circle r="88" fill="none" stroke="#2c2c2a" strokeWidth="1.5" />
        <motion.g animate={{ rotate: 360 }} transition={{ duration: speed, repeat: Infinity, ease: "linear" }}>
          {blades.map((_, i) => (
            <path
              key={i}
              d="M 0 -18 C 14 -40, 18 -70, 8 -86 L -4 -86 C 2 -66, -2 -40, -8 -18 Z"
              fill={i % 2 ? "#3a3a38" : "#4a4a47"}
              stroke="#5c5b57"
              strokeWidth="0.6"
              transform={`rotate(${(360 / blades.length) * i})`}
            />
          ))}
        </motion.g>
        <motion.circle
          r="20"
          fill="#232322"
          stroke="#3987e5"
          strokeWidth="2"
          animate={{ strokeOpacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <motion.path
          d="M 0 -8 L 7 4 L -7 4 Z"
          fill="#3987e5"
          animate={{ rotate: 360 }}
          transition={{ duration: speed * 1.5, repeat: Infinity, ease: "linear" }}
        />
      </svg>
    </div>
  );
}
