import React from 'react';

interface RazorpayLogoProps {
  className?: string;
  height?: number;
  showAutopilotBadge?: boolean;
}

export function RazorpayLogo({
  className = '',
  height = 28,
  showAutopilotBadge = true,
}: RazorpayLogoProps) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {/* Official Razorpay SVG Emblem + Wordmark */}
      <svg
        height={height}
        viewBox="0 0 160 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible"
      >
        {/* Left White Blade segment */}
        <path
          d="M10.8 33L20.5 14.2H13.2L3.5 33H10.8Z"
          fill="#FFFFFF"
        />
        {/* Right Blue Lightning/Blade segment */}
        <path
          d="M21.2 3L11.5 21.8H18.8L28.5 3H21.2Z"
          fill="#3395FF"
        />
        {/* Shadow / Depth connecting facet */}
        <path
          d="M13.2 14.2L11.5 21.8H18.8L20.5 14.2H13.2Z"
          fill="#0C65D8"
          opacity="0.9"
        />

        {/* 'Razorpay' Wordmark text with matching italic styling */}
        <text
          x="35"
          y="27"
          fill="#FFFFFF"
          fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
          fontWeight="800"
          fontStyle="italic"
          fontSize="23"
          letterSpacing="-0.5px"
        >
          Razorpay
        </text>
      </svg>

      {showAutopilotBadge && (
        <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
          AI Autopilot
        </span>
      )}
    </div>
  );
}

export function RazorpayIcon({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Left White Blade segment */}
      <path
        d="M10.8 33L20.5 14.2H13.2L3.5 33H10.8Z"
        fill="#FFFFFF"
      />
      {/* Right Blue Lightning/Blade segment */}
      <path
        d="M21.2 3L11.5 21.8H18.8L28.5 3H21.2Z"
        fill="#3395FF"
      />
      {/* Shadow facet */}
      <path
        d="M13.2 14.2L11.5 21.8H18.8L20.5 14.2H13.2Z"
        fill="#0C65D8"
        opacity="0.9"
      />
    </svg>
  );
}
