<template>
  <div class="ai-assistant-page">
    <el-card class="hero-card" shadow="never">
      <div class="hero-content">
        <div>
          <div class="hero-badge">AI 小助手主入口</div>
          <h2>实验室预约智能助手</h2>
          <p>
            你可以在这里查询可预约实验室、查看预约规则、生成预约草稿，
            并在确认后提交预约请求。
          </p>
        </div>
        <el-tag type="success" effect="light">半自动预约</el-tag>
      </div>
    </el-card>

    <el-row :gutter="20" class="feature-row">
      <el-col :xs="24" :md="8">
        <el-card class="feature-card" shadow="hover">
          <h3>1. 自然语言问答</h3>
          <p>直接问“还有哪些实验室可以预约”，AI 会结合业务数据给你答案。</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card class="feature-card" shadow="hover">
          <h3>2. 预约草稿生成</h3>
          <p>输入一句话即可生成预约草稿，系统会先做规则校验与冲突检测。</p>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card class="feature-card" shadow="hover">
          <h3>3. 确认后提交</h3>
          <p>AI 会先展示摘要信息，你确认后再提交到原有业务系统，保证安全可靠。</p>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="shortcut-row">
      <el-col :xs="24" :md="6" v-for="item in shortcuts" :key="item.title">
        <el-card class="shortcut-card" shadow="hover" @click="openChat(item.prompt)">
          <div class="shortcut-icon">{{ item.icon }}</div>
          <h4>{{ item.title }}</h4>
          <p>{{ item.desc }}</p>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="assistant-launch-card" shadow="never">
      <div class="launch-content">
        <div>
          <h3>开始使用 AI 小助手</h3>
          <p>点击快捷入口可直接打开聊天窗，或使用右下角悬浮按钮随时唤起。</p>
        </div>
        <div class="launch-actions">
          <el-button @click="scrollToTips">查看使用说明</el-button>
          <el-button type="primary" @click="openChat()">打开聊天窗</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="assistant-flow-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>推荐交互流程</span>
        </div>
      </template>
      <el-steps :active="4" align-center finish-status="success">
        <el-step title="提出需求" description="用自然语言描述预约意图" />
        <el-step title="AI 追问" description="信息不全时先补齐关键字段" />
        <el-step title="生成草稿" description="展示资源、时间和冲突结果" />
        <el-step title="确认提交" description="用户确认后走业务接口" />
      </el-steps>
    </el-card>

    <el-card class="tips-card" shadow="never" ref="tipsRef">
      <template #header>
        <div class="card-header">
          <span>使用说明</span>
        </div>
      </template>
      <el-steps :active="3" finish-status="success" simple>
        <el-step title="提出问题" description="直接问空闲资源、预约规则或已有预约" />
        <el-step title="生成草稿" description="AI 返回可预约资源或预约草稿" />
        <el-step title="确认提交" description="确认后提交到业务后端" />
      </el-steps>
    </el-card>

    <el-card class="history-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>会话历史说明</span>
        </div>
      </template>
      <p>AI 服务会保留当前会话的消息历史，用于支持追问和多轮上下文；点击右下角悬浮按钮即可继续上次对话。</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const tipsRef = ref(null)

const shortcuts = [
  { icon: '🔎', title: '查空闲实验室', desc: '快速查询当前可预约资源', prompt: '还有哪些实验室可以预约？' },
  { icon: '📝', title: '生成预约草稿', desc: '直接帮你生成预约摘要', prompt: '帮我预约下周三下午 2 点到 4 点的 301 实验室' },
  { icon: '📅', title: '查询我的预约', desc: '查看当前的个人预约情况', prompt: '帮我查询我今天的预约' },
  { icon: '📘', title: '查看预约规则', desc: '了解预约限制和审批规则', prompt: '预约规则是什么？' }
]

const openChat = (prompt = '') => {
  window.dispatchEvent(new CustomEvent('open-ai-assistant', { detail: { prompt } }))
  ElMessage.success('已打开聊天窗')
}

const scrollToTips = () => {
  tipsRef.value?.$el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<style scoped>
.ai-assistant-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card,
.assistant-launch-card,
.feature-card,
.shortcut-card,
.tips-card,
.assistant-flow-card {
  border-radius: 16px;
}

.assistant-flow-card {
  margin-bottom: 4px;
}

.assistant-flow-card :deep(.el-card__body) {
  padding-top: 8px;
}

.assistant-flow-card :deep(.el-step__title) {
  font-size: 14px;
}

.assistant-flow-card :deep(.el-step__description) {
  font-size: 12px;
}

.assistant-flow-card :deep(.el-steps--horizontal) {
  overflow: auto;
}

.assistant-flow-card :deep(.el-step) {
  min-width: 180px;
}

.hero-content,
.launch-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.hero-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(64, 158, 255, 0.12);
  color: #409eff;
  font-size: 12px;
  margin-bottom: 12px;
}

.hero-content h2,
.launch-content h3,
.feature-card h3,
.shortcut-card h4 {
  margin: 0 0 10px;
}

.hero-content p,
.launch-content p,
.feature-card p,
.shortcut-card p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.feature-row,
.shortcut-row {
  margin-top: 4px;
}

.feature-card,
.shortcut-card {
  min-height: 140px;
}

.shortcut-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.shortcut-card:hover {
  transform: translateY(-2px);
}

.shortcut-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(64, 158, 255, 0.12);
  margin-bottom: 12px;
  font-size: 22px;
}

.launch-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

@media (max-width: 768px) {
  .hero-content,
  .launch-content {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
