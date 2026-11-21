import Tracker from "@/components/Tracker";
import { offers, skillImplies } from "@/lib/data";

export const metadata = { title: "Mon suivi — Internship Finder" };

export default function Page() {
  return <Tracker offers={offers} skillImplies={skillImplies} />;
}
