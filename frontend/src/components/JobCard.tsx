"use client";
import { useEffect, useState } from "react";
import {
  Download, Upload, CheckCircle, XCircle, Loader2,
  FileText, RefreshCw, Trash2, ExternalLink
} from "lucide-react";
import {
  JobInfo, JobStatus, statusLabel, statusColor,
  createJobWebSocket, getDownloadFileUrl, uploadToTikTok
} from "@/lib/api";
import clsx from "clsx";

interface Props {
  initialJob: JobInfo;
  onRemove?: (jobId: string) => void;
}

const progressColor: Record<JobStatus, string> = {
  pending: "bg-gray-500",
  downloading: "bg-blue-500",
  transcribing: "bg-purple-500",
  translating: "bg-yellow-500",
  merging: "bg-orange-500",
  uploading: "bg-cyan-500",
  done: "bg-green-500",
  error: "bg-red-500",
};

export default function JobCard({ initialJob, onRemove }: Props) {
  const [job, setJob] = useState<JobInfo>(initialJob);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadTitle, setUploadTitle] = useState(initialJob.video_title);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string>("");

  useEffect(() => {
    if (job.status === "done" || job.status === "error") return;
    const ws = createJobWebSocket(job.job_id);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setJob((prev) => ({ ...prev, ...data }));
      } catch {}
    };
    ws.onerror = () => ws.close();
    return () => ws.close();
  }, [job.job_id, job.status]);

  const handleUpload = async () => {
    setUploading(true);
    try {
      const result = await uploadToTikTok({
        job_id: job.job_id,
        title: uploadTitle,
        description: `#douyin #tiktok #viral`,
      });
      setUploadResult(`Upload thành công! Publish ID: ${result.publish_id}`);
      setShowUpload(false);
    } catch (err: any) {
      setUploadResult(`Lỗi: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={clsx(
      "card transition-all duration-300",
      job.status === "done" && "border-green-800/40",
      job.status === "error" && "border-red-800/40"
    )}>
      <div className="flex items-start gap-3">
        {/* Status icon */}
        <div className="mt-0.5">
          {job.status === "done" ? (
            <CheckCircle size={20} className="text-green-400" />
          ) : job.status === "error" ? (
            <XCircle size={20} className="text-red-400" />
          ) : (
            <Loader2 size={20} className={clsx("animate-spin", statusColor[job.status])} />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-medium text-sm truncate">{job.video_title}</p>
              <p className="text-xs text-gray-500 mt-0.5">ID: {job.job_id}</p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <span className={clsx("badge bg-dark-600", statusColor[job.status])}>
                {statusLabel[job.status]}
              </span>
              {onRemove && (
                <button
                  onClick={() => onRemove(job.job_id)}
                  className="p-1 text-gray-600 hover:text-red-400 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          </div>

          {/* Progress bar */}
          {job.status !== "done" && job.status !== "error" && (
            <div className="mt-2">
              <div className="progress-bar">
                <div
                  className={clsx("progress-fill", progressColor[job.status])}
                  style={{ width: `${job.progress}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">{job.message}</p>
            </div>
          )}

          {/* Done: action buttons */}
          {job.status === "done" && (
            <div className="mt-3 flex flex-wrap gap-2">
              <a
                href={getDownloadFileUrl(job.job_id)}
                download
                className="btn-secondary text-xs py-1.5 px-3"
              >
                <Download size={13} /> Tải về
              </a>
              {job.subtitle_vi && (
                <a
                  href={`/api/subtitle/${job.job_id}/download/vi`}
                  download
                  className="btn-secondary text-xs py-1.5 px-3"
                >
                  <FileText size={13} /> Tải SRT
                </a>
              )}
              <button
                onClick={() => setShowUpload((v) => !v)}
                className="btn-primary text-xs py-1.5 px-3"
              >
                <Upload size={13} /> Upload TikTok
              </button>
            </div>
          )}

          {/* Error */}
          {job.status === "error" && (
            <div className="mt-2 text-red-400 text-xs bg-red-950/30 border border-red-900 rounded px-2 py-1.5">
              {job.error}
            </div>
          )}

          {/* Upload form */}
          {showUpload && (
            <div className="mt-3 bg-dark-700 rounded-lg p-3 space-y-2">
              <p className="text-sm font-medium">Đăng lên TikTok</p>
              <input
                type="text"
                className="input-field text-sm py-2"
                placeholder="Tiêu đề video TikTok"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleUpload}
                  className="btn-primary text-xs py-1.5 flex-1 justify-center"
                  disabled={uploading}
                >
                  {uploading ? <><Loader2 size={13} className="animate-spin" />Đang upload...</> : <><Upload size={13} />Xác nhận upload</>}
                </button>
                <button
                  onClick={() => setShowUpload(false)}
                  className="btn-secondary text-xs py-1.5 px-3"
                >
                  Huỷ
                </button>
              </div>
              {uploadResult && (
                <p className={clsx("text-xs", uploadResult.startsWith("Lỗi") ? "text-red-400" : "text-green-400")}>
                  {uploadResult}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
