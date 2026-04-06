"use client";
import { useEffect, useState, useCallback } from "react";
import { RefreshCw, Inbox, CheckCircle, XCircle, Loader2 } from "lucide-react";
import JobCard from "@/components/JobCard";
import { getAllJobs, JobInfo, JobStatus } from "@/lib/api";
import clsx from "clsx";

const FILTER_OPTIONS: { value: "all" | JobStatus; label: string }[] = [
  { value: "all", label: "Tất cả" },
  { value: "pending", label: "Chờ" },
  { value: "downloading", label: "Đang tải" },
  { value: "transcribing", label: "Nhận dạng" },
  { value: "translating", label: "Dịch" },
  { value: "merging", label: "Ghép phụ đề" },
  { value: "done", label: "Hoàn tất" },
  { value: "error", label: "Lỗi" },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobInfo[]>([]);
  const [filter, setFilter] = useState<"all" | JobStatus>("all");
  const [loading, setLoading] = useState(true);
  const [removedIds, setRemovedIds] = useState<Set<string>>(new Set());

  const fetchJobs = useCallback(async () => {
    try {
      const data = await getAllJobs();
      setJobs(data.reverse()); // Mới nhất lên trên
    } catch {}
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const handleRemove = (jobId: string) => {
    setRemovedIds((prev) => new Set([...prev, jobId]));
  };

  const filtered = jobs.filter(
    (j) => !removedIds.has(j.job_id) && (filter === "all" || j.status === filter)
  );

  const stats = {
    total: jobs.length,
    done: jobs.filter((j) => j.status === "done").length,
    error: jobs.filter((j) => j.status === "error").length,
    running: jobs.filter((j) => !["done", "error", "pending"].includes(j.status)).length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Hàng đợi xử lý</h1>
        <button onClick={fetchJobs} className="btn-secondary text-sm py-1.5">
          <RefreshCw size={14} />
          Làm mới
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Tổng", value: stats.total, color: "text-white" },
          { label: "Đang chạy", value: stats.running, color: "text-blue-400" },
          { label: "Hoàn tất", value: stats.done, color: "text-green-400" },
          { label: "Lỗi", value: stats.error, color: "text-red-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="card text-center">
            <div className={clsx("text-2xl font-bold", color)}>{value}</div>
            <div className="text-gray-400 text-sm">{label}</div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setFilter(opt.value)}
            className={clsx(
              "px-3 py-1.5 rounded-lg text-sm transition-colors",
              filter === opt.value
                ? "bg-brand-600 text-white"
                : "bg-dark-700 text-gray-400 hover:text-white"
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Jobs list */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">
          <Loader2 size={32} className="animate-spin mx-auto mb-2" />
          Đang tải...
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-600">
          <Inbox size={48} className="mx-auto mb-3" />
          <p className="text-lg">Chưa có job nào</p>
          <p className="text-sm mt-1">Vào trang chủ để chọn video và bắt đầu tải</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((job) => (
            <JobCard key={job.job_id} initialJob={job} onRemove={handleRemove} />
          ))}
        </div>
      )}
    </div>
  );
}
