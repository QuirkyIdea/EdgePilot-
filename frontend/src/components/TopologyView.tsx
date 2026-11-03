import React, { useMemo } from "react";
import type { TopologyNode, TopologyLink } from "../services/api";

// Lightweight SVG radial topology: cloud centre, edges ring, devices outer.
export function TopologyView({
  nodes,
  links,
}: {
  nodes: TopologyNode[];
  links: TopologyLink[];
}) {
  const W = 640;
  const H = 360;
  const cx = W / 2;
  const cy = H / 2;

  const pos = useMemo(() => {
    const p: Record<string, { x: number; y: number }> = {};
    p["cloud"] = { x: cx, y: cy };
    const edges = nodes.filter((n) => n.kind === "edge");
    const devices = nodes.filter((n) => n.kind === "device");
    edges.forEach((e, i) => {
      const a = (2 * Math.PI * i) / Math.max(edges.length, 1);
      p[e.id] = { x: cx + 95 * Math.cos(a), y: cy + 95 * Math.sin(a) };
    });
    devices.forEach((d, i) => {
      const a = (2 * Math.PI * i) / Math.max(devices.length, 1);
      p[d.id] = { x: cx + 160 * Math.cos(a), y: cy + 160 * Math.sin(a) };
    });
    return p;
  }, [nodes]);

  const util = (u?: number) => {
    if (u === undefined) return "#4c72b0";
    // green (idle) -> red (busy)
    const r = Math.round(85 + 150 * u);
    const g = Math.round(168 - 120 * u);
    return `rgb(${r},${g},80)`;
  };

  return (
    <div className="topo">
      <svg viewBox={`0 0 ${W} ${H}`}>
        {links.slice(0, 400).map((l, i) => {
          const a = pos[l.source];
          const b = pos[l.target];
          if (!a || !b) return null;
          return (
            <line
              key={i}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="#2d3a4f"
              strokeWidth={0.5}
              opacity={0.5}
            />
          );
        })}
        {nodes.map((n) => {
          const p = pos[n.id];
          if (!p) return null;
          if (n.kind === "device")
            return <circle key={n.id} cx={p.x} cy={p.y} r={3} fill="#92a0b4" />;
          if (n.kind === "edge")
            return (
              <g key={n.id}>
                <rect
                  x={p.x - 8}
                  y={p.y - 8}
                  width={16}
                  height={16}
                  rx={3}
                  fill={util(n.u_true)}
                  stroke="#fff"
                  strokeWidth={0.6}
                />
              </g>
            );
          return (
            <g key={n.id}>
              <circle cx={p.x} cy={p.y} r={18} fill="#4c72b0" stroke="#fff" />
              <text x={p.x} y={p.y + 4} fontSize={10} fill="#fff" textAnchor="middle">
                cloud
              </text>
            </g>
          );
        })}
      </svg>
      <div className="legend">
        <span>● devices</span>
        <span>■ edge servers (green=idle → red=busy)</span>
        <span>● cloud</span>
      </div>
    </div>
  );
}
