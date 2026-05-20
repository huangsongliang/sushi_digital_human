# 前端构建 Dockerfile

# ==================== 第一阶段：构建 ====================
FROM node:20-alpine AS builder

WORKDIR /app

# 设置环境变量
ENV NODE_ENV=production
ENV NPM_CONFIG_LOGLEVEL=warn

# 复制 package 文件
COPY package*.json ./

# 安装依赖（使用淘宝镜像）
RUN npm config set registry https://registry.npmmirror.com && \
    npm ci

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# ==================== 第二阶段：运行 ====================
FROM nginx:alpine AS production

# 从构建阶段复制静态文件
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义配置（可选）
# COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动命令
CMD ["nginx", "-g", "daemon off;"]
