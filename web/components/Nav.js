"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Mes matchs" },
  { href: "/suivi", label: "Mon suivi" },
  { href: "/marche", label: "Marché" },
  { href: "/profil", label: "Profil" },
];

export default function Nav() {
  const path = usePathname();
  const isActive = (href) => (href === "/" ? path === "/" || path.startsWith("/offre") : path.startsWith(href));
  return (
    <nav className="nav" aria-label="Navigation principale">
      <Link href="/" className="logo">internship<span>.</span>finder</Link>
      <div className="nav-links">
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href} className="nav-link" aria-current={isActive(l.href) ? "page" : undefined}>{l.label}</Link>
        ))}
      </div>
    </nav>
  );
}
