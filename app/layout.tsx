import type { Metadata } from "next";
import "./globals.css";
import NotesWidget from "@/components/NotesWidget";
import { paperTitle } from "@/lib/paper";

export const metadata: Metadata = {
  title: paperTitle,
  description: "Read the paper and jot notes as you go.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {children}
        <NotesWidget />
      </body>
    </html>
  );
}
