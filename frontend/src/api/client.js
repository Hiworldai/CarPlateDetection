import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120000,
  withCredentials: true
})

export function mediaUrl(path) {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  return path
}

function normalizeDateFilter(value) {
  if (!value) return ''
  const trimmed = value.trim()
  if (!trimmed) return ''
  const normalized = trimmed.replace(/\//g, '-').replace(/\s+/, 'T')
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(normalized) ? normalized : trimmed
}

export function recognitionParams(filters, page, perPage) {
  const params = {
    page,
    per_page: perPage
  }

  if (filters.plate_text) params.plate_text = filters.plate_text
  if (filters.source_type) params.source_type = filters.source_type
  if (filters.start_time) params.start_time = normalizeDateFilter(filters.start_time)
  if (filters.end_time) params.end_time = normalizeDateFilter(filters.end_time)

  return params
}

export async function fetchAuthState() {
  const response = await api.get('/auth/me')
  return response.data
}

export async function login(payload) {
  const response = await api.post('/auth/login', payload)
  return response.data
}

export async function logout() {
  const response = await api.post('/auth/logout')
  return response.data
}
