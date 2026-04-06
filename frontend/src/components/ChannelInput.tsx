"use client";
import { useState } from "react";
import { Search, Loader2, AlertCircle } from "lucide-react";
import { getChannelVideos, ChannelVideosResponse } from "@/lib/api";

interface Props {
  onResult: (data: ChannelVideosResponse) => void;
}

export default function ChannelInput({ onResult }: Props) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setError("");
    setLoading(true);
    try {
      const data = await getChannelVideos(url.trim());
      onResult(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Không thể lấy thông tin kênh. Kiểm tra lại URL.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Search size={20} className="text-brand-500" />
        Nhập link kênh Douyin
      </h2>
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="url"
          className="input-field flex-1"
          placeholder="https://www.douyin.com/user/xxxxx"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn-primary min-w-[120px] justify-center" disabled={loading || !url.trim()}>
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Đang tải...
            </>
          ) : (
            <>
              <Search size={16} />
              Tìm kiếm
            </>
          )}
        </button>
      </form>
      {error && (
        <div className="mt-3 flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-900 rounded-lg px-3 py-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}
      <p className="mt-2 text-gray-500 text-xs">
        Hỗ trợ: douyin.com/user/... | v.douyin.com/... | iesdouyin.com/...
      </p>
    </div>
  );
}
