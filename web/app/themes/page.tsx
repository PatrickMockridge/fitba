import Link from "next/link";
import { EmptyState } from "@/components/EmptyState";
import { LegendDisclosure } from "@/components/LegendDisclosure";
import { PageHeader } from "@/components/PageHeader";
import { TableFrame, Th } from "@/components/TableFrame";
import { ThemeCard } from "@/components/ThemeCard";
import { plainText } from "@/lib/format";
import { getThemes, type ThemeBlock } from "@/lib/data";

export const metadata = { title: "The bigger picture · fitba" };

function anchor(theme: ThemeBlock) {
  return theme.theme_id.replaceAll("_", "-");
}

function keyNumber(theme: ThemeBlock) {
  const item = theme.evidence[0];
  if (!item) return "—";
  const value = item.value === null || item.value === undefined ? "—" : String(item.value);
  return item.note ? `${value} ${item.note}` : value;
}

export default function ThemesPage() {
  const data = getThemes();
  if (!data) {
    return (
      <EmptyState
        title="No theme layer published"
        body="The theme layer is built from the local match, squad and history data. The next-match view is still available."
        action={
          <Link className="button button-ghost" href="/matchday/">
            Matchday
          </Link>
        }
      />
    );
  }

  const seasonThemes = data.themes.filter((theme) => theme.horizon === "season");
  const mission = data.themes.find((theme) => theme.horizon === "mission");

  return (
    <>
      <PageHeader
        eyebrow="The bigger picture"
        title="Where is the squad strong and weak?"
        summary="Five questions. Five answers. One number each."
      />

      {data.state !== "fresh" ? (
        <p className="stale-banner">
          {data.state === "stale"
            ? "This theme layer is carried forward from an earlier publish."
            : data.state === "partial"
              ? "Some theme layers are partial; the missing pieces are labelled."
              : "The theme layer is unavailable for this publish."}
        </p>
      ) : null}

      <section className="section">
        <TableFrame
          label="Theme answers"
          caption="Theme question, answer and key number"
        >
          <thead>
            <tr>
              <Th>Question</Th>
              <Th>Answer</Th>
              <Th className="num">Key number</Th>
            </tr>
          </thead>
          <tbody>
            {data.themes.map((theme) => (
              <tr key={theme.theme_id}>
                <td>
                  <a href={`#${anchor(theme)}`}>{theme.fan_question}</a>
                </td>
                <td>{plainText(theme.headline ?? theme.title)}</td>
                <td className="num">{keyNumber(theme)}</td>
              </tr>
            ))}
          </tbody>
        </TableFrame>
      </section>

      <section className="section">
        <div className="theme-stack">
          {seasonThemes.map((theme) => (
            <section className="theme-block" key={theme.theme_id}>
              <h2>{theme.fan_question}</h2>
              <ThemeCard theme={theme} />
            </section>
          ))}
        </div>
      </section>

      {mission ? (
        <section className="section">
          <h2>{mission.fan_question}</h2>
          <ThemeCard theme={mission} />
        </section>
      ) : null}

      <LegendDisclosure title="How the themes are measured">
        <p>
          Provider ratings are external match ratings, not a fitba rating. They
          are Premiership-only, minutes-weighted and not position-adjusted. A
          family mean can hide a high-variance unit; the evidence shows the
          spread.
        </p>
        <p>
          Availability is unknown without a verified team-news entry. The data
          cannot distinguish selection from availability, and “trust” is not
          measured.
        </p>
        <p>
          {data.coverage.fixtures_total ?? "—"} fixtures ·{" "}
          {data.coverage.starts_with_role ?? "—"}/{data.coverage.starts_total ?? "—"}{" "}
          starts with a role · {data.coverage.provider_ratings}.{" "}
          <Link href="/methodology/">Method</Link> ·{" "}
          <Link href="/sources/">Sources</Link> ·{" "}
          <Link href="/squad/">Squad</Link> ·{" "}
          <Link href="/transfers/">Transfers</Link> ·{" "}
          <Link href="/history/">The Cormack era</Link>
        </p>
      </LegendDisclosure>
    </>
  );
}
