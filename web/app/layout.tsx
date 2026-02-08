import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sloppy Jobulator",
  description: "Public research opportunity catalogue"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
