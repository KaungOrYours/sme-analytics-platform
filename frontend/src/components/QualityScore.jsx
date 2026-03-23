function QualityScore({ before, after }) {

  function getColor(score) {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    return 'text-red-400'
  }

  function getLabel(score) {
    if (score >= 80) return 'Good'
    if (score >= 60) return 'Fair'
    return 'Poor'
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
      <h3 className="text-white font-semibold text-lg mb-4">
        📊 Data Quality Score
      </h3>
      <div className="grid grid-cols-2 gap-4">

        {/* Before */}
        <div className="text-center bg-gray-700 rounded-lg p-4">
          <p className="text-gray-400 text-sm mb-2">Before Cleaning</p>
          <p className={`text-4xl font-bold ${getColor(before)}`}>
            {before}%
          </p>
          <p className={`text-sm mt-1 ${getColor(before)}`}>
            {getLabel(before)}
          </p>
        </div>

        {/* After */}
        <div className="text-center bg-gray-700 rounded-lg p-4">
          <p className="text-gray-400 text-sm mb-2">After Cleaning</p>
          <p className={`text-4xl font-bold ${getColor(after)}`}>
            {after}%
          </p>
          <p className={`text-sm mt-1 ${getColor(after)}`}>
            {getLabel(after)}
          </p>
        </div>

      </div>

      {/* Improvement */}
      {after > before && (
        <div className="mt-4 bg-green-900/30 rounded-lg p-3 text-center">
          <p className="text-green-400 text-sm">
            ✅ Improved by {(after - before).toFixed(1)}% after auto cleaning!
          </p>
        </div>
      )}
    </div>
  )
}

export default QualityScore