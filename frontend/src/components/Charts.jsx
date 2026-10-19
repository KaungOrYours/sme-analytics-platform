import { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-dist-min'

function Charts({ chartData }) {
  if (!chartData) return null

  const entries = Object.entries(chartData)
  if (entries.length === 0) return null

  const correlationEntry = entries.find(([, data]) => data.type === 'correlation')
  const otherEntries = entries.filter(([, data]) => data.type !== 'correlation')

  return (
    <div className="mb-6">
      <h3 className="text-white font-semibold text-lg mb-4">
        Auto Generated Charts
      </h3>
      {correlationEntry && (
        <div className="mb-4">
          <CorrelationHeatmap data={correlationEntry[1]} />
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {otherEntries.map(([col, data]) => (
          <ChartItem key={col} col={col} data={data} />
        ))}
      </div>
    </div>
  )
}

function CorrelationHeatmap({ data }) {
  const ref = useRef(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return

    const text = data.matrix.map(row => row.map(v => v.toFixed(2)))

    Plotly.newPlot(node, [{
      z: data.matrix,
      x: data.columns,
      y: data.columns,
      type: 'heatmap',
      zmin: -1,
      zmax: 1,
      colorscale: [
        [0, '#ef4444'],
        [0.5, '#1f2937'],
        [1, '#3b82f6']
      ],
      text,
      texttemplate: '%{text}',
      textfont: { color: '#ffffff', size: 11 },
      hovertemplate: '%{x} vs %{y}: %{z:.2f}<extra></extra>'
    }], {
      paper_bgcolor: '#1f2937',
      plot_bgcolor: '#1f2937',
      font: { color: '#9ca3af' },
      margin: { t: 50, r: 20, b: 60, l: 90 },
      title: {
        text: 'Correlation Between Numeric Columns',
        font: { color: '#ffffff', size: 13 }
      },
      xaxis: { tickfont: { color: '#9ca3af', size: 10 } },
      yaxis: { tickfont: { color: '#9ca3af', size: 10 }, autorange: 'reversed' }
    }, {
      responsive: true,
      displayModeBar: false
    })

    return () => {
      Plotly.purge(node)
    }
  }, [data])

  return (
    <div className="bg-gray-800 rounded-lg p-2">
      <div
        ref={ref}
        style={{ width: '100%', height: '320px' }}
      />
    </div>
  )
}

function ChartItem({ col, data }) {
  const ref = useRef(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return

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
      Plotly.newPlot(node, [{
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
      Plotly.newPlot(node, [{
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
      Plotly.purge(node)
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