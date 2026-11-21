import React from 'react';
import { Activity, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function SourceHealth({ sources }) {
  return (
    <div className="bg-[#0B0F19] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            Active Signal Source Registry & Anti-Bot Health
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            5 Distinct News Outlets + 5 Job Boards + arXiv & YC verified directories
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full">
          <ShieldCheck className="w-4 h-4" />
          <span>Anti-Bot Stealth Active</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {sources?.map((s, idx) => (
          <div
            key={idx}
            className="flex items-center justify-between p-3 rounded-lg bg-[#111827]/60 border border-gray-800/80 hover:border-gray-700 transition-colors"
          >
            <div className="space-y-0.5">
              <div className="text-xs font-medium text-white flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                {s.name}
              </div>
              <div className="text-[10px] text-gray-400 font-mono">
                {s.type} • {s.target}
              </div>
            </div>
            <span className="text-[10px] font-mono font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              {s.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
