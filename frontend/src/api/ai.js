import axios from 'axios'

const aiRequest = axios.create({
  baseURL: 'http://localhost:3001/api/ai',
  timeout: 15000
})

export const sendAiMessage = (payload) => aiRequest.post('/chat', payload)
export const getAiSession = (sessionId) => aiRequest.get(`/session/${sessionId}`)
export const getAiSuggestions = () => aiRequest.get('/suggestions')
export const generateReservationDraft = (payload) => aiRequest.post('/reservation/draft', payload)
export const confirmReservationDraft = (payload) => aiRequest.post('/reservation/confirm', payload)
export const queryAvailableResources = (payload) => aiRequest.post('/resources/available', payload)
export const resetAiConversation = (payload) => aiRequest.delete('/conversation/reset', { data: payload })
