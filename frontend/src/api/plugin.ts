import { get, post } from '@/utils/request'

export interface PluginInfo {
  name: string
  version: string
  description: string
  author: string
  enabled: boolean
}

export interface PluginDetail extends PluginInfo {
  dependencies: string[]
}

export interface HookInfo {
  name: string
  callback_count: number
}

export const pluginApi = {
  /** 获取插件列表 */
  list: () => get<{ plugins: PluginInfo[]; count: number }>('/api/plugins/list'),

  /** 获取插件详情 */
  detail: (name: string) => get<PluginDetail>(`/api/plugins/${name}`),

  /** 启用插件 */
  enable: (name: string) =>
    post<{ status: string; message: string }>(`/api/plugins/${name}/enable`),

  /** 禁用插件 */
  disable: (name: string) =>
    post<{ status: string; message: string }>(`/api/plugins/${name}/disable`),

  /** 卸载插件 */
  unload: (name: string) =>
    post<{ status: string; message: string }>(`/api/plugins/${name}/unload`),

  /** 发现插件 */
  discover: () =>
    post<{ discovered_count: number; plugin_dir: string; plugins: Array<{ name: string; version: string; description: string }> }>(
      '/api/plugins/discover',
    ),

  /** 获取钩子列表 */
  hooks: () => get<{ hooks: HookInfo[]; count: number }>('/api/plugins/hooks/list'),
}
