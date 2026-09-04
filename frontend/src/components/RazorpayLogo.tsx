import React from 'react';

interface RazorpayLogoProps {
  className?: string;
  height?: number;
  showAutopilotBadge?: boolean;
  theme?: 'dark' | 'light';
}

export function RazorpayLogo({
  className = '',
  height = 28,
  showAutopilotBadge = true,
  theme = 'dark',
}: RazorpayLogoProps) {
  const isDark = theme === 'dark';
  const leftBladeColor = isDark ? '#FFFFFF' : '#1A293E';
  const rightBladeColor = '#3395FF';
  const textColor = isDark ? '#FFFFFF' : '#16233B';

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {/* Official Razorpay SVG Emblem + Wordmark */}
      <svg
        height={height}
        viewBox="0 0 170 38"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="overflow-visible select-none"
      >
        {/* Left lower angled blade */}
        <path
          d="M8.5 32.5L19.2 11.5H12.8L2.1 32.5H8.5Z"
          fill={leftBladeColor}
        />
        {/* Right upper blue lightning blade */}
        <path
          d="M20.5 2.5L9.8 23.5H16.2L26.9 2.5H20.5Z"
          fill={rightBladeColor}
        />
        {/* Subtle dynamic facet overlap */}
        <path
          d="M12.8 11.5L9.8 23.5H16.2L19.2 11.5H12.8Z"
          fill="#0C65D8"
          opacity="0.85"
        />

        {/* Razorpay Wordmark typography */}
        <text
          x="33"
          y="26"
          fill={textColor}
          fontFamily="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
          fontWeight="800"
          fontStyle="italic"
          fontSize="24"
          letterSpacing="-0.6px"
        >
          Razorpay
        </text>
      </svg>

      {showAutopilotBadge && (
        <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 whitespace-nowrap">
          AI Autopilot
        </span>
      )}
    </div>
  );
}

export function RazorpayIcon({ size = 28, theme = 'dark' }: { size?: number; theme?: 'dark' | 'light' }) {
  const isDark = theme === 'dark';
  const leftBladeColor = isDark ? '#FFFFFF' : '#1A293E';
  const rightBladeColor = '#3395FF';

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 30 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="select-none"
    >
      {/* Left lower blade */}
      <path
        d="M8.5 32.5L19.2 11.5H12.8L2.1 32.5H8.5Z"
        fill={leftBladeColor}
      />
      {/* Right upper blue lightning blade */}
      <path
        d="M20.5 2.5L9.8 23.5H16.2L26.9 2.5H20.5Z"
        fill={rightBladeColor}
      />
      {/* Dynamic facet overlap */}
      <path
        d="M12.8 11.5L9.8 23.5H16.2L19.2 11.5H12.8Z"
        fill="#0C65D8"
        opacity="0.85"
      />
    </svg>
  );
}
