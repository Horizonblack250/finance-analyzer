/**
 * Shared helper for filtering any month-keyed object (monthly_trends,
 * cash_flow -- both shaped as { "2026-06": {...}, "2026-07": {...} })
 * down to a selected range, so the same control can drive multiple charts.
 */

export function getAvailableMonths(data) {
  return Object.keys(data).sort()
}

export function filterByMonthRange(data, range) {
  const months = getAvailableMonths(data)

  if (range === 'all') return data

  if (range.startsWith('last_')) {
    const n = parseInt(range.split('_')[1], 10)
    const selected = months.slice(-n)
    return Object.fromEntries(selected.map((m) => [m, data[m]]))
  }

  // Otherwise, range is a specific month key, e.g. "2026-06"
  return data[range] ? { [range]: data[range] } : {}
}
