import axios from 'axios'
import { supabase } from '../supabaseClient'

// In dev, Vite's proxy (see vite.config.js) forwards /api/* to the FastAPI
// backend at http://127.0.0.1:8000.
const client = axios.create({
  baseURL: '/api',
})

// Attach the current login token to every outgoing request. Without this,
// the backend's auth check (which now requires a valid token on /upload
// and /analyze) would reject every single request with a 401, even from
// a logged-in user -- the frontend was never telling the backend WHO was
// making the request.
client.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})

export async function fetchAnalysis() {
  const response = await client.get('/analyze')
  return response.data
}

export async function uploadStatement(file, statementFormat, password) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('statement_format', statementFormat)
  if (password) {
    formData.append('password', password)
  }

  const response = await client.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function fetchBudget() {
  const response = await client.get('/budget')
  return response.data
}

export async function setBudget(monthlyIncome) {
  const response = await client.post('/budget', { monthly_income: monthlyIncome })
  return response.data
}

export async function fetchVisualizations() {
  const response = await client.get('/visualizations')
  return response.data
}

export async function fetchCategories() {
  const response = await client.get('/categories')
  return response.data.categories
}

export async function setCategoryForMerchant(merchantName, category) {
  const response = await client.post('/corrections', { merchant_name: merchantName, category })
  return response.data
}

export async function excludeMerchantFromAnomalies(merchantName) {
  const response = await client.post('/anomaly-exclusions', { merchant_name: merchantName })
  return response.data
}

export async function fetchCoverage() {
  const response = await client.get('/coverage')
  return response.data
}

export default client
