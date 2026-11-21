import React from 'react';
import { Sparkles, ArrowRight, CheckCircle } from 'lucide-react';

export default function EntityResolutionLog({ mappings }) {
  return (
    <div className="bg-[#0B0F19] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            Deterministic Entity Resolution Audit Trail
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Normalizing messy scraped organization strings to seed canonicals (e.g. OpenAI Inc → OpenAI)
          </p>
        </div>
        <span className="text-xs font-mono text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 rounded-full">
          Live Canonicalizer
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 uppercase text-[10px]">
              <th className="pb-3 px-2">Raw Entity Name</th>
              <th className="pb-3 px-2">Canonical Resolved Name</th>
              <th className="pb-3 px-2">Resolution Method</th>
              <th className="pb-3 px-2 text-right">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60 text-gray-300">
            {mappings?.slice(0, 8).map((m, idx) => (
              <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                <td className="py-2.5 px-2 text-gray-400 font-sans">{m.raw_name}</td>
                <td className="py-2.5 px-2 font-medium text-white font-sans flex items-center gap-1.5">
                  <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
                  {m.canonical_name}
                </td>
                <td className="py-2.5 px-2">
                  <span className="px-2 py-0.5 rounded text-[10px] bg-gray-800 text-gray-300 border border-gray-700">
                    {m.resolution_method}
                  </span>
                </td>
                <td className="py-2.5 px-2 text-right">
                  <span className={`px-2 py-0.5 rounded text-[10px] ${
                    m.confidence_score >= 0.95
                      ? 'text-emerald-400 bg-emerald-500/10'
                      : m.confidence_score >= 0.85
                      ? 'text-indigo-400 bg-indigo-500/10'
                      : 'text-amber-400 bg-amber-500/10'
                  }`}>
                    {(m.confidence_score * 100).toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
