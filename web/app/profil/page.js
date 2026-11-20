import ProfileEditor from "@/components/ProfileEditor";
import { offers, skillImplies, roleFamilies } from "@/lib/data";

export const metadata = { title: "Mon profil — Internship Finder" };

export default function Page() {
  return <ProfileEditor offers={offers} skillImplies={skillImplies} roleFamilies={roleFamilies} />;
}
