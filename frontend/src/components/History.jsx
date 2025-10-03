import React, { useState, useEffect } from 'react'

export function History({ api, onSelectVideo, currentVideoId }) {
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    if (showHistory) {
      loadHistory()
    }
  }, [showHistory])

  async function loadHistory() {
    try {
      setLoading(true)
      const response = await api.getHistory()
      setVideos(response.videos || [])
    } catch (e) {
      console.error('Failed to load history:', e)
    } finally {
      setLoading(false)
    }
  }

  function formatDate(dateString) {
    if (!dateString) return 'Unknown'
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return 'Unknown'
    }
  }

  return (
    <div className="panel vstack">
      <div className="hstack" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="section-title">Video Library</div>
        <button 
          className="button" 
          onClick={() => setShowHistory(!showHistory)}
        >
          {showHistory ? 'Hide Library' : 'Show Library'}
        </button>
      </div>
      
      {showHistory && (
        <div className="vstack" style={{ gap: 8 }}>
          {loading ? (
            <div>Loading history...</div>
          ) : videos.length === 0 ? (
            <div className="no-results">No videos processed yet.</div>
          ) : (
            videos.map((video) => (
              <div
                key={video.video_id}
                className={`history-item ${currentVideoId === video.video_id ? 'active' : ''}`}
                onClick={() => onSelectVideo(video.video_id)}
              >
                <div className="history-header">
                  <div className="history-title">{video.title}</div>
                  <div className="history-date">{formatDate(video.created_at)}</div>
                </div>
                <div className="history-details">
                  {video.is_local_file ? (
                    <span className="history-type local">📁 Local File</span>
                  ) : (
                    <span className="history-type youtube">🎥 YouTube</span>
                  )}
                  {video.url && !video.is_local_file && (
                    <a 
                      href={video.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="history-url"
                      onClick={(e) => e.stopPropagation()}
                    >
                      View Original
                    </a>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
