import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Paper Read",
  description: "Read papers and jot notes as you go.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
