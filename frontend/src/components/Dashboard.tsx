import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Upload, 
  FileText, 
  Layers, 
  Sparkles, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  FileSpreadsheet, 
  FileCheck,
  ChevronRight,
  Database,
  ArrowRight,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { SampleFile, ToolMetadata } from '../types';

interface DashboardProps {
  onWorkflowStarted: (workflowId: string) => void;
  onSelectWorkflow: (workflowId: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onWorkflowStarted, onSelectWorkflow }) => {
  const [objective, setObjective] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [useSampleFiles, setUseSampleFiles] = useState(true);
  const [sampleFiles, setSampleFiles] = useState<SampleFile[]>([]);
  const [recentWorkflows, setRecentWorkflows] = useState<any[]>([]);
  const [tools, setTools] = useState<ToolMetadata[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showToolsModal, setShowToolsModal] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [samples, workflows, toolsList] = await Promise.all([
        api.getSampleFiles().catch(() => []),
        api.listWorkflows(6).catch(() => []),
        api.listTools().catch(() => [])
      ]);
      setSampleFiles(samples);
      setRecentWorkflows(workflows);
      setTools(toolsList);
    } catch (e) {
      console.error('Error loading dashboard data', e);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
      setUseSampleFiles(false);
    }
  };

  const removeFile = (idx: number) => {
    setSelectedFiles(selectedFiles.filter((_, i) => i !== idx));
  };

  const applyPreset = (presetText: string) => {
    setObjective(presetText);
    setUseSampleFiles(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!objective.trim()) return;

    setIsSubmitting(true);
    try {
      // If useSampleFiles is checked and no custom files uploaded, pass empty files array
      // Backend automatically maps sample PDFs when empty
      const res = await api.startWorkflow(objective, selectedFiles);
      onWorkflowStarted(res.workflow_id);
    } catch (err: any) {
      alert(`Error starting workflow: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Hero Welcome */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-blue-900/40 via-indigo-900/20 to-slate-900 border border-slate-800 p-8 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-4">
            <Sparkles className="h-3.5 w-3.5" />
            <span>Autonomous Multi-Task Planning & Output Verification</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Autonomous Agentic Automation & Verification System
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-300 leading-relaxed">
            Specify high-level objectives in natural language. The agent dynamically generates DAG-based execution plans,
            orchestrates 23+ specialized tools, independently verifies mathematical and structural integrity, and self-heals from errors.
          </p>

          <div className="mt-6 flex flex-wrap gap-4 text-xs text-slate-300">
            <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>Independent Math Recalculation</span>
            </div>
            <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60">
              <Layers className="h-4 w-4 text-indigo-400" />
              <span>Stateful LangGraph Execution</span>
            </div>
            <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60">
              <FileSpreadsheet className="h-4 w-4 text-blue-400" />
              <span>Excel & ReportLab Generation</span>
            </div>
            <button
              onClick={() => setShowToolsModal(true)}
              className="flex items-center space-x-1.5 text-blue-400 hover:text-blue-300 font-medium px-2 py-1.5 rounded-lg hover:bg-blue-500/10 transition-colors"
            >
              <span>Explore {tools.length} Registered Tools</span>
              <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Task Input Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left 2 Cols: Objective & Files */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-7 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Objective Input */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-semibold text-slate-200">
                  User Objective & Task Instructions
                </label>
                <span className="text-xs text-slate-400">Natural Language Intent</span>
              </div>
              <textarea
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                placeholder="Example: Take these three PDF reports, extract the relevant data, organize it into an Excel spreadsheet, calculate the required totals, and generate a summary report..."
                rows={4}
                className="w-full rounded-xl bg-slate-950 border border-slate-700/80 p-4 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                required
              />
            </div>

            {/* Presets Quick Selector */}
            <div>
              <p className="text-xs font-medium text-slate-400 mb-2">One-Click Example Scenarios:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => applyPreset("Take these three PDF reports, extract the relevant data, organize it into an Excel spreadsheet, calculate the required totals, and generate a summary report.")}
                  className="text-left p-3 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-blue-500/50 text-xs transition-all group"
                >
                  <div className="font-semibold text-slate-200 flex items-center justify-between">
                    <span>3 PDFs → Excel Totals → PDF Summary</span>
                    <Sparkles className="h-3.5 w-3.5 text-blue-400 group-hover:scale-110 transition-transform" />
                  </div>
                  <p className="text-slate-400 text-[11px] mt-1 line-clamp-1">Extract quarterly metrics, verify sums, output deliverables.</p>
                </button>

                <button
                  type="button"
                  onClick={() => applyPreset("Ingest sales CSV data, clean missing values and duplicates, compute profit margins, and export a formatted Excel workbook.")}
                  className="text-left p-3 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-indigo-500/50 text-xs transition-all group"
                >
                  <div className="font-semibold text-slate-200 flex items-center justify-between">
                    <span>Clean Sales CSV → Margins → Excel</span>
                    <FileCheck className="h-3.5 w-3.5 text-indigo-400 group-hover:scale-110 transition-transform" />
                  </div>
                  <p className="text-slate-400 text-[11px] mt-1 line-clamp-1">Data pipeline with cleaning, stats, and spreadsheet creation.</p>
                </button>
              </div>
            </div>

            {/* File Upload & Preloaded Files Option */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-slate-200">Input Documents & Datasets</label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="sample_toggle"
                    checked={useSampleFiles}
                    onChange={(e) => setUseSampleFiles(e.target.checked)}
                    className="rounded bg-slate-800 border-slate-700 text-blue-600 focus:ring-blue-500 h-4 w-4"
                  />
                  <label htmlFor="sample_toggle" className="text-xs text-blue-400 cursor-pointer font-medium">
                    Include preloaded Q1, Q2, Q3 PDF reports
                  </label>
                </div>
              </div>

              {/* Upload Dropzone */}
              <div className="relative border-2 border-dashed border-slate-700/80 hover:border-blue-500/60 rounded-xl p-5 text-center transition-colors bg-slate-950/40">
                <input
                  type="file"
                  multiple
                  accept=".pdf,.docx,.xlsx,.xls,.csv,.txt"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <Upload className="mx-auto h-7 w-7 text-slate-400" />
                <p className="mt-2 text-xs font-medium text-slate-300">
                  <span className="text-blue-400 underline">Upload files</span> or drag and drop
                </p>
                <p className="text-[11px] text-slate-500 mt-1">Supports PDF, DOCX, XLSX, CSV, and TXT</p>
              </div>

              {/* Attached Files List */}
              {selectedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {selectedFiles.map((f, i) => (
                    <div key={i} className="flex items-center space-x-2 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-xs text-slate-200">
                      <FileText className="h-3.5 w-3.5 text-blue-400" />
                      <span className="max-w-[140px] truncate">{f.name}</span>
                      <button type="button" onClick={() => removeFile(i)} className="text-slate-400 hover:text-red-400">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Notice for Preloaded Sample Files */}
              {useSampleFiles && selectedFiles.length === 0 && (
                <div className="flex items-center space-x-2.5 p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs">
                  <Database className="h-4 w-4 text-blue-400 flex-shrink-0" />
                  <span>3 sample financial PDF reports (Q1, Q2, Q3) will be ingested for demonstration.</span>
                </div>
              )}
            </div>

            {/* Launch Button */}
            <button
              type="submit"
              disabled={isSubmitting || !objective.trim()}
              className="w-full flex items-center justify-center space-x-2 py-3.5 px-6 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-blue-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <div className="h-4 w-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Constructing Autonomous Plan...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  <span>Launch Autonomous Agent Workflow</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Col: Recent Executions & Stats */}
        <div className="space-y-6">
          
          {/* Quick Stats Widget */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center space-x-2">
              <Clock className="h-4 w-4 text-indigo-400" />
              <span>System Telemetry</span>
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 text-[11px]">Registered Tools</span>
                <p className="text-xl font-bold text-white mt-0.5">{tools.length}</p>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 text-[11px]">Verification Tiers</span>
                <p className="text-xl font-bold text-emerald-400 mt-0.5">5 Rules</p>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 text-[11px]">Max Retries</span>
                <p className="text-xl font-bold text-blue-400 mt-0.5">3 Attempts</p>
              </div>
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 text-[11px]">Execution Sandboxing</span>
                <p className="text-xl font-bold text-purple-400 mt-0.5">Enforced</p>
              </div>
            </div>
          </div>

          {/* Recent Executions List */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200">Recent Executions</h3>
              <span className="text-xs text-slate-400">{recentWorkflows.length} runs</span>
            </div>

            {recentWorkflows.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">No previous workflows recorded yet.</p>
            ) : (
              <div className="space-y-2.5">
                {recentWorkflows.map((wf) => (
                  <div
                    key={wf.id}
                    onClick={() => onSelectWorkflow(wf.id)}
                    className="p-3 rounded-xl bg-slate-950 hover:bg-slate-800/70 border border-slate-800 hover:border-slate-700 cursor-pointer transition-all flex items-center justify-between group"
                  >
                    <div className="space-y-1 min-w-0 pr-2">
                      <p className="text-xs font-semibold text-slate-200 truncate">{wf.objective}</p>
                      <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          wf.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400' :
                          wf.status === 'RUNNING' ? 'bg-blue-500/10 text-blue-400 animate-pulse' :
                          'bg-red-500/10 text-red-400'
                        }`}>
                          {wf.status}
                        </span>
                        <span>• {wf.completed_tasks}/{wf.total_tasks} tasks</span>
                        {wf.duration_seconds > 0 && <span>• {wf.duration_seconds}s</span>}
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-blue-400 transition-colors flex-shrink-0" />
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>

      {/* Tools Catalog Modal */}
      {showToolsModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">Registered Tool Catalog</h3>
                <p className="text-xs text-slate-400">Specialized functions available for autonomous agent task dispatch</p>
              </div>
              <button onClick={() => setShowToolsModal(false)} className="text-slate-400 hover:text-white p-2">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {tools.map((t) => (
                  <div key={t.name} className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-blue-400">{t.name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium">{t.category}</span>
                    </div>
                    <p className="text-xs text-slate-300">{t.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
