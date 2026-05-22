# 项目代码规范指南

## 一、Python 代码规范（PEP8）

### 1. 导入规范
- 所有 `import` 语句必须放在文件顶部
- 导入顺序：标准库 → 第三方库 → 项目内部模块
- 不要在函数/类内部导入模块

### 2. 注释规范
- 单行注释：`#` 后面必须跟**一个空格**
- 文档字符串：使用三引号 `"""` 包裹
- 函数/类必须有文档字符串说明

### 3. 空行规范
- 类定义后：**两个空行**
- 函数定义后：**两个空行**
- 逻辑段落之间：**一个空行**

### 4. 代码风格
- 行长度：最大120字符
- 缩进：使用4个空格
- 变量命名：`snake_case`
- 类命名：`PascalCase`

### 5. 类型注解
- 所有函数参数和返回值必须有类型注解
- 使用 `Optional[T]` 表示可选参数
- 使用 `List[T]`, `Dict[K, V]` 等泛型类型

---

## 二、Vue/TypeScript 规范

### 1. 响应式规范
- **禁止直接解构 Pinia store**（会丢失响应式）
- 正确方式：`const store = useStore()` 然后 `store.value`
- 计算属性必须使用 `computed()` 包裹

### 2. 事件处理
- 使用 `@click.stop` 阻止事件冒泡
- 遮罩层和内容区要分离处理
- z-index 层级：容器(1000) → 遮罩(1001) → 内容(1002)

### 3. 组件结构
- `<template>` → `<script setup>` → `<style scoped>`
- 导入语句放在 `<script>` 顶部
- 使用 TypeScript 类型注解

---

## 三、代码质量检查工具

### 1. Python 检查
```bash
# 代码风格检查
uv run flake8 backend/ --max-line-length=120

# 自动修复
uv run black backend/        # 格式化
uv run isort backend/        # 导入排序
```

### 2. Vue 检查
```bash
# 代码风格检查
cd frontend && npm run lint

# 自动修复
cd frontend && npm run lint -- --fix
```

---

## 四、智能体代码输出格式要求

### Python 文件输出格式
```python
"""模块文档字符串"""

from typing import List, Dict, Optional

# 代码实现
```

### Vue 文件输出格式
```vue
<template>
  <div class="component-name"></div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
</script>

<style scoped>
</style>
```

---

## 五、提交前检查清单

✅ flake8 检查通过  
✅ 单元测试通过  
✅ 代码符合上述规范  
✅ 没有硬编码敏感信息