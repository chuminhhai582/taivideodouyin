"use client";
import { useState } from "react";
import { Download, CheckSquare, Square, Play, Eye, Heart, Clock } from "lucide-react";
import Image from "next/image";
import { VideoInfo, ChannelVideosResponse, formatDuration, formatNumber, startDownload } from "@/lib/api";
import clsx from "clsx";

interface Props {
  data: ChannelVideosResponse;
  onJobsCreated: (jobIds: string[]) => void;
}

export default function VideoGrid({ data, onJobsCreated }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [downloading, setDownloading] = useState(false);
  const [autoProcess, setAutoProcess] = useState(true);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === data.videos.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(data.videos.map((v) => v.id)));
    }
  };

  const handleDownload = async () => {
    if (selected.size === 0) return;
    setDownloading(true);
    try {
      const selectedVideos = data.videos.filter((v) => selected.has(v.id));
      const result = await startDownload(
        selectedVideos.map((v) => v.id),
        selectedVideos.map((v) => v.url),
        autoProcess
      );
      onJobsCreated(result.job_ids);
      setSelected(new Set());
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Lỗi khi tạo job tải xuống");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div>
      {/* Header kênh */}
      <div className="card mb-4 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-bold">{data.channel_name}</h2>
          <p className="text-gray-400 text-sm mt-0.5">
            {data.total} video • ID: {data.channel_id}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Auto process toggle */}
          <label className="flex items-center gap-2 cursor-pointer text-sm">
            <div
              onClick={() => setAutoProcess((v) => !v)}
              className={clsx(
                "w-10 h-5 rounded-full transition-colors relative",
                autoProcess ? "bg-brand-600" : "bg-dark-500"
              )}
            >
              <div
                className={clsx(
                  "absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform",
                  autoProcess ? "translate-x-5" : "translate-x-0.5"
                )}
              />
            </div>
            <span className="text-gray-300">Tự động dịch & ghép phụ đề</span>
          </label>

          <button onClick={selectAll} className="btn-secondary text-sm">
            {selected.size === data.videos.length ? (
              <><CheckSquare size={16} /> Bỏ chọn tất cả</>
            ) : (
              <><Square size={16} /> Chọn tất cả</>
            )}
          </button>

          <button
            onClick={handleDownload}
            className="btn-primary text-sm"
            disabled={selected.size === 0 || downloading}
          >
            <Download size={16} />
            {downloading ? "Đang tạo job..." : `Tải ${selected.size > 0 ? `(${selected.size})` : ""} video`}
          </button>
        </div>
      </div>

      {/* Video grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {data.videos.map((video) => (
          <VideoCard
            key={video.id}
            video={video}
            selected={selected.has(video.id)}
            onToggle={() => toggleSelect(video.id)}
          />
        ))}
      </div>
    </div>
  );
}

function VideoCard({
  video,
  selected,
  onToggle,
}: {
  video: VideoInfo;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      onClick={onToggle}
      className={clsx(
        "relative rounded-xl overflow-hidden cursor-pointer border-2 transition-all duration-200 group",
        selected ? "border-brand-500 shadow-lg shadow-brand-500/20" : "border-transparent hover:border-dark-500"
      )}
    >
      {/* Thumbnail */}
      <div className="aspect-[9/16] bg-dark-700 relative">
        {video.thumbnail ? (
          <Image
            src={video.thumbnail}
            alt={video.title}
            fill
            className="object-cover"
            unoptimized
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <Play size={32} className="text-gray-600" />
          </div>
        )}

        {/* Overlay khi hover */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Play size={28} className="text-white" />
        </div>

        {/* Duration */}
        {video.duration && (
          <div className="absolute bottom-1 right-1 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded flex items-center gap-1">
            <Clock size={10} />
            {formatDuration(video.duration)}
          </div>
        )}

        {/* Checkbox */}
        <div className={clsx(
          "absolute top-2 left-2 transition-opacity",
          selected ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        )}>
          <div className={clsx(
            "w-6 h-6 rounded-full border-2 flex items-center justify-center",
            selected ? "bg-brand-500 border-brand-500" : "bg-black/50 border-white/70"
          )}>
            {selected && <span className="text-white text-xs font-bold">✓</span>}
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="p-2 bg-dark-800">
        <p className="text-xs text-white line-clamp-2 leading-tight mb-1.5">{video.title}</p>
        <div className="flex items-center gap-2 text-gray-500 text-xs">
          {video.view_count != null && (
            <span className="flex items-center gap-0.5">
              <Eye size={10} />{formatNumber(video.view_count)}
            </span>
          )}
          {video.like_count != null && (
            <span className="flex items-center gap-0.5">
              <Heart size={10} />{formatNumber(video.like_count)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
