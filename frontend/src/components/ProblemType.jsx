function ProblemType({ detection }) {
  if (!detection) return null

  const icons = {
    time_series: '📈',
    classification: '🎯',
    regression: '📊',
    clustering: '🔵'
  }

  const labels = {
    time_series: 'Sales Forecasting',
    classification: 'Pattern Classification',
    regression: 'Value Prediction',
    clustering: 'Customer Grouping'
  }

  const colors = {
    time_series: 'border-blue-500 bg-blue-900/20',
    classification: 'border-green-500 bg-green-900/20',
    regression: 'border-purple-500 bg-purple-900/20',
    clustering: 'border-yellow-500 bg-yellow-900/20'
  }

  return (
    <div className={`border-2 rounded-lg p-6 mb-6 ${colors[detection.problem_type]}`}>
      <div className="flex items-center gap-3 mb-3">
        <span className="text-3xl">
          {icons[detection.problem_type]}
        </span>
        <div>
          <p className="text-white font-semibold text-lg">
            {labels[detection.problem_type]}
          </p>
          <p className="text-gray-400 text-sm">
            Confidence: {detection.confidence}%
          </p>
        </div>
      </div>
      <p className="text-gray-300 text-sm">
        {detection.reason}
      </p>
      {detection.suggested_target && (
        <div className="mt-3 bg-gray-800 rounded px-3 py-2">
          <p className="text-gray-400 text-xs">
            Suggested target column:
            <span className="text-white font-semibold ml-1">
              {detection.suggested_target}
            </span>
          </p>
        </div>
      )}
    </div>
  )
}

export default ProblemType