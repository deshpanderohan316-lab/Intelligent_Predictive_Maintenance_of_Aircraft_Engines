// Validated categorical palette (dark-surface steps) - assign in this fixed order, never cycled.
export const SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"];

export const STATUS = { healthy: "#0ca30c", warning: "#fab219", serious: "#ec835a", critical: "#d03b3b" } as const;

export const INK = { primary: "#f0efec", secondary: "#c3c2b7", muted: "#898781", grid: "#2c2c2a", axis: "#383835" };

export const axisProps = {
  stroke: INK.axis,
  tick: { fill: INK.muted, fontSize: 11 },
  tickLine: false,
} as const;

export const gridProps = { stroke: INK.grid, strokeDasharray: "0", vertical: false } as const;

export const tooltipProps = {
  contentStyle: {
    background: "#232322",
    border: `1px solid ${INK.axis}`,
    borderRadius: 10,
    color: INK.primary,
    fontSize: 12,
  },
  labelStyle: { color: INK.secondary },
  itemStyle: { color: INK.primary },
  cursor: { stroke: INK.muted, strokeWidth: 1 },
} as const;
