import axios from "axios";

const API_BASE = "http://localhost:8000/api";


export function useApi() {
  return {
    ingestVideo: async (url) => {
      const res = await axios.post(`${API_BASE}/ingest_video`, { video_url: url });
      return res.data;
    },
    searchTimestamps: async ({ query, k, video_id }) => {
      const res = await axios.post(`${API_BASE}/search_timestamps`, { query, k, video_id });
      return res.data;
    },
    getHistory: async () => {
      const res = await axios.get(`${API_BASE}/history`);
      return res.data;
    },
    uploadVideo: async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await axios.post(`${API_BASE}/upload_video`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return res.data;
    },
  };
}

