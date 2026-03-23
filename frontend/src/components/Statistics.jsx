function Statistics({ statistics }) {
  if (!statistics) return null

  const numericCols = Object.entries(
    statistics.numeric_stats || {}
  )
  const categoricalCols = Object.entries(
    statistics.categorical_stats || {}
  )

  if (numericCols.length === 0 &&
      categoricalCols.length === 0) return null

  return (
    <div className="mb-6">
      <h3 className="text-white font-semibold text-lg mb-4">
        📈 Detailed Statistics
      </h3>

      {/* Numeric Stats */}
      {numericCols.length > 0 && (
        <div className="mb-4">
          <p className="text-gray-400 text-sm mb-3">
            Numeric Columns
          </p>
          <div className="grid grid-cols-1 gap-3">
            {numericCols.slice(0, 4).map(([col, stats]) => (
              <div
                key={col}
                className="bg-gray-800 rounded-lg p-4"
              >
                <p className="text-white font-semibold
                mb-3 capitalize">
                  {col.replace(/_/g, ' ')}
                </p>
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center">
                    <p className="text-blue-400 font-bold">
                      {stats.mean.toLocaleString()}
                    </p>
                    <p className="text-gray-500 text-xs">
                      Average
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-green-400 font-bold">
                      {stats.min.toLocaleString()}
                    </p>
                    <p className="text-gray-500 text-xs">
                      Minimum
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-purple-400 font-bold">
                      {stats.max.toLocaleString()}
                    </p>
                    <p className="text-gray-500 text-xs">
                      Maximum
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Categorical Stats */}
      {categoricalCols.length > 0 && (
        <div>
          <p className="text-gray-400 text-sm mb-3">
            Category Columns
          </p>
          <div className="grid grid-cols-2 gap-3">
            {categoricalCols.slice(0, 4).map(([col, stats]) => (
              <div
                key={col}
                className="bg-gray-800 rounded-lg p-4"
              >
                <p className="text-white font-semibold
                mb-2 capitalize text-sm">
                  {col.replace(/_/g, ' ')}
                </p>
                <p className="text-blue-400 font-bold text-lg">
                  {stats.most_common}
                </p>
                <p className="text-gray-500 text-xs">
                  Most common •{' '}
                  {stats.unique_values} unique values
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Statistics