import { get, post } from '@/utils/request'

export type NodeType = 'start' | 'end' | 'task' | 'condition' | 'parallel' | 'loop'

export interface WorkflowNode {
  id: string
  type: NodeType
  name: string
  next_nodes: string[]
  // task
  task_type?: string
  task_config?: Record<string, unknown>
  // condition
  condition?: string
  true_branch?: string
  false_branch?: string
  // parallel
  branches?: string[][]
  join_node?: string
  // loop
  loop_condition?: string
  loop_body?: string[]
  exit_node?: string
}

export interface WorkflowDefinition {
  id: string
  name: string
  description?: string
  version: string
  start_node_id: string
  nodes: WorkflowNode[]
}

export interface VersionInfo {
  version: string
  description?: string
  created_at: string
  is_active: boolean
}

export interface ExecutionResult {
  workflow_id: string
  execution_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped'
  output?: Record<string, unknown>
  error?: string
  started_at: string
  completed_at?: string
  node_executions?: Array<{
    node_id: string
    node_type: string
    timestamp: number
    result: unknown
    error?: string
  }>
}

export const workflowApi = {
  /** 定义/保存流程 */
  define: (workflow: Record<string, unknown>, versionDescription?: string) =>
    post<{ success: boolean; workflow_id: string; version: string; message: string }>(
      '/api/workflow/define',
      { workflow, version_description: versionDescription },
    ),

  /** 执行流程 */
  execute: (workflowId: string, inputData?: Record<string, unknown>, version?: string) =>
    post<{ success: boolean; execution_id: string; status: string; message: string }>(
      '/api/workflow/execute',
      { workflow_id: workflowId, input_data: inputData || {}, version },
    ),

  /** 查询执行状态 */
  status: (executionId: string) =>
    get<ExecutionResult>(`/api/workflow/status?execution_id=${executionId}`),

  /** 停止执行 */
  stop: (executionId: string) =>
    post<{ success: boolean; message: string }>('/api/workflow/stop', { execution_id: executionId }),

  /** 获取版本列表 */
  versions: (workflowId: string) =>
    get<{ workflow_id: string; versions: VersionInfo[] }>(`/api/workflow/versions?workflow_id=${workflowId}`),

  /** 版本回滚 */
  rollback: (workflowId: string, targetVersion: string) =>
    post<{ success: boolean; workflow_id: string; target_version: string; message: string }>(
      '/api/workflow/rollback',
      { workflow_id: workflowId, target_version: targetVersion },
    ),

  /** 对比版本 */
  compare: (workflowId: string, fromVersion: string, toVersion: string) =>
    post<{
      workflow_id: string; from_version: string; to_version: string
      added_nodes: string[]; removed_nodes: string[]; modified_nodes: string[]; changed_config: string[]
    }>('/api/workflow/compare', { workflow_id: workflowId, from_version: fromVersion, to_version: toVersion }),

  /** 获取活跃版本 */
  activeVersion: (workflowId: string) =>
    get<{ workflow_id: string; version: string; name: string; description: string }>(
      `/api/workflow/active-version?workflow_id=${workflowId}`,
    ),

  /** 运行中的流程 */
  running: () =>
    get<{ running_executions: string[]; count: number }>('/api/workflow/running'),
}
