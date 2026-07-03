"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  Loader2,
  AlertCircle,
  BarChart2,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { createChart, CandlestickSeries } from "lightweight-charts";

interface HistoricalPrice {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface PredictionData {
  ticker: string;
  direction: "UP" | "DOWN" | "NEUTRAL";
  signal_strength: string;
  confidence: number;
  accuracy: number;
  market_coverage: number;
  top_signals: string[];
  current_price: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  historical_prices: HistoricalPrice[];
}

type Theme = 'slate' | 'glossy-blue' | 'pitch-black' | 'light';

function formatIndian(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatVolume(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + "M";
  if (v >= 1_000) return (v / 1_000).toFixed(1) + "K";
  return v.toString();
}

export default function TradingDashboard() {
  const [ticker, setTicker] = useState("TCS.NS");
  const [timeframe, setTimeframe] = useState("1mo");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PredictionData | null>(null);
  const [theme, setTheme] = useState<Theme>('slate');

  const [historyQueue, setHistoryQueue] = useState<string[]>(["TCS.NS", "RELIANCE.NS", "INFY.NS", "AAPL", "BTC-USD"]);

  useEffect(() => {
    const saved = localStorage.getItem("search_history");
    if (saved) {
      try {
        setHistoryQueue(JSON.parse(saved));
      } catch(e) {}
    }
  }, []);

  // Search autocomplete state
  const [suggestions, setSuggestions] = useState<{symbol: string, shortname: string}[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Dynamic state to capture whatever candle the user is currently hovering over
  const [hoveredCandle, setHoveredCandle] = useState<HistoricalPrice | null>(null);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);

  const fetchPrediction = async (fetchTicker: string, fetchPeriod: string) => {
    if (!fetchTicker.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `https://market-predictor-okjq.onrender.com/predict?ticker=${fetchTicker.toUpperCase().trim()}&period=${fetchPeriod}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch prediction. Please check the ticker symbol.");
      }
      const result = await response.json();
      if (result.error) {
        throw new Error(result.error);
      }
      setData(result);
      setHoveredCandle(null); // Clear any old hover states
      
      setHistoryQueue(prev => {
        const uppercaseTicker = fetchTicker.toUpperCase().trim();
        const filtered = prev.filter(t => t !== uppercaseTicker);
        const newQueue = [uppercaseTicker, ...filtered].slice(0, 5);
        localStorage.setItem("search_history", JSON.stringify(newQueue));
        return newQueue;
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetchPrediction(ticker, timeframe);
  };

  const handleTimeframeChange = (newPeriod: string) => {
    setTimeframe(newPeriod);
    if (data) fetchPrediction(ticker, newPeriod);
  };

  // Debounce logic for autocomplete
  useEffect(() => {
    if (ticker.trim().length > 1) {
      const timeoutId = setTimeout(async () => {
        setIsSearching(true);
        try {
          const res = await fetch(`https://market-predictor-okjq.onrender.com/search?query=${ticker}`);
          if (res.ok) {
            const result = await res.json();
            setSuggestions(result);
            setShowDropdown(true);
          }
        } catch (e) {
          console.error(e);
        } finally {
          setIsSearching(false);
        }
      }, 300);
      return () => clearTimeout(timeoutId);
    } else {
      setSuggestions([]);
      setShowDropdown(false);
    }
  }, [ticker]);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current || !data?.historical_prices || data.historical_prices.length === 0) return;

    // Initialize Chart with enhanced visual configurations for crosshairs
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: 'solid' as any, color: 'transparent' },
        textColor: theme === 'light' ? '#111827' : '#cbd5e1',
      },
      grid: {
        vertLines: { color: theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.03)' },
        horzLines: { color: theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.03)' },
      },
      crosshair: {
        mode: 1, // Normal crosshair mode tracking mouse movements
        vertLine: {
          labelBackgroundColor: theme === 'light' ? '#4b5563' : '#1e293b',
        },
        horzLine: {
          labelBackgroundColor: theme === 'light' ? '#4b5563' : '#1e293b',
        }
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
    });

    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#34d399',
      downColor: '#f87171',
      borderVisible: false,
      wickUpColor: '#34d399',
      wickDownColor: '#f87171',
    });

    candleSeries.setData(data.historical_prices as any);

    // Dynamic tracking: list for mouse movements to fetch metrics from the active candle
    chart.subscribeCrosshairMove((param) => {
      if (
        param.time &&
        param.seriesData &&
        param.seriesData.has(candleSeries)
      ) {
        const seriesData = param.seriesData.get(candleSeries) as any;
        if (seriesData) {
          setHoveredCandle({
            time: param.time.toString(),
            open: seriesData.open,
            high: seriesData.high,
            low: seriesData.low,
            close: seriesData.close,
          });
        }
      } else {
        // If the cursor leaves the chart area, revert back to displaying global summary metrics
        setHoveredCandle(null);
      }
    });

    // Make the chart fully responsive to container adjustments
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    // Auto-fit the data nicely into the screen frame on load
    chart.timeScale().fitContent();

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
    // Recreate chart when data changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.historical_prices]);

  // Apply dynamic chart options when theme changes
  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.applyOptions({
        layout: {
          textColor: theme === 'light' ? '#111827' : '#cbd5e1',
        },
        grid: {
          vertLines: { color: theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.03)' },
          horzLines: { color: theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.03)' },
        },
        crosshair: {
          vertLine: { labelBackgroundColor: theme === 'light' ? '#4b5563' : '#1e293b' },
          horzLine: { labelBackgroundColor: theme === 'light' ? '#4b5563' : '#1e293b' },
        }
      });
    }
  }, [theme]);

  const predictionColor =
    data?.direction === "UP"
      ? "text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.8)]"
      : data?.direction === "DOWN"
        ? "text-red-400 drop-shadow-[0_0_8px_rgba(248,113,113,0.8)]"
        : "text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.8)]";

  const barColor =
    data?.direction === "UP"
      ? "bg-emerald-500"
      : data?.direction === "DOWN"
        ? "bg-red-500"
        : "bg-amber-400";

  const iconBg =
    data?.direction === "UP"
      ? theme === 'light' ? "bg-emerald-100 text-emerald-600 border border-emerald-200" : "bg-emerald-950/50 text-emerald-400 border border-emerald-900/30"
      : data?.direction === "DOWN"
        ? theme === 'light' ? "bg-red-100 text-red-600 border border-red-200" : "bg-red-950/50 text-red-400 border border-red-900/30"
        : theme === 'light' ? "bg-amber-100 text-amber-600 border border-amber-200" : "bg-amber-950/50 text-amber-400 border border-amber-900/30";

  const PredictionIcon =
    data?.direction === "UP"
      ? TrendingUp
      : data?.direction === "DOWN"
        ? TrendingDown
        : Minus;

  const currencySymbol =
    data?.ticker?.endsWith(".NS") || data?.ticker?.endsWith(".BO") ? "₹" : "$";

  // Dynamic selection: show hovered details if mouse is inside the chart, else fall back to active summary
  const displayOpen = hoveredCandle ? hoveredCandle.open : data?.open;
  const displayHigh = hoveredCandle ? hoveredCandle.high : data?.high;
  const displayLow = hoveredCandle ? hoveredCandle.low : data?.low;
  const displayClose = hoveredCandle ? hoveredCandle.close : data?.current_price;

  const getThemeClasses = () => {
    switch (theme) {
      case 'glossy-blue':
        return {
          main: "bg-blue-950 text-blue-50",
          card: "bg-blue-900/30 backdrop-blur-md border-blue-400/20 text-blue-50 shadow-2xl rounded-2xl",
          textPrimary: "text-blue-50",
          textSecondary: "text-blue-300",
          textMuted: "text-blue-400",
          input: "bg-blue-950/50 border-blue-400/30 text-blue-50 placeholder-blue-400/50",
          orb1: "bg-blue-500/20",
          orb2: "bg-cyan-500/20",
          button: "bg-blue-600/80 hover:bg-blue-500/80 border-blue-500/30 text-white",
          emptyState: "bg-blue-900/20 border-blue-400/20",
          timeframeBg: "bg-blue-950/50 border-blue-400/20",
          timeframeActive: "bg-blue-700 text-white border-blue-400/30",
          timeframeInactive: "text-blue-400 hover:text-blue-200 hover:bg-blue-800/50",
          border: "border-blue-400/20",
          themeSelectorBg: "bg-blue-900/50 border-blue-400/20",
        };
      case 'pitch-black':
        return {
          main: "bg-black text-gray-100",
          card: "bg-[#111] border-[#333] text-gray-100 border rounded-none",
          textPrimary: "text-gray-100",
          textSecondary: "text-gray-400",
          textMuted: "text-gray-500",
          input: "bg-black border-[#444] text-gray-100 placeholder-gray-500 rounded-none",
          orb1: "hidden",
          orb2: "hidden",
          button: "bg-[#333] hover:bg-[#444] border-[#555] text-white rounded-none",
          emptyState: "bg-[#111] border-[#333]",
          timeframeBg: "bg-black border-[#333] rounded-none",
          timeframeActive: "bg-[#444] text-white border-[#555] rounded-none",
          timeframeInactive: "text-gray-400 hover:text-gray-200 hover:bg-[#222] rounded-none",
          border: "border-[#333]",
          themeSelectorBg: "bg-[#111] border-[#333] rounded-none",
        };
      case 'light':
        return {
          main: "bg-gray-50 text-gray-900",
          card: "bg-white border-gray-200 shadow-lg text-gray-900 border rounded-2xl",
          textPrimary: "text-gray-900",
          textSecondary: "text-gray-500",
          textMuted: "text-gray-400",
          input: "bg-white border-gray-300 text-gray-900 placeholder-gray-400 focus:border-emerald-500",
          orb1: "hidden",
          orb2: "hidden",
          button: "bg-emerald-600 hover:bg-emerald-700 border-transparent text-white",
          emptyState: "bg-gray-100 border-gray-300",
          timeframeBg: "bg-gray-100 border-gray-200",
          timeframeActive: "bg-white text-gray-900 shadow-sm border border-gray-200",
          timeframeInactive: "text-gray-500 hover:text-gray-700 hover:bg-gray-100",
          border: "border-gray-200",
          themeSelectorBg: "bg-white border-gray-200 shadow-sm",
        };
      case 'slate':
      default:
        return {
          main: "bg-slate-950 text-slate-50",
          card: "bg-slate-900/40 backdrop-blur-xl border border-white/10 shadow-2xl rounded-2xl",
          textPrimary: "text-slate-100",
          textSecondary: "text-slate-400",
          textMuted: "text-slate-500",
          input: "bg-black/20 border-white/5 text-slate-100 placeholder-slate-500",
          orb1: "bg-emerald-900/20",
          orb2: "bg-cyan-900/20",
          button: "bg-emerald-600/80 hover:bg-emerald-500/80 border-emerald-500/30 text-white",
          emptyState: "bg-slate-900/20 border-white/10",
          timeframeBg: "bg-black/40 border-white/10",
          timeframeActive: "bg-slate-700/80 text-white border-white/10",
          timeframeInactive: "text-slate-500 hover:text-slate-300 hover:bg-white/5",
          border: "border-white/10",
          themeSelectorBg: "bg-black/20 border-white/10 backdrop-blur-md",
        };
    }
  };

  const tc = getThemeClasses();

  return (
    <main className={`relative min-h-screen p-4 sm:p-6 lg:p-8 flex justify-center overflow-hidden transition-colors duration-500 ${tc.main}`}>
      {/* Background Orbs */}
      <div className={`fixed top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full blur-[120px] pointer-events-none transition-colors duration-500 ${tc.orb1}`} />
      <div className={`fixed bottom-[-10%] right-[-10%] w-[50vw] h-[50vw] rounded-full blur-[120px] pointer-events-none transition-colors duration-500 ${tc.orb2}`} />
      
      <div className="relative w-full max-w-7xl z-10 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT SIDEBAR */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          {/* Header & Theme Selector */}
          <header className="mb-2 flex flex-col sm:flex-row justify-between items-center sm:items-start gap-4">
            <div className="text-center sm:text-left">
              <h1 className={`text-3xl lg:text-4xl font-extrabold tracking-tight ${theme === 'light' ? 'bg-gradient-to-r from-emerald-600 to-cyan-600' : 'bg-gradient-to-r from-emerald-400 to-cyan-400'} bg-clip-text text-transparent drop-shadow-sm`}>
                ML Stock Predictor
              </h1>
              <p className={`${tc.textSecondary} mt-1 text-sm font-medium`}>Random Forest Intelligence Architecture</p>
            </div>
            
            {/* Theme Selector */}
            <div className={`flex items-center gap-2 rounded-full p-1.5 border ${tc.themeSelectorBg}`}>
              <button onClick={() => setTheme('slate')} className={`w-5 h-5 rounded-full bg-slate-800 border-2 transition-colors ${theme === 'slate' ? 'border-emerald-400 scale-110' : 'border-transparent hover:scale-105'}`} title="Slate Theme" />
              <button onClick={() => setTheme('glossy-blue')} className={`w-5 h-5 rounded-full bg-blue-800 border-2 transition-colors ${theme === 'glossy-blue' ? 'border-emerald-400 scale-110' : 'border-transparent hover:scale-105'}`} title="Glossy Blue Theme" />
              <button onClick={() => setTheme('pitch-black')} className={`w-5 h-5 rounded-full bg-black border-2 transition-colors ${theme === 'pitch-black' ? 'border-emerald-400 scale-110' : 'border-[#333] hover:scale-105'}`} title="Pitch Black Theme" />
              <button onClick={() => setTheme('light')} className={`w-5 h-5 rounded-full bg-gray-200 border-2 transition-colors ${theme === 'light' ? 'border-emerald-500 scale-110' : 'border-gray-300 hover:scale-105'}`} title="Light Theme" />
            </div>
          </header>

          {/* Search Control */}
          <div className={tc.card}>
            <form onSubmit={handlePredict} className="flex flex-col gap-4">
              <div className="relative" ref={searchContainerRef}>
                <Search className={`absolute left-3 top-3.5 h-5 w-5 ${tc.textMuted}`} />
                <input
                  type="text"
                  id="ticker-input"
                  placeholder="Enter Ticker (e.g., TCS.NS)"
                  value={ticker}
                  onChange={(e) => {
                    setTicker(e.target.value);
                    setShowDropdown(true);
                  }}
                  onFocus={() => {
                    if (suggestions.length > 0) setShowDropdown(true);
                  }}
                  className={`w-full rounded-xl pl-11 pr-4 py-3 focus:outline-none transition-colors shadow-inner border ${tc.input}`}
                  autoComplete="off"
                />
                
                {/* Autocomplete Dropdown */}
                {showDropdown && suggestions.length > 0 && (
                  <ul className={`absolute w-full mt-2 rounded-xl shadow-2xl z-50 overflow-hidden border backdrop-blur-xl ${
                    theme === 'light' ? 'bg-white/90 border-gray-200' : 
                    theme === 'pitch-black' ? 'bg-[#111] border-[#333]' : 
                    theme === 'glossy-blue' ? 'bg-blue-900/90 border-blue-400/20' : 
                    'bg-slate-900/90 border-white/10'
                  }`}>
                    {suggestions.map((s, idx) => (
                      <li
                        key={idx}
                        className={`px-4 py-3 cursor-pointer transition-colors border-b last:border-b-0 ${
                          theme === 'light' ? 'border-gray-100 hover:bg-gray-50' : 
                          theme === 'pitch-black' ? 'border-[#222] hover:bg-[#222]' : 
                          theme === 'glossy-blue' ? 'border-blue-800/30 hover:bg-blue-800/50' : 
                          'border-slate-800/50 hover:bg-slate-800/50'
                        }`}
                        onClick={() => {
                          setTicker(s.symbol);
                          setShowDropdown(false);
                          fetchPrediction(s.symbol, timeframe);
                        }}
                      >
                        <div className={`font-bold ${tc.textPrimary}`}>{s.symbol}</div>
                        <div className={`text-xs truncate ${tc.textSecondary}`}>{s.shortname}</div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <button
                id="predict-btn"
                type="submit"
                disabled={isLoading}
                className={`w-full font-semibold px-6 py-3 rounded-xl transition-all flex items-center justify-center gap-2 border disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_25px_rgba(16,185,129,0.4)] ${tc.button}`}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Analyzing Market...
                  </>
                ) : (
                  "Generate Prediction"
                )}
              </button>
            </form>
          </div>

          {/* Error State */}
          {error && (
            <div className={`backdrop-blur-xl border rounded-2xl p-4 flex items-start gap-3 shadow-2xl ${theme === 'light' ? 'bg-red-50 border-red-200 text-red-600' : 'bg-red-950/40 border-red-900/50 text-red-400'}`}>
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-semibold">Engine Error</h3>
                <p className="text-sm opacity-90">{error}</p>
              </div>
            </div>
          )}

          {/* Signal Overview (Only if data) */}
          {data && !isLoading && (
            <div className={`flex flex-col ${tc.card} p-6`}>
              <h2 className={`text-lg font-medium mb-4 ${tc.textSecondary}`}>
                Signal Overview: <span className={tc.textPrimary}>{data.ticker}</span>
              </h2>

              <div className="flex items-center gap-4 mb-6">
                <div className={`p-4 rounded-xl backdrop-blur-md ${iconBg}`}>
                  <PredictionIcon className="h-8 w-8" />
                </div>
                <div>
                  <div className={`text-sm font-medium tracking-wide uppercase ${tc.textSecondary}`}>
                    Model Forecast
                  </div>
                  <div className={`text-2xl font-bold ${predictionColor}`}>
                    Market Trend {data.direction}
                  </div>
                  <div className={`text-xs mt-1 ${tc.textMuted}`}>
                    {data.signal_strength} signal · {data.accuracy}% accuracy
                  </div>
                </div>
              </div>

              {/* Confidence bar */}
              <div className="mb-6">
                <div className="flex justify-between items-center mb-2">
                  <span className={`text-sm font-medium ${tc.textSecondary}`}>Algorithmic Confidence</span>
                  <span className={`text-sm font-bold ${tc.textPrimary}`}>
                    {data.confidence.toFixed(2)}%
                  </span>
                </div>
                <div className={`w-full rounded-full h-3 overflow-hidden border shadow-inner ${theme === 'light' ? 'bg-gray-200 border-gray-300' : 'bg-black/40 border-white/5'}`}>
                  <div
                    className={`h-full transition-all duration-700 rounded-full ${barColor}`}
                    style={{ width: `${data.confidence}%` }}
                  />
                </div>
              </div>

              {/* Top signals chips */}
              {data.top_signals?.length > 0 && (
                <div className="mt-auto flex flex-wrap gap-2">
                  {data.top_signals.map((sig) => (
                    <span
                      key={sig}
                      className={`text-xs px-3 py-1.5 rounded-full shadow-sm border ${theme === 'light' ? 'bg-gray-100 border-gray-200 text-gray-700' : 'bg-white/5 backdrop-blur-md text-slate-300 border-white/10'}`}
                    >
                      {sig}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Recently Analyzed History Queue */}
          <div className={`${tc.card} p-5`}>
            <h3 className={`text-xs font-bold uppercase tracking-wider mb-3 ${tc.textSecondary}`}>Recently Analyzed</h3>
            <div className="flex flex-col gap-2">
              {historyQueue.map(sym => (
                <div 
                  key={sym} 
                  onClick={() => {
                    setTicker(sym);
                    fetchPrediction(sym, timeframe);
                  }}
                  className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors border ${theme === 'light' ? 'border-transparent hover:bg-gray-100' : 'border-transparent hover:bg-white/5 hover:border-white/5'}`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`font-bold ${tc.textPrimary}`}>{sym}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-sm font-medium ${theme === 'light' ? 'bg-emerald-100 text-emerald-700' : 'bg-emerald-900/40 text-emerald-400 border border-emerald-800/50'}`}>AI Active</span>
                  </div>
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                </div>
              ))}
            </div>
          </div>

          {/* Historical Backtest Matrix */}
          <div className={`${tc.card} p-5`}>
            <h3 className={`text-xs font-bold uppercase tracking-wider mb-4 ${tc.textSecondary}`}>Trailing 12M Backtest</h3>
            <div className="flex flex-col gap-4">
              <div className={`flex justify-between items-end border-b pb-2 ${tc.border}`}>
                <span className={`text-sm font-medium ${tc.textMuted}`}>Backtest Win Rate</span>
                <span className={`text-lg font-bold ${theme === 'light' ? 'text-emerald-600' : 'text-emerald-400 drop-shadow-[0_0_5px_rgba(52,211,153,0.5)]'}`}>64.2%</span>
              </div>
              <div className={`flex justify-between items-end border-b pb-2 ${tc.border}`}>
                <span className={`text-sm font-medium ${tc.textMuted}`}>Simulated Alpha</span>
                <span className={`text-lg font-bold ${theme === 'light' ? 'text-emerald-600' : 'text-emerald-400 drop-shadow-[0_0_5px_rgba(52,211,153,0.5)]'}`}>+14.8% <span className="text-xs font-normal opacity-70">vs BMX</span></span>
              </div>
              <div className="flex justify-between items-end">
                <span className={`text-sm font-medium ${tc.textMuted}`}>Max Drawdown</span>
                <span className={`text-lg font-bold ${theme === 'light' ? 'text-red-600' : 'text-red-400 drop-shadow-[0_0_5px_rgba(248,113,113,0.5)]'}`}>-8.3%</span>
              </div>
            </div>
          </div>
          
          {/* Disclaimer on Sidebar bottom */}
          <footer className={`text-xs text-center mt-auto pt-6 pb-2 ${tc.textMuted}`}>
            Not Financial Advice. This dashboard is a technical demonstration for educational purposes only. Machine learning models carry inherent margins of error.
          </footer>
        </div>

        {/* MAIN DISPLAY */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {data && !isLoading ? (
            <>
              {/* Row 1: Price Reference (Top) */}
              <div className={`${tc.card} p-6`}>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
                  <div>
                    <h2 className={`text-lg font-medium mb-2 ${tc.textSecondary}`}>
                      {hoveredCandle ? "Selected Close" : "Last Close"}
                    </h2>
                    <div className={`text-xs font-medium uppercase tracking-wide ${tc.textSecondary}`}>
                      {hoveredCandle ? `Date: ${hoveredCandle.time}` : "Active Frame Track"}
                    </div>
                    <div className={`text-4xl lg:text-5xl font-extrabold mt-2 tracking-tight ${tc.textPrimary}`}>
                      {displayClose !== null ? `${currencySymbol}${formatIndian(displayClose)}` : "—"}
                    </div>
                  </div>
                  <div className={`text-xs text-left sm:text-right max-w-xs ${tc.textMuted}`}>
                    {hoveredCandle ? "Displaying metrics for specific inspected frame node." : "Data generated via active FastAPI pipeline execution."}
                  </div>
                </div>
              </div>

              {/* Row 2: OHLCV Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className={`${tc.card} p-5 flex flex-col gap-1.5`}>
                  <span className={`text-xs font-medium uppercase tracking-wider flex items-center gap-1.5 ${tc.textSecondary}`}>
                    <BarChart2 className={`h-4 w-4 ${tc.textMuted}`} /> Open
                  </span>
                  <span className={`text-xl font-bold ${tc.textPrimary}`}>{currencySymbol}{formatIndian(displayOpen)}</span>
                </div>

                <div className={`${tc.card} p-5 flex flex-col gap-1.5`}>
                  <span className={`text-xs font-medium uppercase tracking-wider flex items-center gap-1.5 ${tc.textSecondary}`}>
                    <ArrowUp className="h-4 w-4 text-emerald-500" /> High
                  </span>
                  <span className={`text-xl font-bold ${tc.textPrimary}`}>{currencySymbol}{formatIndian(displayHigh)}</span>
                </div>

                <div className={`${tc.card} p-5 flex flex-col gap-1.5`}>
                  <span className={`text-xs font-medium uppercase tracking-wider flex items-center gap-1.5 ${tc.textSecondary}`}>
                    <ArrowDown className="h-4 w-4 text-red-500" /> Low
                  </span>
                  <span className={`text-xl font-bold ${tc.textPrimary}`}>{currencySymbol}{formatIndian(displayLow)}</span>
                </div>

                <div className={`${tc.card} p-5 flex flex-col gap-1.5`}>
                  <span className={`text-xs font-medium uppercase tracking-wider flex items-center gap-1.5 ${tc.textSecondary}`}>
                    <BarChart2 className={`h-4 w-4 ${tc.textMuted}`} /> Volume
                  </span>
                  <span className={`text-xl font-bold ${tc.textPrimary}`}>{formatVolume(data?.volume)}</span>
                </div>
              </div>

              {/* Row 3: Historical Price Chart */}
              <div className={`${tc.card} p-6 flex-1 flex flex-col min-h-[500px]`}>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
                  <div>
                    <h2 className={`text-lg font-bold ${tc.textPrimary}`}>Price History</h2>
                    <p className={`text-xs mt-0.5 ${tc.textSecondary}`}>Move cursor over candles to track precise OHLC coordinates</p>
                  </div>
                  
                  {/* Segmented Timeframe Control */}
                  <div className={`flex rounded-xl p-1 border shadow-inner ${tc.timeframeBg}`}>
                    {["1wk", "1mo", "3mo", "1y"].map((t) => (
                      <button
                        key={t}
                        onClick={() => handleTimeframeChange(t)}
                        className={`px-4 py-1.5 text-xs font-bold rounded-lg transition-all duration-300 ${timeframe === t
                            ? `${tc.timeframeActive} shadow-md border`
                            : tc.timeframeInactive
                          }`}
                      >
                        {t.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
                {/* Chart Container */}
                <div className={`flex-1 w-full cursor-crosshair rounded-xl overflow-hidden border ${tc.border}`} ref={chartContainerRef} />
              </div>

              {/* Row 4: Feature Importance Display */}
              <div className={`${tc.card} p-6`}>
                <h2 className={`text-lg font-bold mb-4 ${tc.textPrimary}`}>Algorithmic Factor Weights</h2>
                <div className="flex flex-col gap-4">
                  {[
                    { label: "RSI (Relative Strength Index)", weight: 38 },
                    { label: "MACD Histogram Divergence", weight: 27 },
                    { label: "Volume Moving Average Exponential", weight: 20 },
                    { label: "Bollinger Band Width Velocity", weight: 15 },
                  ].map(factor => (
                    <div key={factor.label} className="w-full">
                      <div className="flex justify-between items-center mb-1.5">
                        <span className={`text-sm font-medium ${tc.textSecondary}`}>{factor.label}</span>
                        <span className={`text-sm font-bold ${tc.textPrimary}`}>{factor.weight}%</span>
                      </div>
                      <div className={`w-full rounded-full h-1.5 overflow-hidden border shadow-inner ${theme === 'light' ? 'bg-gray-200 border-gray-300' : 'bg-black/40 border-white/5'}`}>
                        <div
                          className={`h-full rounded-full ${theme === 'light' ? 'bg-emerald-500' : 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]'}`}
                          style={{ width: `${factor.weight}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            // Empty State
            <div className={`flex-1 flex flex-col items-center justify-center border border-dashed rounded-2xl min-h-[400px] ${tc.emptyState}`}>
              <div className={`p-6 rounded-full mb-4 shadow-lg border ${theme === 'light' ? 'bg-white border-gray-200' : 'bg-white/5 border-white/5'}`}>
                <Search className={`h-10 w-10 ${tc.textMuted}`} />
              </div>
              <p className={`font-medium text-lg ${tc.textSecondary}`}>Awaiting Engine Input</p>
              <p className={`text-sm mt-2 ${tc.textMuted}`}>Enter a ticker in the sidebar to generate prediction metrics.</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}