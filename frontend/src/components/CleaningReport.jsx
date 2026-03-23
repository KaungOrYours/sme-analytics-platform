function CleaningReport({ report }) {
  if (!report || report.length === 0) return null

  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
      <h3 className="text-white font-semibold text-lg mb-4">
        🧹 Auto Cleaning Report
      </h3>
      <div className="space-y-2">
        {report.map((item, index) => (
          <div
            key={index}
            className="bg-gray-700 rounded-lg px-4 py-2"
          >
            <p className="text-gray-300 text-sm">{item}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default CleaningReport
