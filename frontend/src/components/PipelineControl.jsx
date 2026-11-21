import React, { useState } from 'react';
import { Play, Loader2, Download, Table, CheckCircle, RefreshCw } from 'lucide-react';
import { triggerPipelineRun } from '../api/client';

export default function PipelineControl({ status, exportsMeta, onRefresh }) {
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleRun = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      const res = await triggerPipelineRun();
      setFeedback({ type: 'success', msg: 'Pipeline triggered in background!' });
      onRefresh();
    } catch (err) {
      setFeedback({ type: 'error', msg: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#0B0F19] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-indigo-400" />
            Ingestion Pipeline Controls & Exports
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Trigger concurrent multi-threaded data acquisition or export 6-tab Google Sheets datasets
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleRun}
            disabled={loading || status?.is_running}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold tracking-wide uppercase transition-all shadow-lg ${
              status?.is_running
                ? 'bg-amber-600/30 text-amber-300 border border-amber-500/30 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-500/20 active:scale-95'
            }`}
          >
            {status?.is_running ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Pipeline Ingesting...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                Run Full Ingestion
              </>
            )}
          </button>

          <button
            onClick={onRefresh}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-gray-800/80 hover:bg-gray-700 text-gray-200 border border-gray-700 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh State
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`mt-3 text-xs p-2 rounded border ${
          feedback.type === 'success'
            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
            : 'bg-red-500/10 border-red-500/20 text-red-300'
        }`}>
          {feedback.msg}
        </div>
      )}

      {/* Export Files Download Bar */}
      <div className="mt-5 pt-4 border-t border-gray-800">
        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Table className="w-4 h-4 text-emerald-400" />
            Generated Google Sheets Tabs & Master XLSX
          </span>
          <span className="text-emerald-400 font-mono text-[11px] flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" />
            6 Tabs Complete & Ready for Google Sheets
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
          {exportsMeta?.files?.map((f, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded-lg bg-[#111827] border border-gray-800/80 hover:border-indigo-500/40 transition-colors"
            >
              <div className="text-[11px] font-medium text-gray-200 truncate" title={f.filename}>
                {f.filename}
              </div>
              <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                {(f.size_bytes / 1024).toFixed(1)} KB
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
