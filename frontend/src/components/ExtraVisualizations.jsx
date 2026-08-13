import { useEffect, useState } from 'react'
import {
  ScatterChart, Scatter, ComposedChart, Bar, Line, BarChart,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { fetchVisualizations } from '../api/client'
import { filterByMonthRange } from '../utils/dateRange'

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

function AnomalyScatter({ data }) {
  if (!data || data.length === 0) return null

  const normal = data.filter((d) => !d.is_anomaly)
  const anomalous = data.filter((d) => d.is_anomaly)

  return (
    <section>
      <SectionEyebrow>Anomaly Detection — Feature Space</SectionEyebrow>
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
        <p className="text-xs text-paper-dim mb-4">
          Every transaction plotted by day of month and amount — this is the actual
          feature space the Isolation Forest model evaluates. Gold points are what
          it flagged as anomalous.
        </p>
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#23304a" />
            <XAxis type="number" dataKey="day_of_month" name="Day of Month" stroke="#a4adc0" fontSize={12} domain={[1, 31]} />
            <YAxis type="number" dataKey="amount" name="Amount" stroke="#a4adc0" fontSize={12} tickFormatter={(v) => `₹${v}`} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ background: '#111a2b', border: '1px solid #23304a', borderRadius: 8 }}
              formatter={(value, name) => (name === 'Amount' ? formatRupees(value) : value)}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Scatter name="Normal" data={normal} fill="#7c93c4" opacity={0.6} />
            <Scatter name="Flagged Anomaly" data={anomalous} fill="#ddc088" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

// Discrete quantile-based buckets (GitHub-contribution-graph style) instead
// of continuous opacity scaling. Continuous scaling let one outlier day
// (e.g. a rent payment) stretch the whole range, squashing every other
// day into visually indistinguishable near-zero shades. Discrete buckets
// based on where each day's value falls relative to the OTHER non-zero
// days reads far more clearly.
const BUCKET_COLORS = [
  'var(--color-ink-800)',   // 0: no spend
  'rgba(198, 161, 91, 0.25)', // low
  'rgba(198, 161, 91, 0.45)', // medium-low
  'rgba(198, 161, 91, 0.65)', // medium-high
  'rgba(198, 161, 91, 0.85)', // high
  '#ddc088',                  // highest
]

function bucketFor(value, sortedNonZeroValues) {
  if (value <= 0) return 0
  const rank = sortedNonZeroValues.findIndex((v) => v >= value)
  const percentile = rank / Math.max(sortedNonZeroValues.length - 1, 1)
  if (percentile <= 0.2) return 1
  if (percentile <= 0.4) return 2
  if (percentile <= 0.6) return 3
  if (percentile <= 0.8) return 4
  return 5
}

function CalendarHeatmap({ data, monthRange }) {
  if (!data || Object.keys(data).length === 0) return null

  // data is { "2026-01": { "1": 0, "2": 500, ... }, "2026-02": {...} }
  const filtered = filterByMonthRange(data, monthRange)

  // Sum across whichever months are currently selected, per day
  const dayTotals = {}
  for (let day = 1; day <= 31; day++) {
    dayTotals[day] = Object.values(filtered).reduce((sum, monthData) => sum + (monthData[String(day)] || 0), 0)
  }

  const nonZeroSorted = Object.values(dayTotals).filter((v) => v > 0).sort((a, b) => a - b)

  return (
    <section>
      <SectionEyebrow>Spending by Day of Month</SectionEyebrow>
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
        <div className="grid grid-cols-7 gap-2">
          {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => {
            const value = dayTotals[day] || 0
            const bucket = bucketFor(value, nonZeroSorted)
            return (
              <div
                key={day}
                title={`Day ${day}: ${formatRupees(value)}`}
                className="aspect-square rounded-md flex items-center justify-center text-xs text-paper-dim"
                style={{ backgroundColor: BUCKET_COLORS[bucket] }}
              >
                {day}
              </div>
            )
          })}
        </div>
        <div className="flex items-center gap-1.5 mt-4 text-xs text-paper-dim">
          <span>Less</span>
          {BUCKET_COLORS.map((color, i) => (
            <div key={i} className="w-4 h-4 rounded" style={{ backgroundColor: color }} />
          ))}
          <span>More</span>
        </div>
      </div>
    </section>
  )
}

function CashFlowChart({ data }) {
  if (!data || Object.keys(data).length === 0) return null
  const chartData = Object.entries(data).map(([month, d]) => ({ month, ...d }))

  return (
    <section>
      <SectionEyebrow>Cash Flow — Income vs Expense</SectionEyebrow>
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#23304a" />
            <XAxis dataKey="month" stroke="#a4adc0" fontSize={12} />
            <YAxis stroke="#a4adc0" fontSize={12} tickFormatter={(v) => `₹${v / 1000}k`} />
            <Tooltip
              contentStyle={{ background: '#111a2b', border: '1px solid #23304a', borderRadius: 8 }}
              formatter={(value) => formatRupees(value)}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="income" fill="#4fae8d" name="Income" />
            <Bar dataKey="expense" fill="#c0575a" name="Expense" />
            <Line type="monotone" dataKey="net" stroke="#c6a15b" strokeWidth={2.5} name="Net" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

function TopMerchants({ data }) {
  if (!data || data.length === 0) return null

  return (
    <section>
      <SectionEyebrow>Top Merchants</SectionEyebrow>
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
        <ResponsiveContainer width="100%" height={Math.max(280, data.length * 36)}>
          <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#23304a" />
            <XAxis type="number" stroke="#a4adc0" fontSize={12} tickFormatter={(v) => `₹${v / 1000}k`} />
            <YAxis type="category" dataKey="merchant" stroke="#a4adc0" fontSize={12} width={110} />
            <Tooltip
              contentStyle={{ background: '#111a2b', border: '1px solid #23304a', borderRadius: 8 }}
              formatter={(value) => formatRupees(value)}
            />
            <Bar dataKey="total" fill="#c6a15b" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

function ExtraVisualizations({ monthRange = 'all' }) {
  const [viz, setViz] = useState(null)

  useEffect(() => {
    fetchVisualizations().then(setViz)
  }, [])

  if (!viz) return null

  const filteredCashFlow = filterByMonthRange(viz.cash_flow, monthRange)

  return (
    <>
      <CashFlowChart data={filteredCashFlow} />
      <TopMerchants data={viz.top_merchants} />
      <CalendarHeatmap data={viz.calendar_heatmap} monthRange={monthRange} />
      <AnomalyScatter data={viz.anomaly_scatter} />
    </>
  )
}

export default ExtraVisualizations
