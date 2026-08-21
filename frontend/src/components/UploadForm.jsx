import { useState, useEffect } from 'react'
import { uploadStatement, fetchCoverage } from '../api/client'

function formatMonthLabel(monthKey) {
  const [year, month] = monthKey.split('-')
  const date = new Date(parseInt(year), parseInt(month) - 1)
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
}

function UploadForm({ onUploaded }) {
  const [file, setFile] = useState(null)
  const [format, setFormat] = useState('relationship_summary')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')
  const [coverage, setCoverage] = useState(null)

  useEffect(() => {
    fetchCoverage().then(setCoverage)
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file) return

    setStatus('uploading')
    setErrorMessage('')

    try {
      const data = await uploadStatement(file, format, password || undefined)
      setResult(data)
      setStatus('success')
      fetchCoverage().then(setCoverage)
      if (onUploaded) onUploaded()
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setErrorMessage(detail)
      setStatus('error')
    }
  }

  return (
    <div className="max-w-xl mx-auto px-6 py-16">
      <div className="text-xs tracking-[0.2em] uppercase text-paper-dim mb-2">Upload</div>
      <h1 className="font-display text-3xl text-paper mb-4">Add a Bank Statement</h1>

      {coverage && (
        <div className="bg-ink-900 border border-ink-700 rounded-full px-5 py-2.5 mb-8 text-sm">
          {coverage.has_data ? (
            <span className="text-paper-dim">
              Data currently covers{' '}
              <span className="text-brass">{formatMonthLabel(coverage.earliest_month)}</span>
              {' – '}
              <span className="text-brass">{formatMonthLabel(coverage.latest_month)}</span>
              {' '}({coverage.total_transactions} transactions)
            </span>
          ) : (
            <span className="text-paper-dim">No data uploaded yet — this will be your first statement.</span>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm text-paper-dim mb-2">Statement PDF</label>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files[0])}
            className="block w-full text-sm text-paper file:mr-4 file:py-2 file:px-5
                       file:rounded-full file:border-0 file:bg-brass file:text-ink-950
                       file:font-medium file:cursor-pointer file:hover:bg-brass-bright
                       bg-ink-900 border border-ink-700 rounded-full p-2 pl-4"
          />
        </div>

        <div>
          <label className="block text-sm text-paper-dim mb-2">Statement Format</label>
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            className="w-full bg-ink-900 border border-ink-700 rounded-full p-3 px-5 text-paper"
          >
            <option value="relationship_summary">SBI — Relationship Summary</option>
            <option value="statement_of_account">SBI — Statement of Account</option>
            <option value="hdfc">HDFC (coming soon)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm text-paper-dim mb-2">Password (if protected)</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Leave blank if not password-protected"
            className="w-full bg-ink-900 border border-ink-700 rounded-full p-3 px-5 text-paper placeholder:text-paper-dim/50"
          />
        </div>

        <button
          type="submit"
          disabled={!file || status === 'uploading'}
          className="w-full bg-brass text-ink-950 font-medium py-3 rounded-full
                     disabled:opacity-40 disabled:cursor-not-allowed hover:bg-brass-bright transition-colors"
        >
          {status === 'uploading' ? 'Processing...' : 'Upload and Analyze'}
        </button>
      </form>

      {status === 'success' && result && (
        <div className="mt-6 bg-ink-900 border border-emerald/40 rounded-2xl p-4">
          <div className="text-emerald font-medium mb-2">Statement imported</div>
          <div className="text-sm text-paper-dim space-y-1 font-mono">
            <div>{result.total_parsed} transactions parsed</div>
            <div>{result.inserted} new transactions added</div>
            <div>{result.skipped_duplicates} already imported (skipped)</div>
            <div>{result.needs_review} need your review</div>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="mt-6 bg-ink-900 border border-brick/40 rounded-2xl p-4 text-brick text-sm">
          {errorMessage}
        </div>
      )}
    </div>
  )
}

export default UploadForm
