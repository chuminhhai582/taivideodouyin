import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// ── Types ──────────────────────────────────────────────────────────────────
export interface VideoInfo {
  id: string;
  title: string;
  thumbnail?: string;
  duration?: number;
  url: string;
  view_count?: number;
  like_count?: number;
  upload_date?: string;
}

export interface ChannelVideosResponse {
  channel_name: string;
  channel_id: string;
  videos: VideoInfo[];
  total: number;
}

export type JobStatus =
  | "pending"
  | "downloading"
  | "transcribing"
  | "translating"
  | "merging"
  | "uploading"
  | "done"
  | "error";

export interface JobInfo {
  job_id: string;
  video_id: string;
  video_title: string;
  status: JobStatus;
  progress: number;
  message: string;
  output_path?: string;
  subtitle_vi?: string;
  error?: string;
}

export interface SubtitleSegment {
  index: number;
  start: string;
  end: string;
  text: string;
}

// ── API Calls ──────────────────────────────────────────────────────────────
export const getChannelVideos = async (url: string): Promise<ChannelVideosResponse> => {
  const res = await api.get("/channel/videos", { params: { url } });
  return res.data;
};

export const startDownload = async (
  videoIds: string[],
  videoUrls: string[],
  autoProcess: boolean = true
): Promise<{ job_ids: string[]; total: number }> => {
  const res = await api.post("/download/start", {
    video_ids: videoIds,
    video_urls: videoUrls,
    auto_process: autoProcess,
  });
  return res.data;
};

export const getJob = async (jobId: string): Promise<JobInfo> => {
  const res = await api.get(`/jobs/${jobId}`);
  return res.data;
};

export const getAllJobs = async (): Promise<JobInfo[]> => {
  const res = await api.get("/jobs/");
  return res.data;
};

export const getSubtitleVi = async (jobId: string) => {
  const res = await api.get(`/subtitle/${jobId}/vietnamese`);
  return res.data;
};

export const getTikTokAuthUrl = async (): Promise<{ auth_url: string; state: string }> => {
  const res = await api.get("/tiktok/auth");
  return res.data;
};

export const getTikTokStatus = async (): Promise<{ authenticated: boolean }> => {
  const res = await api.get("/tiktok/status");
  return res.data;
};

export const uploadToTikTok = async (params: {
  job_id: string;
  title: string;
  description?: string;
  privacy_level?: string;
}) => {
  const res = await api.post("/tiktok/upload", params);
  return res.data;
};

export const getDownloadFileUrl = (jobId: string) =>
  `${API_BASE}/download/file/${jobId}`;

// ── WebSocket ──────────────────────────────────────────────────────────────
export const createJobWebSocket = (jobId: string): WebSocket => {
  const WS_BASE = (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000").replace(/^http/, "ws");
  return new WebSocket(`${WS_BASE}/jobs/ws/${jobId}`);
};

// ── Helpers ────────────────────────────────────────────────────────────────
export const formatDuration = (seconds?: number): string => {
  if (!seconds) return "--:--";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
};

export const formatNumber = (n?: number): string => {
  if (!n) return "0";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
};

export const statusLabel: Record<JobStatus, string> = {
  pending: "Chờ xử lý",
  downloading: "Đang tải",
  transcribing: "Nhận dạng giọng nói",
  translating: "Đang dịch",
  merging: "Ghép phụ đề",
  uploading: "Đang upload TikTok",
  done: "Hoàn tất",
  error: "Lỗi",
};

export const statusColor: Record<JobStatus, string> = {
  pending: "text-gray-400",
  downloading: "text-blue-400",
  transcribing: "text-purple-400",
  translating: "text-yellow-400",
  merging: "text-orange-400",
  uploading: "text-cyan-400",
  done: "text-green-400",
  error: "text-red-400",
};
