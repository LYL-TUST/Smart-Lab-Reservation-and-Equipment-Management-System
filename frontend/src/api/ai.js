import axios from 'axios'
import { useUserStore } from '../stores/user'

const aiRequest = axios.create({
  baseURL: 'http://localhost:3001/api/ai',
  timeout: 45000,
  withCredentials: true
})

aiRequest.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

export const sendAiMessage = (payload) => aiRequest.post('/chat', payload)
export const getAiSession = (sessionId) => aiRequest.get(`/session/${sessionId}`)
export const getAiSuggestions = () => aiRequest.get('/suggestions')
export const generateReservationDraft = (payload) => aiRequest.post('/reservation/draft', payload)
export const confirmReservationDraft = (payload) => aiRequest.post('/reservation/confirm', payload)
export const queryAvailableResources = (payload) => aiRequest.post('/resources/available', payload)
export const resetAiConversation = (payload) => aiRequest.delete('/conversation/reset', { data: payload })
