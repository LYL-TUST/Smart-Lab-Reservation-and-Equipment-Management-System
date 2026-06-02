<template>
  <div class="ai-assistant">
    <el-drawer
      v-model="visible"
      title="AI 小助手"
      direction="rtl"
      size="min(100vw, 760px)"
      class="ai-drawer"
      :with-header="true"
      :destroy-on-close="false"
    >
      <div class="assistant-panel">
        <div class="assistant-header">
          <div>
            <h3>实验室预约智能助手</h3>
            <p>可以帮你查询空闲实验室、解释规则、生成预约草稿</p>
          </div>
          <div class="header-meta">
            <el-tag type="success" effect="light">半自动预约</el-tag>
            <el-tag v-if="currentIntentLabel" type="info" effect="light">{{ currentIntentLabel }}</el-tag>
          </div>
        </div>

        <div class="quick-actions">
          <el-button size="small" @click="applyQuickPrompt('还有哪些实验室可以预约？')">查可预约实验室</el-button>
          <el-button size="small" @click="applyQuickPrompt('帮我查询我今天的预约')">查我的预约</el-button>
          <el-button size="small" @click="applyQuickPrompt('帮我预约下周三下午 2 点到 4 点的 301 实验室')">自动生成预约草稿</el-button>
          <el-button size="small" @click="resetConversation">清空会话</el-button>
        </div>

        <div class="assistant-body">
          <div class="assistant-main">
            <div v-if="suggestions.length" class="suggestion-card">
              <div class="section-title">AI 建议你补充的信息</div>
              <div class="suggestion-list">
                <el-tag
                  v-for="item in suggestions"
                  :key="item"
                  class="suggestion-item"
                  effect="plain"
                  @click="applyQuickPrompt(item)"
                >
                  {{ item }}
                </el-tag>
              </div>
            </div>

            <el-collapse v-model="historyPanel">
              <el-collapse-item name="history">
                <template #title>
                  <div class="history-title">
                    <span>会话历史</span>
                    <el-tag size="small" effect="plain">{{ messages.length }} 条消息</el-tag>
                  </div>
                </template>
                <div class="history-list">
                  <div v-for="item in historyPreview" :key="item.id" class="history-item">
                    <div class="history-row">
                      <span class="history-role">{{ item.role === 'user' ? '我' : 'AI' }}</span>
                      <span class="history-time">{{ item.time }}</span>
                    </div>
                    <div class="history-content">{{ item.content }}</div>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>

            <div ref="messageListRef" class="message-list">
              <div
                v-for="msg in messages"
                :key="msg.id"
                :class="['message-item', msg.role]"
              >
                <div class="message-bubble">
                  <div class="message-role-row">
                    <div class="message-role">{{ msg.role === 'user' ? '我' : 'AI 助手' }}</div>
                    <div class="message-time">{{ msg.time }}</div>
                  </div>
                  <div class="message-content">{{ msg.content }}</div>

                  <div v-if="msg.resources && msg.resources.length" class="resource-card">
                    <div class="section-title">可预约资源</div>
                    <button
                      v-for="resource in msg.resources"
                      :key="resource.id"
                      class="resource-item resource-selectable"
                      :class="{ selected: selectedResourceId === resource.id }"
                      type="button"
                      @click="selectResource(resource, msg)"
                    >
                      <div class="resource-top-row">
                        <div class="resource-name">
                          {{ resource.name }}
                          <el-tag v-if="selectedResourceId === resource.id" size="small" effect="dark" type="success" class="selected-tag">已选中</el-tag>
                        </div>
                        <el-tag size="small" effect="plain" type="success">{{ getRecommendLevel(resource) }}</el-tag>
                      </div>
                      <div class="resource-meta">
                        容量 {{ resource.capacity }} 人 · {{ resource.status }}
                      </div>
                      <div v-if="resource.reason" class="resource-reason">
                        推荐理由：{{ resource.reason }}
                      </div>
                      <div class="resource-hint">点击即可选中并填入预约草稿</div>
                    </button>
                  </div>

                  <div v-if="msg.suggestions && msg.suggestions.length" class="suggestion-card message-suggestion-card">
                    <div class="section-title">继续追问 / 快捷建议</div>
                    <div class="suggestion-list">
                      <el-tag
                        v-for="item in msg.suggestions"
                        :key="item"
                        class="suggestion-item"
                        effect="plain"
                        @click="applyQuickPrompt(item)"
                      >
                        {{ item }}
                      </el-tag>
                    </div>
                  </div>

                  <div v-if="msg.clarification" class="clarification-card">
                    <div class="section-title">需要补充</div>
                    <div class="clarification-text">{{ msg.clarification }}</div>
                  </div>

                  <div v-if="msg.draft" class="draft-card">
                    <div class="section-title">预约草稿</div>
                    <div class="draft-item" v-for="(value, key) in displayDraftFields(msg.draft)" :key="key">
                      <span class="draft-key">{{ labelMap[key] || key }}</span>
                      <span class="draft-value">{{ value }}</span>
                    </div>
                    <div v-if="!isDraftComplete(msg.draft)" class="draft-missing">
                      <div class="section-title">还缺少的信息</div>
                      <div class="missing-tag-list">
                        <el-tag
                          v-for="field in getMissingDraftFields(msg.draft)"
                          :key="field"
                          type="warning"
                          effect="plain"
                          class="missing-tag"
                        >
                          {{ field }}
                        </el-tag>
                      </div>
                      <div class="clarification-text missing-tip">
                        请先补全后再提交，我也可以继续帮你追问这些信息。
                      </div>
                    </div>
                    <div class="draft-actions">
                      <el-button v-if="isDraftComplete(msg.draft)" size="small" type="primary" @click="confirmDraft(msg.draft)">确认提交</el-button>
                      <el-button size="small" @click="fillDraftToInput(msg.draft)">编辑后再确认</el-button>
                    </div>
                  </div>

                  <div v-if="msg.reservationResult" class="result-card">
                    <div class="section-title">预约结果</div>
                    <div class="result-status" :class="msg.reservationResult.success ? 'success' : 'fail'">
                      {{ msg.reservationResult.success ? '提交成功' : '提交失败' }}
                    </div>
                    <div class="result-message">{{ msg.reservationResult.message }}</div>
                    <div v-if="msg.reservationResult.reservation" class="result-meta">
                      <div v-for="(value, key) in msg.reservationResult.reservation" :key="key" class="result-item">
                        <span class="result-key">{{ labelMap[key] || key }}</span>
                        <span class="result-value">{{ value }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="loading || typing" class="message-item ai">
                <div class="message-bubble typing-bubble">
                  <div class="message-role-row">
                    <div class="message-role">AI 助手</div>
                    <div class="message-time">正在输入</div>
                  </div>
                  <div class="typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="assistant-side">
            <div class="side-card side-guide">
              <div class="section-title">使用提示</div>
              <ul class="guide-list">
                <li>先描述实验室、时间和人数，AI 会自动生成草稿</li>
                <li>选中右侧资源卡后，可以直接带入草稿</li>
                <li>草稿完整后再点确认提交，减少误操作</li>
              </ul>
            </div>

            <div v-if="lastDraft" class="side-card side-draft">
              <div class="section-title">当前草稿</div>
              <div v-for="(value, key) in displayDraftFields(lastDraft)" :key="key" class="side-draft-item">
                <span class="draft-key">{{ labelMap[key] || key }}</span>
                <span class="draft-value">{{ value }}</span>
              </div>
              <div class="side-draft-footer">
                <el-button size="small" type="primary" @click="fillFromLatestDraft">填入草稿</el-button>
                <el-button size="small" @click="resetConversation">重新开始</el-button>
              </div>
            </div>
          </div>
        </div>

        <div class="input-area">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="4"
            resize="none"
            placeholder="请输入你的问题，例如：帮我预约周三下午 2 点的实验室"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <div class="input-actions">
            <el-button @click="visible = false">关闭</el-button>
            <el-button plain @click="fillFromLatestDraft">填入草稿</el-button>
            <el-button type="primary" :loading="loading" @click="sendMessage">发送</el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-button
      v-if="showFloatingButton"
      class="floating-btn"
      type="primary"
      circle
      size="large"
      @click="openAssistant"
    >
      <el-icon :size="22"><ChatDotRound /></el-icon>
    </el-button>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { confirmReservationDraft, resetAiConversation, sendAiMessage, getAiSession } from '../api/ai'

const props = defineProps({
  showFloatingButton: {
    type: Boolean,
    default: true
  },
  defaultVisible: {
    type: Boolean,
    default: false
  }
})

const visible = ref(props.defaultVisible)
const inputText = ref('')
const loading = ref(false)
const typing = ref(false)
const messageListRef = ref(null)
const sessionId = ref(`session_${Date.now()}`)
const messages = ref([
  {
    id: Date.now(),
    role: 'ai',
    content: '你好，我是实验室预约智能助手。你可以问我空闲实验室、预约规则，或者直接让我帮你生成预约草稿。',
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
])
const historyPanel = ref(['history'])
const currentIntent = ref('')
const suggestions = ref([])
const lastDraft = ref(null)

const intentLabelMap = {
  reservation_request: '预约草稿',
  resource_query: '资源查询',
  my_reservation_query: '我的预约',
  policy_query: '规则说明',
  reservation_change: '改期/取消',
  general_chat: '普通问答'
}

const currentIntentLabel = computed(() => intentLabelMap[currentIntent.value] || '')
const historyPreview = computed(() => messages.value.slice(-8))
const isDraftComplete = (draft = {}) => Boolean((draft?.labId || draft?.laboratoryName) && draft?.startTime && draft?.endTime && draft?.participantCount && draft?.purpose)
const getMissingDraftFields = (draft = {}) => {
  const missing = []
  if (!draft?.labId && !draft?.laboratoryName) missing.push('实验室名称')
  if (!draft?.startTime || !draft?.endTime) missing.push('预约时间')
  if (!draft?.participantCount) missing.push('人数')
  if (!draft?.purpose) missing.push('用途')
  return missing
}

const labelMap = {
  laboratoryName: '实验室',
  startTime: '开始时间',
  endTime: '结束时间',
  purpose: '用途',
  participantCount: '人数',
  equipment: '设备需求'
}

const getRecommendLevel = (resource) => {
  if (!resource) return '推荐'
  if (String(resource.status || '').toUpperCase() !== 'IDLE') return '候选'
  const reason = String(resource.reason || '')
  if (reason.includes('匹配设备') || reason.includes('满足')) return '优先推荐'
  if (reason.includes('接近')) return '可选'
  return '推荐'
}

const displayDraftFields = (draft = {}) => {
  const keys = ['laboratoryName', 'startTime', 'endTime', 'participantCount', 'equipment', 'purpose']
  return keys
    .filter(key => draft[key] !== undefined && draft[key] !== null && draft[key] !== '')
    .reduce((acc, key) => {
      acc[key] = draft[key]
      return acc
    }, {})
}

const parseDraftDate = (value) => {
  if (!value) return null
  const normalized = String(value).trim().replace(' ', 'T')
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

const toBackendDateTime = (value) => {
  const date = parseDraftDate(value)
  if (!date) return value
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:00`
}

const normalizeDraftForSubmit = (draft = {}) => ({
  ...draft,
  startTime: toBackendDateTime(draft.startTime),
  endTime: toBackendDateTime(draft.endTime)
})

const isPastDraftTime = (draft = {}) => {
  const start = parseDraftDate(draft?.startTime)
  if (!start) return false
  return start.getTime() < Date.now()
}

const formatConfirmError = (error) => {
  const rawMessage = error?.response?.data?.data?.message || error?.response?.data?.message || error?.message || ''
  const text = String(rawMessage)
  if (/已过期|过期|过去时间|时间已过/i.test(text)) return '预约时间已过期，请选择未来时间后再提交。'
  if (/冲突|占用|已被预约|不可用/i.test(text)) return '该时间段已被占用，请更换时间或实验室。'
  if (/信息不完整|缺少|实验室.*为空|时间.*为空|草稿.*不完整/i.test(text)) return '实验室信息不完整，请先补全实验室名称、时间等信息。'
  if (/未认证|登录|token|权限/i.test(text)) return '当前登录已失效，请重新登录后再试。'
  return text || '提交失败，请检查信息是否完整或是否存在时间冲突。'
}

const openAssistant = () => {
  visible.value = true
}

defineExpose({ visible, inputText, openAssistant })

const scrollToBottom = async () => {
  await nextTick()
  const el = messageListRef.value
  if (el) el.scrollTop = el.scrollHeight
}

const loadSessionHistory = async () => {
  try {
    const { data } = await getAiSession(sessionId.value)
    const history = data?.data || data || []
    if (Array.isArray(history) && history.length) {
      messages.value = history.map((item, index) => ({
        id: Date.now() + index,
        role: item.role === 'user' ? 'user' : 'ai',
        content: item.content || '',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }))
    }
  } catch (error) {
    // ignore session restore issues
  }
}

watch(messages, scrollToBottom, { deep: true })
watch(visible, (val) => {
  if (val) scrollToBottom()
})

const applyQuickPrompt = (text) => {
  inputText.value = text
  openAssistant()
}

const pushMessage = (role, content, extra = {}) => {
  messages.value.push({
    id: Date.now() + Math.random(),
    role,
    content,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    ...extra
  })
}

const applyPayload = (payload = {}) => {
  currentIntent.value = payload.intent || ''
  suggestions.value = payload.suggestions || []
  if (payload.draft) {
    lastDraft.value = payload.draft
  }
  return payload
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text) {
    ElMessage.warning('请输入内容')
    return
  }

  pushMessage('user', text)
  inputText.value = ''
  loading.value = true

  const timeoutFallback = setTimeout(() => {
    if (loading.value) {
      pushMessage('ai', 'AI 正在处理这个请求，当前响应较慢。你可以稍等片刻，或者重新用更简短的描述再试一次。')
    }
  }, 25000)

  try {
    typing.value = true
    const [aiResponse, sessionResponse] = await Promise.allSettled([
      sendAiMessage({
        sessionId: sessionId.value,
        message: text
      }),
      getAiSession(sessionId.value)
    ])

    let payload = {}
    if (aiResponse.status === 'fulfilled') {
      const { data } = aiResponse.value
      payload = applyPayload(data?.data || data || {})
    }

    if (sessionResponse.status === 'fulfilled') {
      const history = sessionResponse.value?.data?.data || sessionResponse.value?.data || []
      if (Array.isArray(history) && history.length > 0) {
        const latestAi = [...history].reverse().find(item => item.role === 'assistant')
        if (latestAi?.content && !payload.reply) {
          payload.reply = latestAi.content
        }
      }
    }

    const reply = payload.reply || '我已经收到你的消息。'
    await new Promise(resolve => setTimeout(resolve, 250))
    pushMessage('ai', reply, {
      ...(payload.draft ? { draft: payload.draft } : {}),
      ...(payload.resources?.length ? { resources: payload.resources } : {}),
      ...(payload.needsClarification ? { clarification: payload.clarification } : {}),
      ...(payload.suggestions?.length ? { suggestions: payload.suggestions } : {})
    })
  } catch (error) {
    const errorMessage = error?.response?.data?.message || error?.response?.data?.data?.message || error?.message || '未知错误'
    pushMessage('ai', `抱歉，请求 AI 服务失败：${errorMessage}`)
  } finally {
    clearTimeout(timeoutFallback)
    typing.value = false
    loading.value = false
    scrollToBottom()
  }
}

const confirmDraft = async (draft) => {
  if (isPastDraftTime(draft)) {
    pushMessage('ai', '这条草稿的开始时间已经是过去时间了，请先修改为未来时间后再提交。', {
      reservationResult: {
        success: false,
        message: '草稿时间已过期，请先修改为未来时间。',
        reservation: null
      }
    })
    return
  }

  try {
    await ElMessageBox.confirm(
      '确认提交这条预约草稿吗？提交前系统仍会进行业务校验。',
      '确认提交',
      { type: 'warning' }
    )

    const { data } = await confirmReservationDraft({
      sessionId: sessionId.value,
      draft: normalizeDraftForSubmit(draft)
    })

    const result = data?.data || data
    const successMessage = result?.success ? (result?.message || '预约已提交。') : formatConfirmError({ response: { data: { data: { message: result?.message } } } })
    pushMessage('ai', successMessage, {
      reservationResult: {
        success: result?.success ?? true,
        message: successMessage,
        reservation: result?.reservation || null
      }
    })
    suggestions.value = []
  } catch (error) {
    if (error !== 'cancel') {
      const errorMessage = formatConfirmError(error)
      pushMessage('ai', `提交失败：${errorMessage}`, {
        reservationResult: {
          success: false,
          message: errorMessage,
          reservation: null
        }
      })
    }
  }
}

const fillDraftToInput = (draft) => {
  const parts = []
  if (draft.laboratoryName) parts.push(`请帮我预约${draft.laboratoryName}`)
  if (draft.participantCount) parts.push(`人数${draft.participantCount}人`)
  if (draft.equipment) parts.push(`需要${draft.equipment}`)
  if (draft.specialRequirement) parts.push(`特殊要求${draft.specialRequirement}`)
  if (draft.purpose) parts.push(`用途是${draft.purpose}`)
  if (draft.startTime && draft.endTime) parts.push(`时间是${draft.startTime}到${draft.endTime}`)
  inputText.value = parts.join('，') || '请帮我完善这条预约草稿'
}

const selectedResourceId = ref(null)
const pendingResourceChange = ref(null)

const applyResourceSelection = (resource = {}, msg = {}) => {
  const draft = {
    labId: resource?.id || null,
    laboratoryName: resource?.name || '',
    startTime: msg?.draft?.startTime || '',
    endTime: msg?.draft?.endTime || '',
    participantCount: msg?.draft?.participantCount || '',
    equipment: msg?.draft?.equipment || '',
    purpose: msg?.draft?.purpose || '',
    specialRequirement: msg?.draft?.specialRequirement || ''
  }
  lastDraft.value = draft
  selectedResourceId.value = resource?.id || null
  fillDraftToInput(draft)
  currentIntent.value = 'reservation_request'
  ElMessage.success(`已选中 ${resource?.name || '实验室'}，可以继续补充时间并提交预约。`)
}

const selectResource = async (resource, msg = {}) => {
  if (!resource) return
  const currentDraft = lastDraft.value || {}
  const hasExistingDraft = Boolean(
    currentDraft.labId || currentDraft.laboratoryName || currentDraft.startTime || currentDraft.endTime || currentDraft.participantCount || currentDraft.purpose || currentDraft.equipment || currentDraft.specialRequirement
  )
  const sameResource = selectedResourceId.value === resource.id

  if (hasExistingDraft && !sameResource) {
    pendingResourceChange.value = { resource, msg }
    try {
      await ElMessageBox.confirm(
        `当前草稿已有内容，切换到「${resource?.name || '该实验室'}」会覆盖现有草稿，是否继续？`,
        '确认覆盖草稿',
        { type: 'warning', confirmButtonText: '继续覆盖', cancelButtonText: '取消' }
      )
      applyResourceSelection(resource, msg)
      pendingResourceChange.value = null
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error('切换实验室失败，请稍后重试')
      }
    }
    return
  }

  applyResourceSelection(resource, msg)
}

const fillFromLatestDraft = () => {
  if (!lastDraft.value) {
    ElMessage.info('当前没有可填入的预约草稿')
    return
  }

  fillDraftToInput(lastDraft.value)
}

const resetConversation = async () => {
  try {
    await resetAiConversation({ sessionId: sessionId.value })
  } catch (error) {
    // ignore reset errors, local state still clears
  }

  sessionId.value = `session_${Date.now()}`
  messages.value = [
    {
      id: Date.now(),
      role: 'ai',
      content: '会话已重置。你可以重新开始咨询实验室预约问题。',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]
  currentIntent.value = ''
  suggestions.value = []
  lastDraft.value = null
  inputText.value = ''
}

const handleOpenEvent = (event) => {
  const prompt = event?.detail?.prompt
  if (prompt) {
    inputText.value = prompt
  }
  openAssistant()
}

onMounted(() => {
  window.addEventListener('open-ai-assistant', handleOpenEvent)
  loadSessionHistory()
})

onUnmounted(() => {
  window.removeEventListener('open-ai-assistant', handleOpenEvent)
})
</script>

<style scoped>
.ai-assistant {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 2000;
}

.floating-btn {
  width: 56px;
  height: 56px;
  box-shadow: 0 12px 30px rgba(64, 158, 255, 0.35);
}

.assistant-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 16px;
  min-height: 0;
}

.assistant-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-shrink: 0;
}

.header-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.assistant-header h3 {
  margin: 0 0 6px;
}

.assistant-header p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}

.assistant-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 16px;
  min-height: 0;
  flex: 1;
}

.assistant-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  gap: 12px;
}

.assistant-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.side-card,
.suggestion-card,
.history-list {
  padding: 12px;
  border-radius: 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
}

.side-card {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.03);
}

.side-guide {
  background: linear-gradient(180deg, rgba(64, 158, 255, 0.08), rgba(64, 158, 255, 0.02));
}

.guide-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  line-height: 1.7;
  font-size: 13px;
}

.side-draft-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  margin-bottom: 6px;
}

.side-draft-footer {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.history-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 8px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 220px;
  overflow: auto;
}

.history-item {
  padding: 10px;
  border-radius: 12px;
  background: rgba(64, 158, 255, 0.06);
}

.history-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.history-role {
  font-size: 12px;
  font-weight: 600;
}

.history-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.history-content {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-primary);
}

.suggestion-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestion-item {
  cursor: pointer;
}

.message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 4px;
}

.message-item {
  display: flex;
}

.message-item.user {
  justify-content: flex-end;
}

.message-item.ai {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 88%;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
}

.message-item.user .message-bubble {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  border-color: transparent;
}

.message-role-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.message-role {
  font-size: 12px;
  opacity: 0.75;
}

.message-time {
  font-size: 12px;
  opacity: 0.65;
}

.message-content {
  line-height: 1.6;
  white-space: pre-wrap;
}

.section-title {
  font-weight: bold;
  margin-bottom: 8px;
}

.resource-card,
.draft-card,
.clarification-card,
.result-card {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgba(255, 255, 255, 0.2);
}

.message-item.ai .resource-card,
.message-item.ai .draft-card,
.message-item.ai .clarification-card,
.message-item.ai .result-card,
.message-item.ai .message-suggestion-card {
  border-top-color: var(--border-color);
}

.result-status {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  margin-bottom: 8px;
}

.result-status.success {
  background: rgba(103, 194, 58, 0.12);
  color: #67c23a;
}

.result-status.fail {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}

.result-message {
  font-size: 13px;
  margin-bottom: 8px;
}

.result-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.result-key {
  color: var(--text-secondary);
}

.clarification-text {
  color: var(--text-secondary);
  line-height: 1.6;
}

.resource-item {
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.resource-item:last-child {
  border-bottom: none;
}

.resource-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.resource-name {
  font-weight: 600;
}

.resource-meta {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.resource-reason {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 6px;
  line-height: 1.5;
  background: rgba(64, 158, 255, 0.06);
  padding: 8px 10px;
  border-radius: 10px;
}

.draft-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  margin-bottom: 4px;
}

.draft-key {
  color: var(--text-secondary);
}

.draft-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.typing-bubble {
  min-width: 120px;
}

.typing-indicator {
  display: flex;
  gap: 6px;
  align-items: center;
  min-height: 20px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-secondary);
  opacity: 0.65;
  animation: bounce 1s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.3s;
}

.input-area {
  border-top: 1px solid var(--border-color);
  padding-top: 12px;
  flex-shrink: 0;
}

.input-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

:deep(.ai-drawer .el-drawer__body) {
  padding: 16px 18px 18px;
  height: calc(100vh - 54px);
  overflow: hidden;
}

:deep(.ai-drawer .el-drawer__header) {
  margin-bottom: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

@media (max-width: 1200px) {
  .assistant-body {
    grid-template-columns: 1fr;
  }

  .assistant-side {
    order: -1;
  }
}

@media (max-width: 640px) {
  :deep(.ai-drawer) {
    width: 100vw !important;
  }

  :deep(.ai-drawer .el-drawer__body) {
    padding: 12px;
  }

  .assistant-header,
  .input-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .input-actions .el-button {
    width: 100%;
  }
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0.7);
    opacity: 0.55;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
