import './globals.css';

export const metadata = {
  title: "Nexus Dashboard",
  description: "Autonomous IHSG AI Analyst",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
