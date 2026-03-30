const candles = [
  { x: 148, open: 266, close: 240, high: 224, low: 288, width: 14, delay: "0s", tone: "up" },
  { x: 196, open: 240, close: 256, high: 228, low: 274, width: 14, delay: "-1.2s", tone: "down" },
  { x: 244, open: 256, close: 206, high: 188, low: 278, width: 16, delay: "-2.6s", tone: "up" },
  { x: 294, open: 206, close: 218, high: 194, low: 236, width: 14, delay: "-0.7s", tone: "down" },
  { x: 342, open: 218, close: 178, high: 164, low: 240, width: 16, delay: "-1.8s", tone: "up" },
  { x: 392, open: 178, close: 188, high: 168, low: 208, width: 14, delay: "-3.1s", tone: "down" },
  { x: 442, open: 188, close: 152, high: 138, low: 210, width: 16, delay: "-1.4s", tone: "up" },
  { x: 494, open: 152, close: 166, high: 144, low: 182, width: 14, delay: "-2.2s", tone: "down" },
  { x: 544, open: 166, close: 136, high: 122, low: 190, width: 16, delay: "-0.9s", tone: "up" },
  { x: 596, open: 136, close: 148, high: 126, low: 168, width: 14, delay: "-2.8s", tone: "down" },
  { x: 646, open: 148, close: 126, high: 112, low: 172, width: 16, delay: "-1.1s", tone: "up" },
  { x: 698, open: 126, close: 142, high: 116, low: 156, width: 14, delay: "-3.4s", tone: "down" },
  { x: 748, open: 142, close: 158, high: 132, low: 178, width: 14, delay: "-1.6s", tone: "down" },
  { x: 798, open: 158, close: 184, high: 150, low: 206, width: 16, delay: "-2.1s", tone: "down" },
  { x: 850, open: 184, close: 166, high: 154, low: 214, width: 15, delay: "-0.5s", tone: "up" },
  { x: 900, open: 166, close: 196, high: 160, low: 220, width: 16, delay: "-2.9s", tone: "down" },
  { x: 954, open: 196, close: 176, high: 164, low: 228, width: 15, delay: "-1.3s", tone: "up" },
  { x: 1006, open: 176, close: 150, high: 138, low: 204, width: 16, delay: "-3.2s", tone: "up" },
];

export function MarketHeroBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-x-[8%] top-10 h-64 rounded-full bg-[radial-gradient(circle,_rgba(14,165,233,0.16),_rgba(125,211,252,0.06)_40%,_transparent_72%)] blur-3xl" />
      <div className="absolute inset-x-0 top-0 h-full bg-[linear-gradient(180deg,rgba(248,252,255,0.14)_0%,rgba(248,252,255,0)_52%,rgba(248,252,255,0.26)_100%)]" />

      <svg
        className="market-hero-graphic absolute left-1/2 top-4 h-[28rem] w-[min(96rem,150vw)] -translate-x-1/2 opacity-80"
        viewBox="0 0 1200 520"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="marketBullCandle" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#0EA5E9" stopOpacity="0.28" />
            <stop offset="1" stopColor="#38BDF8" stopOpacity="0.12" />
          </linearGradient>
          <linearGradient id="marketBearCandle" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#94A3B8" stopOpacity="0.22" />
            <stop offset="1" stopColor="#CBD5E1" stopOpacity="0.1" />
          </linearGradient>
          <linearGradient id="marketTrendGlow" x1="138" y1="288" x2="1034" y2="148" gradientUnits="userSpaceOnUse">
            <stop stopColor="#7DD3FC" stopOpacity="0.05" />
            <stop offset="0.5" stopColor="#38BDF8" stopOpacity="0.18" />
            <stop offset="1" stopColor="#0EA5E9" stopOpacity="0.06" />
          </linearGradient>
          <pattern id="marketGrid" width="72" height="56" patternUnits="userSpaceOnUse">
            <path d="M72 0H0V56" stroke="rgba(15, 23, 42, 0.08)" strokeWidth="1" />
          </pattern>
        </defs>

        <rect x="96" y="72" width="1008" height="328" rx="32" fill="url(#marketGrid)" />
        <path
          d="M132 298C180 286 210 220 250 216C300 210 322 244 366 236C424 226 454 142 510 140C564 138 590 176 642 180C700 184 722 132 774 132C828 132 846 200 904 200C964 200 990 170 1046 150"
          stroke="url(#marketTrendGlow)"
          strokeWidth="12"
          strokeLinecap="round"
          opacity="0.7"
        />

        {candles.map((candle) => {
          const bodyTop = Math.min(candle.open, candle.close);
          const bodyHeight = Math.max(Math.abs(candle.close - candle.open), 12);
          const fill = candle.tone === "up" ? "url(#marketBullCandle)" : "url(#marketBearCandle)";
          const stroke = candle.tone === "up" ? "rgba(14,165,233,0.28)" : "rgba(148,163,184,0.22)";

          return (
          <g
            key={candle.x}
            className="market-hero-candle"
            style={{ animationDelay: candle.delay }}
          >
            <line x1={candle.x} y1={candle.high} x2={candle.x} y2={candle.low} stroke={stroke} strokeWidth="2" strokeLinecap="round" />
            <rect
              x={candle.x - candle.width / 2}
              y={bodyTop}
              width={candle.width}
              height={bodyHeight}
              rx="6"
              fill={fill}
              stroke={stroke}
            />
          </g>
          );
        })}

        <rect x="96" y="72" width="1008" height="328" rx="32" fill="url(#marketGrid)" opacity="0.24" />
      </svg>
    </div>
  );
}