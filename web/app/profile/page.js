import ProfileEditor from "@/components/ProfileEditor";
import { offers, skillImplies, roleFamilies, skillAliases } from "@/lib/data";

export const metadata = { title: "My profile — Internship Finder" };

export default function Page() {
  return <ProfileEditor offers={offers} skillImplies={skillImplies} roleFamilies={roleFamilies} skillAliases={skillAliases} />;
}
