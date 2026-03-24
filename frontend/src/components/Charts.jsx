import { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'

function Charts({ chartData }) {
  if (!chartData) return null

  const entries = Object.entries(chartData)
  if (entries.length === 0) return null

  return (
    <div className="mb-6">
      <h3 className="text-white font-semibold text-lg mb-4">
        📊 Auto Generated Charts
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {entries.map(([col, data]) => (
          <ChartItem key={col} col={col} data={data} />
        ))}
      </div>
    </div>
  )
}

function ChartItem({ col, data }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!ref.current) return

    const darkLayout = {
      paper_bgcolor: '#1f2937',
      plot_bgcolor: '#1f2937',
      font: { color: '#9ca3af' },
      margin: { t: 50, r: 20, b: 80, l: 70 },
      showlegend: false,
      title: {
        text: col.replace(/_/g, ' ')
              .replace(/\b\w/g, l => l.toUpperCase()),
        font: { color: '#ffffff', size: 13 }
      },
      xaxis: {
        gridcolor: '#374151',
        tickfont: { color: '#9ca3af', size: 10 },
        title: {
          text: col.replace(/_/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase()),
          font: { color: '#6b7280', size: 11 },
          standoff: 15
        }
      },
      yaxis: {
        gridcolor: '#374151',
        tickfont: { color: '#9ca3af', size: 10 },
        title: {
          text: data.type === 'numeric'
                ? 'Count' : 'Number of Records',
          font: { color: '#6b7280', size: 11 },
          standoff: 15
        }
      }
    }

    if (data.type === 'numeric') {
      Plotly.newPlot(ref.current, [{
        x: data.values,
        type: 'histogram',
        marker: {
          color: '#3b82f6',
          line: { color: '#1d4ed8', width: 0.5 }
        },
        nbinsx: 20,
        hovertemplate: 'Value: %{x}<br>Count: %{y}<extra></extra>'
      }], darkLayout, {
        responsive: true,
        displayModeBar: false
      })
    } else {
      Plotly.newPlot(ref.current, [{
        x: data.labels,
        y: data.values,
        type: 'bar',
        marker: {
          color: '#10b981',
          line: { color: '#059669', width: 0.5 }
        },
        hovertemplate: '%{x}: %{y} records<extra></extra>'
      }], darkLayout, {
        responsive: true,
        displayModeBar: false
      })
    }

    return () => {
      if (ref.current) Plotly.purge(ref.current)
    }
  }, [col, data])

  return (
    <div className="bg-gray-800 rounded-lg p-2">
      <div
        ref={ref}
        style={{ width: '100%', height: '280px' }}
      />
    </div>
  )
}

export default Charts