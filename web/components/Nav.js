"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "My matches" },
  { href: "/tracker", label: "My tracker" },
  { href: "/profile", label: "Profile" },
];

export default function Nav() {
  const path = usePathname();
  const isActive = (href) => (href === "/" ? path === "/" || path.startsWith("/offer") : path.startsWith(href));
  return (
    <nav className="nav" aria-label="Main navigation">
      <Link href="/" className="logo">internship<span>.</span>finder</Link>
      <div className="nav-links">
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href} className="nav-link" aria-current={isActive(l.href) ? "page" : undefined}>{l.label}</Link>
        ))}
      </div>
    </nav>
  );
}
