<template>
  <div class="plugin-page">
    <header class="page-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1 class="page-title">插件市场</h1>
      <button class="action-btn" @click="handleDiscover">发现插件</button>
    </header>

    <el-tabs v-model="activeTab">
      <!-- 已安装插件 -->
      <el-tab-pane label="已安装" name="installed">
        <div class="plugin-grid">
          <div v-for="p in plugins" :key="p.name" class="plugin-card">
            <div class="card-top">
              <span class="plugin-icon">🧩</span>
              <div class="plugin-meta">
                <h3 class="plugin-name">{{ p.name }}</h3>
                <span class="plugin-ver">v{{ p.version }}</span>
              </div>
              <el-switch
                :model-value="p.enabled"
                @change="(v: boolean) => togglePlugin(p.name, v)"
                :loading="toggling === p.name"
              />
            </div>
            <p class="plugin-desc">{{ p.description }}</p>
            <div class="card-bottom">
              <span class="plugin-author">{{ p.author }}</span>
              <div class="card-actions">
                <button class="link-btn" @click="viewDetail(p)">详情</button>
                <button class="link-btn link-btn-danger" @click="handleUnload(p.name)">卸载</button>
              </div>
            </div>
          </div>

          <div v-if="!loading && plugins.length === 0" class="empty-state">
            <div class="empty-icon">🧩</div>
            <p>暂无已安装插件</p>
          </div>
        </div>
      </el-tab-pane>

      <!-- 钩子管理 -->
      <el-tab-pane label="钩子" name="hooks">
        <el-table :data="hookList" v-loading="hookLoading" stripe>
          <el-table-column prop="name" label="钩子名称" width="200" />
          <el-table-column prop="callback_count" label="回调数量" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="row.callback_count > 0 ? 'success' : 'info'" size="small">
                {{ row.callback_count }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="200">
            <template #default="{ row }">
              <span class="hook-hint">{{ hookHints[row.name] || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="!hookLoading && hookList.length === 0" class="empty-state">
          <p>暂无已注册钩子</p>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 插件详情弹窗 -->
    <el-dialog v-model="showDetail" :title="`插件详情 - ${detailPlugin?.name || ''}`" width="440px">
      <div v-if="detailPlugin" class="detail-body">
        <div class="detail-row"><span class="d-label">名称</span><span>{{ detailPlugin.name }}</span></div>
        <div class="detail-row"><span class="d-label">版本</span><span>v{{ detailPlugin.version }}</span></div>
        <div class="detail-row"><span class="d-label">作者</span><span>{{ detailPlugin.author }}</span></div>
        <div class="detail-row"><span class="d-label">描述</span><span>{{ detailPlugin.description }}</span></div>
        <div class="detail-row"><span class="d-label">状态</span><el-tag :type="detailPlugin.enabled ? 'success' : 'info'" size="small">{{ detailPlugin.enabled ? '已启用' : '已禁用' }}</el-tag></div>
        <div class="detail-row" v-if="detailPlugin.dependencies?.length">
          <span class="d-label">依赖</span>
          <span>
            <el-tag v-for="d in detailPlugin.dependencies" :key="d" size="small" class="dep-tag">{{ d }}</el-tag>
          </span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { pluginApi, type PluginInfo, type PluginDetail, type HookInfo } from '@/api/plugin'
import { useNotificationStore } from '@/stores/notification'

const router = useRouter()
const notifStore = useNotificationStore()
const activeTab = ref('installed')

const plugins = ref<PluginInfo[]>([])
const loading = ref(false)
const toggling = ref('')

const hookList = ref<HookInfo[]>([])
const hookLoading = ref(false)

const showDetail = ref(false)
const detailPlugin = ref<PluginDetail | null>(null)

const hookHints: Record<string, string> = {
  before_chat: '对话前调用',
  after_chat: '对话后调用',
  before_document_load: '文档加载前',
  after_document_load: '文档加载后',
  on_startup: '应用启动',
  on_shutdown: '应用关闭',
}

function goBack() { router.push('/') }

onMounted(() => {
  loadPlugins()
})

async function loadPlugins() {
  loading.value = true
  try {
    const res = await pluginApi.list()
    plugins.value = res.plugins
  } catch {
    // 无插件时返回空
    plugins.value = []
  } finally {
    loading.value = false
  }
}

async function togglePlugin(name: string, enable: boolean) {
  toggling.value = name
  try {
    if (enable) {
      await pluginApi.enable(name)
      notifStore.toastSuccess(`${name} 已启用`)
    } else {
      await pluginApi.disable(name)
      notifStore.toastSuccess(`${name} 已禁用`)
    }
    loadPlugins()
  } catch {
    notifStore.toastError('操作失败')
  } finally {
    toggling.value = ''
  }
}

async function viewDetail(p: PluginInfo) {
  try {
    detailPlugin.value = await pluginApi.detail(p.name)
    showDetail.value = true
  } catch {
    notifStore.toastError('获取详情失败')
  }
}

async function handleUnload(name: string) {
  try {
    await ElMessageBox.confirm(`确定卸载插件「${name}」吗？`, '确认卸载', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
    await pluginApi.unload(name)
    notifStore.toastSuccess('卸载成功')
    loadPlugins()
  } catch { /* cancel */ }
}

async function handleDiscover() {
  try {
    const res = await pluginApi.discover()
    notifStore.toastInfo(`发现 ${res.discovered_count} 个插件`)
    loadPlugins()
  } catch {
    notifStore.toastError('发现插件失败')
  }
}

async function loadHooks() {
  hookLoading.value = true
  try {
    const res = await pluginApi.hooks()
    hookList.value = res.hooks
  } catch {
    hookList.value = []
  } finally {
    hookLoading.value = false
  }
}

import { watch } from 'vue'
watch(activeTab, (tab) => {
  if (tab === 'hooks' && hookList.value.length === 0) loadHooks()
})
</script>

<style scoped>
.plugin-page { height: 100vh; display: flex; flex-direction: column; background: var(--color-paper-warm); }
.page-header { display: flex; align-items: center; padding: 20px 24px; border-bottom: 1px solid rgba(139,115,85,0.15); gap: 16px; }
.back-btn { padding: 8px 14px; border: 1px solid rgba(139,115,85,0.2); background: transparent; border-radius: var(--radius-md); color: var(--color-ink-light); cursor: pointer; font-size: 14px; }
.back-btn:hover { background: rgba(139,115,85,0.08); }
.page-title { flex: 1; font-size: 20px; color: var(--color-ink-black); margin: 0; }
.action-btn { padding: 8px 16px; border: 1px solid var(--color-accent); background: transparent; border-radius: var(--radius-md); color: var(--color-accent); cursor: pointer; font-size: 13px; transition: all 0.15s; }
.action-btn:hover { background: rgba(139,115,85,0.1); }
.el-tabs { flex: 1; padding: 0 24px; }
.el-tabs :deep(.el-tabs__content) { flex: 1; overflow-y: auto; }
.plugin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; padding: 16px 0; }
.plugin-card { background: white; border-radius: var(--radius-md); padding: 16px; border: 1px solid rgba(139,115,85,0.1); transition: all 0.15s; }
.plugin-card:hover { border-color: rgba(139,115,85,0.2); box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
.card-top { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.plugin-icon { font-size: 28px; }
.plugin-meta { flex: 1; }
.plugin-name { font-size: 15px; color: var(--color-ink-black); margin: 0; }
.plugin-ver { font-size: 12px; color: var(--color-ink-faint); font-family: monospace; }
.plugin-desc { font-size: 13px; color: var(--color-ink-light); margin: 0 0 12px 0; }
.card-bottom { display: flex; align-items: center; justify-content: space-between; }
.plugin-author { font-size: 12px; color: var(--color-ink-faint); }
.card-actions { display: flex; gap: 8px; }
.link-btn { border: none; background: transparent; color: var(--color-accent); cursor: pointer; font-size: 12px; padding: 0; }
.link-btn:hover { text-decoration: underline; }
.link-btn-danger { color: var(--color-error); }
.empty-state { text-align: center; padding: 80px; grid-column: 1 / -1; color: var(--color-ink-faint); }
.empty-icon { font-size: 48px; opacity: 0.3; margin-bottom: 12px; }
.detail-body { display: flex; flex-direction: column; gap: 12px; }
.detail-row { display: flex; gap: 12px; font-size: 14px; align-items: center; }
.d-label { width: 60px; flex-shrink: 0; color: var(--color-ink-faint); font-size: 13px; }
.dep-tag { margin-right: 4px; }
.hook-hint { font-size: 13px; color: var(--color-ink-faint); }
</style>
