import React, { useEffect, useState } from 'react';
import { useAriaStore } from '../store/useAriaStore';
import { AgentRun } from '../types';
import { ToolBadge } from './ToolBadge';

export const Dashboard: React.FC = () => {
  const { allRuns, sessions, isLoadingRuns, fetchDashboardData } = useAriaStore();
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Compute stats client-side
  const totalRuns = allRuns.length;
  const completedRuns = allRuns.filter(r => r.status === 'completed').length;
  const failedRuns = allRuns.filter(r => r.status === 'failed' || r.status === 'cancelled').length;

  const toolCounts: Record<string, number> = {};
  allRuns.forEach(r => {
    if (r.tools_used) {
      r.tools_used.forEach(tool => {
        toolCounts[tool] = (toolCounts[tool] || 0) + 1;
      });
    }
  });

  const sortedTools = Object.entries(toolCounts).sort((a, b) => b[1] - a[1]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto bg-zinc-50 dark:bg-zinc-950 p-6 md:p-8">
      <div className="max-w-5xl w-full mx-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">Audit & Metrics Dashboard</h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            Observability and execution logs aggregated from Redis & PostgreSQL
          </p>
        </div>

        {/* Metrics Overview Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">Total Sessions</span>
            <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1">{sessions.length}</div>
          </div>
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">Agent Runs</span>
            <div className="text-2xl font-bold text-teal-600 dark:text-teal-400 mt-1">{totalRuns}</div>
          </div>
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">Success Rate</span>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
              {totalRuns > 0 ? ((completedRuns / totalRuns) * 100).toFixed(0) : 100}%
            </div>
          </div>
          <div className="p-4 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs">
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">Failed / Cancelled</span>
            <div className="text-2xl font-bold text-red-500 mt-1">{failedRuns}</div>
          </div>
        </div>

        {/* Tool Breakdown */}
        <div className="p-5 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-4">Tool Utilization</h2>
          {sortedTools.length === 0 ? (
            <p className="text-xs text-zinc-400">No tool actions recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {sortedTools.map(([tool, count]) => {
                const percentage = totalRuns > 0 ? (count / totalRuns) * 100 : 0;
                return (
                  <div key={tool} className="space-y-1">
                    <div className="flex justify-between text-xs font-mono">
                      <ToolBadge name={tool} />
                      <span className="text-zinc-500">{count} calls ({percentage.toFixed(0)}%)</span>
                    </div>
                    <div className="w-full bg-zinc-100 dark:bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                      <div className="bg-teal-600 h-1.5 rounded-full" style={{ width: `${percentage}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent Runs Audit Table */}
        <div className="rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs overflow-hidden">
          <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Audit Log (Recent Agent Executions)</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-50 dark:bg-zinc-800/50 text-zinc-400 border-b border-zinc-200 dark:border-zinc-800">
                <tr>
                  <th className="px-4 py-3 font-medium">Input Query</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Tools Used</th>
                  <th className="px-4 py-3 font-medium">Duration</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {isLoadingRuns ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-zinc-400">Loading audit records...</td>
                  </tr>
                ) : allRuns.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-zinc-400">No agent runs logged yet.</td>
                  </tr>
                ) : (
                  allRuns.slice(0, 15).map((run) => (
                    <tr key={run.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/40 transition-colors">
                      <td className="px-4 py-3 font-medium text-zinc-800 dark:text-zinc-200 max-w-xs truncate">
                        {run.input}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wide ${
                          run.status === 'completed'
                            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                            : 'bg-red-50 text-red-700 dark:bg-red-950/60 dark:text-red-300 border border-red-200 dark:border-red-800'
                        }`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {run.tools_used && run.tools_used.length > 0 ? (
                            run.tools_used.map((t, idx) => <ToolBadge key={idx} name={t} />)
                          ) : (
                            <span className="text-zinc-400 italic">none</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-zinc-500">
                        {run.duration ? `${run.duration.toFixed(2)}s` : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => setSelectedRun(run)}
                          className="text-teal-600 hover:text-teal-700 dark:text-teal-400 font-medium hover:underline"
                        >
                          View Trace
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Trace Inspector Modal */}
      {selectedRun && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl animate-in zoom-in-95">
            <div className="p-5 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-zinc-900 dark:text-zinc-100 text-sm">Execution Trace Inspector</h3>
                <span className="text-xs font-mono text-zinc-400">Run ID: {selectedRun.id}</span>
              </div>
              <button
                onClick={() => setSelectedRun(null)}
                className="p-1 rounded-lg text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 font-mono text-xs">
              <div className="p-3 bg-zinc-100 dark:bg-zinc-950 rounded-lg">
                <span className="font-semibold text-zinc-500 block mb-1">USER QUERY:</span>
                <p className="font-sans text-zinc-800 dark:text-zinc-200 text-sm">{selectedRun.input}</p>
              </div>

              <div>
                <span className="font-semibold text-zinc-500 block mb-2">REASONING CHAIN STEPS:</span>
                {selectedRun.reasoning_trace && selectedRun.reasoning_trace.length > 0 ? (
                  <div className="space-y-3">
                    {selectedRun.reasoning_trace.map((step, idx) => (
                      <div key={idx} className="p-3 border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-900/50 space-y-2">
                        {step.thought && <div className="text-zinc-700 dark:text-zinc-300 font-sans text-xs">💭 {step.thought}</div>}
                        {step.action && (
                          <div className="flex items-center gap-2">
                            <span className="text-zinc-400">Action:</span>
                            <ToolBadge name={step.action} input={step.input} output={step.observation} />
                          </div>
                        )}
                        {step.observation && (
                          <pre className="p-2 rounded bg-zinc-950 text-zinc-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
                            {step.observation}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-400 italic">No structured intermediate steps.</p>
                )}
              </div>

              <div className="p-3 bg-zinc-100 dark:bg-zinc-950 rounded-lg">
                <span className="font-semibold text-zinc-500 block mb-1">FINAL OUTPUT:</span>
                <p className="font-sans text-zinc-800 dark:text-zinc-200 text-sm whitespace-pre-wrap">
                  {selectedRun.output || 'No output recorded'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};