import { useState } from 'react'
import axios from 'axios'

function AIExplanation({ fileData }) {
  const [explanation, setExplanation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [question, setQuestion] = useState('')

  async function getExplanation() {
    setLoading(true)
    try {
      const response = await axios.post(
        'http://localhost:8000/explain',
        {
          ...fileData,
          question: question ||
            'Explain this business data in simple terms. What are the key findings and what actions should I take?'
        }
      )
      setExplanation(response.data.explanation)
    } catch (err) {
      setExplanation('Could not generate explanation.')
    } finally {
      setLoading(false)
    }
  }

  if (!fileData) return null

  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
      <h3 className="text-white font-semibold text-lg mb-4">
        🤖 AI Business Advisor
      </h3>

      {/* Question Input */}
      <div className="mb-4">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask anything about your data... (optional)"
          className="w-full bg-gray-700 text-white
          rounded-lg px-4 py-3 text-sm
          border border-gray-600
          focus:border-blue-500
          focus:outline-none"
        />
      </div>

      {/* Suggested Questions */}
      <div className="flex flex-wrap gap-2 mb-4">
        {[
          'What should I focus on?',
          'What are the risks?',
          'How can I improve sales?',
          'What does this mean for my business?'
        ].map((q, i) => (
          <button
            key={i}
            onClick={() => setQuestion(q)}
            className="bg-gray-700 hover:bg-gray-600
            text-gray-300 text-xs px-3 py-1
            rounded-full transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Ask Button */}
      <button
        onClick={getExplanation}
        disabled={loading}
        className="bg-blue-600 hover:bg-blue-700
        disabled:bg-gray-600
        text-white px-6 py-3 rounded-lg
        transition-colors text-sm font-semibold
        w-full mb-4"
      >
        {loading ? '🤔 Thinking...' : '✨ Get AI Explanation'}
      </button>

      {/* Explanation */}
      {explanation && (
        <div className="bg-gray-700 rounded-lg p-4">
          <p className="text-green-400 text-xs mb-2">
            AI Business Advisor Says:
          </p>
          <p className="text-gray-200 text-sm
          leading-relaxed whitespace-pre-wrap">
            {explanation}
          </p>
        </div>
      )}
    </div>
  )
}

export default AIExplanation