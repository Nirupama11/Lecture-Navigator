import React, { useState, useRef } from 'react'

export function VideoInput({ onIngest, onUpload, loading }){
  const [url, setUrl] = useState('')
  const [inputMode, setInputMode] = useState('url') // 'url' or 'file'
  const fileInputRef = useRef(null)

  function handleFileSelect(event) {
    const file = event.target.files[0]
    if (file && onUpload) {
      onUpload(file)
    }
  }

  function triggerFileInput() {
    fileInputRef.current?.click()
  }

  return (
    <div className="vstack" style={{width:'100%', gap: 12}}>
      {/* Mode Toggle */}
      <div className="hstack" style={{gap: 8}}>
        <button 
          className={`button ${inputMode === 'url' ? 'active' : ''}`}
          onClick={() => setInputMode('url')}
          disabled={loading}
        >
          YouTube URL
        </button>
        <button 
          className={`button ${inputMode === 'file' ? 'active' : ''}`}
          onClick={() => setInputMode('file')}
          disabled={loading}
        >
          Upload File
        </button>
      </div>

      {/* URL Input Mode */}
      {inputMode === 'url' && (
        <div className="hstack" style={{width:'100%'}}>
          <input 
            className="input" 
            placeholder="Paste YouTube URL (https://youtube.com/watch?v=...)" 
            value={url} 
            onChange={e=>setUrl(e.target.value)} 
            disabled={loading}
          />
          <button 
            className="button" 
            disabled={!url || loading} 
            onClick={()=> onIngest?.(url)}
          >
            {loading? 'Processing...' : 'Ingest'}
          </button>
        </div>
      )}

      {/* File Upload Mode */}
      {inputMode === 'file' && (
        <div className="hstack" style={{width:'100%'}}>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*,.mp4,.avi,.mov,.mkv,.webm,.m4v,.flv,.wmv"
            onChange={handleFileSelect}
            style={{display: 'none'}}
          />
          <div className="input" style={{cursor: 'pointer', display: 'flex', alignItems: 'center'}} onClick={triggerFileInput}>
            📁 Click to select video file...
          </div>
          <button 
            className="button" 
            onClick={triggerFileInput}
            disabled={loading}
          >
            {loading? 'Processing...' : 'Browse'}
          </button>
        </div>
      )}
    </div>
  )
}





