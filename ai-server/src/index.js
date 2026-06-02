import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'

dotenv.config({ override: true })

const app = express()
const port = process.env.PORT || 3001
const envSource = {
  PORT: process.env.PORT ? 'env' : 'default',
  BACKEND_BASE_URL: process.env.BACKEND_BASE_URL ? 'env' : 'default',
  SILICONFLOW_API_KEY: process.env.SILICONFLOW_API_KEY ? 'env' : 'missing',
  SILICONFLOW_BASE_URL: process.env.SILICONFLOW_BASE_URL ? 'env' : 'default',
  DEEPSEEK_MODEL: process.env.DEEPSEEK_MODEL ? 'env' : 'default'
}
const rawSiliconflowApiKey = process.env.SILICONFLOW_API_KEY || ''
const rawDeepseekModel = process.env.DEEPSEEK_MODEL || ''
const siliconflowApiKey = String(rawSiliconflowApiKey).trim().replace(/^Bearer\s+/i, '')
const siliconflowBaseUrl = String(process.env.SILICONFLOW_BASE_URL || 'https://api.siliconflow.cn/v1').trim()
const deepseekModel = String(rawDeepseekModel || 'deepseek-ai/DeepSeek-V4-Flash').trim()
const siliconflowApiKeyPreview = siliconflowApiKey
  ? `${siliconflowApiKey.slice(0, 6)}...${siliconflowApiKey.slice(-4)}`
  : 'empty'
const rawSiliconflowApiKeyLength = rawSiliconflowApiKey.length
const rawDeepseekModelTrimmed = String(rawDeepseekModel).trim()
const rawDeepseekModelHasWhitespace = rawDeepseekModel !== rawDeepseekModelTrimmed
const rawSiliconflowApiKeyHasWhitespace = rawSiliconflowApiKey !== String(rawSiliconflowApiKey).trim()

app.use(cors({
  origin: true,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}))
app.use(express.json())

const sessions = new Map()

const suggestions = [
  '还有哪些实验室可以预约？',
  '帮我查询今天的预约',
  '帮我预约下周三下午 2 点到 4 点的 301 实验室',
  '哪些教室支持 30 人以上使用？'
]

const parseTimeText = (message = '') => {
  const text = String(message)
  const now = new Date()
  const dayMap = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7, '天': 7 }
  const dayMatch = text.match(/(下周|本周|这周|周)([一二三四五六日天])/)
  const timeMatch = text.match(/(上午|下午|晚上)?\s*(\d{1,2})\s*点?(?:到|至|-|—|~)?\s*(\d{1,2})?\s*点?/) 
  if (!dayMatch || !timeMatch) return null

  const weekPrefix = dayMatch[1]
  const targetDow = dayMap[dayMatch[2]]
  const currentDow = now.getDay() === 0 ? 7 : now.getDay()
  let delta = (targetDow - currentDow + 7) % 7
  if (weekPrefix === '下周') {
    delta = delta + 7 || 7
  } else if (weekPrefix === '本周' || weekPrefix === '这周') {
    if (delta === 0) delta = 7
  } else {
    delta = delta || 7
  }

  const date = new Date(now)
  date.setDate(now.getDate() + delta)
  const period = timeMatch[1]
  let startHour = Number(timeMatch[2])
  let endHour = Number(timeMatch[3] || Number(timeMatch[2]) + 2)
  if (period === '下午' && startHour < 12) { startHour += 12; endHour += 12 }
  if (period === '晚上' && startHour < 12) { startHour += 12; endHour += 12 }
  if (period === '上午' && startHour === 12) startHour = 0
  const pad = (n) => String(n).padStart(2, '0')
  const dateStr = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  return {
    startTime: `${dateStr} ${pad(startHour)}:00`,
    endTime: `${dateStr} ${pad(endHour)}:00`
  }
}

const mockResources = [
  { id: 1, name: '计算机实验室A', capacity: 40, status: '可预约', equipment: ['投影仪', '多媒体'] },
  { id: 2, name: '物理实验室B', capacity: 30, status: '可预约', equipment: ['投影仪'] },
  { id: 3, name: '化学实验室C', capacity: 25, status: '维护中', equipment: ['通风系统'] }
]

const mockReservations = [
  {
    id: 1,
    laboratoryName: '计算机实验室A',
    startTime: '2026-06-03 14:00',
    endTime: '2026-06-03 16:00',
    status: 'PENDING'
  },
  {
    id: 2,
    laboratoryName: '物理实验室B',
    startTime: '2026-06-04 09:00',
    endTime: '2026-06-04 11:00',
    status: 'APPROVED'
  }
]

const buildRecommendReason = (item, payload = {}) => {
  const reasons = []
  const participantCount = Number(payload.participantCount || 0)
  const equipment = String(payload.equipment || '').trim()
  if (item.status === 'IDLE') reasons.push('当前状态可预约')
  if (participantCount) {
    if (item.capacity >= participantCount) {
      reasons.push(`容量 ${item.capacity} 人，满足 ${participantCount} 人需求`)
    } else {
      reasons.push(`容量 ${item.capacity} 人，接近 ${participantCount} 人需求`)
    }
  } else {
    reasons.push(`容量 ${item.capacity} 人`)
  }
  if (equipment) {
    const text = `${item.name || ''} ${item.type || ''} ${item.description || ''} ${item.location || ''}`.toLowerCase()
    if (text.includes(equipment.toLowerCase())) {
      reasons.push(`匹配设备需求「${equipment}」`)
    }
  }
  if (item.location) reasons.push(`地点 ${item.location}`)
  return reasons.slice(0, 3).join('；')
}

const findAvailableResources = async (payload = {}, authHeaders = {}) => {
  const { participantCount, equipment } = payload
  const authHeader = pickAuthHeader(authHeaders).Authorization || ''
  try {
    const headerObject = pickAuthHeader(authHeaders)
    const resourceStartedAt = Date.now()
    const { response, data } = await backendFetchJson('/api/laboratory/page?current=1&size=50', {
      headers: headerObject
    })
    console.log(`[ai-server] resource_query backend status=${response.status} ok=${response.ok}`)
    console.log(`[ai-server] resource_query backend raw=${JSON.stringify(data)}`)
    console.log(`[ai-server] resource_query backend data=${JSON.stringify(data?.data)}`)
    console.log(`[ai-server] resource_query backend elapsed=${Date.now() - resourceStartedAt}ms`)
    const records = data?.data?.records || data?.data?.data?.records || data?.records || []
    console.log(`[ai-server] resource_query auth=${authHeader ? 'present' : 'empty'} authPreview=${authHeader ? `${authHeader.slice(0, 12)}...${authHeader.slice(-6)}` : 'empty'} records=${Array.isArray(records) ? records.length : 'n/a'}`)

    const normalized = records
      .filter((item) => String(item.status || '').toUpperCase() === 'IDLE')
      .map((item) => {
        const capacity = Number(item.capacity || 0)
        const diff = participantCount ? Math.abs(capacity - Number(participantCount)) : 0
        const text = `${item.name || ''} ${item.type || ''} ${item.description || ''} ${item.location || ''}`.toLowerCase()
        const eq = String(equipment || '').toLowerCase().trim()
        const equipmentMatch = !equipment || text.includes(eq)
        return {
          id: item.id,
          name: item.name,
          capacity,
          status: item.status,
          type: item.type,
          location: item.location,
          description: item.description,
          equipmentCount: item.equipmentCount,
          reason: buildRecommendReason({ ...item, capacity, status: item.status }, payload),
          equipmentMatch,
          score: (capacity >= Number(participantCount || 0) ? 100 : 0) + (equipmentMatch ? 50 : 0) - diff
        }
      })
      .sort((a, b) => b.score - a.score)

    const matched = normalized.filter((item) => {
      const enoughCapacity = !participantCount || item.capacity >= Number(participantCount)
      return enoughCapacity && item.equipmentMatch
    })

    const result = matched.length ? matched : normalized.slice(0, 5)
    return result.map(({ equipmentMatch, score, ...item }) => item)
  } catch (error) {
    const normalized = mockResources
      .filter((item) => item.status === '可预约')
      .map((item) => {
        const capacity = Number(item.capacity || 0)
        const diff = participantCount ? Math.abs(capacity - Number(participantCount)) : 0
        const equipmentMatch = !equipment || item.equipment.some(e => String(equipment).includes(e) || e.includes(String(equipment)))
        return {
          ...item,
          reason: buildRecommendReason(item, payload),
          equipmentMatch,
          score: (capacity >= Number(participantCount || 0) ? 100 : 0) + (equipmentMatch ? 50 : 0) - diff
        }
      })
      .sort((a, b) => b.score - a.score)

    const matched = normalized.filter((item) => {
      const enoughCapacity = !participantCount || item.capacity >= Number(participantCount)
      return enoughCapacity && item.equipmentMatch
    })

    const result = matched.length ? matched : normalized.slice(0, 5)
    return result.map(({ equipmentMatch, score, ...item }) => item)
  }
}

const backendBaseUrl = () => process.env.BACKEND_BASE_URL || 'http://localhost:8080'

const backendFetchJson = async (path, options = {}) => {
  const response = await fetch(new URL(path, backendBaseUrl()), {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  })
  const data = await response.json().catch(() => ({}))
  return { response, data }
}

const debugAuth = (label, authHeader) => {
  const preview = authHeader ? 'present' : 'empty'
  console.log(`[ai-server] ${label} auth=${preview}`)
}

const withAuthHeaders = (incomingHeaders = {}) => {
  const authorization = incomingHeaders.authorization || incomingHeaders.Authorization || ''
  return authorization ? { Authorization: authorization } : {}
}

const pickAuthHeader = (headers = {}) => {
  const authorization = headers.Authorization || headers.authorization || ''
  return authorization ? { Authorization: authorization } : {}
}

const siliconflowChat = async (messages = []) => {
  if (!siliconflowApiKey) {
    console.log('[ai-server] siliconflow skipped: missing API key')
    return null
  }

  const baseUrl = siliconflowBaseUrl.replace(/\/$/, '')
  const requestHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${siliconflowApiKey}`,
    'X-API-Key': siliconflowApiKey
  }
  const headersPreview = {
    'Content-Type': requestHeaders['Content-Type'],
    Authorization: requestHeaders.Authorization ? `${requestHeaders.Authorization.slice(0, 12)}...${requestHeaders.Authorization.slice(-4)}` : '',
    'X-API-Key': siliconflowApiKeyPreview
  }
  const requestBody = {
    model: deepseekModel,
    messages,
    temperature: 0.4,
    stream: false
  }
  console.log(`[ai-server] siliconflow request start baseUrl=${baseUrl} model=${deepseekModel} messages=${messages.length}`)
  console.log(`[ai-server] siliconflow request key preview=${siliconflowApiKeyPreview} length=${siliconflowApiKey.length}`)
  console.log(`[ai-server] siliconflow request headers preview=${JSON.stringify(headersPreview)}`)
  console.log(`[ai-server] siliconflow request body preview=${JSON.stringify(requestBody).slice(0, 800)}`)

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: 'POST',
    headers: requestHeaders,
    body: JSON.stringify(requestBody)
  })

  const rawText = await response.text().catch(() => '')
  console.log(`[ai-server] siliconflow response status=${response.status} ok=${response.ok}`)
  console.log(`[ai-server] siliconflow response raw=${rawText}`)
  console.log(`[ai-server] siliconflow response preview=${rawText.slice(0, 500)}`)

  if (!response.ok) {
    throw new Error(rawText || `SiliconFlow request failed: ${response.status}`)
  }

  try {
    return JSON.parse(rawText)
  } catch (error) {
    console.log('[ai-server] siliconflow response parse failed')
    throw error
  }
}

const createDraft = (message = '') => ({
  laboratoryName: '计算机实验室A',
  startTime: '2026-06-03 14:00',
  endTime: '2026-06-03 16:00',
  purpose: message || '实验教学',
  participantCount: 20,
  equipment: '投影仪'
})

const getBaseReply = (message = '') => {
  const text = String(message)
  if (text.includes('规则')) {
    return '当前预约规则：先确认时间和资源是否空闲，系统会自动检测冲突；若涉及审批流程，需等待管理员审核。'
  }
  if (text.includes('我的预约')) {
    return '你今天有 1 条待审核预约、1 条已通过预约。'
  }
  if (text.includes('空闲') || text.includes('可预约')) {
    return '我帮你筛选了当前可预约资源，并列在下方。你也可以继续告诉我人数、设备和时间，我会进一步筛选。'
  }
  return '我已收到你的消息。你可以继续问我实验室可用情况，或者让我帮你生成预约草稿。'
}

const detectIntent = (message = '') => {
  const text = String(message)

  if (/(帮我|我要|请帮我).*(预约|预定)/.test(text)) {
    return 'reservation_request'
  }
  if (/(有哪些|还有哪些|空闲|可预约|能预约)/.test(text)) {
    return 'resource_query'
  }
  if (/(我的预约|今天的预约|本周预约|最近预约)/.test(text)) {
    return 'my_reservation_query'
  }
  if (/(规则|怎么预约|预约流程|审批)/.test(text)) {
    return 'policy_query'
  }
  if (/(取消|撤销|改期|修改)/.test(text)) {
    return 'reservation_change'
  }
  if (/(设备|投影仪|人数|容量|时间|周一|周二|周三|周四|周五|周六|周日)/.test(text) && /(预约|实验室|教室)/.test(text)) {
    return 'reservation_request'
  }
  return 'general_chat'
}

const parseDateTime = (value = '') => {
  const normalized = String(value).trim().replace(' ', 'T')
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

const formatDateTime = (date) => {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const normalizeFutureDraftTime = (draft = {}) => {
  const start = parseDateTime(draft.startTime)
  const end = parseDateTime(draft.endTime)
  if (!start || !end) return draft
  if (start.getTime() >= Date.now()) return draft

  const durationMs = Math.max(end.getTime() - start.getTime(), 60 * 60 * 1000)
  const now = new Date()
  const futureStart = new Date(now.getTime() + 24 * 60 * 60 * 1000)
  futureStart.setHours(start.getHours(), start.getMinutes(), 0, 0)
  if (futureStart.getTime() <= Date.now()) {
    futureStart.setDate(futureStart.getDate() + 1)
  }
  const futureEnd = new Date(futureStart.getTime() + durationMs)
  return {
    ...draft,
    startTime: formatDateTime(futureStart),
    endTime: formatDateTime(futureEnd)
  }
}

const getNextAvailableTimeSuggestion = () => {
  const now = new Date()
  const suggestionStart = new Date(now.getTime() + 24 * 60 * 60 * 1000)
  suggestionStart.setHours(9, 0, 0, 0)
  if (suggestionStart.getTime() <= Date.now()) {
    suggestionStart.setDate(suggestionStart.getDate() + 1)
  }
  const suggestionEnd = new Date(suggestionStart.getTime() + 2 * 60 * 60 * 1000)
  return `${formatDateTime(suggestionStart)} 到 ${formatDateTime(suggestionEnd)}`
}

const extractFields = (message = '') => {
  const text = String(message)
  const draft = { ...createDraft(message) }
  const missingFields = []

  const labMatch = text.match(/(\d+号?实验室|\d+室|[\u4e00-\u9fa5A-Za-z]+实验室[A-Z]?)/)
  if (labMatch) draft.laboratoryName = labMatch[1]
  else missingFields.push('laboratoryName')

  const participantMatch = text.match(/(\d+)\s*人/)
  if (participantMatch) draft.participantCount = Number(participantMatch[1])

  const equipmentMatch = text.match(/(投影仪|多媒体|电脑|通风|实验台|音响)/)
  if (equipmentMatch) draft.equipment = equipmentMatch[1]

  const parsedTime = parseTimeText(text)
  if (parsedTime) {
    draft.startTime = parsedTime.startTime
    draft.endTime = parsedTime.endTime
  } else {
    missingFields.push('time')
  }

  if (!/预约|预定/.test(text)) missingFields.push('intent')

  return { draft: normalizeFutureDraftTime(draft), missingFields: [...new Set(missingFields)] }
}

const detectBackendConflict = async (draft, authHeaders = {}) => {
  if (!draft?.laboratoryName || !draft?.startTime || !draft?.endTime) return null
  try {
    const { data } = await backendFetchJson('/api/reservation/calendar?start=' + encodeURIComponent(draft.startTime) + '&end=' + encodeURIComponent(draft.endTime), {
      headers: pickAuthHeader(authHeaders)
    })
    const events = data?.data || data?.data?.records || []
    const conflict = Array.isArray(events) && events.length > 0
    return conflict
      ? { hasConflict: true, message: `该时间段已有 ${events.length} 条预约/占用记录，请更换时间或实验室。` }
      : { hasConflict: false }
  } catch (error) {
    return null
  }
}

const buildSystemPrompt = () => `你是高校实验室预约系统的 AI 小助手。你要帮助用户查询预约规则、推荐可预约实验室、生成预约草稿，并在信息不完整时主动追问。

你必须输出严格 JSON，字段如下：
{
  "reply": "给用户看的自然语言回复",
  "intent": "general_chat | resource_query | reservation_request | my_reservation_query | policy_query | reservation_change",
  "needsClarification": true/false,
  "clarification": "需要补充的信息，若不需要则为空字符串",
  "draft": {
    "laboratoryName": "",
    "labId": null,
    "startTime": "YYYY-MM-DD HH:mm",
    "endTime": "YYYY-MM-DD HH:mm",
    "purpose": "",
    "participantCount": null,
    "equipment": ""
  },
  "suggestions": ["快捷追问/建议，最多3条"],
  "resourceQuery": {
    "participantCount": null,
    "equipment": ""
  }
}

要求：
- 回复必须自然，不要只输出实验室名字。
- 当返回资源查询时，reply 要说明为什么推荐这些实验室，尽量提到容量、设备、状态等原因。
- 当用户表达预约意图时，要尽量提取实验室、时间、人数、设备需求，并主动给出下一步建议。
- 信息不完整时，needsClarification 必须为 true，并给出 clarification 和 suggestions。
- 当用户询问可预约资源时，intent 使用 resource_query，并尽量给出 resourceQuery。
- 不要输出 JSON 之外的任何内容。`

const buildReply = async ({ message = '', sessionId = 'default', authHeader = '' } = {}) => {
  const startedAt = Date.now()
  const session = sessions.get(sessionId) || []
  const historyContext = session.slice(-8).map(item => ({
    role: item.role === 'assistant' ? 'assistant' : 'user',
    content: item.content
  }))

  const userInput = String(message || '').trim()
  let parsed = null

  if (siliconflowApiKey) {
    try {
      console.log('[ai-server] entering model branch')
      const completion = await siliconflowChat([
        { role: 'system', content: buildSystemPrompt() },
        ...historyContext,
        { role: 'user', content: userInput }
      ])
      const raw = completion?.choices?.[0]?.message?.content || '{}'
      const rawText = String(raw)
      const normalized = rawText
        .replace(/```json\s*/i, '')
        .replace(/```\s*$/i, '')
        .trim()
      console.log(`[ai-server] model raw reply=${rawText}`)
      console.log(`[ai-server] model raw reply preview=${rawText.slice(0, 500)}`)
      console.log(`[ai-server] model normalized reply=${normalized}`)
      parsed = typeof raw === 'string' ? JSON.parse(normalized) : raw
      console.log(`[ai-server] model parsed intent=${parsed?.intent || 'none'}`)
      console.log(`[ai-server] model branch elapsed=${Date.now() - startedAt}ms`)
    } catch (error) {
      console.log(`[ai-server] model branch failed: ${error?.message || error}`)
      parsed = null
    }
  } else {
    console.log('[ai-server] entering fallback branch: missing api key')
  }

  if (parsed && typeof parsed === 'object') {
    const intent = parsed.intent || 'general_chat'
    const resources = intent === 'resource_query'
      ? await findAvailableResources({
          participantCount: parsed.resourceQuery?.participantCount,
          equipment: parsed.resourceQuery?.equipment
        }, { Authorization: authHeader })
      : []

    const conflict = intent === 'reservation_request' && parsed.draft
      ? await detectBackendConflict(parsed.draft, { Authorization: authHeader })
      : null

    const resourceNames = resources.slice(0, 4).map(item => item.name).join('、')
    const resourceSummary = resources.length
      ? `我帮你筛选到 ${resources.length} 个比较合适的实验室：${resourceNames}。`
      : ''
    const resourceReasons = resources.slice(0, 3).map(item => item.reason).filter(Boolean)
    const resourceIntro = resourceReasons.length
      ? `我帮你筛选到 ${resources.length} 个比较合适的实验室：${resourceNames}。推荐理由：${resourceReasons.join('；')}。`
      : resourceSummary

    const isReservationIntent = intent === 'reservation_request'
    const isGeneralResourceQuestion = intent === 'resource_query'
    const missingDraftInfo = isReservationIntent && (!parsed.draft?.laboratoryName || !parsed.draft?.startTime || !parsed.draft?.endTime)
    const modelReply = String(parsed.reply || '').trim()
    const draftFields = parsed.draft || {}
    const draftConfidence = [draftFields.laboratoryName, draftFields.startTime, draftFields.endTime, draftFields.participantCount, draftFields.equipment].filter(Boolean).length
    const reservationReason = draftFields.laboratoryName
      ? `我先帮你看了${draftFields.laboratoryName}附近的可用情况。`
      : '我先帮你筛了几间适合你需求的实验室。'
    const reservationFollowUp = draftConfidence >= 3
      ? '如果你确认具体时间，我可以继续帮你完善草稿并提交。'
      : '如果你确认具体时间和实验室，我可以继续帮你生成草稿。'

    const assistantMsg = {
      role: 'assistant',
      content: modelReply || resourceIntro || reservationReason || '我已经收到你的消息。',
      draft: isReservationIntent ? {
        ...draftFields,
        ...(draftFields.participantCount ? { participantCount: Number(draftFields.participantCount) } : {}),
        ...(draftFields.laboratoryName ? { laboratoryName: draftFields.laboratoryName } : {}),
        ...(draftFields.startTime ? { startTime: draftFields.startTime } : {}),
        ...(draftFields.endTime ? { endTime: draftFields.endTime } : {})
      } : null,
      resources: resources.length ? resources : [],
      intent,
      needsClarification: Boolean(parsed.needsClarification || conflict?.hasConflict || missingDraftInfo),
      clarification: conflict?.message || parsed.clarification || '',
      suggestions: Array.isArray(parsed.suggestions) ? parsed.suggestions.slice(0, 3) : [],
      resourceReasons
    }

    if (isGeneralResourceQuestion) {
      if (resources.length) {
        const reasonText = resourceReasons.length ? `推荐理由：${resourceReasons.join('；')}。` : ''
        assistantMsg.content = modelReply || `可以，当前比较合适的有：${resourceNames}。${reasonText}如果你告诉我人数或是否需要投影仪，我可以继续缩小范围。`
      } else {
        assistantMsg.content = modelReply || '我暂时没有筛到合适的实验室，你可以告诉我人数、时间或设备需求，我再继续帮你找。'
      }
    }

    if (isReservationIntent) {
      if (assistantMsg.needsClarification && !assistantMsg.clarification) {
        assistantMsg.clarification = '我还需要你补充一些信息，比如具体实验室名称和预约时间。'
      }
      if (!modelReply) {
        assistantMsg.content = `${reservationReason}${reservationFollowUp}`
      }
    }

    sessions.set(sessionId, [...session, { role: 'user', content: userInput }, assistantMsg])
    return assistantMsg
  }

  const intent = detectIntent(userInput)
  const { draft, missingFields } = extractFields(userInput)

  let content = getBaseReply(userInput)
  let resources = []
  let needsClarification = false
  let clarification = ''

  if (intent === 'reservation_request') {
    resources = await findAvailableResources(draft, { Authorization: authHeader })
    if (missingFields.length) {
      needsClarification = true
      clarification = '我还需要你补充一些信息，比如具体实验室名称和预约时间。'
      content = clarification
    } else {
      const conflict = await detectBackendConflict(draft, { Authorization: authHeader })
      if (conflict?.hasConflict) {
        needsClarification = true
        clarification = conflict.message || '当前时间段存在冲突，请尝试更换时间或实验室。'
        content = clarification
      } else {
        content = '我已经根据你的描述生成了预约草稿，请核对后确认提交。'
      }
    }
  }

  if (intent === 'resource_query') {
    resources = await findAvailableResources({
      participantCount: draft.participantCount,
      equipment: draft.equipment
    }, { Authorization: authHeader })
    content = resources.length
      ? `当前可预约的资源有：${resources.map(item => item.name).join('、')}。`
      : '当前没有找到满足条件的可预约资源。'
  }

  if (intent === 'my_reservation_query') {
    content = `当前查询到你的预约记录共 ${mockReservations.length} 条，分别包含待审核和已通过状态。`
  }

  if (intent === 'policy_query') {
    content = '当前预约流程为：选择资源、确认时间、提交申请、等待审核；如有冲突，系统会提示你更换时间或资源。'
  }

  if (intent === 'reservation_change') {
    content = '我可以帮你处理改期或取消请求，但需要先确认是哪一条预约。请提供预约编号或时间信息。'
    needsClarification = true
  }

  const assistantMsg = {
    role: 'assistant',
    content,
    draft: intent === 'reservation_request' && !needsClarification ? draft : null,
    resources,
    intent,
    needsClarification,
    clarification,
    suggestions: intent === 'reservation_request' && missingFields.length ? [
      '请告诉我具体实验室名称',
      '请告诉我预约日期和时间',
      '请告诉我人数和设备需求'
    ] : []
  }

  if (intent === 'reservation_request' && missingFields.includes('time')) {
    const timeSuggestion = getNextAvailableTimeSuggestion()
    assistantMsg.suggestions = [...assistantMsg.suggestions, `例如：${timeSuggestion}`].slice(0, 3)
    if (!assistantMsg.clarification) {
      assistantMsg.clarification = `我暂时没解析出具体时间，你可以试试：${timeSuggestion}`
    }
  }

  sessions.set(sessionId, [...session, { role: 'user', content: userInput }, assistantMsg])

  return assistantMsg
}

app.get('/api/ai/health', (_req, res) => {
  res.json({ code: 200, message: 'ok', data: { status: 'running' } })
})

app.get('/api/ai/suggestions', (_req, res) => {
  res.json({ code: 200, data: suggestions })
})

app.get('/api/ai/session/:sessionId', (req, res) => {
  const session = sessions.get(req.params.sessionId) || []
  res.json({ code: 200, data: session })
})

app.get('/api/ai/reservations/mock', (_req, res) => {
  res.json({ code: 200, data: mockReservations })
})

app.post('/api/ai/chat', async (req, res) => {
  const requestStartedAt = Date.now()
  const { sessionId = 'default', message = '' } = req.body || {}
  const result = await buildReply({ sessionId, message, authHeader: req.headers.authorization || '' })
  console.log(`[ai-server] chat total elapsed=${Date.now() - requestStartedAt}ms`)
  res.json({
    code: 200,
    data: {
      reply: result.content,
      draft: result.draft,
      resources: result.resources,
      intent: result.intent,
      needsClarification: result.needsClarification,
      clarification: result.clarification,
      suggestions: result.suggestions
    }
  })
})

app.get('/api/ai/sessions/:sessionId', (req, res) => {
  const session = sessions.get(req.params.sessionId) || []
  res.json({ code: 200, data: session })
})

app.post('/api/ai/reservation/draft', async (req, res) => {
  const { message = '', sessionId = 'default' } = req.body || {}
  const result = await buildReply({ message, sessionId, authHeader: req.headers.authorization || '' })
  res.json({
    code: 200,
    data: {
      reply: result.draft ? '已生成预约草稿，请确认后提交。' : result.content,
      draft: result.draft,
      resources: result.resources,
      needsClarification: result.needsClarification,
      clarification: result.clarification,
      suggestions: result.suggestions,
      intent: result.intent
    }
  })
})

app.post('/api/ai/reservation/confirm', async (req, res) => {
  const { draft } = req.body || {}
  const ok = Boolean(draft?.laboratoryName && draft?.startTime && draft?.endTime)
  if (!ok) {
    res.status(400).json({
      code: 400,
      data: {
        success: false,
        message: '预约草稿信息不完整，请先补充实验室和时间信息。'
      }
    })
    return
  }

  try {
    const payload = {
      labId: draft.labId || draft.laboratoryId || null,
      startTime: draft.startTime,
      endTime: draft.endTime,
      purpose: draft.purpose || 'AI 小助手预约',
      participantCount: draft.participantCount || 1,
      equipment: draft.equipment || '',
      type: draft.type || 'SINGLE'
    }
    const { response, data } = await backendFetchJson('/reservation/single', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    res.status(response.ok ? 200 : 400).json({
      code: response.ok ? 200 : 400,
      data: {
        success: response.ok,
        message: data?.message || data?.msg || '预约提交完成',
        reservation: data?.data || null
      }
    })
  } catch (error) {
    res.status(500).json({
      code: 500,
      data: {
        success: false,
        message: '调用业务后端失败，请确认 Spring Boot 服务已启动。'
      }
    })
  }
})

app.post('/api/ai/resources/available', (req, res) => {
  res.json({ code: 200, data: findAvailableResources(req.body || {}) })
})

app.post('/api/ai/intent/parse', async (req, res) => {
  const { message = '', sessionId = 'default' } = req.body || {}
  const result = await buildReply({ message, sessionId, authHeader: req.headers.authorization || '' })
  res.json({
    code: 200,
    data: {
      intent: result.intent,
      draft: result.draft,
      missingFields: result.needsClarification ? ['details'] : [],
      clarification: result.clarification,
      suggestions: result.suggestions
    }
  })
})

app.post('/api/ai/faq', (req, res) => {
  const { question = '' } = req.body || {}
  res.json({
    code: 200,
    data: {
      answer: `关于“${question}”的常见说明：预约前需要先确认时间、场地和权限，系统会自动检测冲突。`
    }
  })
})

app.delete('/api/ai/conversation/reset', (req, res) => {
  const { sessionId = 'default' } = req.body || {}
  sessions.delete(sessionId)
  res.json({ code: 200, data: { success: true } })
})

app.post('/api/ai/conversation/reset', (req, res) => {
  const { sessionId = 'default' } = req.body || {}
  sessions.delete(sessionId)
  res.json({ code: 200, data: { success: true } })
})

app.listen(port, () => {
  console.log(`AI service running at http://localhost:${port}`)
  console.log(`[ai-server] boot config model=${deepseekModel} baseUrl=${siliconflowBaseUrl} keyPreview=${siliconflowApiKeyPreview} keyLength=${siliconflowApiKey.length}`)
  console.log(`[ai-server] env source PORT=${envSource.PORT} BACKEND_BASE_URL=${envSource.BACKEND_BASE_URL} SILICONFLOW_API_KEY=${envSource.SILICONFLOW_API_KEY} SILICONFLOW_BASE_URL=${envSource.SILICONFLOW_BASE_URL} DEEPSEEK_MODEL=${envSource.DEEPSEEK_MODEL}`)
  console.log(`[ai-server] raw env model=${JSON.stringify(rawDeepseekModel)} trimmed=${JSON.stringify(rawDeepseekModelTrimmed)} hasWhitespace=${rawDeepseekModelHasWhitespace}`)
  console.log(`[ai-server] raw env apiKeyLength=${rawSiliconflowApiKeyLength} hasWhitespace=${rawSiliconflowApiKeyHasWhitespace} keyPreview=${siliconflowApiKeyPreview}`)
})
