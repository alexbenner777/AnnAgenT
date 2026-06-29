import axios from 'axios'

const BASE = '/api'

const api = axios.create({ baseURL: BASE, timeout: 10000 })

export const healthApi = {
  getDaily: (days = 7) => api.get<any[]>('/health/daily', { params: { days } }).then(r => r.data),
  postDaily: (data: any) => api.post('/health/daily', data).then(r => r.data),
  getMedications: () => api.get<any[]>('/health/medications').then(r => r.data),
  addMedication: (data: any) => api.post('/health/medications', data).then(r => r.data),
  logIntake: (medId: number, data: any) => api.post(`/health/medications/${medId}/intake`, data).then(r => r.data),
  getVisits: () => api.get<any[]>('/health/visits').then(r => r.data),
  addVisit: (data: any) => api.post('/health/visits', data).then(r => r.data),
  getLabs: () => api.get<any[]>('/health/labs').then(r => r.data),
  getLabTrends: (markerKey: string) => api.get<any[]>('/health/labs/trends', { params: { marker_key: markerKey } }).then(r => r.data),
}

export const calendarApi = {
  getEvents: (days = 7) => api.get<any[]>('/calendar/events', { params: { days } }).then(r => r.data),
  getToday: () => api.get<any[]>('/calendar/today').then(r => r.data),
  addEvent: (data: any) => api.post('/calendar/events', data).then(r => r.data),
}

export const financesApi = {
  getSummary: () => api.get<any>('/finances/summary').then(r => r.data),
  getExpenses: (days = 30) => api.get<any[]>('/finances/expenses', { params: { days } }).then(r => r.data),
  addExpense: (data: any) => api.post('/finances/expenses', data).then(r => r.data),
  getMonthlyTrend: () => api.get<any[]>('/finances/monthly-trend').then(r => r.data),
}

export const stateApi = {
  getHistory: (days = 7) => api.get<any[]>('/state/history', { params: { days } }).then(r => r.data),
  logState: (data: any) => api.post('/state/log', data).then(r => r.data),
  getToday: () => api.get<any>('/state/today').then(r => r.data),
}

export const briefingApi = {
  getToday: () => api.get<any[]>('/briefing/today').then(r => r.data),
  getHistory: (days = 7) => api.get<any[]>('/briefing/history', { params: { days } }).then(r => r.data),
}

export const contactsApi = {
  getAll: (circle?: string) => api.get<any[]>('/contacts', { params: circle ? { circle } : {} }).then(r => r.data),
  add: (data: any) => api.post('/contacts', data).then(r => r.data),
  getBirthdays: (days = 30) => api.get<any[]>('/contacts/birthdays', { params: { days } }).then(r => r.data),
}

export const meetingsApi = {
  getAll: () => api.get<any[]>('/meetings').then(r => r.data),
  add: (data: any) => api.post('/meetings', data).then(r => r.data),
  getOne: (id: number) => api.get<any>(`/meetings/${id}`).then(r => r.data),
}

export const remindersApi = {
  getAll: () => api.get<any[]>('/reminders').then(r => r.data),
  add: (data: any) => api.post('/reminders', data).then(r => r.data),
  action: (id: number, data: any) => api.post(`/reminders/${id}/action`, data).then(r => r.data),
}

export const settingsApi = {
  get: () => api.get<any>('/settings').then(r => r.data),
  update: (data: any) => api.post('/settings', data).then(r => r.data),
}

export const dashboardApi = {
  get: () => api.get<any>('/dashboard').then(r => r.data),
}

export default api
