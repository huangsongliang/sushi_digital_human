<template>
  <div class="demo-page">
    <el-card class="demo-card">
      <template #header>
        <div class="card-header">
          <span>🎨 系统功能演示</span>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="通知系统" name="notifications">
          <div class="notification-demo">
            <el-space wrap>
              <el-button type="success" @click="showSuccess">
                <el-icon><SuccessFilled /></el-icon>
                成功通知
              </el-button>
              <el-button type="info" @click="showInfo">
                <el-icon><InfoFilled /></el-icon>
                信息通知
              </el-button>
              <el-button type="warning" @click="showWarning">
                <el-icon><WarningFilled /></el-icon>
                警告通知
              </el-button>
              <el-button type="danger" @click="showError">
                <el-icon><CircleCloseFilled /></el-icon>
                错误通知
              </el-button>
            </el-space>
            <el-divider />
            <p class="description">点击按钮查看通知效果</p>
          </div>
        </el-tab-pane>

        <el-tab-pane label="主题切换" name="theme">
          <div class="theme-demo">
            <el-space direction="vertical" size="large">
              <div>
                <p class="description">
                  点击右上角的主题切换按钮，体验深色/浅色主题
                </p>
              </div>
              <el-card>
                <p>这是一张示例卡片，会随主题变化样式</p>
                <el-space>
                  <el-button>按钮1</el-button>
                  <el-button type="primary">主按钮</el-button>
                  <el-button type="success">成功按钮</el-button>
                </el-space>
              </el-card>
            </el-space>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useNotificationStore } from '../stores/notification'
import {
  SuccessFilled,
  InfoFilled,
  WarningFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue'

const activeTab = ref('notifications')
const notificationStore = useNotificationStore()

function showSuccess() {
  notificationStore.success('操作成功！', '您的任务已完成。')
}

function showInfo() {
  notificationStore.info('提示信息', '这是一条普通的系统通知。')
}

function showWarning() {
  notificationStore.warning('注意', '请注意检查您的输入。')
}

function showError() {
  notificationStore.error('发生错误', '操作失败，请重试。')
}
</script>

<style scoped>
.demo-page {
  padding: 40px;
  max-width: 900px;
  margin: 0 auto;
}

.demo-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.notification-demo {
  padding: 20px;
}

.theme-demo {
  padding: 20px;
}

.description {
  color: var(--color-ink-light);
  margin: 10px 0;
}
</style>
