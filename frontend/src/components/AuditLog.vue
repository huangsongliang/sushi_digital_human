<template>
  <div class="audit-page">
    <!-- 顶部栏 -->
    <header class="page-header">
      <button class="back-btn" @click="goBack">
        <span>←</span> 返回
      </button>
      <h1 class="page-title">审计日志</h1>
      <div class="header-actions">
        <button class="action-btn" @click="handleExport">
          导出
        </button>
        <button class="action-btn action-btn-danger" @click="handleCleanup">
          清理旧日志
        </button>
      </div>
    </header>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="audit-tabs">
      <el-tab-pane label="操作日志" name="logs">
        <!-- 筛选条件 -->
        <div class="filter-panel">
          <el-row :gutter="12">
            <el-col :span="6">
              <el-select
                v-model="filters.action"
                placeholder="操作类型"
                clearable
                class="filter-select"
              >
                <el-option
                  v-for="a in actionTypes"
                  :key="a.value"
                  :label="a.name"
                  :value="a.value"
                />
              </el-select>
            </el-col>
            <el-col :span="6">
              <el-select
                v-model="filters.category"
                placeholder="类别"
                clearable
                class="filter-select"
              >
                <el-option
                  v-for="c in categoryTypes"
                  :key="c.value"
                  :label="c.name"
                  :value="c.value"
                />
              </el-select>
            </el-col>
            <el-col :span="6">
              <el-input
                v-model="filters.user_id"
                placeholder="用户ID"
                clearable
                class="filter-select"
              />
            </el-col>
            <el-col :span="6">
              <el-select
                v-model="filters.status"
                placeholder="状态"
                clearable
                class="filter-select"
              >
                <el-option label="成功" value="success" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-col>
          </el-row>
          <el-row :gutter="12" style="margin-top: 12px;">
            <el-col :span="6">
              <el-date-picker
                v-model="filters.start_time"
                type="datetime"
                placeholder="开始时间"
                format="YYYY-MM-DD HH:mm"
                class="filter-select"
              />
            </el-col>
            <el-col :span="6">
              <el-date-picker
                v-model="filters.end_time"
                type="datetime"
                placeholder="结束时间"
                format="YYYY-MM-DD HH:mm"
                class="filter-select"
              />
            </el-col>
            <el-col :span="6">
              <el-input
                v-model="filters.resource_type"
                placeholder="资源类型"
                clearable
                class="filter-select"
              />
            </el-col>
            <el-col :span="6">
              <div class="filter-actions">
                <el-button type="primary" @click="searchLogs">查询</el-button>
                <el-button @click="resetFilters">重置</el-button>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 日志表格 -->
        <el-table
          :data="logs"
          v-loading="loading"
          stripe
          class="log-table"
          max-height="calc(100vh - 380px)"
        >
          <el-table-column prop="created_at" label="时间" width="170">
            <template #default="{ row }">
              <span class="time-cell">{{ formatDateTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="user_id" label="用户" width="120" />
          <el-table-column prop="action" label="操作" width="110">
            <template #default="{ row }">
              <el-tag :type="actionTagType(row.action)" size="small">
                {{ row.action }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="类别" width="100">
            <template #default="{ row }">
              <el-tag :type="categoryTagType(row.category)" size="small" effect="plain">
                {{ row.category }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="resource_type" label="资源类型" width="110">
            <template #default="{ row }">
              {{ row.resource_type || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="resource_id" label="资源ID" width="160">
            <template #default="{ row }">
              <span v-if="row.resource_id" class="resource-id">{{ row.resource_id }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <span :class="['status-badge', row.status === 'success' ? 'status-success' : 'status-failed']">
                {{ row.status === 'success' ? '成功' : '失败' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="ip_address" label="IP" width="130">
            <template #default="{ row }">
              {{ row.ip_address || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="details" label="详情" min-width="180">
            <template #default="{ row }">
              <span class="details-cell">{{ row.details || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="totalLogs"
            layout="total, prev, pager, next"
            @current-change="handlePageChange"
          />
        </div>
      </el-tab-pane>

      <!-- 安全事件 -->
      <el-tab-pane label="安全事件" name="security">
        <div class="security-panel">
          <div class="security-sub-tabs">
            <button
              :class="['sub-tab', { active: securityView === 'events' }]"
              @click="loadSecurity('events')"
            >
              安全事件
            </button>
            <button
              :class="['sub-tab', { active: securityView === 'failed' }]"
              @click="loadSecurity('failed')"
            >
              失败尝试
            </button>
          </div>

          <el-table
            :data="securityLogs"
            v-loading="securityLoading"
            stripe
            class="log-table"
            max-height="calc(100vh - 380px)"
          >
            <el-table-column prop="created_at" label="时间" width="170">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="user_id" label="用户" width="120" />
            <el-table-column prop="action" label="操作" width="120">
              <template #default="{ row }">
                <el-tag type="danger" size="small">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="ip_address" label="IP" width="140" />
            <el-table-column prop="resource_type" label="资源类型" width="110">
              <template #default="{ row }">
                {{ row.resource_type || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="details" label="详情" min-width="200">
              <template #default="{ row }">
                {{ row.details || '-' }}
              </template>
            </el-table-column>
          </el-table>

          <div v-if="!securityLoading && securityLogs.length === 0" class="empty-state">
            <div class="empty-icon">🛡️</div>
            <p>暂无安全事件</p>
          </div>
        </div>
      </el-tab-pane>

      <!-- 统计概览 -->
      <el-tab-pane label="统计概览" name="statistics">
        <div class="stats-panel" v-loading="statsLoading">
          <div class="stats-summary">
            <div class="stat-card">
              <div class="stat-value">{{ stats?.statistics?.total_count || 0 }}</div>
              <div class="stat-label">总操作数</div>
            </div>
            <div class="stat-card stat-card-warning">
              <div class="stat-value">{{ stats?.statistics?.failed_count || 0 }}</div>
              <div class="stat-label">失败操作</div>
            </div>
            <div class="stat-card stat-card-info">
              <div class="stat-value">{{ stats?.days || 7 }}</div>
              <div class="stat-label">统计天数</div>
            </div>
          </div>

          <!-- 操作分布 -->
          <div class="stats-section" v-if="stats?.statistics?.actions">
            <h3 class="section-title">操作分布</h3>
            <div class="bar-chart">
              <div
                v-for="(count, action) in stats.statistics.actions"
                :key="action"
                class="bar-row"
              >
                <span class="bar-label">{{ action }}</span>
                <div class="bar-track">
                  <div
                    class="bar-fill"
                    :style="{ width: barWidth(count, stats.statistics.total_count) }"
                  ></div>
                </div>
                <span class="bar-count">{{ count }}</span>
              </div>
            </div>
          </div>

          <!-- 类别分布 -->
          <div class="stats-section" v-if="stats?.statistics?.categories">
            <h3 class="section-title">类别分布</h3>
            <div class="bar-chart">
              <div
                v-for="(count, cat) in stats.statistics.categories"
                :key="cat"
                class="bar-row"
              >
                <span class="bar-label">{{ cat }}</span>
                <div class="bar-track">
                  <div
                    class="bar-fill bar-fill-category"
                    :style="{ width: barWidth(count, stats.statistics.total_count) }"
                  ></div>
                </div>
                <span class="bar-count">{{ count }}</span>
              </div>
            </div>
          </div>

          <!-- Top 用户 -->
          <div class="stats-section" v-if="stats?.statistics?.top_users?.length">
            <h3 class="section-title">活跃用户 Top 10</h3>
            <div class="bar-chart">
              <div
                v-for="user in stats.statistics.top_users"
                :key="user.user_id"
                class="bar-row"
              >
                <span class="bar-label">{{ user.user_id }}</span>
                <div class="bar-track">
                  <div
                    class="bar-fill bar-fill-user"
                    :style="{ width: barWidth(user.count, stats.statistics.top_users[0]?.count || 1) }"
                  ></div>
                </div>
                <span class="bar-count">{{ user.count }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { auditApi, type AuditLogEntry, type AuditStatisticsResponse, type ActionType, type CategoryType } from '@/api/audit'
import { useNotificationStore } from '@/stores/notification'

const router = useRouter()
const notifStore = useNotificationStore()

const activeTab = ref('logs')

// ======= 日志列表 =======
const logs = ref<AuditLogEntry[]>([])
const loading = ref(false)
const totalLogs = ref(0)
const currentPage = ref(1)
const pageSize = 50

const filters = ref({
  action: '',
  category: '',
  user_id: '',
  status: '',
  start_time: null as Date | null,
  end_time: null as Date | null,
  resource_type: '',
})

const actionTypes = ref<ActionType[]>([])
const categoryTypes = ref<CategoryType[]>([])

// ======= 安全事件 =======
const securityView = ref<'events' | 'failed'>('events')
const securityLogs = ref<AuditLogEntry[]>([])
const securityLoading = ref(false)

// ======= 统计 =======
const stats = ref<AuditStatisticsResponse | null>(null)
const statsLoading = ref(false)

function goBack() {
  router.push('/')
}

onMounted(() => {
  loadActionTypes()
  loadCategoryTypes()
  searchLogs()
})

async function loadActionTypes() {
  try {
    const res = await auditApi.actionTypes()
    actionTypes.value = res.actions
  } catch { /* ignore */ }
}

async function loadCategoryTypes() {
  try {
    const res = await auditApi.categoryTypes()
    categoryTypes.value = res.categories
  } catch { /* ignore */ }
}

async function searchLogs() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize,
    }
    if (filters.value.action) params.action = filters.value.action
    if (filters.value.category) params.category = filters.value.category
    if (filters.value.user_id) params.user_id = filters.value.user_id
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.resource_type) params.resource_type = filters.value.resource_type
    if (filters.value.start_time) params.start_time = filters.value.start_time.toISOString()
    if (filters.value.end_time) params.end_time = filters.value.end_time.toISOString()

    const res = await auditApi.queryLogs(params as Record<string, string>)
    logs.value = res.logs
    totalLogs.value = res.count
  } catch {
    notifStore.toastError('查询失败', '无法获取审计日志')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = {
    action: '',
    category: '',
    user_id: '',
    status: '',
    start_time: null,
    end_time: null,
    resource_type: '',
  }
  currentPage.value = 1
  searchLogs()
}

function handlePageChange(page: number) {
  currentPage.value = page
  searchLogs()
}

function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const h = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  const s = String(date.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${d} ${h}:${min}:${s}`
}

function actionTagType(action: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    create: 'success',
    read: 'info',
    update: 'warning',
    delete: 'danger',
    login: 'success',
    logout: 'info',
    login_failed: 'danger',
    permission_change: 'warning',
    system_config: 'warning',
    export: '',
    import: '',
    share: 'info',
    download: '',
  }
  return map[action] || 'info'
}

function categoryTagType(cat: string): '' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, '' | 'success' | 'warning' | 'info' | 'danger'> = {
    user: 'info',
    document: 'success',
    permission: 'warning',
    system: '',
    security: 'danger',
    data: '',
  }
  return map[cat] || 'info'
}

async function loadSecurity(view: 'events' | 'failed') {
  securityView.value = view
  securityLoading.value = true
  try {
    if (view === 'events') {
      const res = await auditApi.securityEvents(7, 100)
      securityLogs.value = res.logs
    } else {
      const res = await auditApi.failedAttempts(24, 100)
      securityLogs.value = res.logs
    }
  } catch {
    notifStore.toastError('加载失败', '无法获取安全事件')
  } finally {
    securityLoading.value = false
  }
}

async function loadStatistics() {
  statsLoading.value = true
  try {
    stats.value = await auditApi.statistics(7)
  } catch {
    notifStore.toastError('加载失败', '无法获取统计数据')
  } finally {
    statsLoading.value = false
  }
}

function barWidth(count: number, total: number): string {
  if (total === 0) return '0%'
  return Math.max((count / total) * 100, 2).toFixed(1) + '%'
}

async function handleExport() {
  try {
    const startTime = filters.value.start_time || new Date(Date.now() - 7 * 86400000)
    const endTime = filters.value.end_time || new Date()
    const res = await auditApi.exportLogs(startTime.toISOString(), endTime.toISOString())
    notifStore.toastSuccess('导出成功', `导出了 ${res.count} 条日志`)
  } catch {
    notifStore.toastError('导出失败')
  }
}

async function handleCleanup() {
  try {
    await ElMessageBox.confirm(
      '将删除 90 天前的审计日志，此操作不可恢复。确定继续吗？',
      '确认清理',
      { confirmButtonText: '确定清理', cancelButtonText: '取消', type: 'warning' },
    )
    const res = await auditApi.cleanup(90)
    notifStore.toastSuccess('清理完成', `删除了 ${res.deleted_count} 条旧日志`)
    searchLogs()
  } catch { /* 用户取消 */ }
}

// 切换到统计 tab 时加载数据
import { watch } from 'vue'
watch(activeTab, (tab) => {
  if (tab === 'statistics' && !stats.value) {
    loadStatistics()
  } else if (tab === 'security' && securityLogs.value.length === 0) {
    loadSecurity('events')
  }
})
</script>

<style scoped>
.audit-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-paper-warm);
}

.page-header {
  display: flex;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(139, 115, 85, 0.15);
  gap: 16px;
}

.back-btn {
  padding: 8px 14px;
  border: 1px solid rgba(139, 115, 85, 0.2);
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--color-ink-light);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: rgba(139, 115, 85, 0.08);
  color: var(--color-ink-black);
}

.page-title {
  flex: 1;
  font-size: 20px;
  color: var(--color-ink-black);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 8px 16px;
  border: 1px solid rgba(139, 115, 85, 0.2);
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--color-accent);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(139, 115, 85, 0.1);
}

.action-btn-danger {
  color: var(--color-error);
}

.action-btn-danger:hover {
  background: rgba(181, 71, 71, 0.1);
}

.audit-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 24px;
}

.audit-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.audit-tabs :deep(.el-tab-pane) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.filter-panel {
  padding: 16px 0;
}

.filter-select {
  width: 100%;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.log-table {
  flex: 1;
  font-size: 13px;
}

.time-cell {
  font-family: monospace;
  font-size: 12px;
}

.resource-id {
  font-family: monospace;
  font-size: 12px;
  color: var(--color-ink-light);
  word-break: break-all;
}

.details-cell {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 12px;
  color: var(--color-ink-light);
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.status-success {
  background: rgba(103, 194, 58, 0.1);
  color: var(--color-success);
}

.status-failed {
  background: rgba(181, 71, 71, 0.1);
  color: var(--color-error);
}

.pagination-bar {
  padding: 12px 0;
  display: flex;
  justify-content: center;
}

/* 安全面板 */
.security-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.security-sub-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 16px;
  border-bottom: 2px solid rgba(139, 115, 85, 0.1);
}

.sub-tab {
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: var(--color-ink-light);
  cursor: pointer;
  font-size: 14px;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s ease;
}

.sub-tab:hover {
  color: var(--color-ink-black);
}

.sub-tab.active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
  font-weight: 500;
}

/* 统计面板 */
.stats-panel {
  overflow-y: auto;
  flex: 1;
}

.stats-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  padding: 20px;
  background: white;
  border-radius: var(--radius-md);
  text-align: center;
  border: 1px solid rgba(139, 115, 85, 0.1);
}

.stat-card-warning {
  border-color: rgba(230, 162, 60, 0.3);
  background: rgba(230, 162, 60, 0.03);
}

.stat-card-info {
  border-color: rgba(64, 158, 255, 0.3);
  background: rgba(64, 158, 255, 0.03);
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-ink-black);
  font-family: monospace;
}

.stat-label {
  font-size: 13px;
  color: var(--color-ink-light);
  margin-top: 4px;
}

.stats-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  color: var(--color-ink-black);
  margin-bottom: 12px;
}

.bar-chart {
  background: white;
  border-radius: var(--radius-md);
  padding: 16px;
  border: 1px solid rgba(139, 115, 85, 0.1);
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.bar-row:last-child {
  margin-bottom: 0;
}

.bar-label {
  width: 100px;
  font-size: 13px;
  color: var(--color-ink-black);
  text-align: right;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  flex: 1;
  height: 22px;
  background: rgba(139, 115, 85, 0.08);
  border-radius: 11px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-accent) 0%, var(--color-accent-light) 100%);
  border-radius: 11px;
  transition: width 0.5s ease;
  min-width: 4px;
}

.bar-fill-category {
  background: linear-gradient(90deg, #409eff 0%, #79bbff 100%);
}

.bar-fill-user {
  background: linear-gradient(90deg, #67c23a 0%, #95d475 100%);
}

.bar-count {
  width: 50px;
  font-size: 13px;
  color: var(--color-ink-light);
  font-family: monospace;
  flex-shrink: 0;
}

.empty-state {
  text-align: center;
  padding: 80px 40px;
}

.empty-icon {
  font-size: 56px;
  margin-bottom: 16px;
  opacity: 0.4;
}

.empty-state p {
  font-size: 14px;
  color: var(--color-ink-faint);
}
</style>
