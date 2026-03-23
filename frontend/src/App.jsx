import { useState } from 'react'
import axios from 'axios'
import FileUpload from './components/FileUpload'
import QualityScore from './components/QualityScore'
import CleaningReport from './components/CleaningReport'

function App() {
  const [fileData, setFileData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleFileUpload(file) {
    setLoading(true)
    setError(null)
    setFileData(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post(
        'http://localhost:8000/upload',
        formData
      )
      setFileData(response.data)
    } catch (err) {
      setError('Failed to process file. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 py-12 px-4">
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">
            SME Analytics Platform
          </h1>
          <p className="text-gray-400 text-lg">
            Upload your Excel, get instant business insights
          </p>
        </div>

        {/* File Upload */}
        <FileUpload onFileUpload={handleFileUpload} />

        {/* Loading */}
        {loading && (
          <div className="mt-8 text-center">
            <p className="text-blue-400 text-lg animate-pulse">
              ⏳ Analyzing and cleaning your data...
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-8 bg-red-900/50 border border-red-500 rounded-lg p-4">
            <p className="text-red-400">❌ {error}</p>
          </div>
        )}

        {/* Results */}
        {fileData && (
          <div className="mt-8">

            {/* Quality Score */}
            <QualityScore
              before={fileData.quality_before}
              after={fileData.quality_after}
            />

            {/* Cleaning Report */}
            <CleaningReport report={fileData.cleaning_report} />

            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-blue-400">
                  {fileData.rows}
                </p>
                <p className="text-gray-400 text-sm mt-1">Total Rows</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-green-400">
                  {fileData.columns}
                </p>
                <p className="text-gray-400 text-sm mt-1">Total Columns</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-purple-400">
                  {fileData.quality_after}%
                </p>
                <p className="text-gray-400 text-sm mt-1">Quality Score</p>
              </div>
            </div>

            {/* Column Names */}
            <div className="bg-gray-800 rounded-lg p-4 mb-6">
              <p className="text-white font-semibold mb-2">
                📋 Columns Detected:
              </p>
              <div className="flex flex-wrap gap-2">
                {fileData.column_names.map((col, i) => (
                  <span
                    key={i}
                    className="bg-gray-700 text-gray-300 px-3 py-1 rounded-full text-sm"
                  >
                    {col}
                  </span>
                ))}
              </div>
            </div>

            {/* Data Preview */}
            <div className="bg-gray-800 rounded-lg p-4">
              <p className="text-white font-semibold mb-4">
                👀 Data Preview (First 5 rows):
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      {fileData.column_names.map((col, i) => (
                        <th
                          key={i}
                          className="text-left text-gray-400 pb-2 pr-4"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {fileData.preview.map((row, i) => (
                      <tr key={i} className="border-t border-gray-700">
                        {fileData.column_names.map((col, j) => (
                          <td
                            key={j}
                            className="text-gray-300 py-2 pr-4"
                          >
                            {row[col]}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

      </div>
    </div>
  )
}

export default App
