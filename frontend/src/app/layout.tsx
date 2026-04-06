import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "Douyin → TikTok | Tải & Việt Hoá Video",
  description: "Tải video Douyin không watermark, thêm phụ đề tiếng Việt và đăng lên TikTok",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className="dark">
      <body className={`${inter.className} bg-dark-900 text-white min-h-screen`}>
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
