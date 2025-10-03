import React from 'react'

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer-content">
        <span>© {new Date().getFullYear()} Lecture Navigator</span>
        {' '}
        <span>·</span>
        {' '}
        <a href="https://github.com/" target="_blank" rel="noreferrer" style={{ color: '#6aa6ff', textDecoration: 'none' }}>GitHub</a>
      </div>
    </footer>
  )
}


