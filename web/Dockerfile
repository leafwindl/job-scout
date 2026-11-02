# ---- Next.js Web ----
FROM node:22-alpine AS base
RUN corepack enable
WORKDIR /app

# 国内网络用 npmmirror；海外可删掉这一行
RUN pnpm config set registry https://registry.npmmirror.com

# 依赖层
# minimumReleaseAge：pnpm 10 默认拒绝「太新」的包（供应链防护），
# 我们的 lockfile 里 next 15.5.28 刚发布，容器内放行（个人项目，锁文件已审核）
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --config.minimumReleaseAge=0

# 源码层
COPY . .

# NEXT_PUBLIC_ 变量在构建期注入，运行期改无效
ARG NEXT_PUBLIC_API_BASE=http://localhost:8001
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build

ENV NODE_ENV=production
EXPOSE 3000

CMD ["pnpm", "start"]
