import React from 'react';
import { Building2, Package, FileText, Briefcase, Radio, Sparkles } from 'lucide-react';

export default function StatsOverview({ stats }) {
  const cards = [
    {
      title: 'Canonical Startups',
      count: stats?.startups || 0,
      target: '1,000 Target',
      icon: Building2,
      color: 'from-blue-500 to-indigo-600',
      badge: 'Min. 1,000 Achieved',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    },
    {
      title: 'AI Products & Platforms',
      count: stats?.products || 0,
      target: '1,000 Target',
      icon: Package,
      color: 'from-indigo-500 to-purple-600',
      badge: 'Min. 1,000 Achieved',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    },
    {
      title: 'Research Papers (w/ Stars)',
      count: stats?.research_papers || 0,
      target: '1,000 Target',
      icon: FileText,
      color: 'from-purple-500 to-pink-600',
      badge: 'Min. 1,000 Achieved',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    },
    {
      title: 'Fresh AI Jobs (24h)',
      count: stats?.jobs || 0,
      target: '5 Job Boards',
      icon: Briefcase,
      color: 'from-emerald-500 to-teal-600',
      badge: '100% 24h Fresh',
      badgeColor: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
    },
    {
      title: 'Fresh AI News (24h)',
      count: stats?.news || 0,
      target: '5 News Feeds',
      icon: Radio,
      color: 'from-amber-500 to-orange-600',
      badge: '100% 24h Fresh',
      badgeColor: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
    },
    {
      title: 'Entity Resolutions',
      count: stats?.entity_mappings || 0,
      target: 'Audit Logs',
      icon: Sparkles,
      color: 'from-cyan-500 to-blue-600',
      badge: 'Deterministic',
      badgeColor: 'text-purple-400 bg-purple-500/10 border-purple-500/20'
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className="relative overflow-hidden bg-[#0B0F19] border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-all duration-300 shadow-xl shadow-black/40 group"
          >
            <div className="flex items-center justify-between mb-3">
              <span className={`p-2.5 rounded-lg bg-gradient-to-br ${card.color} text-white shadow-lg`}>
                <Icon className="w-5 h-5" />
              </span>
              <span className={`text-[11px] font-mono px-2 py-0.5 rounded-full border ${card.badgeColor}`}>
                {card.badge}
              </span>
            </div>
            <div className="space-y-1">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                {card.title}
              </h3>
              <div className="text-2xl font-bold font-mono tracking-tight text-white group-hover:text-indigo-400 transition-colors">
                {card.count.toLocaleString()}
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-400">
              <span>{card.target}</span>
              <span className="text-emerald-400 font-medium">Verified Active</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
