# 🎥 Lecture Navigator — Jump-to-Timestamp Agent

> Long lectures slow down doubt resolution; this project ingests video transcripts, embeds them, and lets you **search and jump directly to relevant timestamps** with a brief AI-generated answer.

---

## 🚀 Features
- **Video Processing**: YouTube URL ingestion + local video file uploads
- **Transcript Processing**: YouTube/SubRip/VTT or Whisper fallback for any video
- **Smart Segmentation**: Overlapping chunks with precise timestamps
- **Semantic Search**: Vector-based search + keyword fallback → top-3 timestamps
- **AI Answers**: Context-aware responses using OpenAI (with local embeddings fallback)
- **Video Library**: History/library of all processed videos with metadata
- **Modern UI**: React frontend with YouTube mini-player and file upload support

---

## 📂 Project Structure
- **backend/** → FastAPI app with LangChain, vector store, embeddings.
- **frontend/** → React + Vite app for UI, player, and search.
- **docs/** → Architecture diagram, Postman collection.

---

## ⚙️ Setup Instructions

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🆕 New Features

### 📚 Video Library/History
- **Automatic History**: All processed videos are automatically saved to your library
- **Quick Access**: Click "Show Library" to see all your processed videos
- **Smart Metadata**: View processing date, video type (YouTube/Local), and original URLs
- **One-Click Switch**: Click any video in your library to instantly switch to it

### 📁 Local Video Upload
- **File Support**: Upload MP4, AVI, MOV, MKV, WebM, M4V, FLV, WMV files
- **Automatic Processing**: Uses Whisper AI for accurate transcription of local files
- **Seamless Integration**: Local videos work exactly like YouTube videos for search
- **Easy Toggle**: Switch between "YouTube URL" and "Upload File" modes

### 🎯 How to Use New Features

1. **Upload Local Videos**:
   - Click "Upload File" tab in the video input section
   - Select your video file (supports most common formats)
   - Wait for processing (may take a few minutes for Whisper transcription)
   - Start searching immediately after processing

2. **Access Your Library**:
   - Click "Show Library" to expand your video history
   - See all previously processed videos with dates and types
   - Click any video to switch to it instantly
   - Original YouTube URLs are clickable for reference

---

## 🛠️ Technical Details

### Backend Enhancements
- New `/history` endpoint for video library management
- New `/upload_video` endpoint with multipart file support
- Enhanced database schema with video metadata storage
- Automatic cleanup of temporary uploaded files

### Frontend Improvements
- New `History` component for library management
- Enhanced `VideoInput` with dual-mode support (URL/File)
- Improved state management for video switching
- Modern UI with visual indicators for video types
