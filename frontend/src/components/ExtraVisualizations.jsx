import { useEffect, useState } from 'react'
import {
  ScatterChart, Scatter, ComposedChart, Bar, Line, BarChart,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts'
import { fetchVisualizations } from '../api/client'

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

function CalendarHeatmap({ data }) {
  if (!data) return null
  const values = Object.values(data)
  const max = Math.max(...values, 1)

  return (
    <section>
      <SectionEyebrow>Spending by Day of Month</SectionEyebrow>
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-6">
        <div className="grid grid-cols-7 gap-2">
          {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => {
            const value = data[String(day)] || 0
            const intensity = value / max
            const bg = intensity === 0
              ? 'var(--color-ink-800)'
              : `rgba(198, 161, 91, ${0.15 + intensity * 0.85})`
            return (
              <div
                key={day}
                title={`Day ${day}: ${formatRupees(value)}`}
                className="aspect-square rounded-md flex items-center justify-center text-xs text-paper-dim"
                style={{ backgroundColor: bg }}
              >
                {day}
              </div>
            )
          })}
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

function ExtraVisualizations() {
  const [viz, setViz] = useState(null)

  useEffect(() => {
    fetchVisualizations().then(setViz)
  }, [])

  if (!viz) return null

  return (
    <>
      <CashFlowChart data={viz.cash_flow} />
      <TopMerchants data={viz.top_merchants} />
      <CalendarHeatmap data={viz.calendar_heatmap} />
      <AnomalyScatter data={viz.anomaly_scatter} />
    </>
  )
}

export default ExtraVisualizations
