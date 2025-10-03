import React, { useEffect, useRef } from 'react'

export function Player({ videoId, currentTime, videoInfo }) {
  const iframeRef = useRef(null)
  const videoRef = useRef(null)

  useEffect(() => {
    if (currentTime && videoId) {
      if (videoInfo?.is_local_file && videoRef.current) {
        // For local videos, set the current time
        videoRef.current.currentTime = currentTime
      } else if (iframeRef.current && !videoInfo?.is_local_file) {
        // For YouTube videos, update the iframe src
        iframeRef.current.src = `https://www.youtube.com/embed/${videoId}?start=${Math.floor(currentTime)}&autoplay=1`
      }
    }
  }, [currentTime, videoId, videoInfo])

  if (!videoId) return <div>No video loaded yet.</div>

  // Check if this is a local video
  const isLocalVideo = videoInfo?.is_local_file
  
  if (isLocalVideo) {
    // For local videos, use HTML5 video player
    const videoUrl = videoInfo?.url ? `http://localhost:8000/api/video/${videoInfo.url}` : null
    
    if (!videoUrl) {
      return <div>Local video file not available.</div>
    }

    return (
      <div className="video-wrapper">
        <video
          ref={videoRef}
          width="800"
          height="450"
          controls
          style={{ backgroundColor: '#000' }}
        >
          <source src={videoUrl} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      </div>
    )
  }

  // For YouTube videos, use iframe
  return (
    <div className="video-wrapper">
      <iframe
        ref={iframeRef}
        width="800"
        height="450"
        src={`https://www.youtube.com/embed/${videoId}`}
        frameBorder="0"
        allow="autoplay; encrypted-media"
        allowFullScreen
        title="Lecture Video"
      />
    </div>
  )
}
