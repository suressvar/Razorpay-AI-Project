import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';

interface RazorpaySplashScreenProps {
  onLoaded?: () => void;
  minDurationMs?: number;
}

/**
 * Fullscreen Razorpay Splash Loader
 * Displays authentic Razorpay animated dual-blade emblem, glowing orbital ring,
 * enterprise security status, and animated progress bar on initial portal load.
 */
export function RazorpaySplashScreen({
  onLoaded,
  minDurationMs = 1500,
}: RazorpaySplashScreenProps) {
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsFadingOut(true);
      const finishTimer = setTimeout(() => {
        if (onLoaded) onLoaded();
      }, 500);
      return () => clearTimeout(finishTimer);
    }, minDurationMs);

    return () => clearTimeout(timer);
  }, [minDurationMs, onLoaded]);

  return (
    <div
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#071529] text-white transition-opacity duration-500 select-none ${
        isFadingOut ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      style={{
        backgroundImage: `radial-gradient(circle at 50% 45%, rgba(12, 101, 216, 0.20) 0%, rgba(7, 21, 41, 0.98) 75%)`,
      }}
    >
      {/* Background Tech Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(#1e3a5f_1px,transparent_1px)] [background-size:24px_24px] opacity-20" />

      {/* Main Container */}
      <div className="relative z-10 flex flex-col items-center">
        {/* Animated Razorpay Dual Blade Emblem Container */}
        <div className="relative flex items-center justify-center w-28 h-28 mb-5">
          {/* Outer Pulsing Glow Halo */}
          <div className="absolute inset-0 rounded-full bg-blue-500/20 blur-xl animate-pulse" />

          {/* High-Tech Spinning Orbital Rings */}
          <div
            className="absolute inset-0 rounded-full border-2 border-transparent border-t-blue-400 border-r-blue-500/40 animate-spin"
            style={{ animationDuration: '1.8s' }}
          />
          <div
            className="absolute inset-2 rounded-full border-2 border-transparent border-b-cyan-400 border-l-blue-600/30 animate-spin"
            style={{ animationDuration: '2.6s', animationDirection: 'reverse' }}
          />
          <div className="absolute inset-4 rounded-full border border-blue-400/20" />

          {/* Centered Glowing Razorpay Blade SVG */}
          <div className="relative z-10 filter drop-shadow-[0_0_12px_rgba(51,149,255,0.6)] animate-bounce-subtle">
            <svg
              width="44"
              height="52"
              viewBox="0 0 30 36"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Left blade - crisp white with subtle metallic gradient */}
              <path
                d="M8.5 32.5L19.2 11.5H12.8L2.1 32.5H8.5Z"
                fill="url(#leftBladeGrad)"
              />
              {/* Right blade - Razorpay signature electric blue */}
              <path
                d="M20.5 2.5L9.8 23.5H16.2L26.9 2.5H20.5Z"
                fill="url(#rightBladeGrad)"
              />
              {/* Facet overlap */}
              <path
                d="M12.8 11.5L9.8 23.5H16.2L19.2 11.5H12.8Z"
                fill="#0C65D8"
                opacity="0.9"
              />
              <defs>
                <linearGradient id="leftBladeGrad" x1="2" y1="11" x2="19" y2="33" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#FFFFFF" />
                  <stop offset="1" stopColor="#CBD5E1" />
                </linearGradient>
                <linearGradient id="rightBladeGrad" x1="10" y1="2" x2="27" y2="24" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#58A6FF" />
                  <stop offset="1" stopColor="#0C65D8" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>

        {/* Clean Razorpay Text Only */}
        <div className="flex items-center justify-center">
          <span className="font-extrabold text-3xl tracking-tight text-white italic font-sans drop-shadow-[0_2px_10px_rgba(51,149,255,0.3)]">
            Razorpay
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * Top Page Route Progress Loader
 * Shows when switching between routes in the dashboard (Overview -> Copilot -> Cases -> etc.)
 */
export function RazorpayRouteLoader() {
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Start top loader on route change
    setLoading(true);
    setProgress(25);

    const timer1 = setTimeout(() => setProgress(75), 100);
    const timer2 = setTimeout(() => {
      setProgress(100);
      const timer3 = setTimeout(() => {
        setLoading(false);
        setProgress(0);
      }, 250);
      return () => clearTimeout(timer3);
    }, 280);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [location.pathname]);

  if (!loading && progress === 0) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] pointer-events-none">
      <div
        className="h-1 bg-gradient-to-r from-blue-700 via-blue-500 to-cyan-400 shadow-[0_0_12px_rgba(51,149,255,0.9)] transition-all duration-200 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}

/**
 * Inline Component Loader styled with Razorpay dual blades
 */
export function RazorpayInlineLoader({
  text = 'Loading Razorpay data...',
  size = 'md',
}: {
  text?: string;
  size?: 'sm' | 'md' | 'lg';
}) {
  const iconSize = size === 'sm' ? 20 : size === 'lg' ? 36 : 26;

  return (
    <div className="flex flex-col items-center justify-center p-8 text-center select-none">
      <div className="relative flex items-center justify-center mb-3">
        {/* Orbital spinner */}
        <div
          className="rounded-full border-2 border-slate-200 border-t-blue-600 animate-spin"
          style={{ width: iconSize + 16, height: iconSize + 16 }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <svg
            width={iconSize}
            height={iconSize}
            viewBox="0 0 30 36"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M8.5 32.5L19.2 11.5H12.8L2.1 32.5H8.5Z" fill="#1A293E" />
            <path d="M20.5 2.5L9.8 23.5H16.2L26.9 2.5H20.5Z" fill="#3395FF" />
            <path d="M12.8 11.5L9.8 23.5H16.2L19.2 11.5H12.8Z" fill="#0C65D8" opacity="0.85" />
          </svg>
        </div>
      </div>
      <p className="text-xs font-semibold text-slate-600">{text}</p>
      <span className="text-[10px] text-slate-400 mt-0.5">Secured by Razorpay</span>
    </div>
  );
}
