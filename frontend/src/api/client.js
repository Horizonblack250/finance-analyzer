import axios from 'axios'

// In dev, Vite's proxy (see vite.config.js) forwards /api/* to the FastAPI
// backend at http://127.0.0.1:8000, so we never hardcode that URL here --
// this means the same code works once deployed, just by pointing the
// deployed frontend's proxy/env at the deployed backend URL instead.
const client = axios.create({
  baseURL: '/api',
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

export default client
