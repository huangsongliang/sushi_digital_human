---
description: Vue3 + TypeScript + Element Plus 前端代码规范
alwaysApply: true
---

# Vue3 / TypeScript 代码规范

## 组件结构顺序

```vue
<template>
  <!-- 1. 模板：HTML 结构 -->
  <div class="component-name">
    <el-button @click.stop="handleClick">按钮</el-button>
  </div>
</template>

<script setup lang="ts">
// 2. 脚本：逻辑
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import type { User } from '@/types'

// 组件命名用 PascalCase
defineOptions({ name: 'ComponentName' })

// ref / reactive
const loading = ref<boolean>(false)
const userList = ref<User[]>([])

// computed 必须用 computed() 包裹
const filteredUsers = computed(() =>
  userList.value.filter(u => u.active)
)

// 方法
const handleClick = () => { ... }

onMounted(() => { ... })
</script>

<style scoped>
/* 3. 样式：scoped 避免污染 */
.component-name { }
</style>
```

## 响应式规范（重要）

```typescript
// ❌ 错误：直接解构会丢失响应式
const { user, setUser } = useUserStore()  // 错误！

// ✅ 正确：通过 store 实例访问
const userStore = useUserStore()
const user = computed(() => userStore.user)
const setUser = userStore.setUser

// ✅ 正确：用 storeToRefs（仅对 state 使用）
import { storeToRefs } from 'pinia'
const { user } = storeToRefs(useUserStore())
```

## 事件处理规范

```vue
<!-- 阻止事件冒泡 -->
<div class="modal-mask" @click.self="closeModal">
  <div class="modal-container" @click.stop>
    <!-- 内容区点击不关闭弹窗 -->
  </div>
</div>

<!-- 阻止默认行为 -->
<form @submit.prevent="handleSubmit">
```

## z-index 层级规范

```
容器（如 modal 外层）: 1000
遮罩层（mask）:          1001
弹窗内容区:               1002
全局通知/Toast:            9999
```

## TypeScript 类型规范

```typescript
// 所有 props 必须有类型注解
interface Props {
  visible: boolean
  title: string
  width?: string  // 可选参数用 ?
}

const props = withDefaults(defineProps<Props>(), {
  width: '500px',  // 默认值
})

// 所有 emit 必须有类型注解
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'submit', data: FormData): void
}>()

// API 响应类型
interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}
```

## API 调用封装规范

```typescript
// frontend/src/api/ 目录下统一封装
// frontend/src/api/document.ts
import request from '@/utils/request'

export interface Document {
  id: string
  title: string
  createdAt: string
}

export const documentApi = {
  list: () => request.get<ApiResponse<Document[]>>('/api/documents/list'),
  upload: (file: File, desc: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('description', desc)
    return request.post('/api/documents/upload', formData)
  },
}
```

## 路由规范

```typescript
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/views/Home.vue'),  // 懒加载
      meta: { requiresAuth: true },
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.token) {
    next('/login')
  } else {
    next()
  }
})
```

## 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件文件名 | `kebab-case.vue` | `user-profile.vue` |
| 组件注册名 | `PascalCase` | `UserProfile` |
| 变量/函数 | `camelCase` | `getUserInfo` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| CSS 类名 | `kebab-case` | `.user-profile { }` |
| Pinia store | `camelCase` + `Store` 后缀 | `useUserStore` |

## Element Plus 使用规范

```vue
<!-- 表单：用 el-form 的 rules 做校验 -->
<el-form ref="formRef" :model="form" :rules="rules">
  <el-form-item label="用户名" prop="username">
    <el-input v-model="form.username" />
  </el-form-item>
</el-form>

<!-- 表格：用 slot 自定义列 -->
<el-table :data="userList">
  <el-table-column label="操作">
    <template #default="{ row }">
      <el-button @click="editUser(row)">编辑</el-button>
    </template>
  </el-table-column>
</el-table>
```

## 禁止事项

- ❌ 禁止 `any` 类型（用 `unknown` + 类型守卫替代）
- ❌ 禁止直接解构 Pinia store
- ❌ 禁止在模板中写复杂逻辑（用 computed 替代）
- ❌ 禁止硬编码 API 地址（用环境变量 `import.meta.env.VITE_API_BASE_URL`）
