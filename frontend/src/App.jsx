import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [projectInfo, setProjectInfo] = useState(null)

  useEffect(() => {
    axios.get('http://localhost:8000')
      .then(response => {
        setProjectInfo(response.data)
      })
      .catch(error => {
        console.log('Error:', error)
      })
  }, [])

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-4">
          SME Analytics Platform
        </h1>
        <p className="text-gray-400 text-lg mb-8">
          Upload your Excel, get instant business insights
        </p>

        {/* Show data from backend */}
        {projectInfo ? (
          <div className="bg-gray-800 p-6 rounded-lg text-left">
            <p className="text-green-400 mb-2">
              Backend Connected!
            </p>
            <p className="text-white">
              Status: {projectInfo.status}
            </p>
            <p className="text-gray-400">
              Version: {projectInfo.version}
            </p>
          </div>
        ) : (
          <p className="text-yellow-400">
            Connecting to backend...
          </p>
        )}
      </div>
    </div>
  )
}

export default App