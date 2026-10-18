import localFont from 'next/font/local';
import './globals.css';

const nexusSans = localFont({
  src: './fonts/nexus-sans-latin.woff2',
  variable: '--font-next-sans',
  display: 'swap',
});

const nexusMono = localFont({
  src: './fonts/nexus-mono-latin.woff2',
  variable: '--font-next-mono',
  display: 'swap',
});

export const metadata = {
  title: "Nexus Dashboard",
  description: "Autonomous IHSG AI Analyst",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${nexusSans.variable} ${nexusMono.variable}`}>
      <body>
        {children}
      </body>
    </html>
  );
}

