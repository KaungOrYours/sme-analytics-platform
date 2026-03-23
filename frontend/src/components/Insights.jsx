function Insights({ insights }) {
  if (!insights || insights.length === 0) return null

  const colors = {
    positive: 'border-green-500 bg-green-900/20',
    warning: 'border-yellow-500 bg-yellow-900/20',
    info: 'border-blue-500 bg-blue-900/20'
  }

  return (
    <div className="mb-6">
      <h3 className="text-white font-semibold text-lg mb-4">
        💡 Key Business Insights
      </h3>
      <div className="space-y-3">
        {insights.map((insight, i) => (
          <div
            key={i}
            className={`border rounded-lg px-4 py-3 
            flex items-start gap-3 ${colors[insight.type]}`}
          >
            <span className="text-xl flex-shrink-0">
              {insight.icon}
            </span>
            <p className="text-gray-300 text-sm leading-relaxed">
              {insight.text}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Insights
