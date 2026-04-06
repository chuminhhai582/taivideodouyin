"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle, LogIn, LogOut, Upload, ExternalLink } from "lucide-react";
import { getTikTokAuthUrl, getTikTokStatus } from "@/lib/api";

export default function TikTokPage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const searchParams = useSearchParams();
  const status = searchParams.get("status");

  useEffect(() => {
    getTikTokStatus().then((data) => {
      setAuthenticated(data.authenticated);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleLogin = async () => {
    const { auth_url } = await getTikTokAuthUrl();
    window.location.href = auth_url;
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold">Kết nối TikTok</h1>

      {status === "success" && (
        <div className="bg-green-950/40 border border-green-800 rounded-xl px-4 py-3 flex items-center gap-2 text-green-400">
          <CheckCircle size={18} />
          Đăng nhập TikTok thành công!
        </div>
      )}

      {/* Auth card */}
      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center text-2xl">
            🎵
          </div>
          <div>
            <h2 className="font-semibold">TikTok Account</h2>
            <p className="text-sm text-gray-400">
              {loading ? "Đang kiểm tra..." : authenticated ? "Đã kết nối" : "Chưa kết nối"}
            </p>
          </div>
          <div className="ml-auto">
            {authenticated ? (
              <span className="badge bg-green-900/50 text-green-400">
                <CheckCircle size={12} /> Đã xác thực
              </span>
            ) : (
              <span className="badge bg-dark-600 text-gray-400">Chưa đăng nhập</span>
            )}
          </div>
        </div>

        {!authenticated ? (
          <div>
            <p className="text-gray-400 text-sm mb-4">
              Kết nối tài khoản TikTok để có thể upload video trực tiếp từ ứng dụng này.
              Bạn cần có <strong className="text-white">TikTok Business/Creator Account</strong> với quyền Content Posting API.
            </p>
            <button onClick={handleLogin} className="btn-primary">
              <LogIn size={16} />
              Đăng nhập TikTok
              <ExternalLink size={14} />
            </button>
          </div>
        ) : (
          <div>
            <p className="text-gray-400 text-sm mb-4">
              Tài khoản đã được kết nối. Bạn có thể upload video từ trang <strong className="text-white">Hàng đợi</strong>.
            </p>
            <div className="flex gap-2">
              <a href="/jobs" className="btn-primary">
                <Upload size={16} />
                Đến hàng đợi để upload
              </a>
            </div>
          </div>
        )}
      </div>

      {/* Hướng dẫn */}
      <div className="card space-y-3">
        <h3 className="font-semibold text-base">Hướng dẫn cấu hình TikTok API</h3>
        <ol className="space-y-2 text-sm text-gray-300 list-decimal list-inside">
          <li>Truy cập <span className="text-brand-400">developers.tiktok.com</span> và tạo app</li>
          <li>Thêm sản phẩm <strong>Login Kit</strong> và <strong>Content Posting API</strong></li>
          <li>Cấu hình Redirect URI: <code className="bg-dark-700 px-1.5 py-0.5 rounded text-xs">http://localhost:3000/tiktok/callback</code></li>
          <li>Copy Client Key và Client Secret vào file <code className="bg-dark-700 px-1.5 py-0.5 rounded text-xs">.env</code></li>
          <li>Khởi động lại server và đăng nhập lại</li>
        </ol>
      </div>

      {/* Quy trình */}
      <div className="card">
        <h3 className="font-semibold mb-3">Quy trình hoàn chỉnh</h3>
        <div className="space-y-2">
          {[
            { step: "1", label: "Nhập link kênh Douyin", desc: "Trang chủ → nhập URL kênh" },
            { step: "2", label: "Chọn video cần tải", desc: "Chọn 1 hoặc nhiều video" },
            { step: "3", label: "Tự động xử lý", desc: "Tải → Transcribe → Dịch → Ghép phụ đề" },
            { step: "4", label: "Upload lên TikTok", desc: "1-click upload từ trang Hàng đợi" },
          ].map(({ step, label, desc }) => (
            <div key={step} className="flex items-center gap-3 p-2 rounded-lg bg-dark-700/50">
              <div className="w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center text-xs font-bold shrink-0">
                {step}
              </div>
              <div>
                <p className="text-sm font-medium">{label}</p>
                <p className="text-xs text-gray-400">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
