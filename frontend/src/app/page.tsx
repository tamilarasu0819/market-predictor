"use client";

import React, { useState } from "react";
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

interface PredictionData {
  ticker: string;
  prediction: "UP" | "DOWN" | "NEUTRAL";
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
}

function formatIndian(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatVolume(v: number | null): string {
  if (v === null || v === undefined) return "—";
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + "M";
  if (v >= 1_000) return (v / 1_000).toFixed(1) + "K";
  return v.toString();
}

export default function TradingDashboard() {
  const [ticker, setTicker] = useState("TCS.NS");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PredictionData | null>(null);

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:8000/predict?ticker=${ticker.toUpperCase().trim()}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch prediction. Please check the ticker symbol.");
      }
      const result = await response.json();
      if (result.error) {
        throw new Error(result.error);
      }
      setData(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const predictionColor =
    data?.prediction === "UP"
      ? "text-emerald-400"
      : data?.prediction === "DOWN"
      ? "text-red-400"
      : "text-amber-400";

  const barColor =
    data?.prediction === "UP"
      ? "bg-emerald-500"
      : data?.prediction === "DOWN"
      ? "bg-red-500"
      : "bg-amber-400";

  const iconBg =
    data?.prediction === "UP"
      ? "bg-emerald-950/50 text-emerald-400 border border-emerald-900/30"
      : data?.prediction === "DOWN"
      ? "bg-red-950/50 text-red-400 border border-red-900/30"
      : "bg-amber-950/50 text-amber-400 border border-amber-900/30";

  const PredictionIcon =
    data?.prediction === "UP"
      ? TrendingUp
      : data?.prediction === "DOWN"
      ? TrendingDown
      : Minus;

  const ohlcvStats = data
    ? [
        { label: "Open",   value: `₹${formatIndian(data.open)}`,   icon: BarChart2 },
        { label: "High",   value: `₹${formatIndian(data.high)}`,   icon: ArrowUp   },
        { label: "Low",    value: `₹${formatIndian(data.low)}`,    icon: ArrowDown  },
        { label: "Volume", value: formatVolume(data.volume),        icon: BarChart2 },
      ]
    : [];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 p-6 flex flex-col items-center">
      <div className="w-full max-w-4xl mt-8">
        {/* Header */}
        <header className="mb-8 text-center md:text-left">
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            ML Stock Predictor Dashboard
          </h1>
          <p className="text-slate-400 mt-1">Random Forest Intelligence Architecture</p>
        </header>

        {/* Search Control */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8 shadow-md">
          <form onSubmit={handlePredict} className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3.5 h-5 w-5 text-slate-500" />
              <input
                type="text"
                id="ticker-input"
                placeholder="Enter Ticker (e.g., TCS.NS, RELIANCE.NS, AAPL)"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-11 pr-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
              />
            </div>
            <button
              id="predict-btn"
              type="submit"
              disabled={loading}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-medium px-6 py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
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
          <div className="bg-red-950/30 border border-red-900/50 rounded-xl p-4 mb-8 flex items-start gap-3 text-red-400">
            <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="font-semibold">Engine Error</h3>
              <p className="text-sm opacity-90">{error}</p>
            </div>
          </div>
        )}

        {/* Results */}
        {data && !loading && (
          <div className="flex flex-col gap-6">
            {/* Row 1 — Signal Overview + Price Reference */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Signal card (2 cols) */}
              <div className="md:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-md">
                <h2 className="text-lg font-medium text-slate-400 mb-4">
                  Signal Overview: <span className="text-slate-200">{data.ticker}</span>
                </h2>

                <div className="flex items-center gap-4 mb-6">
                  <div className={`p-4 rounded-xl ${iconBg}`}>
                    <PredictionIcon className="h-8 w-8" />
                  </div>
                  <div>
                    <div className="text-sm text-slate-500 font-medium tracking-wide uppercase">
                      Model Forecast
                    </div>
                    <div className={`text-2xl font-bold ${predictionColor}`}>
                      Market Trend {data.prediction}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {data.signal_strength} signal · {data.accuracy}% back-test accuracy
                    </div>
                  </div>
                </div>

                {/* Confidence bar */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-slate-400">Algorithmic Confidence</span>
                    <span className="text-sm font-bold text-slate-200">
                      {data.confidence.toFixed(2)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-950 rounded-full h-3 overflow-hidden border border-slate-800">
                    <div
                      className={`h-full transition-all duration-700 rounded-full ${barColor}`}
                      style={{ width: `${data.confidence}%` }}
                    />
                  </div>
                </div>

                {/* Top signals chips */}
                {data.top_signals?.length > 0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {data.top_signals.map((sig) => (
                      <span
                        key={sig}
                        className="text-xs bg-slate-800 text-slate-300 border border-slate-700 px-3 py-1 rounded-full"
                      >
                        {sig}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Price card (1 col) */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-md flex flex-col justify-between">
                <div>
                  <h2 className="text-lg font-medium text-slate-400 mb-4">Price Reference</h2>
                  <div className="text-sm text-slate-500 font-medium uppercase tracking-wide">
                    Last Closing Price
                  </div>
                  <div className="text-3xl font-extrabold text-slate-100 mt-1">
                    {data.current_price !== null ? `₹${formatIndian(data.current_price)}` : "—"}
                  </div>
                </div>
                <div className="pt-4 border-t border-slate-800 mt-4 text-xs text-slate-500">
                  Data generated by processing indicators via active FastAPI pipeline execution.
                </div>
              </div>
            </div>

            {/* Row 2 — OHLCV Stats Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {ohlcvStats.map(({ label, value }) => (
                <div
                  key={label}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-1"
                >
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                    {label}
                  </span>
                  <span className="text-lg font-bold text-slate-100">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
