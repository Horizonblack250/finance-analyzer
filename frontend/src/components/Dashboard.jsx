import { useEffect, useState } from 'react'
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { fetchAnalysis } from '../api/client'

// A restrained, ledger-appropriate palette for chart series -- cycles
// through these for however many categories exist that month.
const SERIES_COLORS = [
  '#c6a15b', '#4fae8d', '#7c93c4', '#c0575a', '#9b7fb8',
  '#5aa7c6', '#b8925a', '#6fae5a', '#c67f9e', '#8a93a6',
]

function computePieData(monthlyTrends, mode) {
  const months = Object.keys(monthlyTrends).sort()
  if (months.length === 0) return []

  const totals = {}
  const monthsToSum = mode === 'this_month' ? [months[months.length - 1]] : months

  monthsToSum.forEach((month) => {
    Object.entries(monthlyTrends[month]).forEach(([category, amount]) => {
      totals[category] = (totals[category] || 0) + amount
    })
  })

  return Object.entries(totals)
    .map(([name, value]) => ({ name, value: Math.round(value) }))
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value)
}

function buildForecastChartData(monthlyTrends, category, forecast) {
  const months = Object.keys(monthlyTrends).sort()
  const historicalValues = months.map((m) => monthlyTrends[m][category] || 0)

  // Trim leading zero months so a category that only recently started
  // appearing doesn't drag the chart's left edge down to zero pointlessly.
  const firstNonZero = historicalValues.findIndex((v) => v > 0)
  const trimmedMonths = firstNonZero >= 0 ? months.slice(firstNonZero) : months
  const trimmedValues = firstNonZero >= 0 ? historicalValues.slice(firstNonZero) : historicalValues

  const data = trimmedMonths.map((month, i) => ({
    month,
    actual: trimmedValues[i],
    // forecastLine is null everywhere except the LAST historical point (so
    // the dashed line visually connects to it) -- this is the standard
    // recharts trick for rendering a solid line that transitions into a
    // dashed "projected" segment at the end.
    forecastLine: i === trimmedValues.length - 1 ? trimmedValues[i] : null,
  }))

  if (forecast) {
    data.push({ month: 'Next Month', actual: null, forecastLine: forecast.predicted })
  }

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

function Dashboard() {
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [pieMode, setPieMode] = useState('this_month')
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

  const { data: chartData, categories } = transformTrendsForChart(analysis.monthly_trends)

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-12">
      <header>
        <div className="text-xs tracking-[0.2em] uppercase text-paper-dim mb-2">Statement of Account</div>
        <h1 className="font-display text-4xl text-paper">Your Spending, Consolidated</h1>
      </header>

      {/* Monthly trends chart */}
      <section>
        <SectionEyebrow>Monthly Spending by Category</SectionEyebrow>
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

      {/* Category share pie chart, toggleable this-month vs all-time */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <SectionEyebrow>Where It Went</SectionEyebrow>
          <div className="flex gap-1 bg-ink-900 border border-ink-700 rounded-full p-1">
            <button
              onClick={() => setPieMode('this_month')}
              className={`px-3 py-1 rounded-full text-xs transition-colors ${pieMode === 'this_month' ? 'bg-brass text-ink-950 font-medium' : 'text-paper-dim'}`}
            >
              This Month
            </button>
            <button
              onClick={() => setPieMode('all_time')}
              className={`px-3 py-1 rounded-full text-xs transition-colors ${pieMode === 'all_time' ? 'bg-brass text-ink-950 font-medium' : 'text-paper-dim'}`}
            >
              All Time
            </button>
          </div>
        </div>
        <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
          <ResponsiveContainer width="100%" height={340}>
            <PieChart>
              <Pie
                data={computePieData(analysis.monthly_trends, pieMode)}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={120}
                paddingAngle={2}
              >
                {computePieData(analysis.monthly_trends, pieMode).map((entry, i) => (
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

      {/* Month over month change */}
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

      {/* Recurring payments */}
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

      {/* Forecast */}
      <section>
        {(() => {
          const forecastEntries = Object.entries(analysis.forecast_next_month)
          const sortedByPredicted = [...forecastEntries].sort((a, b) => b[1].predicted - a[1].predicted)
          const activeCategory = forecastCategory || sortedByPredicted[0]?.[0]
          const activeForecast = analysis.forecast_next_month[activeCategory]
          const lineData = activeCategory
            ? buildForecastChartData(analysis.monthly_trends, activeCategory, activeForecast)
            : []

          return (
            <>
              <div className="flex items-center justify-between mb-3">
                <SectionEyebrow>Next Month Forecast</SectionEyebrow>
                <select
                  value={activeCategory || ''}
                  onChange={(e) => setForecastCategory(e.target.value)}
                  className="bg-ink-900 border border-ink-700 rounded-full text-sm text-paper px-4 py-1.5"
                >
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
                      predicted for next month &middot; {activeForecast.method === 'trend' ? 'linear regression trend' : 'historical average'} &middot; {activeForecast.months_used} months of data
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

        {/* Quick-scan grid for every category */}
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

      {/* Anomalies */}
      <section>
        <SectionEyebrow>Worth a Second Look</SectionEyebrow>
        {analysis.anomalies.length === 0 ? (
          <div className="text-paper-dim text-sm">Nothing unusual detected.</div>
        ) : (
          <div className="space-y-2">
            {analysis.anomalies.map((a, i) => (
              <div key={i} className="bg-ink-900 border border-ink-700 rounded-lg p-4 flex justify-between items-center">
                <div>
                  <div className="text-paper">{a.merchant}</div>
                  <div className="text-xs text-paper-dim">{a.date} · {a.category}</div>
                </div>
                <div className="ledger-number text-lg text-brass-bright">{formatRupees(a.amount)}</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default Dashboard
