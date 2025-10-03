import React, { useMemo, useState } from 'react'
import { useApi } from './services/api'
import { VideoInput } from './components/VideoInput'
import { SearchBar } from './components/SearchBar'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Player } from './components/Player'
import { History } from './components/History'

export default function App() {
  const api = useApi()
  const [videoId, setVideoId] = useState('')
  const [videoInfo, setVideoInfo] = useState(null)
  const [query, setQuery] = useState('')
  const [loadingIngest, setLoadingIngest] = useState(false)
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState([])
  const [answer, setAnswer] = useState('')
  const [currentTime, setCurrentTime] = useState(0)

  const canSearch = useMemo(() => videoId && query.length > 1, [videoId, query])

  async function handleIngest(url) {
    try {
      setLoadingIngest(true)
      const { video_id } = await api.ingestVideo(url)
      setVideoId(video_id)
      setVideoInfo({ is_local_file: false, url: url })
    } catch (e) {
      // Try to show backend error message if available
      let msg = 'Failed to ingest video.'
      if (e?.response?.data?.detail) {
        msg += '\n' + e.response.data.detail
      } else if (e?.message) {
        msg += '\n' + e.message
      }
      alert(msg)
    } finally {
      setLoadingIngest(false)
    }
  }

  async function handleUpload(file) {
    try {
      setLoadingIngest(true)
      const { video_id } = await api.uploadVideo(file)
      setVideoId(video_id)
      // For uploaded files, we'll get the video info from history
      await loadVideoInfo(video_id)
    } catch (e) {
      alert('Failed to upload video: ' + (e?.message || e))
    } finally {
      setLoadingIngest(false)
    }
  }

  async function loadVideoInfo(selectedVideoId) {
    try {
      const history = await api.getHistory()
      const video = history.videos.find(v => v.video_id === selectedVideoId)
      setVideoInfo(video || null)
    } catch (e) {
      console.error('Failed to load video info:', e)
      setVideoInfo(null)
    }
  }

  async function handleSelectVideo(selectedVideoId) {
    setVideoId(selectedVideoId)
    await loadVideoInfo(selectedVideoId)
    // Clear previous search results when switching videos
    setResults([])
    setAnswer('')
    setQuery('')
  }

  async function handleSearch(q) {
    setQuery(q)
    if (!q || q.length < 2 || !videoId) return
    try {
      setSearching(true)
      const resp = await api.searchTimestamps({ query: q, k: 3, video_id: videoId })
      setResults(resp.results || [])
      setAnswer(resp.answer || '')
    } catch (e) {
      console.error(e)
    } finally {
      setSearching(false)
    }
  }

  function jumpTo(t) {
    setCurrentTime(t)
  }

  return (
    <div className="main-layout">
      <Header />
      <main className="scroll-content">
      <div className="container vstack" style={{ gap: 16 }}>
      <div className="panel vstack">
        <div className="hstack">
          <VideoInput onIngest={handleIngest} onUpload={handleUpload} loading={loadingIngest} />
        </div>
        <div className="hstack">
          <SearchBar value={query} onChange={handleSearch} loading={searching} disabled={!videoId} />
        </div>
      </div>

      <History api={api} onSelectVideo={handleSelectVideo} currentVideoId={videoId} />

      <div className="panel vstack">
        <div className="section-title">Player</div>
        <Player videoId={videoId} currentTime={currentTime} videoInfo={videoInfo} />
      </div>

      <div className="panel vstack">
        <div className="section-title">Answer</div>
        <div>{answer || 'Ask a question about the lecture.'}</div>
      </div>

      <div className="panel vstack results-box">
        <div className="section-title">Top Matches</div>
        <div className="results-section">
          {results.length > 0 ? (
            results.map((r, idx) => {
              const isActive = currentTime >= r.t_start && currentTime <= r.t_end
              return (
                <div
                  key={idx}
                  className={`timestamp-card ${isActive ? 'active' : ''}`}
                  onClick={() => jumpTo(r.t_start)}
                >
                  <div className="timestamp-header">
                    ⏱ {Math.floor(r.t_start)}s - {Math.floor(r.t_end)}s
                  </div>
                  <div className="timestamp-snippet">{r.snippet}</div>
                  <button className="jump-btn">Jump ▶</button>
                </div>
              )
            })
          ) : (
            <div className="no-results">No results yet.</div>
          )}
        </div>
      </div>
      </div>
      </main>
      <Footer />
    </div>
  )
}
