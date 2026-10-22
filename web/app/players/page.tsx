import Link from "next/link";
import { ContractPage } from "@/components/ContractPage";
import { getSquad } from "@/lib/data";

export const metadata = {
  alternates: { canonical: "/players/" },
  title: "Players · fitba",
  description: "Current Aberdeen players and their profile pages.",
};

export default function PlayersPage() {
  const squad = getSquad();
  return (
    <ContractPage surface="players">
      <section className="page-head">
        <p className="eyebrow">Squad</p>
        <h1>Player profiles</h1>
        <p className="lede">
          Every current Aberdeen player and current loanee with a static profile:
          role evidence, competitive minutes, current-season output and the
          explicit unknown states.
        </p>
      </section>
      {squad?.players.length ? (
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Current squad</p>
              <h2>{squad.players.length} profiles</h2>
            </div>
            <Link className="text-link" href="/squad/">
              Squad board →
            </Link>
          </div>
          <ul className="plain-list">
            {squad.players
              .filter((player) => player.href)
              .map((player) => (
                <li key={player.player_id}>
                  <Link className="text-link" href={player.href as string}>
                    {player.name}
                  </Link>
                  {player.position ? ` · ${player.position}` : ""}
                  {player.status === "loan_out" ? " · loan out" : ""}
                </li>
              ))}
          </ul>
        </section>
      ) : (
        <p className="empty-state">No squad is published in this build.</p>
      )}
    </ContractPage>
  );
}
