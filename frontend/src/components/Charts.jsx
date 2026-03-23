import Plot from 'react-plotly.js'
import { useEffect, useRef } from 'react'

function PlotChart({ data, layout }) {
  const ref = useRef(null)

  useEffect(() => {
    if (ref.current) {
      Plotly.newPlot(ref.current, data, layout, {
        responsive: true
      })
    }
  }, [data, layout])

  return <div ref={ref} style={{ width: '100%' }} />
}

function Charts({ fileData }) {
  if (!fileData || !fileData.statistics) return null

  const charts = []
  const darkLayout = {
    paper_bgcolor: '#1f2937',
    plot_bgcolor: '#1f2937',
    font: { color: '#9ca3af' },
    margin: { t: 40, r: 20, b: 60, l: 60 },
    showlegend: false
  }

  // Numeric bar charts
  const numericCols = Object.entries(
    fileData.statistics.numeric_stats || {}
  )

  numericCols.slice(0, 2).forEach(([col, stats]) => {
    charts.push({
      data: [{
        x: ['Min', 'Average', 'Median', 'Max'],
        y: [stats.min, stats.mean, stats.median, stats.max],
        type: 'bar',
        marker: { color: '#3b82f6' }
      }],
      layout: {
        ...darkLayout,
        title: {
          text: col.replace(/_/g, ' '),
          font: { color: '#ffffff', size: 14 }
        },
        xaxis: { gridcolor: '#374151' },
        yaxis: { gridcolor: '#374151' }
      }
    })
  })

  // Categorical bar charts
  const catCols = Object.entries(
    fileData.statistics.categorical_stats || {}
  )

  catCols.slice(0, 2).forEach(([col, stats]) => {
    charts.push({
      data: [{
        x: Object.keys(stats.top_5),
        y: Object.values(stats.top_5),
        type: 'bar',
        marker: { color: '#10b981' }
      }],
      layout: {
        ...darkLayout,
        title: {
          text: col.replace(/_/g, ' '),
          font: { color: '#ffffff', size: 14 }
        },
        xaxis: { gridcolor: '#374151' },
        yaxis: { gridcolor: '#374151' }
      }
    })
  })

  if (charts.length === 0) return null

  return (
    <div className="mb-6">
      <h3 className="text-white font-semibold text-lg mb-4">
        📊 Auto Generated Charts
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {charts.map((chart, i) => (
          <div key={i} className="bg-gray-800 rounded-lg p-4">
            <PlotChart
              data={chart.data}
              layout={chart.layout}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

export default Charts