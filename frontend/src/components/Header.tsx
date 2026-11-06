import React from 'react';
import { Bot, Activity, ShieldCheck, Cpu, PlayCircle, BarChart3, FileSpreadsheet } from 'lucide-react';

interface HeaderProps {
  activeTab: 'dashboard' | 'workspace' | 'results' | 'evaluation';
  setActiveTab: (tab: 'dashboard' | 'workspace' | 'results' | 'evaluation') => void;
  hasActiveWorkflow: boolean;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, hasActiveWorkflow }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand / Logo */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-500 to-emerald-400 p-0.5 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <div className="h-full w-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Bot className="h-5 w-5 text-blue-400 animate-pulse" />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg text-white tracking-tight">Agentic AI</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                Autonomous OS
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">Task Automation & Multi-Tier Verification</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex space-x-1 sm:space-x-2 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center space-x-2 ${
              activeTab === 'dashboard'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Activity className="h-4 w-4" />
            <span>Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab('workspace')}
            className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center space-x-2 relative ${
              activeTab === 'workspace'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <PlayCircle className="h-4 w-4" />
            <span>Workspace</span>
            {hasActiveWorkflow && (
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping absolute -top-0.5 -right-0.5" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('results')}
            className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center space-x-2 ${
              activeTab === 'results'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <FileSpreadsheet className="h-4 w-4" />
            <span>Results</span>
          </button>

          <button
            onClick={() => setActiveTab('evaluation')}
            className={`px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center space-x-2 ${
              activeTab === 'evaluation'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            <span>Evaluation</span>
          </button>
        </nav>

        {/* System Indicators */}
        <div className="hidden lg:flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5 bg-slate-800/80 px-2.5 py-1.5 rounded-lg border border-slate-700/60 text-slate-300">
            <Cpu className="h-3.5 w-3.5 text-indigo-400" />
            <span>LangGraph Engine</span>
          </div>

          <div className="flex items-center space-x-1.5 bg-emerald-500/10 px-2.5 py-1.5 rounded-lg border border-emerald-500/20 text-emerald-400 font-medium">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>Independent Verifier</span>
          </div>
        </div>

      </div>
    </header>
  );
};
