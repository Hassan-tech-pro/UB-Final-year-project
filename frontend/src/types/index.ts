export type TaskStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'RETRYING' | 'SKIPPED';
export type VerificationStatus = 'PASSED' | 'FAILED' | 'WARNING' | 'PENDING';

export interface TaskDefinition {
  task_id: string;
  task_order: number;
  title: string;
  description: string;
  tool_name: string;
  parameters: Record<string, any>;
  dependencies: string[];
  expected_output: Record<string, any>;
  verification_criteria: Record<string, any>;
  status: TaskStatus;
  actual_output?: Record<string, any> | null;
  retry_count: number;
  error_message?: string | null;
  execution_time_ms: number;
}

export interface ExecutionPlan {
  workflow_id: string;
  objective: string;
  reasoning: string;
  tasks: TaskDefinition[];
  uploaded_files: string[];
}

export interface ToolCallResult {
  id: string;
  task_id: string;
  workflow_id: string;
  tool_name: string;
  input_params: Record<string, any>;
  output_data: Record<string, any>;
  success: boolean;
  error_message?: string | null;
  duration_ms: number;
  timestamp: string;
}

export interface VerificationResult {
  id: string;
  task_id: string;
  workflow_id: string;
  status: VerificationStatus;
  expected_result: string;
  actual_result: string;
  checks_passed: number;
  checks_failed: number;
  detected_errors: string[];
  explanation: string;
  suggested_recovery?: string | null;
  timestamp: string;
}

export interface ArtifactInfo {
  id: string;
  workflow_id: string;
  task_id?: string | null;
  filename: string;
  file_path: string;
  file_size: number;
  file_type: string;
  download_url: string;
  created_at: string;
}

export interface ExecutionLogEntry {
  workflow_id: string;
  task_id?: string | null;
  level: string;
  message: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface WorkflowResponse {
  id: string;
  objective: string;
  status: string;
  plan?: ExecutionPlan | null;
  tasks: TaskDefinition[];
  tool_calls: ToolCallResult[];
  verifications: VerificationResult[];
  artifacts: ArtifactInfo[];
  logs: ExecutionLogEntry[];
  duration_seconds: number;
  created_at: string;
  updated_at: string;
}

export interface EvaluationMetrics {
  task_completion_rate: number;
  planning_accuracy: number;
  tool_selection_accuracy: number;
  execution_success_rate: number;
  verification_accuracy: number;
  error_recovery_rate: number;
  average_execution_time_sec: number;
  total_retries: number;
  overall_workflow_success_rate: number;
}

export interface BenchmarkResult {
  id: string;
  suite_name: string;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  metrics: EvaluationMetrics;
  scenario_results: Array<{
    scenario_name: string;
    passed: boolean;
    duration_seconds: number;
    error?: string;
    total_tasks: number;
    completed_tasks: number;
  }>;
  created_at: string;
}

export interface ToolMetadata {
  name: string;
  description: string;
  category: string;
  parameters_schema: Record<string, any>;
  output_schema: Record<string, any>;
}

export interface SampleFile {
  filename: string;
  path: string;
  size_bytes: number;
  type: string;
}
