import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  XCircle, 
  RotateCcw, 
  ShieldCheck, 
  Layers, 
  Terminal, 
  FileCode, 
  ChevronDown, 
  ChevronRight,
  Download,
  FileSpreadsheet,
  FileText,
  Activity,
  Cpu
} from 'lucide-react';
import { WorkflowResponse, TaskDefinition, VerificationResult } from '../types';
import { api } from '../services/api';

interface WorkspaceProps {
  workflowId: string | null;
  onViewResults: () => void;
}

export const Workspace: React.FC<WorkspaceProps> = ({ workflowId, onViewResults }) => {
  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>({});
  const [activeTab, setActiveTab] = useState<'plan' | 'logs' | 'verifications'>('plan');
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!workflowId) return;

    loadWorkflowDetails();

    // Setup live WebSocket
    const ws = api.createWebSocket(workflowId, (event) => {
      // Refresh on incoming event
      loadWorkflowDetails();
    });
    wsRef.current = ws;

    const interval = setInterval(() => {
      loadWorkflowDetails();
    }, 2000);

    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, [workflowId]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [workflow?.logs]);

  const loadWorkflowDetails = async () => {
    if (!workflowId) return;
    try {
      const data = await api.getWorkflow(workflowId);
      setWorkflow(data);
      // Auto expand running or failed tasks
      const newExpanded: Record<string, boolean> = {};
      data.tasks.forEach((t) => {
        if (t.status === 'RUNNING' || t.status === 'FAILED' || t.status === 'RETRYING') {
          newExpanded[t.task_id] = true;
        }
      });
      setExpandedTasks((prev) => ({ ...prev, ...newExpanded }));
    } catch (e) {
      console.error('Failed loading workflow details', e);
    }
  };

  const toggleTask = (taskId: string) => {
    setExpandedTasks((prev) => ({ ...prev, [taskId]: !prev[taskId] }));
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Completed</span>
          </span>
        );
      case 'RUNNING':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-semibold animate-pulse">
            <Activity className="h-3.5 w-3.5 animate-spin" />
            <span>Running</span>
          </span>
        );
      case 'RETRYING':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-semibold">
            <RotateCcw className="h-3.5 w-3.5 animate-spin" />
            <span>Retrying</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-semibold">
            <XCircle className="h-3.5 w-3.5" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700 text-xs font-medium">
            <Clock className="h-3.5 w-3.5" />
            <span>Pending</span>
          </span>
        );
    }
  };

  if (!workflowId) {
    return (
      <div className="text-center py-24 bg-slate-900 border border-slate-800 rounded-2xl p-8">
        <Layers className="h-12 w-12 text-slate-600 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-white">No Active Workflow Selected</h3>
        <p className="text-sm text-slate-400 mt-1">Please launch a task from the Dashboard or select a recent run to inspect.</p>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const verifMap = new Map<string, VerificationResult>();
  workflow.verifications.forEach((v) => verifMap.set(v.task_id, v));

  const completedCount = workflow.tasks.filter((t) => t.status === 'COMPLETED').length;
  const progressPercent = Math.round((completedCount / Math.max(1, workflow.tasks.length)) * 100);

  return (
    <div className="space-y-6 pb-16">
      
      {/* Workspace Objective Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-xs text-slate-400">
              <span className="font-mono text-blue-400 font-semibold">{workflow.id}</span>
              <span>•</span>
              <span>Created {new Date(workflow.created_at).toLocaleTimeString()}</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white">{workflow.objective}</h2>
          </div>

          <div className="flex items-center space-x-3">
            {getStatusBadge(workflow.status)}
            {workflow.status === 'COMPLETED' && (
              <button
                onClick={onViewResults}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition shadow-lg shadow-blue-500/20 flex items-center space-x-1.5"
              >
                <span>View Full Results</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar & Reasoning */}
        <div className="space-y-2 pt-2">
          <div className="flex justify-between text-xs text-slate-400">
            <span>Execution Progress: {completedCount}/{workflow.tasks.length} tasks completed</span>
            <span className="font-semibold text-slate-200">{progressPercent}%</span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
            <div 
              className="bg-gradient-to-r from-blue-500 to-emerald-400 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {workflow.plan?.reasoning && (
            <p className="text-xs text-slate-400 bg-slate-950 p-3 rounded-xl border border-slate-800/80 mt-2">
              <span className="text-slate-300 font-semibold">Planner Reasoning: </span>
              {workflow.plan.reasoning}
            </p>
          )}
        </div>
      </div>

      {/* Visual Execution Timeline */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center space-x-2">
          <Layers className="h-4 w-4 text-blue-400" />
          <span>Execution Plan DAG Timeline</span>
        </h3>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {workflow.tasks.map((task, idx) => {
            const isCompleted = task.status === 'COMPLETED';
            const isRunning = task.status === 'RUNNING';
            const isFailed = task.status === 'FAILED';
            const isRetrying = task.status === 'RETRYING';

            return (
              <React.Fragment key={task.task_id}>
                <div 
                  onClick={() => toggleTask(task.task_id)}
                  className={`px-3 py-2 rounded-xl text-xs font-medium cursor-pointer transition-all border flex items-center space-x-2 ${
                    isRunning ? 'bg-blue-600/20 border-blue-500 text-blue-300 shadow-md animate-pulse' :
                    isCompleted ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20' :
                    isRetrying ? 'bg-amber-500/10 border-amber-500/30 text-amber-300' :
                    isFailed ? 'bg-red-500/10 border-red-500/30 text-red-300' :
                    'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <span className="font-mono text-[10px] opacity-75">{task.task_id}</span>
                  <span className="truncate max-w-[130px]">{task.title}</span>
                  {isCompleted && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
                  {isRunning && <Activity className="h-3.5 w-3.5 text-blue-400 animate-spin" />}
                  {isFailed && <XCircle className="h-3.5 w-3.5 text-red-400" />}
                </div>

                {idx < workflow.tasks.length - 1 && (
                  <span className="text-slate-600 hidden sm:inline">→</span>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Tabs: Task Cards vs Live Logs */}
      <div className="flex space-x-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('plan')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'plan' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'
          }`}
        >
          Task Cards & Verifications ({workflow.tasks.length})
        </button>

        <button
          onClick={() => setActiveTab('logs')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 ${
            activeTab === 'logs' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'
          }`}
        >
          <Terminal className="h-3.5 w-3.5" />
          <span>Live Console Stream ({workflow.logs.length})</span>
        </button>
      </div>

      {/* Tab 1: Task Cards */}
      {activeTab === 'plan' && (
        <div className="space-y-4">
          {workflow.tasks.map((task) => {
            const isExpanded = !!expandedTasks[task.task_id];
            const verif = verifMap.get(task.task_id);

            return (
              <div 
                key={task.task_id}
                className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg transition"
              >
                {/* Header */}
                <div 
                  onClick={() => toggleTask(task.task_id)}
                  className="p-5 flex items-center justify-between cursor-pointer hover:bg-slate-800/40 transition select-none"
                >
                  <div className="flex items-center space-x-4 min-w-0 pr-4">
                    <div className="h-8 w-8 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-center font-mono text-xs font-bold text-slate-300">
                      {task.task_order}
                    </div>
                    <div className="space-y-0.5 min-w-0">
                      <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-semibold text-white truncate">{task.title}</h4>
                        <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                          {task.tool_name}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 line-clamp-1">{task.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3 flex-shrink-0">
                    {getStatusBadge(task.status)}
                    {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="border-t border-slate-800/80 p-5 bg-slate-950/60 space-y-5">
                    
                    {/* Metadata & Dependencies */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                      <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                        <span className="text-slate-500">Dependencies:</span>
                        <p className="font-mono text-slate-300 mt-0.5">
                          {task.dependencies.length ? task.dependencies.join(', ') : 'None (Root Task)'}
                        </p>
                      </div>

                      <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                        <span className="text-slate-500">Execution Tool:</span>
                        <p className="font-mono text-blue-400 mt-0.5">{task.tool_name}</p>
                      </div>

                      <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                        <span className="text-slate-500">Retries & Recovery:</span>
                        <p className="font-mono text-amber-400 mt-0.5">{task.retry_count} retries</p>
                      </div>
                    </div>

                    {/* Parameters Schema */}
                    <div className="space-y-1.5">
                      <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-300">
                        <FileCode className="h-3.5 w-3.5 text-blue-400" />
                        <span>Tool Input Parameters</span>
                      </div>
                      <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48">
                        {JSON.stringify(task.parameters, null, 2)}
                      </pre>
                    </div>

                    {/* Verification Result Card (Critical Component) */}
                    {verif && (
                      <div className="rounded-xl border p-4 space-y-3 bg-slate-900 border-slate-800">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <ShieldCheck className="h-4 w-4 text-emerald-400" />
                            <span className="text-xs font-bold text-white">Independent Verification Engine Audit</span>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            verif.status === 'PASSED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            verif.status === 'WARNING' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                            'bg-red-500/10 text-red-400 border border-red-500/20'
                          }`}>
                            {verif.status} ({verif.checks_passed} Passed / {verif.checks_failed} Failed)
                          </span>
                        </div>

                        <div className="space-y-1.5 text-xs">
                          <p className="text-slate-400">
                            <span className="text-slate-300 font-semibold">Explanation: </span>
                            {verif.explanation}
                          </p>
                          <p className="text-slate-400">
                            <span className="text-slate-300 font-semibold">Expected: </span>
                            {verif.expected_result}
                          </p>
                          <p className="text-slate-400">
                            <span className="text-slate-300 font-semibold">Actual: </span>
                            {verif.actual_result}
                          </p>
                        </div>

                        {verif.detected_errors.length > 0 && (
                          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs space-y-1">
                            <span className="font-semibold flex items-center space-x-1">
                              <AlertTriangle className="h-3.5 w-3.5" />
                              <span>Detected Discrepancies:</span>
                            </span>
                            <ul className="list-disc pl-5 space-y-0.5">
                              {verif.detected_errors.map((err, i) => (
                                <li key={i}>{err}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {verif.suggested_recovery && (
                          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs">
                            <span className="font-semibold">Suggested Recovery Action: </span>
                            {verif.suggested_recovery}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Output Inspector */}
                    {task.actual_output && (
                      <div className="space-y-1.5">
                        <span className="text-xs font-semibold text-slate-300">Tool Output Data</span>
                        <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-emerald-400 overflow-x-auto max-h-56">
                          {JSON.stringify(task.actual_output, null, 2)}
                        </pre>
                      </div>
                    )}

                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Tab 2: Live Console Stream */}
      {activeTab === 'logs' && (
        <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 font-mono text-xs shadow-2xl max-h-[600px] overflow-y-auto space-y-2">
          {workflow.logs.length === 0 ? (
            <p className="text-slate-600 text-center py-12">Listening for workflow events...</p>
          ) : (
            workflow.logs.map((log, i) => (
              <div key={i} className="flex items-start space-x-3 text-slate-300">
                <span className="text-slate-600 text-[10px] select-none">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                  log.level === 'ERROR' ? 'bg-red-500/20 text-red-400' :
                  log.level === 'WARNING' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-blue-500/20 text-blue-400'
                }`}>
                  {log.level}
                </span>
                {log.task_id && (
                  <span className="text-indigo-400">[{log.task_id}]</span>
                )}
                <span className="flex-1">{log.message}</span>
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      )}

    </div>
  );
};
