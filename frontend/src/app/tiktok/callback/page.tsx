"use client";
import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

export default function TikTokCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    if (code) {
      // Backend xử lý callback qua /tiktok/callback?code=...
      // Next.js rewrite sẽ forward về backend
      // Sau đó backend redirect về /tiktok?status=success
      fetch(`/api/tiktok/callback?code=${code}&state=${state || ""}`)
        .then(() => router.push("/tiktok?status=success"))
        .catch(() => router.push("/tiktok?status=error"));
    }
  }, [searchParams, router]);

  return (
    <div className="flex items-center justify-center py-24">
      <div className="text-center">
        <Loader2 size={40} className="animate-spin mx-auto mb-4 text-brand-500" />
        <p className="text-gray-400">Đang xác thực TikTok...</p>
      </div>
    </div>
  );
}
