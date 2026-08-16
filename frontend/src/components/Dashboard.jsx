import { useEffect, useState } from 'react'
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { fetchAnalysis, fetchBudget, setBudget } from '../api/client'
import ExtraVisualizations from './ExtraVisualizations'
import AnomalyItem from './AnomalyItem'
import { getAvailableMonths, filterByMonthRange } from '../utils/dateRange'
import ChatWidget from './ChatWidget'

const SERIES_COLORS = [
  '#c6a15b', '#4fae8d', '#7c93c4', '#c0575a', '#9b7fb8',
  '#5aa7c6', '#b8925a', '#6fae5a', '#c67f9e', '#8a93a6',
]

const TOTAL_OPTION_KEY = '__total__'

function computePieData(monthlyTrends) {
  const totals = {}
  Object.values(monthlyTrends).forEach((monthData) => {
    Object.entries(monthData).forEach(([category, amount]) => {
      totals[category] = (totals[category] || 0) + amount
    })
  })

  return Object.entries(totals)
    .map(([name, value]) => ({ name, value: Math.round(value) }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)
}

// Sums every category together per month -- used for the "Total (All
// Categories)" consolidated forecast view, as opposed to a single
// category's own trend.
function computeTotalMonthlyTrend(monthlyTrends) {
  const totals = {}
  Object.entries(monthlyTrends).forEach(([month, categories]) => {
    totals[month] = Object.values(categories).reduce((sum, v) => sum + v, 0)
  })
  return totals
}

function buildForecastChartData(monthlyTrends, category, forecast) {
  const months = Object.keys(monthlyTrends).sort()
  const historicalValues = months.map((m) => monthlyTrends[m][category] || 0)

  const firstNonZero = historicalValues.findIndex((v) => v > 0)
  const trimmedMonths = firstNonZero >= 0 ? months.slice(firstNonZero) : months
  const trimmedValues = firstNonZero >= 0 ? historicalValues.slice(firstNonZero) : historicalValues

  const data = trimmedMonths.map((month, i) => ({
    month,
    actual: trimmedValues[i],
    forecastLine: i === trimmedValues.length - 1 ? trimmedValues[i] : null,
  }))

  if (forecast) {
    data.push({ month: 'Next Month', actual: null, forecastLine: forecast.predicted })
  }

  return data
}

// Same shape as buildForecastChartData, but built from the pre-summed
// total-per-month series instead of a single category's series.
function buildTotalForecastChartData(monthlyTrends, totalPredicted) {
  const totalByMonth = computeTotalMonthlyTrend(monthlyTrends)
  const months = Object.keys(totalByMonth).sort()
  const values = months.map((m) => totalByMonth[m])

  const data = months.map((month, i) => ({
    month,
    actual: values[i],
    forecastLine: i === values.length - 1 ? values[i] : null,
  }))

  data.push({ month: 'Next Month', actual: null, forecastLine: totalPredicted })
  return data
}

function transformTrendsForChart(monthlyTrends) {
  const months = Object.keys(monthlyTrends).sort()
  const allCategories = new Set()
  months.forEach((m) => Object.keys(monthlyTrends[m]).forEach((c) => allCategories.add(c)))
  const categories = Array.from(allCategories)

  const data = months.map((month) => {
    const row = { month }
    categories.forEach((cat) => {
      row[cat] = monthlyTrends[month][cat] || 0
    })
    return row
  })

  return { data, categories }
}

function formatRupees(amount) {
  return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

function SectionEyebrow({ children }) {
  return (
    <div className="text-xs tracking-[0.2em] uppercase text-brass font-medium mb-3">
      {children}
    </div>
  )
}

function BudgetSection() {
  const [budget, setBudgetData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [incomeInput, setIncomeInput] = useState('')
  const [saving, setSaving] = useState(false)

  const loadBudget = () => {
    fetchBudget()
      .then(setBudgetData)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadBudget()
  }, [])

  async function handleSaveIncome(e) {
    e.preventDefault()
    if (!incomeInput) return
    setSaving(true)
    try {
      await setBudget(parseFloat(incomeInput))
      setIncomeInput('')
      loadBudget()
    } finally {
      setSaving(false)
    }
  }

  if (loading || !budget) return null

  return (
    <section>
      <SectionEyebrow>Budget Outlook</SectionEyebrow>
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
        {budget.status === 'no_budget_set' ? (
          <div>
            <p className="text-paper-dim text-sm mb-4">
              Set your monthly income to see whether next month's projected spending
              (currently forecasted at <span className="ledger-number text-paper">{formatRupees(budget.total_predicted_spend)}</span>) will leave you a surplus or a shortfall.
            </p>
            <form onSubmit={handleSaveIncome} className="flex gap-2">
              <input
                type="number"
                value={incomeInput}
                onChange={(e) => setIncomeInput(e.target.value)}
                placeholder="Monthly income (Rs.)"
                className="flex-1 bg-ink-950 border border-ink-700 rounded-full p-3 px-5 text-paper placeholder:text-paper-dim/50"
              />
              <button
                type="submit"
                disabled={saving}
                className="bg-brass text-ink-950 font-medium px-6 rounded-full disabled:opacity-40"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </form>
          </div>
        ) : (
          <div>
            <div className="flex items-baseline gap-3 mb-2">
              <span className={`ledger-number text-3xl ${budget.status === 'surplus' ? 'text-emerald' : 'text-brick'}`}>
                {budget.status === 'surplus' ? '+' : ''}{formatRupees(budget.surplus_or_shortfall)}
              </span>
              <span className="text-sm text-paper-dim">
                projected {budget.status === 'surplus' ? 'surplus' : 'shortfall'} next month
              </span>
            </div>
            <div className="text-sm text-paper-dim mb-5">
              Income {formatRupees(budget.monthly_income)} vs. predicted spend {formatRupees(budget.total_predicted_spend)}
            </div>

            <div className="space-y-3">
              {budget.recommendations.map((rec, i) => (
                <div key={i} className="bg-ink-950 border border-ink-700 rounded-lg p-4 text-sm text-paper-dim">
                  {rec.message}
                </div>
              ))}
            </div>

            <details className="mt-4">
              <summary className="text-xs text-paper-dim cursor-pointer">Update income</summary>
              <form onSubmit={handleSaveIncome} className="flex gap-2 mt-3">
                <input
                  type="number"
                  value={incomeInput}
                  onChange={(e) => setIncomeInput(e.target.value)}
                  placeholder="New monthly income"
                  className="flex-1 bg-ink-950 border border-ink-700 rounded-full p-3 px-5 text-paper placeholder:text-paper-dim/50 text-sm"
                />
                <button type="submit" disabled={saving} className="bg-brass text-ink-950 font-medium px-5 rounded-full text-sm disabled:opacity-40">
                  Save
                </button>
              </form>
            </details>
          </div>
        )}
      </div>
    </section>
  )
}

function Dashboard() {
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [monthRange, setMonthRange] = useState('all')
  const [forecastCategory, setForecastCategory] = useState(null)

  useEffect(() => {
    fetchAnalysis()
      .then(setAnalysis)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="text-paper-dim font-mono text-sm p-8">Loading your statement...</div>
  }

  if (error) {
    return (
      <div className="text-brick p-8">
        Couldn't load your analysis: {error}
      </div>
    )
  }

  const hasData = analysis && Object.keys(analysis.monthly_trends || {}).length > 0

  if (!hasData) {
    return (
      <div className="max-w-xl mx-auto px-6 py-24 text-center">
        <div className="text-xs tracking-[0.2em] uppercase text-paper-dim mb-3">Dashboard</div>
        <h2 className="font-display font-semibold text-2xl text-paper mb-3">No data yet</h2>
        <p className="text-paper-dim">
          Upload a bank statement to see your spending trends, recurring
          payments, forecasts, and anything unusual.
        </p>
      </div>
    )
  }

  const availableMonths = getAvailableMonths(analysis.monthly_trends)
  const filteredTrends = filterByMonthRange(analysis.monthly_trends, monthRange)
  const { data: chartData, categories } = transformTrendsForChart(filteredTrends)

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-12">
      <header>
        <div className="text-xs tracking-[0.2em] uppercase text-paper-dim mb-2">Statement of Account</div>
        <h1 className="font-display text-4xl text-paper">Your Spending, Consolidated</h1>
      </header>

      <BudgetSection />

      <section>
        <div className="flex items-center justify-between mb-3">
          <SectionEyebrow>Monthly Spending by Category</SectionEyebrow>
          <select
            value={monthRange}
            onChange={(e) => setMonthRange(e.target.value)}
            className="bg-ink-900 border border-ink-700 rounded-full text-sm text-paper px-4 py-1.5"
          >
            <option value="all">All Time (Consolidated)</option>
            <option value="last_3">Last 3 Months</option>
            <option value="last_6">Last 6 Months</option>
            <option value="last_1">Last Month</option>
            {availableMonths.length > 0 && (
              <optgroup label="Single Month">
                {[...availableMonths].reverse().map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </optgroup>
            )}
          </select>
        </div>
        <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
          <ResponsiveContainer width="100%" height={360}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#23304a" />
              <XAxis dataKey="month" stroke="#a4adc0" fontSize={12} />
              <YAxis stroke="#a4adc0" fontSize={12} tickFormatter={(v) => `₹${v / 1000}k`} />
              <Tooltip
                contentStyle={{ background: '#111a2b', border: '1px solid #23304a', borderRadius: 8 }}
                formatter={(value) => formatRupees(value)}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {categories.map((cat, i) => (
                <Bar key={cat} dataKey={cat} stackId="a" fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section>
        <SectionEyebrow>Where It Went ({monthRange === 'all' ? 'All Time' : monthRange.startsWith('last_') ? monthRange.replace('last_', 'Last ').replace('_', ' ') + (monthRange === 'last_1' ? ' Month' : ' Months') : monthRange})</SectionEyebrow>
        <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
          <ResponsiveContainer width="100%" height={340}>
            <PieChart>
              <Pie
                data={computePieData(filteredTrends)}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={120}
                paddingAngle={2}
              >
                {computePieData(filteredTrends).map((entry, i) => (
                  <Cell key={entry.name} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#111a2b', border: '1px solid #23304a', borderRadius: 8 }}
                formatter={(value) => formatRupees(value)}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section>
        <SectionEyebrow>This Month vs. Your Average</SectionEyebrow>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(analysis.month_over_month_change).map(([category, d]) => (
            <div key={category} className="bg-ink-900 border border-ink-700 rounded-lg p-4">
              <div className="text-sm text-paper-dim mb-1">{category}</div>
              <div className="ledger-number text-xl text-paper">{formatRupees(d.latest)}</div>
              <div className={`text-xs mt-1 ${d.pct_change > 0 ? 'text-brick' : 'text-emerald'}`}>
                {d.pct_change > 0 ? '↑' : '↓'} {Math.abs(d.pct_change)}% vs avg {formatRupees(d.prior_average)}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionEyebrow>Recurring Payments</SectionEyebrow>
        {analysis.recurring_payments.length === 0 ? (
          <div className="text-paper-dim text-sm">No recurring payments detected yet.</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {analysis.recurring_payments.map((r) => (
              <div key={r.merchant} className="bg-ink-900 border border-ink-700 rounded-lg p-4">
                <div className="font-display text-lg text-paper">{r.merchant}</div>
                <div className="text-xs text-paper-dim mb-2">{r.category}</div>
                <div className="ledger-number text-lg text-brass">{formatRupees(r.average_amount)}</div>
                <div className="text-xs text-paper-dim">every {r.average_interval_days} days</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        {(() => {
          const forecastEntries = Object.entries(analysis.forecast_next_month)
          const sortedByPredicted = [...forecastEntries].sort((a, b) => b[1].predicted - a[1].predicted)
          const totalPredicted = forecastEntries.reduce((sum, [, d]) => sum + d.predicted, 0)

          const activeCategory = forecastCategory || TOTAL_OPTION_KEY
          const isTotal = activeCategory === TOTAL_OPTION_KEY
          const activeForecast = isTotal
            ? { predicted: totalPredicted, method: 'sum of per-category forecasts', months_used: null }
            : analysis.forecast_next_month[activeCategory]

          const lineData = isTotal
            ? buildTotalForecastChartData(analysis.monthly_trends, totalPredicted)
            : (activeCategory ? buildForecastChartData(analysis.monthly_trends, activeCategory, activeForecast) : [])

          return (
            <>
              <div className="flex items-center justify-between mb-3">
                <SectionEyebrow>Next Month Forecast</SectionEyebrow>
                <select
                  value={activeCategory}
                  onChange={(e) => setForecastCategory(e.target.value)}
                  className="bg-ink-900 border border-ink-700 rounded-full text-sm text-paper px-4 py-1.5"
                >
                  <option value={TOTAL_OPTION_KEY}>Total (All Categories)</option>
                  {sortedByPredicted.map(([category]) => (
                    <option key={category} value={category}>{category}</option>
                  ))}
                </select>
              </div>

              <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
                {activeForecast && (
                  <div className="flex items-baseline gap-3 mb-4">
                    <span className="ledger-number text-3xl text-brass-bright">{formatRupees(activeForecast.predicted)}</span>
                    <span className="text-sm text-paper-dim">
                      predicted for next month
                      {isTotal
                        ? ' · sum of every category\'s forecast'
                        : ` · ${activeForecast.method === 'trend' ? 'linear regression trend' : 'historical average'} · ${activeForecast.months_used} months of data`}
                    </span>
                  </div>
                )}
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={lineData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#23304a" />
                    <XAxis dataKey="month" stroke="#a4adc0" fontSize={12} />
                    <YAxis stroke="#a4adc0" fontSize={12} tickFormatter={(v) => `₹${v / 1000}k`} />
                    <Tooltip
                      contentStyle={{ background: '#111a2b', border: '1px solid #23304a', borderRadius: 8 }}
                      formatter={(value) => formatRupees(value)}
                    />
                    <Line type="monotone" dataKey="actual" stroke="#c6a15b" strokeWidth={2.5} dot={{ r: 4 }} name="Actual" />
                    <Line type="monotone" dataKey="forecastLine" stroke="#4fae8d" strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 4 }} name="Projected" connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )
        })()}

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
          {Object.entries(analysis.forecast_next_month).map(([category, d]) => (
            <button
              key={category}
              onClick={() => setForecastCategory(category)}
              className="text-left bg-ink-900 border border-ink-700 rounded-lg p-4 hover:border-brass/50 transition-colors"
            >
              <div className="text-sm text-paper-dim mb-1">{category}</div>
              <div className="ledger-number text-xl text-paper">{formatRupees(d.predicted)}</div>
              <div className="text-xs text-paper-dim mt-1">{d.method} · {d.months_used}mo</div>
            </button>
          ))}
        </div>
      </section>

      <section>
        <SectionEyebrow>Worth a Second Look</SectionEyebrow>
        {analysis.anomalies.length === 0 ? (
          <div className="text-paper-dim text-sm">Nothing unusual detected.</div>
        ) : (
          <div className="space-y-2">
            {analysis.anomalies.map((a, i) => (
              <AnomalyItem
                key={i}
                anomaly={a}
                onPersonalized={() => {
                  fetchAnalysis().then(setAnalysis)
                }}
              />
            ))}
          </div>
        )}
      </section>

      <ExtraVisualizations monthRange={monthRange} />
      <ChatWidget />
    </div>
  )
}

export default Dashboard
