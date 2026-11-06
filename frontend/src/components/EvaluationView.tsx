import React, { useState, useEffect } from 'react';
import { 
  Play, 
  BarChart3, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RotateCcw, 
  ShieldCheck, 
  Zap, 
  TrendingUp, 
  Cpu,
  Award
} from 'lucide-react';
import { BenchmarkResult } from '../types';
import { api } from '../services/api';

export const EvaluationView: React.FC = () => {
  const [currentResult, setCurrentResult] = useState<BenchmarkResult | null>(null);
  const [history, setHistory] = useState<BenchmarkResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const records = await api.getEvaluationHistory();
      setHistory(records);
      if (records.length > 0 && !currentResult) {
        setCurrentResult(records[0]);
      }
    } catch (e) {
      console.error('Failed to load evaluation history', e);
    }
  };

  const runBenchmarkSuite = async () => {
    setIsRunning(true);
    try {
      const result = await api.runBenchmark();
      setCurrentResult(result);
      await loadHistory();
    } catch (err: any) {
      alert(`Benchmark execution failed: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const metrics = currentResult?.metrics;

  return (
    <div className="space-y-8 pb-16">
      
      {/* Hero Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
            <Zap className="h-3.5 w-3.5" />
            <span>Automated Verification & Capability Benchmarks</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">System Evaluation Framework</h1>
          <p className="text-sm text-slate-300 max-w-2xl">
            Stress-tests the agent across 10 specialized scenarios including corrupt file defense,
            independent calculation discrepancy catching, and multi-step dependency orchestration.
          </p>
        </div>

        <button
          onClick={runBenchmarkSuite}
          disabled={isRunning}
          className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-blue-500/30 transition flex items-center space-x-2.5 flex-shrink-0 disabled:opacity-50"
        >
          {isRunning ? (
            <>
              <div className="h-4 w-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              <span>Executing 10 Scenarios...</span>
            </>
          ) : (
            <>
              <Play className="h-4 w-4 fill-current" />
              <span>Run 10-Scenario Test Suite</span>
            </>
          )}
        </button>
      </div>

      {/* Metrics Scorecards */}
      {metrics && (
        <div className="space-y-4">
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <TrendingUp className="h-4 w-4 text-emerald-400" />
            <span>Standardized Evaluation Metrics</span>
          </h2>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
            
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-lg">
              <span className="text-[11px] text-slate-400 font-medium">Task Completion</span>
              <p className="text-2xl font-bold text-white mt-1">{(metrics.task_completion_rate * 100).toFixed(0)}%</p>
              <span className="text-[10px] text-emerald-400">All planned tasks executed</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-lg">
              <span className="text-[11px] text-slate-400 font-medium">Planning Accuracy</span>
              <p className="text-2xl font-bold text-indigo-400 mt-1">{(metrics.planning_accuracy * 100).toFixed(0)}%</p>
              <span className="text-[10px] text-slate-400">DAG topological ordering</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-lg">
              <span className="text-[11px] text-slate-400 font-medium">Tool Selection</span>
              <p className="text-2xl font-bold text-blue-400 mt-1">{(metrics.tool_selection_accuracy * 100).toFixed(0)}%</p>
              <span className="text-[10px] text-slate-400">Exact schema match</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-lg">
              <span className="text-[11px] text-slate-400 font-medium">Verification Accuracy</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1">{(metrics.verification_accuracy * 100).toFixed(0)}%</p>
              <span className="text-[10px] text-emerald-400">Rule & math validation</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-lg">
              <span className="text-[11px] text-slate-400 font-medium">Error Recovery Rate</span>
              <p className="text-2xl font-bold text-amber-400 mt-1">{(metrics.error_recovery_rate * 100).toFixed(0)}%</p>
              <span className="text-[10px] text-slate-400">Graceful fallback</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-lg">
              <span className="text-[11px] text-slate-400 font-medium">Avg Execution Time</span>
              <p className="text-2xl font-bold text-white mt-1">{metrics.average_execution_time_sec}s</p>
              <span className="text-[10px] text-slate-400">Per scenario run</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-lg">
              <span className="text-[11px] text-slate-400 font-medium">Total Retries</span>
              <p className="text-2xl font-bold text-purple-400 mt-1">{metrics.total_retries}</p>
              <span className="text-[10px] text-slate-400">Governed attempts</span>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-lg col-span-2 sm:col-span-1 lg:col-span-3">
              <span className="text-[11px] text-slate-400 font-medium">Overall Workflow Success Rate</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1">{(metrics.overall_workflow_success_rate * 100).toFixed(0)}%</p>
              <span className="text-[10px] text-emerald-400">{currentResult?.passed_scenarios}/{currentResult?.total_scenarios} scenarios passed benchmark</span>
            </div>

          </div>
        </div>
      )}

      {/* 10 Scenarios Breakdown */}
      {currentResult && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <h3 className="text-base font-bold text-white">10 Scenario Verification Test Results</h3>
            <span className="text-xs text-slate-400 font-mono">Run {currentResult.id}</span>
          </div>

          <div className="space-y-3">
            {currentResult.scenario_results.map((scen, idx) => (
              <div 
                key={idx}
                className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 flex items-center justify-between"
              >
                <div className="flex items-center space-x-3.5 min-w-0 pr-4">
                  {scen.passed ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
                  )}
                  <div className="space-y-0.5 min-w-0">
                    <p className="text-xs font-bold text-white truncate">{scen.scenario_name}</p>
                    <p className="text-[11px] text-slate-400">
                      Completed {scen.completed_tasks}/{scen.total_tasks} tasks • Duration: {scen.duration_seconds}s
                    </p>
                  </div>
                </div>

                <span className={`px-2.5 py-1 rounded-full text-xs font-bold flex-shrink-0 ${
                  scen.passed 
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                    : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {scen.passed ? 'PASSED' : 'FAILED'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
