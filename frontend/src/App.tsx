import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { Workspace } from './components/Workspace';
import { Results } from './components/Results';
import { EvaluationView } from './components/EvaluationView';
import { WorkflowResponse } from './types';
import { api } from './services/api';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'workspace' | 'results' | 'evaluation'>('dashboard');
  const [activeWorkflowId, setActiveWorkflowId] = useState<string | null>(null);
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowResponse | null>(null);

  useEffect(() => {
    if (activeWorkflowId) {
      api.getWorkflow(activeWorkflowId)
        .then(setCurrentWorkflow)
        .catch(console.error);
    }
  }, [activeWorkflowId, activeTab]);

  const handleWorkflowStarted = (workflowId: string) => {
    setActiveWorkflowId(workflowId);
    setActiveTab('workspace');
  };

  const handleSelectWorkflow = (workflowId: string) => {
    setActiveWorkflowId(workflowId);
    setActiveTab('workspace');
  };

  const handleViewResults = () => {
    if (activeWorkflowId) {
      api.getWorkflow(activeWorkflowId).then((wf) => {
        setCurrentWorkflow(wf);
        setActiveTab('results');
      });
    } else {
      setActiveTab('results');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation */}
      <Header 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        hasActiveWorkflow={!!activeWorkflowId} 
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        {activeTab === 'dashboard' && (
          <Dashboard 
            onWorkflowStarted={handleWorkflowStarted}
            onSelectWorkflow={handleSelectWorkflow}
          />
        )}

        {activeTab === 'workspace' && (
          <Workspace 
            workflowId={activeWorkflowId} 
            onViewResults={handleViewResults}
          />
        )}

        {activeTab === 'results' && (
          <Results 
            workflow={currentWorkflow} 
            onBackToWorkspace={() => setActiveTab('workspace')}
          />
        )}

        {activeTab === 'evaluation' && (
          <EvaluationView />
        )}
      </main>

      {/* Bottom Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/60 py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <span>Agentic AI Task Automation & Verification System • Production Architecture</span>
          <div className="flex items-center space-x-4">
            <span>FastAPI + LangGraph + React + Tailwind</span>
            <span>•</span>
            <span className="text-emerald-400 font-medium">Independent Verifier Active</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
