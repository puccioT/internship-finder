import "./globals.css";
import Nav from "@/components/Nav";

export const metadata = {
  title: "Internship Finder — ton copilote de recherche de stage",
  description: "Les vraies offres de stage et d'alternance des startups tech françaises, classées selon ton profil.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="fr">
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
        </div>
      </body>
    </html>
  );
}
