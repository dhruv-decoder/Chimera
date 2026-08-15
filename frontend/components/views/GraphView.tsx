"use client";
import { useMemo, useState } from "react";
import { api, GraphSnapshot } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Panel, Metric, Loader, Fade, Tag } from "@/components/ui";

type P = { x: number; y: number };

function layout(g: GraphSnapshot, W: number, H: number): Record<string, P> {
  const pos: Record<string, P> = {};
  const idx: Record<string, number> = {};
  g.nodes.forEach((n, i) => {
    idx[n.id] = i;
    const a = (i / g.nodes.length) * Math.PI * 2;
    pos[n.id] = { x: W / 2 + Math.cos(a) * (W / 3) * (0.4 + Math.random() * 0.6),
                  y: H / 2 + Math.sin(a) * (H / 3) * (0.4 + Math.random() * 0.6) };
  });
  const edges = g.edges.filter((e) => pos[e.source] && pos[e.target]);
  // Lightweight force simulation.
  for (let it = 0; it < 140; it++) {
    const disp: Record<string, P> = {};
    g.nodes.forEach((n) => (disp[n.id] = { x: 0, y: 0 }));
    // repulsion
    for (let i = 0; i < g.nodes.length; i++) {
      for (let j = i + 1; j < g.nodes.length; j++) {
        const a = g.nodes[i].id, b = g.nodes[j].id;
        let dx = pos[a].x - pos[b].x, dy = pos[a].y - pos[b].y;
        let d2 = dx * dx + dy * dy + 0.01;
        const f = 1400 / d2;
        dx *= f; dy *= f;
        disp[a].x += dx; disp[a].y += dy; disp[b].x -= dx; disp[b].y -= dy;
      }
    }
    // springs
    edges.forEach((e) => {
      let dx = pos[e.target].x - pos[e.source].x, dy = pos[e.target].y - pos[e.source].y;
      const d = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const f = (d - 60) * 0.02;
      dx = (dx / d) * f; dy = (dy / d) * f;
      disp[e.source].x += dx; disp[e.source].y += dy;
      disp[e.target].x -= dx; disp[e.target].y -= dy;
    });
    g.nodes.forEach((n) => {
      pos[n.id].x += Math.max(-8, Math.min(8, disp[n.id].x)) + (W / 2 - pos[n.id].x) * 0.008;
      pos[n.id].y += Math.max(-8, Math.min(8, disp[n.id].y)) + (H / 2 - pos[n.id].y) * 0.008;
      pos[n.id].x = Math.max(20, Math.min(W - 20, pos[n.id].x));
      pos[n.id].y = Math.max(20, Math.min(H - 20, pos[n.id].y));
    });
  }
  return pos;
}

export function GraphView() {
  const { data, loading } = useAsync(() => api.graph(), []);
  const [hover, setHover] = useState<string | null>(null);
  const W = 900, H = 560;
  const pos = useMemo(() => (data ? layout(data, W, H) : {}), [data]);

  if (loading) return <Loader label="Reconstructing transfer graph" />;
  if (!data) return <Panel><p className="text-sm text-mist-400">No graph available.</p></Panel>;

  const suspicious = data.nodes.filter((n) => n.suspicious).length;
  const fraudEdges = data.edges.filter((e) => e.is_fraud).length;
  const deg: Record<string, number> = {};
  data.edges.forEach((e) => { deg[e.target] = (deg[e.target] || 0) + 1; });

  return (
    <div className="space-y-5">
      <Fade>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-mist-100">Real-time transfer graph</h2>
          <p className="mt-1 max-w-2xl text-sm text-mist-400">
            Account-to-account flows around mule and structuring campaigns. Fan-in/fan-out structure and
            fund velocity are the features that expose laundering rings a single-transaction view would miss.
          </p>
        </div>
      </Fade>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="accounts shown" value={data.nodes.length} sub="nodes in this view" />
        <Metric label="suspicious accounts" tone="threat" value={suspicious} sub="touch at least one fraud transfer" />
        <Metric label="fraud transfers" tone="threat" value={fraudEdges} sub={`of ${data.edges.length} edges`} />
        <Metric label="legit hubs" tone="defense" value={data.nodes.length - suspicious} sub="normal collectors / merchants" />
      </div>

      <Panel title="Transfer network"
        hint="Each dot is an account; each line is a money transfer between two accounts. Mule rings show up as fan-in / fan-out structure - a shape a single-transaction view can't see.">
        <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[11px] text-mist-400">
          <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-threat" />account touching fraud</span>
          <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-defense" />legitimate account</span>
          <span className="flex items-center gap-2"><span className="inline-block h-0 w-5 border-t-2 border-dashed border-threat" />fraudulent transfer</span>
          <span className="flex items-center gap-2"><span className="inline-block h-0 w-5 border-t border-defense" />legitimate transfer</span>
          <span className="text-mist-600">bigger dot = more incoming transfers</span>
        </div>
        <div className="relative overflow-hidden rounded-lg bg-ink-950/60">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
            {data.edges.map((e, i) => {
              const a = pos[e.source], b = pos[e.target];
              if (!a || !b) return null;
              const on = hover === null || hover === e.source || hover === e.target;
              return (
                <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke={e.is_fraud ? "#ff5c49" : "#2ed6a6"}
                  strokeOpacity={on ? (e.is_fraud ? 0.5 : 0.16) : 0.04}
                  strokeWidth={e.is_fraud ? 1.3 : 0.7}
                  strokeDasharray={e.is_fraud ? "4 3" : undefined}
                  className={e.is_fraud && on ? "animate-dash" : undefined} />
              );
            })}
            {data.nodes.map((n) => {
              const p = pos[n.id]; if (!p) return null;
              const r = 3 + Math.min(6, (deg[n.id] || 0) * 0.5);
              const on = hover === null || hover === n.id;
              return (
                <g key={n.id} onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} className="cursor-pointer">
                  <circle cx={p.x} cy={p.y} r={r}
                    fill={n.suspicious ? "#ff5c49" : "#2ed6a6"}
                    fillOpacity={on ? (n.suspicious ? 0.9 : 0.5) : 0.15}
                    stroke={n.suspicious ? "#ff5c49" : "#2ed6a6"} strokeOpacity={0.4} strokeWidth={on ? 1 : 0} />
                  {n.suspicious && on && <circle cx={p.x} cy={p.y} r={r + 3} fill="none" stroke="#ff5c49" strokeOpacity={0.25} className="animate-pulseSoft" />}
                </g>
              );
            })}
          </svg>
          {hover && (
            <div className="absolute left-3 top-3 panel px-3 py-2">
              <div className="font-mono text-xs text-mist-200">{hover}</div>
              <div className="mt-1 flex gap-2 text-[11px] text-mist-500">
                <span>in-degree <span className="text-mist-300">{deg[hover] || 0}</span></span>
                {data.nodes.find((n) => n.id === hover)?.suspicious && <Tag tone="threat">touches fraud</Tag>}
              </div>
            </div>
          )}
        </div>
      </Panel>
    </div>
  );
}
