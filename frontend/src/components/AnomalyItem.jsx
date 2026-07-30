import { useState } from 'react'
import { fetchCategories, setCategoryForMerchant, excludeMerchantFromAnomalies } from '../api/client'

function formatRupees(amount) {
  return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

function AnomalyItem({ anomaly, onPersonalized }) {
  const [expanded, setExpanded] = useState(false)
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState('')
  const [newCategory, setNewCategory] = useState('')
  const [status, setStatus] = useState('idle') // idle | saving | saved

  async function handleExpand() {
    const next = !expanded
    setExpanded(next)
    if (next && categories.length === 0) {
      const cats = await fetchCategories()
      setCategories(cats)
      setSelectedCategory(cats[0] || '')
    }
  }

  async function handleSaveCategory() {
    const category = newCategory.trim() || selectedCategory
    if (!category) return
    setStatus('saving')
    // Categorizing from THIS screen means "I've reviewed this, it's resolved" --
    // so we also exclude it from future anomaly flags, not just fix its
    // category. (Categorizing from elsewhere in the app wouldn't imply this.)
    const result = await setCategoryForMerchant(anomaly.merchant, category)
    await excludeMerchantFromAnomalies(anomaly.merchant)
    setStatus('saved')
    if (onPersonalized) onPersonalized(result)
  }

  async function handleNeverFlag() {
    setStatus('saving')
    await excludeMerchantFromAnomalies(anomaly.merchant)
    setStatus('saved')
    if (onPersonalized) onPersonalized()
  }

  return (
    <div className="bg-ink-900 border border-ink-700 rounded-lg overflow-hidden">
      <button
        onClick={handleExpand}
        className="w-full p-4 flex justify-between items-center text-left hover:bg-ink-800/50 transition-colors"
      >
        <div>
          <div className="text-paper">{anomaly.merchant}</div>
          <div className="text-xs text-paper-dim">{anomaly.date} · {anomaly.category}</div>
        </div>
        <div className="ledger-number text-lg text-brass-bright">{formatRupees(anomaly.amount)}</div>
      </button>

      {expanded && (
        <div className="border-t border-ink-700 p-4 space-y-3">
          {status === 'saved' ? (
            <div className="text-emerald text-sm">Saved — this will apply going forward.</div>
          ) : (
            <>
              <div>
                <label className="block text-xs text-paper-dim mb-1.5">Categorize as</label>
                <div className="flex gap-2">
                  <select
                    value={selectedCategory}
                    onChange={(e) => { setSelectedCategory(e.target.value); setNewCategory('') }}
                    className="flex-1 bg-ink-950 border border-ink-700 rounded-full text-sm text-paper px-4 py-2"
                  >
                    {categories.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <button
                    onClick={handleSaveCategory}
                    disabled={status === 'saving'}
                    className="bg-brass text-ink-950 font-medium px-4 rounded-full text-sm disabled:opacity-40"
                  >
                    Save
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs text-paper-dim mb-1.5">Or create a new category</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    placeholder="e.g. Kids, Travel, Gym..."
                    className="flex-1 bg-ink-950 border border-ink-700 rounded-full text-sm text-paper px-4 py-2 placeholder:text-paper-dim/50"
                  />
                  <button
                    onClick={handleSaveCategory}
                    disabled={status === 'saving' || !newCategory.trim()}
                    className="bg-brass text-ink-950 font-medium px-4 rounded-full text-sm disabled:opacity-40"
                  >
                    Save
                  </button>
                </div>
              </div>

              <button
                onClick={handleNeverFlag}
                disabled={status === 'saving'}
                className="text-xs text-paper-dim hover:text-paper underline disabled:opacity-40"
              >
                Never flag this merchant as an anomaly again
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default AnomalyItem
