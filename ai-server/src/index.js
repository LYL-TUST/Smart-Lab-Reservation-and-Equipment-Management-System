import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'

dotenv.config()

const app = express()
const port = process.env.PORT || 3001
const siliconflowApiKey = process.env.SILICONFLOW_API_KEY || ''
const siliconflowBaseUrl = process.env.SILICONFLOW_BASE_URL || 'https://api.siliconflow.cn/v1'
const deepseekModel = process.env.DEEPSEEK_MODEL || 'deepseek-ai/DeepSeek-V3'

app.use(cors())
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
  const dayMatch = text.match(/周([一二三四五六日天])/)
  const timeMatch = text.match(/(上午|下午|晚上)?\s*(\d{1,2})\s*点?(?:到|至|-|—|~)?\s*(\d{1,2})?\s*点?/) 
  if (!dayMatch || !timeMatch) return null
  const targetDow = dayMap[dayMatch[1]]
  const currentDow = now.getDay() === 0 ? 7 : now.getDay()
  const delta = (targetDow - currentDow + 7) % 7 || 7
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

const findAvailableResources = async (payload = {}) => {
  const { participantCount, equipment } = payload
  try {
    const { data } = await backendFetchJson('/laboratory/available?current=1&size=50')
    const records = data?.data?.records || data?.data || []
    const filtered = records.filter((item) => {
      const capacityOk = !participantCount || Number(item.capacity || 0) >= Number(participantCount)
      const text = `${item.name || ''} ${item.type || ''} ${item.description || ''}`
      const equipmentOk = !equipment || text.includes(String(equipment))
      return capacityOk && equipmentOk
    })
    return filtered.map((item) => ({
      id: item.id,
      name: item.name,
      capacity: item.capacity,
      status: item.status,
      type: item.type,
      imageUrl: item.imageUrl
    }))
  } catch (error) {
    return mockResources.filter((item) => {
      const capacityOk = !participantCount || item.capacity >= Number(participantCount)
      const equipmentOk = !equipment || item.equipment.some(e => String(equipment).includes(e) || e.includes(String(equipment)))
      return item.status === '可预约' && capacityOk && equipmentOk
    })
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

const siliconflowChat = async (messages = []) => {
  if (!siliconflowApiKey) return null
  const response = await fetch(`${siliconflowBaseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${siliconflowApiKey}`
    },
    body: JSON.stringify({
      model: deepseekModel,
      messages,
      temperature: 0.4,
      response_format: { type: 'json_object' }
    })
  })
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(text || `SiliconFlow request failed: ${response.status}`)
  }
  return response.json()
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

  return { draft, missingFields: [...new Set(missingFields)] }
}

const detectBackendConflict = async (draft) => {
  if (!draft?.laboratoryName || !draft?.startTime || !draft?.endTime) return null
  try {
    const base = process.env.BACKEND_BASE_URL || 'http://localhost:8080'
    const url = new URL('/reservation/conflict', base)
    url.searchParams.set('labName', draft.laboratoryName)
    url.searchParams.set('startTime', draft.startTime)
    url.searchParams.set('endTime', draft.endTime)
    const response = await fetch(url)
    if (!response.ok) return null
    const result = await response.json()
    return result?.data || result || null
  } catch (error) {
    return null
  }
}

const buildSystemPrompt = () => `你是高校实验室预约系统的 AI 小助手。你的任务是帮助用户查询预约规则、推荐可预约实验室、生成预约草稿，并在信息不完整时主动追问。

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
- 当用户表达预约意图时，要尽量提取实验室、时间、人数、设备需求。
- 信息不完整时，needsClarification 必须为 true，并给出 clarification 和 suggestions。
- 当用户询问可预约资源时，intent 使用 resource_query，并尽量给出 resourceQuery。
- 回复要简洁自然，像高校实验室预约助手。
- 不要输出 JSON 之外的任何内容。`

const buildReply = async ({ message = '', sessionId = 'default' } = {}) => {
  const session = sessions.get(sessionId) || []
  const historyContext = session.slice(-8).map(item => ({
    role: item.role === 'assistant' ? 'assistant' : 'user',
    content: item.content
  }))

  const userInput = String(message || '').trim()
  let parsed = null

  if (siliconflowApiKey) {
    try {
      const completion = await siliconflowChat([
        { role: 'system', content: buildSystemPrompt() },
        ...historyContext,
        { role: 'user', content: userInput }
      ])
      const raw = completion?.choices?.[0]?.message?.content || '{}'
      parsed = JSON.parse(raw)
    } catch (error) {
      parsed = null
    }
  }

  if (parsed && typeof parsed === 'object') {
    const resources = parsed.intent === 'resource_query'
      ? await findAvailableResources({
          participantCount: parsed.resourceQuery?.participantCount,
          equipment: parsed.resourceQuery?.equipment
        })
      : []

    const conflict = parsed.intent === 'reservation_request' && parsed.draft
      ? await detectBackendConflict(parsed.draft)
      : null

    const assistantMsg = {
      role: 'assistant',
      content: parsed.reply || '我已经收到你的消息。',
      draft: parsed.intent === 'reservation_request' && !parsed.needsClarification && !conflict?.hasConflict ? parsed.draft : null,
      resources: resources.length ? resources : [],
      intent: parsed.intent || 'general_chat',
      needsClarification: Boolean(parsed.needsClarification || conflict?.hasConflict),
      clarification: conflict?.message || parsed.clarification || '',
      suggestions: Array.isArray(parsed.suggestions) ? parsed.suggestions.slice(0, 3) : []
    }

    if (assistantMsg.needsClarification && !assistantMsg.clarification) {
      assistantMsg.clarification = '我还需要你补充一些信息，比如具体实验室名称和预约时间。'
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
    resources = await findAvailableResources(draft)
    if (missingFields.length) {
      needsClarification = true
      clarification = '我还需要你补充一些信息，比如具体实验室名称和预约时间。'
      content = clarification
    } else {
      const conflict = await detectBackendConflict(draft)
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
    resources = await findAvailableResources(draft)
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
  const { sessionId = 'default', message = '' } = req.body || {}
  const result = await buildReply({ sessionId, message })
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
  const result = await buildReply({ message, sessionId })
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

app.post('/api/ai/intent/parse', (req, res) => {
  const { message = '', sessionId = 'default' } = req.body || {}
  const result = buildReply({ message, sessionId })
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
})
