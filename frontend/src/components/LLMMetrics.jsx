import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { Cpu, Zap, ShieldAlert, Layers } from 'lucide-react';

export default function LLMMetrics({ metrics }) {
  const chartData = [
    { name: 'Gemini Flash (Tier 1)', calls: metrics?.gemini_calls || 0, success: metrics?.gemini_success || 0, color: '#6366F1' },
    { name: 'Groq Llama 3 (Tier 2)', calls: metrics?.groq_calls || 0, success: metrics?.groq_success || 0, color: '#F59E0B' },
    { name: 'DeepSeek (Tier 3)', calls: metrics?.deepseek_calls || 0, success: metrics?.deepseek_success || 0, color: '#EC4899' },
    { name: 'Deterministic Safety', calls: metrics?.fallback_calls || 0, success: metrics?.fallback_success || 0, color: '#10B981' },
  ];

  return (
    <div className="bg-[#0B0F19] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            Multi-Tier LLM Orchestration & Resilience
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Automatic fallback chain with rate limit backoff (429) & token budget chunking (413)
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-lg text-amber-300">
            <ShieldAlert className="w-4 h-4" />
            <span>429 Retries Handled: {metrics?.["429_retries_handled"] || 0}</span>
          </div>
          <div className="flex items-center gap-1.5 bg-cyan-500/10 border border-cyan-500/20 px-3 py-1.5 rounded-lg text-cyan-300">
            <Layers className="w-4 h-4" />
            <span>413 Payloads Chunked: {metrics?.["413_payloads_chunked"] || 0}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" stroke="#6B7280" fontSize={11} tickLine={false} />
              <YAxis stroke="#6B7280" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '8px', fontSize: '12px' }}
                itemStyle={{ color: '#F3F4F6' }}
              />
              <Bar dataKey="calls" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="flex flex-col justify-between space-y-3 bg-[#111827]/50 rounded-lg p-4 border border-gray-800">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-400">Fallback Strategy</div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between p-2 rounded bg-[#0B0F19] border border-gray-800">
              <span className="text-gray-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                Tier 1: Gemini 1.5 Flash
              </span>
              <span className="text-gray-400 font-mono">Primary Extractor</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-[#0B0F19] border border-gray-800">
              <span className="text-gray-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                Tier 2: Groq Llama 3
              </span>
              <span className="text-gray-400 font-mono">Ultra-Fast Fallback</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-[#0B0F19] border border-gray-800">
              <span className="text-gray-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-pink-500"></span>
                Tier 3: DeepSeek Chat
              </span>
              <span className="text-gray-400 font-mono">Deep Reasoning</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-[#0B0F19] border border-gray-800">
              <span className="text-gray-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                Safety Tier: Deterministic
              </span>
              <span className="text-emerald-400 font-mono">100% Zero-Downtime</span>
            </div>
          </div>
          <div className="text-[11px] text-gray-400 pt-2 border-t border-gray-800">
            Jitter Backoff Algorithm: <code className="font-mono text-indigo-300">sleep = min(max, base * 2^attempt + jitter)</code>
          </div>
        </div>
      </div>
    </div>
  );
}
