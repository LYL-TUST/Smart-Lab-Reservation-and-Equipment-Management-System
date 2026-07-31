import axios from 'axios'
import { useUserStore } from '../stores/user'

const aiRequest = axios.create({
  baseURL: 'http://localhost:3001/api/ai',
  timeout: 60000,
  withCredentials: true
})

aiRequest.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

export const sendAiMessage = async (payload, { onDelta, signal } = {}) => {
  const userStore = useUserStore()
  const response = await fetch('http://localhost:3001/api/ai/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {})
    },
    credentials: 'include',
    body: JSON.stringify(payload),
    signal
  })

  if (!response.ok) {
    throw new Error(`AI 请求失败：${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('当前浏览器不支持流式读取')
  }

  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let finalPayload = null

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split(/\n\n/)
      buffer = chunks.pop() || ''
      for (const chunk of chunks) {
        const lines = chunk.split('\n').map(line => line.trim()).filter(Boolean)
        let eventType = 'message'
        let dataText = ''
        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.replace(/^event:\s*/, '')
          } else if (line.startsWith('data:')) {
            dataText += line.replace(/^data:\s*/, '')
          }
        }
        if (!dataText) continue
        const payloadData = JSON.parse(dataText)
        if (eventType === 'delta') {
          onDelta?.(payloadData.delta || '', payloadData.meta)
        } else if (eventType === 'message') {
          finalPayload = payloadData
        } else if (eventType === 'error') {
          throw new Error(payloadData.message || 'AI 流式返回失败')
        }
      }
    }
  } finally {
    reader.releaseLock?.()
  }

  return finalPayload
}

export const getAiSession = (sessionId) => aiRequest.get(`/session/${sessionId}`)
export const getAiSuggestions = () => aiRequest.get('/suggestions')
export const generateReservationDraft = (payload) => aiRequest.post('/reservation/draft', payload)
export const confirmReservationDraft = (payload) => aiRequest.post('/reservation/confirm', payload)
export const queryAvailableResources = (payload) => aiRequest.post('/resources/available', payload)
export const resetAiConversation = (payload) => aiRequest.delete('/conversation/reset', { data: payload })
// test AI Code Review CI trigger
