"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import ChannelInput from "@/components/ChannelInput";
import VideoGrid from "@/components/VideoGrid";
import { ChannelVideosResponse } from "@/lib/api";
import { CheckCircle } from "lucide-react";
import Link from "next/link";

export default function HomePage() {
  const [channelData, setChannelData] = useState<ChannelVideosResponse | null>(null);
  const [createdJobs, setCreatedJobs] = useState<string[]>([]);
  const router = useRouter();

  const handleJobsCreated = (jobIds: string[]) => {
    setCreatedJobs(jobIds);
  };

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="text-center py-8">
        <h1 className="text-3xl font-bold mb-2">
          <span className="text-brand-500">Douyin</span> → <span className="text-white">TikTok</span>
        </h1>
        <p className="text-gray-400 max-w-lg mx-auto">
          Tải video Douyin không watermark · Tự động thêm phụ đề tiếng Việt · Đăng thẳng lên TikTok
        </p>
        <div className="flex items-center justify-center gap-6 mt-4 text-sm text-gray-500">
          {["Không watermark", "Phụ đề AI tiếng Việt", "Upload TikTok 1-click"].map((item) => (
            <span key={item} className="flex items-center gap-1.5">
              <CheckCircle size={14} className="text-green-400" />
              {item}
            </span>
          ))}
        </div>
      </div>

      {/* Input */}
      <ChannelInput onResult={(data) => { setChannelData(data); setCreatedJobs([]); }} />

      {/* Job created notification */}
      {createdJobs.length > 0 && (
        <div className="bg-green-950/40 border border-green-800 rounded-xl px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle size={18} />
            <span>Đã tạo {createdJobs.length} job xử lý thành công!</span>
          </div>
          <Link href="/jobs" className="btn-primary text-sm py-1.5">
            Xem tiến trình →
          </Link>
        </div>
      )}

      {/* Video grid */}
      {channelData && (
        <VideoGrid data={channelData} onJobsCreated={handleJobsCreated} />
      )}

      {/* Empty state */}
      {!channelData && (
        <div className="text-center py-16 text-gray-600">
          <div className="text-6xl mb-4">🎵</div>
          <p className="text-lg">Nhập link kênh Douyin để bắt đầu</p>
          <p className="text-sm mt-1">Ví dụ: https://www.douyin.com/user/MS4wLjABAAAA...</p>
        </div>
      )}
    </div>
  );
}
