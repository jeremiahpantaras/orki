type WhaleMascotProps = {
  className?: string;
  variant?: "default" | "light";
};

export function WhaleMascot({ className, variant = "default" }: WhaleMascotProps) {
  const body = variant === "light" ? "#7DD3FC" : "#2FA2E2";
  const accent = variant === "light" ? "#BAE6FD" : "#1A8AC4";
  const belly = variant === "light" ? "#BAE6FD" : "#60C4F0";
  const spout = variant === "light" ? "white" : "#BAE6FD";
  const sclera = variant === "light" ? "#E0F2FE" : "white";

  return (
    <svg
      viewBox="0 0 520 420"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Orki — friendly blue whale mascot"
    >
      {/* Reflection shadow */}
      <ellipse cx="255" cy="390" rx="172" ry="15" fill={spout} opacity="0.18" />

      {/* Tail fin */}
      <path
        d="M 402 207 C 438 166 474 140 492 118 C 474 148 450 170 428 194 L 417 211 L 428 228 C 450 252 474 274 492 304 C 472 282 436 256 402 215 Z"
        fill={accent}
      />

      {/* Main body */}
      <ellipse cx="224" cy="219" rx="196" ry="117" fill={body} />

      {/* Belly highlight */}
      <ellipse cx="210" cy="250" rx="150" ry="73" fill={belly} opacity="0.38" />

      {/* Dorsal fin */}
      <path d="M 198 105 C 180 68 197 42 217 58 C 228 66 232 84 227 105 Z" fill={accent} />

      {/* Pectoral fin */}
      <path d="M 108 272 C 70 306 70 342 92 356 C 114 340 134 308 152 278 Z" fill={accent} />

      {/* Eye — sclera */}
      <circle cx="110" cy="203" r="28" fill={sclera} />
      {/* Eye — iris */}
      <circle cx="117" cy="198" r="19" fill="#2C3E5A" />
      {/* Eye — pupil */}
      <circle cx="120" cy="195" r="12" fill="#0F172A" />
      {/* Eye — primary shine */}
      <circle cx="127" cy="189" r="5.5" fill="white" />
      {/* Eye — secondary shine */}
      <circle cx="114" cy="202" r="2.5" fill="white" />

      {/* Smile */}
      <path
        d="M 88 232 C 98 248 116 254 136 242"
        stroke={accent}
        strokeWidth="3.5"
        fill="none"
        strokeLinecap="round"
      />

      {/* Spout — wide */}
      <path
        d="M 214 106 C 206 78 213 50 222 32 C 231 50 235 78 225 106 Z"
        fill={spout}
        opacity="0.82"
      />
      {/* Spout — mid */}
      <path
        d="M 233 108 C 227 84 234 62 243 48 C 252 62 253 84 244 108 Z"
        fill={spout}
        opacity="0.62"
      />
      {/* Spout — thin */}
      <path
        d="M 252 110 C 248 90 254 72 261 60 C 268 72 268 90 259 110 Z"
        fill={spout}
        opacity="0.44"
      />

      {/* Ambient sparkle dots */}
      <circle cx="76" cy="136" r="4" fill={body} opacity="0.38" />
      <circle cx="60" cy="166" r="3" fill={body} opacity="0.28" />
      <circle cx="350" cy="126" r="4" fill={belly} opacity="0.46" />
      <circle cx="140" cy="84" r="5" fill={spout} opacity="0.46" />
      <circle cx="294" cy="90" r="3.5" fill={spout} opacity="0.36" />
    </svg>
  );
}
