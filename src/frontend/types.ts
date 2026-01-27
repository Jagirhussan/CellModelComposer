export enum WorkflowNode {
  PLANNER = 'planner',
  RETRIEVER = 'retriever',
  COMPOSER = 'composer',
  RESEARCHER = 'researcher',
  ANALYST = 'analyst',
  COMPLETE = 'complete'
}

export enum AgentStatus {
  IDLE = 'idle',
  RUNNING = 'running',
  PAUSED = 'paused',
  ERROR = 'error',
  SUCCESS = 'success'
}

export interface AgentMessage {
  role: 'system' | 'user' | 'agent';
  content: string;
  timestamp: number;
}

export interface Project {
  id: string;
  name: string;
  notes: string;
  created_at: string;
  state: AgentState;
}

export interface UserSession {
  username: string;
  apiKey: string;
}

export interface WorkflowResponse {
  thread_id: string;
  state: AgentState;
}

// --- Types from newfrontendcomponents ---

export interface MatchEntry {
  row: string;
  col: string;
  score: number;
}

export interface MatchMatrix {
  description: string;
  rows: string[];
  columns: string[];
  non_zero_entries: MatchEntry[];
}

export interface Mechanism {
  id: string;
  name: string;
  type: string;
  library_id: string | null;
  match_reason: string;
  connections?: string[];
}

export interface Step1Data {
  model_name: string;
  explanation: string;
  next_step_context: string;
  match_matrix: MatchMatrix;
  mermaid_source: string;
  domains: string[];
  mechanisms: Mechanism[];
  missing_components: string[];
}

export interface Port {
  mapped_variable: string;
  units: string;
}

export interface ParameterDef {
  value: number;
  units: string;
  description: string;
}

export interface StructuredEquation {
  type: string;
  lhs: string;
  rhs: string;
}

export interface VariableDef {
  units: string;
}

export interface GeneratedComponent {
  id:string;
  description: string;
  ports: Record<string, Port>;
  parameters: Record<string, ParameterDef>;
  structured_equations: StructuredEquation[];
  variables: Record<string, VariableDef>;
}

export interface Step2Data {
  generated_components: GeneratedComponent[];
}

export interface ParameterValue {
  component_id: string;
  parameter_name: string;
  value: number;
  units: string;
  source_citation: string;
  biological_context: string;
  confidence_score: number;
  notes: string;
}

// New interface for the structured issue object
export interface IssueObject {
  issue_id: string;
  description: string;
  severity: string;
}

export interface Step3Data {
  parameter_set: ParameterValue[];
  global_constants: Record<string, any>;
  issues_report: (string | IssueObject)[]; // Updated to allow both strings and objects
}

export interface DetailedLibraryModel {
  filepath: string;
  semantic_version: number;
  description: string;
  keywords: string[];
  global_constants: Record<string, any>;
  ports: Record<string, any>;
  variables: Record<string, any>;
  constitutive_laws: any[];
}

export interface LibraryModel {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  author: string;
  tags: string[];
}

export type StepData = Step1Data | Step2Data | Step3Data;

// --- Updated AgentState ---

export interface AgentState {
  project_name: string;
  project_notes: string;
  user_request: string;
  messages: AgentMessage[];
  
  spec?: Step1Data; 
  planner_thoughts?: string; 
  
  physicist_output?: Step2Data;
  physicist_thoughts?: string; 

  curator_output?: Step3Data;
  curator_thoughts?: string; 

  composite_model?: {
    mermaid?: string;
    description?: string;
    svg?: string; // New field for the rendered diagram
    [key: string]: any;
  };
  
  generated_code?: string;
  composer_logs?: string; 
  
  simulation_report?: string;
  analyst_thoughts?: string; 
  simulation_status?: string;
  analyst_attempts: number;
  currentNode: WorkflowNode;
  status: AgentStatus;
  lastUpdated: number;
}