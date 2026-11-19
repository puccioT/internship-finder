import Matches from "@/components/Matches";
import { offers, skillImplies, roleFamilies, generatedAt } from "@/lib/data";

export default function Home() {
  return <Matches offers={offers} skillImplies={skillImplies} roleFamilies={roleFamilies} generatedAt={generatedAt} />;
}
