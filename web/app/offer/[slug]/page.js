import { Suspense } from "react";
import { notFound } from "next/navigation";
import OfferDetail from "@/components/OfferDetail";
import { offers, skillImplies } from "@/lib/data";

/** Une page par offre, générée à l'avance au moment du build. */
export function generateStaticParams() {
  return offers.map((o) => ({ slug: o.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const offer = offers.find((o) => o.slug === slug);
  return { title: offer ? `${offer.title} · ${offer.company} — Internship Finder` : "Offer not found" };
}

/**
 * La lecture de l'adresse (params) est isolée dans un <Suspense> :
 * Next.js peut ainsi afficher la page instantanément pendant la navigation.
 */
export default function OfferPage({ params }) {
  return (
    <Suspense fallback={<p className="muted">Loading offer…</p>}>
      <Offer params={params} />
    </Suspense>
  );
}

async function Offer({ params }) {
  const { slug } = await params;
  const offer = offers.find((o) => o.slug === slug);
  if (!offer) notFound();

  // Pour « Offres similaires » et « demandé dans N offres » : les offres du même pays
  const sameCountry = offers.filter((o) => o.country === offer.country);
  return <OfferDetail offer={offer} pool={sameCountry} skillImplies={skillImplies} />;
}
