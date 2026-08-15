"use client";

/** Chimera mark: a shield (defense) enclosing a divergent chevron pair (the
 *  adversarial split). Semantic, not a generic lock icon. */
export function Mark({ size = 22 }: { size?: number }) {
  return (
    <span
      className="relative grid place-items-center rounded-xl border border-white/10 bg-ink-800"
      style={{ height: size + 16, width: size + 16 }}
    >
      <svg width={size} height={size} viewBox="0 0 20 20" fill="none" aria-hidden>
        <path
          d="M10 1.6 L17 5.3 V11.4 Q17 15.6 10 18.4 Q3 15.6 3 11.4 V5.3 Z"
          stroke="#2ed6a6"
          strokeWidth="1.2"
          fill="rgba(46,214,166,0.06)"
        />
        <path
          d="M10 5.2 L10 14.8 M6.6 8.4 L13.4 11.6 M13.4 8.4 L6.6 11.6"
          stroke="#ff5c49"
          strokeWidth="1"
          strokeLinecap="round"
          opacity="0.92"
        />
      </svg>
    </span>
  );
}

export function Wordmark({ tag }: { tag?: string }) {
  return (
    <div className="flex items-center gap-3">
      <Mark />
      <div className="leading-none">
        <div className="flex items-center gap-2">
          <span className="text-[15px] font-semibold tracking-tight text-mist-100">Chimera</span>
          {tag && <span className="chip border-defense/25 text-defense">{tag}</span>}
        </div>
        <div className="mt-1 text-[11px] text-mist-500">Adversarial payment-fraud lab</div>
      </div>
    </div>
  );
}
