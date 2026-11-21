import React from 'react';
import { Newspaper, Briefcase, FileCode2, ExternalLink, Star } from 'lucide-react';

export default function RecentActivity({ activity }) {
  return (
    <div className="bg-[#0B0F19] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Newspaper className="w-5 h-5 text-cyan-400" />
            Live Ingestion Streams (24-Hour Fresh Signals)
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Real-time feed of verified research papers, AI vacancies, and breaking signals
          </p>
        </div>
        <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full">
          Streaming Active
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* News Stream */}
        <div className="space-y-3 bg-[#111827]/40 p-4 rounded-lg border border-gray-800/80">
          <div className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
            <Newspaper className="w-4 h-4" />
            Fresh News (24h)
          </div>
          <div className="space-y-2">
            {activity?.news?.map((n, i) => (
              <a
                key={i}
                href={n.url}
                target="_blank"
                rel="noreferrer"
                className="block p-2 rounded bg-[#0B0F19] border border-gray-800/60 hover:border-gray-700 transition-colors group"
              >
                <div className="text-xs font-medium text-gray-200 line-clamp-2 group-hover:text-amber-400 transition-colors">
                  {n.title}
                </div>
                <div className="mt-1 flex items-center justify-between text-[10px] text-gray-400 font-mono">
                  <span>{n.source}</span>
                  <ExternalLink className="w-3 h-3 text-gray-400 group-hover:text-amber-400" />
                </div>
              </a>
            ))}
          </div>
        </div>

        {/* Jobs Stream */}
        <div className="space-y-3 bg-[#111827]/40 p-4 rounded-lg border border-gray-800/80">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
            <Briefcase className="w-4 h-4" />
            AI Positions (24h)
          </div>
          <div className="space-y-2">
            {activity?.jobs?.map((j, i) => (
              <div
                key={i}
                className="p-2 rounded bg-[#0B0F19] border border-gray-800/60"
              >
                <div className="text-xs font-medium text-white line-clamp-1">
                  {j.title || 'AI Engineer'}
                </div>
                <div className="text-[11px] text-gray-400 mt-0.5 font-sans">
                  {j.company}
                </div>
                <div className="mt-1 flex items-center justify-between text-[10px] text-gray-400 font-mono">
                  <span className="text-cyan-400">{j.role}</span>
                  <span className="text-emerald-400">{j.remote ? 'Remote' : 'Onsite'}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Papers Stream */}
        <div className="space-y-3 bg-[#111827]/40 p-4 rounded-lg border border-gray-800/80">
          <div className="text-xs font-semibold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
            <FileCode2 className="w-4 h-4" />
            Research Papers (w/ Stars)
          </div>
          <div className="space-y-2">
            {activity?.papers?.map((p, i) => (
              <a
                key={i}
                href={p.url}
                target="_blank"
                rel="noreferrer"
                className="block p-2 rounded bg-[#0B0F19] border border-gray-800/60 hover:border-gray-700 transition-colors group"
              >
                <div className="text-xs font-medium text-gray-200 line-clamp-2 group-hover:text-purple-400 transition-colors">
                  {p.title}
                </div>
                <div className="mt-1 flex items-center justify-between text-[10px] text-gray-400 font-mono">
                  {p.stars !== null && p.stars !== undefined ? (
                    <span className="flex items-center gap-1 text-amber-400">
                      <Star className="w-3 h-3 fill-amber-400" />
                      {p.stars.toLocaleString()} stars
                    </span>
                  ) : (
                    <span className="text-gray-400">arXiv:cs.AI</span>
                  )}
                  <ExternalLink className="w-3 h-3 text-gray-400 group-hover:text-purple-400" />
                </div>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
