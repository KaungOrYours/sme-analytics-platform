import { useState } from 'react'

function FileUpload({ onFileUpload }) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)

  // Allowed file types
  const allowedTypes = [
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  ]

  // Max file size: 10MB
  const maxSize = 10 * 1024 * 1024

  function validateFile(file) {
    // Check file type
    if (!allowedTypes.includes(file.type)) {
      return "Sorry! We only accept CSV and Excel files (.csv, .xlsx, .xls)"
    }
    // Check file size
    if (file.size > maxSize) {
      return "File is too large! Maximum size is 10MB. Please reduce and try again."
    }
    return null // no error
  }

  function handleFile(file) {
    const errorMessage = validateFile(file)
    if (errorMessage) {
      setError(errorMessage)
      setSelectedFile(null)
      return
    }
    setError(null)
    setSelectedFile(file)
    onFileUpload(file)
  }

  // Handle drag events
  function handleDragOver(e) {
    e.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave() {
    setIsDragging(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  // Handle click to browse
  function handleChange(e) {
    const file = e.target.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="w-full max-w-2xl mx-auto">

      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-xl p-12
          flex flex-col items-center justify-center
          cursor-pointer transition-all duration-200
          ${isDragging
            ? 'border-blue-400 bg-blue-900/20'
            : 'border-gray-600 bg-gray-800/50 hover:border-gray-400'
          }
        `}
      >
        {/* Upload Icon */}
        <div className="text-5xl mb-4">📊</div>

        {/* Main Text */}
        <h3 className="text-white text-xl font-semibold mb-2">
          {isDragging ? 'Drop your file here!' : 'Upload your business data'}
        </h3>

        {/* Sub Text */}
        <p className="text-gray-400 text-sm mb-6 text-center">
          Drag and drop your file here, or click to browse
        </p>

        {/* Browse Button */}
        <label className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg cursor-pointer transition-colors">
          Browse Files
          <input
            type="file"
            className="hidden"
            accept=".csv,.xlsx,.xls"
            onChange={handleChange}
          />
        </label>

        {/* Accepted formats */}
        <p className="text-gray-500 text-xs mt-4">
          Accepts: CSV, Excel (.xlsx, .xls) • Maximum 10MB
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mt-4 bg-red-900/50 border border-red-500 rounded-lg p-4">
          <p className="text-red-400 text-sm">❌ {error}</p>
          <p className="text-gray-400 text-xs mt-1">
            Accepted formats: .csv, .xlsx, .xls
          </p>
        </div>
      )}

      {/* Success Message */}
      {selectedFile && (
        <div className="mt-4 bg-green-900/50 border border-green-500 rounded-lg p-4">
          <p className="text-green-400 text-sm font-semibold">
            ✅ File selected!
          </p>
          <p className="text-gray-300 text-sm mt-1">
            📄 {selectedFile.name}
          </p>
          <p className="text-gray-400 text-xs mt-1">
            Size: {(selectedFile.size / 1024).toFixed(1)} KB
          </p>
        </div>
      )}

    </div>
  )
}

export default FileUpload