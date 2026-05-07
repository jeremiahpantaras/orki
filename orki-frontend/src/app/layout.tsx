import type { Metadata } from "next";
import { Inter, Quicksand } from "next/font/google";
import "./globals.css";

const quicksand = Quicksand({
  variable: "--font-quicksand",
  subsets: ["latin"],
  display: "swap",
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Orki",
  description: "Study smarter for board exam success.",
  icons: {
    icon: [
      { url: "/Logo/OrkiLogo.svg", type: "image/svg+xml" },
      { url: "/Logo/OrkiLogo.webp", type: "image/webp" },
    ],
    shortcut: "/Logo/OrkiLogo.svg",
    apple: "/Logo/OrkiLogo.webp",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${quicksand.variable} ${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
