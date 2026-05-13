import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Weather Station Dashboard",
  description: "Dashboard for the ESP32 smart weather station",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
