import axios from 'axios'
import { supabase } from '../supabaseClient'

// In local dev, Vite's proxy (see vite.config.js) forwards /api/* to
// http://127.0.0.1:8000. That proxy doesn't exist once this is a deployed
// static site (Vercel), so in production we need to call the real backend
// URL directly instead -- set via VITE_API_URL at build time. Falls back
// to the local dev proxy path when that env var isn't set.
const baseURL = import.meta.env.VITE_API_URL || '/api'

const client = axios.create({
  baseURL,
})

// Attach the current login token to every outgoing request.
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
