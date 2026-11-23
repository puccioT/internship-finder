import "./globals.css";
import Nav from "@/components/Nav";

export const metadata = {
  title: "Internship Finder — your internship search copilot",
  description: "Real internship and working-student offers from European tech companies, ranked for your profile.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700&display=swap"
        />
      </head>
      <body>
        <div className="container">
          <Nav />
          {children}
          <footer className="footer">
            <p>
              Offers are collected every day from companies' public career pages (Greenhouse, Lever, Ashby, Workday…)
              and analysed by AI. Summaries can contain mistakes: always read the full posting and apply on the company's site.
            </p>
            <p>Built by Titouan, a business-school student looking for his own internship. Your profile stays in your browser.</p>
          </footer>
        </div>
      </body>
    </html>
  );
}
