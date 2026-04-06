"use client";
import { useEffect, useRef, useState } from "react";
import { Cookie, Upload, CheckCircle, Trash2, AlertCircle } from "lucide-react";
import { uploadCookies, getCookiesStatus, api } from "@/lib/api";

export default function CookiesUpload() {
  const [hasCookies, setHasCookies] = useState(false);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCookiesStatus().then((d) => setHasCookies(d.has_cookies)).catch(() => {});
  }, []);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setMsg("");
    try {
      await uploadCookies(file);
      setHasCookies(true);
      setMsg("Đã lưu cookies! Thử tìm kiếm lại kênh.");
    } catch {
      setMsg("Lỗi khi upload cookies.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    await api.delete("/settings/cookies");
    setHasCookies(false);
    setMsg("Đã xóa cookies.");
  };

  return (
    <div className="card border-dashed border-dark-500">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Cookie size={18} className={hasCookies ? "text-green-400" : "text-yellow-400"} />
          <div>
            <p className="text-sm font-medium">
              {hasCookies ? "Cookies Douyin đã được cấu hình" : "Chưa có cookies Douyin"}
            </p>
            <p className="text-xs text-gray-500">
              {hasCookies
                ? "Đang dùng cookies để xác thực với Douyin"
                : "Cần cookies để lấy danh sách video kênh"}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => inputRef.current?.click()}
            className="btn-secondary text-xs py-1.5"
            disabled={loading}
          >
            <Upload size={13} />
            {loading ? "Đang upload..." : "Upload cookies.txt"}
          </button>
          {hasCookies && (
            <button onClick={handleDelete} className="btn-secondary text-xs py-1.5 text-red-400">
              <Trash2 size={13} /> Xóa
            </button>
          )}
        </div>
      </div>

      {msg && (
        <div className={`mt-2 text-xs flex items-center gap-1.5 ${msg.includes("Lỗi") ? "text-red-400" : "text-green-400"}`}>
          {msg.includes("Lỗi") ? <AlertCircle size={13} /> : <CheckCircle size={13} />}
          {msg}
        </div>
      )}

      {!hasCookies && (
        <div className="mt-3 text-xs text-gray-500 bg-dark-700 rounded-lg p-3 space-y-1">
          <p className="font-medium text-gray-300">Cách lấy cookies.txt:</p>
          <p>1. Mở Chrome/Edge → vào <span className="text-brand-400">douyin.com</span> → đăng nhập</p>
          <p>2. Cài extension <span className="text-white font-medium">"Get cookies.txt LOCALLY"</span> trên Chrome Web Store</p>
          <p>3. Click icon extension → nhấn <span className="text-white">Export</span> → lưu file</p>
          <p>4. Upload file đó vào đây</p>
        </div>
      )}

      <input ref={inputRef} type="file" accept=".txt" className="hidden" onChange={handleFile} />
    </div>
  );
}
