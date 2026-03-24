function MLResults({ results }) {
  if (!results) return null

  if (results.status === 'insufficient_data' ||
      results.status === 'insufficient_features' ||
      results.status === 'time_series') {
    return (
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <h3 className="text-white font-semibold text-lg mb-2">
          🤖 ML Analysis
        </h3>
        <p className="text-yellow-400 text-sm">
          ⚠️ {results.ml_insights[0]}
        </p>
      </div>
    )
  }

  if (results.status === 'error') {
    return (
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <h3 className="text-white font-semibold text-lg mb-2">
          🤖 ML Analysis
        </h3>
        <p className="text-red-400 text-sm">
          ❌ {results.ml_insights[0] ||
              'ML analysis could not complete'}
        </p>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
      <h3 className="text-white font-semibold
      text-lg mb-4">
        🤖 ML Analysis Results
      </h3>

      {/* Model Name */}
      {results.model_name && (
        <div className="bg-gray-700 rounded-lg
        p-4 mb-4">
          <p className="text-gray-400 text-xs mb-1">
            Best Model Selected Automatically
          </p>
          <p className="text-white font-semibold text-lg">
            {results.model_name}
          </p>
        </div>
      )}

      {/* Performance */}
      {Object.keys(results.performance).length > 0 && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          {Object.entries(results.performance).map(
            ([key, value]) => (
              typeof value === 'number' && (
                <div
                  key={key}
                  className="bg-gray-700 rounded-lg
                  p-4 text-center"
                >
                  <p className="text-blue-400
                  font-bold text-2xl">
                    {key.includes('score') ||
                     key === 'accuracy'
                      ? `${(value * 100).toFixed(1)}%`
                      : value.toLocaleString()
                    }
                  </p>
                  <p className="text-gray-400
                  text-xs mt-1 capitalize">
                    {key.replace(/_/g, ' ')}
                  </p>
                </div>
              )
            )
          )}
        </div>
      )}

      {/* Feature Importance */}
      {results.feature_importance &&
       results.feature_importance.length > 0 && (
        <div className="mb-4">
          <p className="text-gray-400 text-sm mb-3">
            🔍 Top Influential Factors:
          </p>
          <div className="space-y-2">
            {results.feature_importance
              .slice(0, 5)
              .map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3"
              >
                <span className="text-gray-500
                text-xs w-4">
                  {i + 1}
                </span>
                <span className="text-gray-300
                text-sm flex-1 capitalize">
                  {item.feature.replace(/_/g, ' ')}
                </span>
                <div className="w-32 bg-gray-700
                rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2
                    rounded-full"
                    style={{
                      width: `${item.importance * 100}%`
                    }}
                  />
                </div>
                <span className="text-gray-500
                text-xs w-8">
                  {(item.importance * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ML Insights */}
      {results.ml_insights &&
       results.ml_insights.length > 0 && (
        <div>
          <p className="text-gray-400 text-sm mb-2">
            📋 ML Findings:
          </p>
          <div className="space-y-2">
            {results.ml_insights.map((insight, i) => (
              <div
                key={i}
                className="bg-gray-700 rounded-lg
                px-4 py-2"
              >
                <p className="text-gray-300 text-sm">
                  {insight}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default MLResults