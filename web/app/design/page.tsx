import { Fragment } from "react";
import Link from "next/link";
import {
  dataAgeHours,
  formatDate,
  getManifest,
  getProvenance,
  getTableFiles,
  getThemes,
  getTransfers,
  type ProvenanceLayer,
} from "@/lib/data";
import { DsBadge, DsFormStrip, DsMeter, DsStat, sourceLabel } from "./parts";

function dateLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return formatDate(value.slice(0, 10));
}

function sourceName(
  provenance: ReturnType<typeof getProvenance>,
  sourceId: string,
): string {
  if (!provenance) return sourceId;
  return (
    provenance.sources.find((source) => source.id === sourceId)?.name ??
    sourceId.replaceAll("_", " ")
  );
}

function primaryRows(layer: ProvenanceLayer): string {
  const rows = layer.sources
    .filter((source) => source.role === "primary")
    .reduce((total, source) => total + (source.rows ?? 0), 0);
  return rows ? rows.toLocaleString("en-GB") : "—";
}

const KIND_LABEL: Record<string, string> = {
  permanent: "Permanent",
  loan: "Loan",
  free: "Free",
  loan_return: "Loan return",
};

const THEMES = [
  { id: "merkland", label: "Merkland", swatch: "merkland" },
  { id: "red-matchday", label: "Red Matchday", swatch: "red-matchday" },
  { id: "aurora", label: "Aurora", swatch: "aurora" },
  { id: "floodlight", label: "Floodlight", swatch: "floodlight" },
];

export default function DesignSpecimenPage() {
  const manifest = getManifest();
  const tables = getTableFiles();
  const table =
    tables.find((item) =>
      item.rows.some((row) => row.team_id === "sco:aberdeen"),
    ) ??
    tables[0] ??
    null;
  const aberdeenRow =
    table?.rows.find((row) => row.team_id === "sco:aberdeen") ?? null;
  const transfers = getTransfers();
  const provenance = getProvenance();
  const themes = getThemes();

  const moves = transfers?.transfers.slice(0, 6) ?? [];
  const layers = provenance?.layers.slice(0, 5) ?? [];
  const theme =
    themes?.themes.find((item) => item.horizon === "season" && item.read) ??
    themes?.themes[0] ??
    null;
  const age = dataAgeHours(manifest);
  const freshness =
    manifest === null
      ? "No published data"
      : age === null
        ? "Unknown freshness"
        : age > 48
          ? `Stale · ${Math.round(age / 24)}d`
          : `Fresh · ${Math.round(age)}h`;
  const season = manifest?.season ?? table?.season ?? "—";
  const generated = manifest?.generated_at
    ? dateLabel(manifest.generated_at)
    : "—";
  const datasetShort = manifest?.dataset_version
    ? `${manifest.dataset_version.slice(0, 10)} · ${
        manifest.dataset_version.split("-").pop() ?? ""
      }`
    : "—";
  const cutoffsByPosition = new Map(
    (table?.cutoffs ?? []).map((cutoff) => [cutoff.after_position, cutoff]),
  );
  const leagueLayer =
    provenance?.layers.find((layer) => layer.id.includes("league")) ??
    provenance?.layers[0] ??
    null;
  const leagueSource = leagueLayer
    ? sourceName(provenance, leagueLayer.primary)
    : "—";
  const featureMove = moves[0] ?? null;

  return (
    <div className="ds-canvas" id="ds-top">
      <a className="ds-skip" href="#ds-main">
        Skip to specimen
      </a>

      <div className="ds-reviewbar">
        <div className="ds-sheet">
          <span>Specimen 001 · noindex · unlinked</span>
          <Link className="ds-close" href="/">
            Close specimen
          </Link>
        </div>
      </div>

      <div className="ds-themebar">
        <div className="ds-sheet">
          <fieldset className="ds-theme-field">
            <legend className="ds-label">Theme</legend>
            <div className="ds-theme-options">
              {THEMES.map((theme) => (
                <Fragment key={theme.id}>
                  <input
                    type="radio"
                    id={`ds-theme-${theme.id}`}
                    name="ds-theme"
                    defaultChecked={theme.id === "merkland"}
                  />
                  <label htmlFor={`ds-theme-${theme.id}`}>
                    <span
                      className={`ds-swatch ds-swatch--${theme.swatch}`}
                      aria-hidden="true"
                    />
                    {theme.label}
                  </label>
                </Fragment>
              ))}
            </div>
          </fieldset>
          <p className="ds-theme-note">Palette themes. One grammar.</p>
        </div>
      </div>

      <header className="ds-masthead">
        <div className="ds-sheet">
          <Link className="ds-wordmark" href="/">
            <span className="ds-wordmark__mark">f</span>
            <span>
              <span className="ds-wordmark__name">fitba</span>
              <span className="ds-wordmark__line">
                Aberdeen FC, without the noise.
              </span>
            </span>
          </Link>
          <nav className="ds-nav" aria-label="Specimen navigation (static)">
            <span>Matchday</span>
            <span>Themes</span>
            <span>Squad</span>
            <span>Off the pitch</span>
            <span>The Cormack era</span>
            <span>News &amp; rumours</span>
          </nav>
          <div className="ds-meta">
            Season {season}
            <br />
            Dataset {datasetShort}
            <br />
            {freshness}
          </div>
        </div>
      </header>

      <div className="ds-main" id="ds-main">
        <div className="ds-sheet">
          <section className="ds-pagehead">
            <p className="ds-kicker">Design specimen · not a product page</p>
            <h1>Interface grammar for the Aberdeen record.</h1>
            <p className="ds-lede">
              A specimen of the square, ruled, monochrome system proposed for
              fitba. It uses the published league table, transfer register,
              provenance and theme data; no production page, contract or
              generated file is changed.
            </p>
            <p className="ds-state">
              Specimen 001 · generated {generated} · season {season} · dataset{" "}
              {datasetShort} · {freshness}
            </p>
          </section>

          <section className="ds-section" id="type">
            <div className="ds-section__head">
              <p className="ds-label">01 · Type and grid</p>
              <h2>Type roles</h2>
            </div>
            <div className="ds-section__body">
              <div className="ds-type-row">
                <span className="ds-label">Display / H1</span>
                <span className="ds-type-h1">The record, measured.</span>
              </div>
              <div className="ds-type-row">
                <span className="ds-label">Section / H2</span>
                <span className="ds-type-h2">A season in the record</span>
              </div>
              <div className="ds-type-row">
                <span className="ds-label">Pane / H3</span>
                <span className="ds-type-h3">Squad needs and market route</span>
              </div>
              <div className="ds-type-row">
                <span className="ds-label">Body</span>
                <span className="ds-type-body">
                  Measured, inferred, curated and unknown are visible at the
                  point of the number. The method note is part of the record.
                </span>
              </div>
              <div className="ds-type-row">
                <span className="ds-label">Data</span>
                <span className="ds-type-data">
                  7th · 11 points · 9 played · 229 moves · 43 signals
                </span>
              </div>
              <div className="ds-type-row">
                <span className="ds-label">Mono / label</span>
                <span className="ds-type-mono">
                  SOURCE · MEASURED · UPDATED 2026-10-22
                </span>
              </div>
              <div className="ds-type-row">
                <span className="ds-label">Note</span>
                <span className="ds-type-note">
                  A note carries the method, scope or caveat without competing
                  with the data.
                </span>
              </div>
              <div className="ds-grid-strip" aria-hidden="true">
                {Array.from({ length: 12 }, (_, index) => (
                  <span key={index}>{index + 1}</span>
                ))}
              </div>
              <p className="ds-note">
                12 columns · 24px gutter · 1180px sheet · no serif · no pixel
                body text.
              </p>
            </div>
          </section>

          <section className="ds-section" id="table">
            <div className="ds-section__head">
              <p className="ds-label">02 · Table</p>
              <h2>The league table</h2>
            </div>
            <div className="ds-section__body ds-section__body--wide">
              <div className="ds-density">
                <fieldset className="ds-field">
                  <legend className="ds-label">Table density</legend>
                  <div className="ds-segmented">
                    <input
                      type="radio"
                      id="ds-density-regular"
                      name="ds-density"
                      defaultChecked
                    />
                    <label htmlFor="ds-density-regular">Regular</label>
                    <input
                      type="radio"
                      id="ds-density-compact"
                      name="ds-density"
                    />
                    <label htmlFor="ds-density-compact">Compact</label>
                  </div>
                </fieldset>

                {table ? (
                  <>
                    <div
                      className="ds-table-scroll"
                      role="region"
                      aria-label={`${table.competition_name} table, ${table.season}`}
                      tabIndex={0}
                    >
                      <table className="ds-table">
                        <caption>
                          {table.competition_name} · {table.season} · after{" "}
                          {table.rows[0]?.played ?? "—"} matches · source{" "}
                          {leagueSource} · updated{" "}
                          {dateLabel(table.rows[0]?.updated_at)}
                        </caption>
                        <thead>
                          <tr>
                            <th scope="col" className="ds-num">
                              #
                            </th>
                            <th scope="col">Club</th>
                            <th scope="col" className="ds-num">
                              P
                            </th>
                            <th scope="col" className="ds-num">
                              W
                            </th>
                            <th scope="col" className="ds-num">
                              D
                            </th>
                            <th scope="col" className="ds-num">
                              L
                            </th>
                            <th scope="col" className="ds-num">
                              GF
                            </th>
                            <th scope="col" className="ds-num">
                              GA
                            </th>
                            <th scope="col" className="ds-num">
                              GD
                            </th>
                            <th scope="col" className="ds-num">
                              Pts
                            </th>
                            <th scope="col">Form</th>
                          </tr>
                        </thead>
                        <tbody>
                          {table.rows.map((row) => {
                            const cutoff = cutoffsByPosition.get(row.position);
                            const isAberdeen = row.team_id === "sco:aberdeen";
                            return (
                              <Fragment key={row.team_id}>
                                <tr
                                  data-ds-highlight={
                                    isAberdeen ? "" : undefined
                                  }
                                >
                                  <td className="ds-num">{row.position}</td>
                                  <th scope="row">
                                    {row.team_name}
                                    {row.deduction > 0 ? (
                                      <DsBadge tone="warn">
                                        −{row.deduction}
                                      </DsBadge>
                                    ) : null}
                                  </th>
                                  <td className="ds-num">{row.played}</td>
                                  <td className="ds-num">{row.won}</td>
                                  <td className="ds-num">{row.drawn}</td>
                                  <td className="ds-num">{row.lost}</td>
                                  <td className="ds-num">{row.gf}</td>
                                  <td className="ds-num">{row.ga}</td>
                                  <td className="ds-num">
                                    {row.gd > 0 ? `+${row.gd}` : row.gd}
                                  </td>
                                  <td className="ds-num">{row.points}</td>
                                  <td>
                                    <DsFormStrip form={row.form} />
                                  </td>
                                </tr>
                                {cutoff ? (
                                  <tr
                                    className="ds-cutoff"
                                    data-ds-cutoff={cutoff.kind}
                                  >
                                    <td colSpan={11}>
                                      <span className="ds-cutoff__label">
                                        {cutoff.label}
                                      </span>
                                      {cutoff.note ? (
                                        <span className="ds-cutoff__note">
                                          {cutoff.note}
                                        </span>
                                      ) : null}
                                    </td>
                                  </tr>
                                ) : null}
                              </Fragment>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <p className="ds-table-hint">
                      Scroll the table horizontally to see every column.
                    </p>
                    {table.qualification_note ? (
                      <p className="ds-note">{table.qualification_note}</p>
                    ) : null}
                  </>
                ) : (
                  <div className="ds-pane">
                    <div className="ds-pane__title">Unavailable</div>
                    <div className="ds-pane__body">
                      <p>No league table published in this build.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="ds-section" id="controls">
            <div className="ds-section__head">
              <p className="ds-label">03 · Controls</p>
              <h2>Controls look like controls</h2>
            </div>
            <div className="ds-section__body">
              <div className="ds-control-row">
                <button className="ds-btn ds-btn--primary" type="button">
                  Primary action
                </button>
                <button className="ds-btn" type="button">
                  Secondary
                </button>
                <button className="ds-btn ds-btn--ghost" type="button">
                  Text action
                </button>
                <button className="ds-btn" type="button" disabled>
                  Disabled
                </button>
              </div>

              <fieldset className="ds-field">
                <legend className="ds-label">Direction</legend>
                <div className="ds-segmented">
                  <input
                    type="radio"
                    id="ds-direction-all"
                    name="ds-direction"
                    defaultChecked
                  />
                  <label htmlFor="ds-direction-all">All</label>
                  <input
                    type="radio"
                    id="ds-direction-in"
                    name="ds-direction"
                  />
                  <label htmlFor="ds-direction-in">In</label>
                  <input
                    type="radio"
                    id="ds-direction-out"
                    name="ds-direction"
                  />
                  <label htmlFor="ds-direction-out">Out</label>
                </div>
              </fieldset>

              <div className="ds-control-row">
                <label className="ds-field">
                  <span className="ds-label">Window</span>
                  <span className="ds-select-wrap">
                    <select className="ds-select" defaultValue="recent">
                      <option value="recent">All recent</option>
                      <option value="further">Further back</option>
                      <option value="out">Out of window</option>
                    </select>
                  </span>
                </label>
                <label className="ds-field">
                  <span className="ds-label">Player</span>
                  <input
                    className="ds-input"
                    type="search"
                    placeholder="Search name or role"
                  />
                </label>
                <label className="ds-check">
                  <input type="checkbox" defaultChecked />
                  Include loans
                </label>
              </div>

              <details className="ds-details">
                <summary>Method note</summary>
                <div className="ds-details__body">
                  A closed disclosure is for method or caveats. It is never used
                  for a contracted data table, column, source or indicator.
                </div>
              </details>
            </div>
          </section>

          <section className="ds-section" id="states">
            <div className="ds-section__head">
              <p className="ds-label">04 · States</p>
              <h2>Data states</h2>
            </div>
            <div className="ds-section__body">
              <div className="ds-control-row">
                <DsBadge tone="ok">Measured</DsBadge>
                <DsBadge tone="warn">Inferred</DsBadge>
                <DsBadge tone="warn">Curated</DsBadge>
                <DsBadge tone="neutral">Unknown</DsBadge>
                <DsBadge tone="ok">High confidence</DsBadge>
                <DsBadge tone="warn">Medium confidence</DsBadge>
                <DsBadge tone="neutral">Availability unknown</DsBadge>
                <DsBadge tone="info">{freshness}</DsBadge>
                <DsBadge tone="club">Source</DsBadge>
              </div>

              <div className="ds-stat-grid">
                <DsStat
                  label="Position"
                  value={aberdeenRow?.position ?? "—"}
                  note="Premiership"
                />
                <DsStat
                  label="Points"
                  value={aberdeenRow?.points ?? "—"}
                  note={`${aberdeenRow?.played ?? "—"} played`}
                />
                <DsStat
                  label="Registered moves"
                  value={transfers?.summary.total ?? "—"}
                  note={
                    transfers
                      ? `${transfers.summary.players} players · ${transfers.summary.period ?? "register"}`
                      : "register"
                  }
                />
                <DsStat
                  label="Source layers"
                  value={provenance?.layers.length ?? "—"}
                  note="layer truth table"
                />
              </div>

              <DsMeter
                label="Points"
                value={aberdeenRow?.points ?? 0}
                max={30}
              />

              <p className="ds-label">Recent form</p>
              <DsFormStrip form={aberdeenRow?.form ?? ""} />

              <div className="ds-unknown">
                <strong>Unknown stays unknown.</strong> No verified public
                team-news entry means availability is unknown, not fit or
                injured. The same rule applies to fees, wages and possession.
              </div>
            </div>
          </section>

          <section className="ds-section" id="register">
            <div className="ds-section__head">
              <p className="ds-label">05 · Register</p>
              <h2>Transfer register</h2>
            </div>
            <div className="ds-section__body ds-section__body--wide">
              {moves.length ? (
                <>
                  <div
                    className="ds-table-scroll"
                    role="region"
                    aria-label="Transfer register excerpt"
                    tabIndex={0}
                  >
                    <table className="ds-table">
                      <caption>
                        Confirmed business · first {moves.length} of{" "}
                        {transfers?.summary.total ?? 0} register rows
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Player</th>
                          <th scope="col">Direction</th>
                          <th scope="col">From</th>
                          <th scope="col">To</th>
                          <th scope="col">Type</th>
                          <th scope="col">Fee</th>
                          <th scope="col">Status</th>
                          <th scope="col">Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {moves.map((move) => (
                          <tr key={move.transfer_id}>
                            <th scope="row">{move.player_name}</th>
                            <td>
                              <DsBadge
                                tone={
                                  move.direction === "in" ? "ok" : "neutral"
                                }
                              >
                                {move.direction === "in" ? "In" : "Out"}
                              </DsBadge>
                            </td>
                            <td>{move.from_club_name}</td>
                            <td>{move.to_club_name}</td>
                            <td>
                              {KIND_LABEL[move.transfer_kind] ??
                                move.transfer_kind}
                            </td>
                            <td className="ds-num">{move.fee_display}</td>
                            <td>
                              <DsBadge
                                tone={
                                  move.verification_status === "confirmed"
                                    ? "ok"
                                    : "warn"
                                }
                              >
                                {move.verification_status}
                              </DsBadge>
                            </td>
                            <td>
                              {move.source_urls.length ? (
                                <span className="ds-control-row">
                                  {move.source_urls.slice(0, 2).map((url) => (
                                    <a
                                      key={url}
                                      href={url}
                                      target="_blank"
                                      rel="noreferrer"
                                    >
                                      {sourceLabel(url)}
                                    </a>
                                  ))}
                                </span>
                              ) : (
                                "—"
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="ds-table-hint">
                    Scroll the table horizontally to see every column.
                  </p>
                </>
              ) : (
                <div className="ds-pane">
                  <div className="ds-pane__title">Unavailable</div>
                  <div className="ds-pane__body">
                    <p>No transfer register published in this build.</p>
                  </div>
                </div>
              )}

              {featureMove ? (
                <div className="ds-editorial">
                  <p className="ds-label">One row, as an editorial pane</p>
                  <h3>{featureMove.player_name}</h3>
                  <p>
                    {featureMove.from_club_name} → {featureMove.to_club_name} ·{" "}
                    {KIND_LABEL[featureMove.transfer_kind] ??
                      featureMove.transfer_kind}{" "}
                    · {dateLabel(featureMove.date_effective)}
                  </p>
                  <div className="ds-control-row">
                    <DsBadge
                      tone={
                        featureMove.verification_status === "confirmed"
                          ? "ok"
                          : "warn"
                      }
                    >
                      {featureMove.verification_status}
                    </DsBadge>
                    <DsBadge tone="neutral">{featureMove.fee_display}</DsBadge>
                    {featureMove.fee_estimate?.confidence ? (
                      <DsBadge tone="warn">
                        {featureMove.fee_estimate.confidence} confidence
                      </DsBadge>
                    ) : null}
                  </div>
                  {featureMove.notes ? (
                    <p className="ds-note">{featureMove.notes}</p>
                  ) : null}
                  {featureMove.source_urls.length ? (
                    <p className="ds-note">
                      Sources:{" "}
                      {featureMove.source_urls.map((url) => (
                        <a key={url} href={url} target="_blank" rel="noreferrer">
                          {sourceLabel(url)}
                        </a>
                      ))}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          </section>

          <section className="ds-section" id="read">
            <div className="ds-section__head">
              <p className="ds-label">06 · Read</p>
              <h2>A read, labelled</h2>
            </div>
            <div className="ds-section__body">
              {theme ? (
                <div className="ds-editorial">
                  <div className="ds-control-row">
                    <DsBadge
                      tone={
                        theme.read_basis === "measured" ? "ok" : "warn"
                      }
                    >
                      {theme.read_basis}
                    </DsBadge>
                    <DsBadge tone="neutral">{theme.confidence} confidence</DsBadge>
                  </div>
                  <h3>{theme.headline ?? theme.title}</h3>
                  <p>{theme.read}</p>
                  <dl className="ds-evidence">
                    {theme.evidence.slice(0, 2).map((item) => (
                      <div key={`${item.label}-${item.value}`}>
                        <dt>
                          {item.label} · {item.basis}
                        </dt>
                        <dd>
                          {item.value === null || item.value === undefined
                            ? "—"
                            : String(item.value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                  {theme.caveats[0] ? (
                    <p className="ds-note">
                      <strong>Caveat:</strong> {theme.caveats[0]}
                    </p>
                  ) : null}
                  <details className="ds-details">
                    <summary>Method and caveats</summary>
                    <div className="ds-details__body">
                      {theme.method ? <p>{theme.method}</p> : null}
                      {theme.caveats.map((caveat) => (
                        <p key={caveat}>{caveat}</p>
                      ))}
                    </div>
                  </details>
                </div>
              ) : (
                <div className="ds-pane">
                  <div className="ds-pane__title">Unavailable</div>
                  <div className="ds-pane__body">
                    <p>No theme layer published in this build.</p>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="ds-section" id="provenance">
            <div className="ds-section__head">
              <p className="ds-label">07 · Provenance</p>
              <h2>Source layers</h2>
            </div>
            <div className="ds-section__body ds-section__body--wide">
              {provenance && layers.length ? (
                <>
                  <div
                    className="ds-table-scroll"
                    role="region"
                    aria-label="Provenance source layers"
                    tabIndex={0}
                  >
                    <table className="ds-table">
                      <caption>
                        Source layers · {provenance.season} · generated{" "}
                        {dateLabel(provenance.generated_at)}
                      </caption>
                      <thead>
                        <tr>
                          <th scope="col">Layer</th>
                          <th scope="col">Primary</th>
                          <th scope="col">Status</th>
                          <th scope="col" className="ds-num">
                            Rows
                          </th>
                          <th scope="col">Scope</th>
                        </tr>
                      </thead>
                      <tbody>
                        {layers.map((layer) => (
                          <tr key={layer.id}>
                            <th scope="row">{layer.label}</th>
                            <td>{sourceName(provenance, layer.primary)}</td>
                            <td>
                              <DsBadge
                                tone={
                                  layer.status === "active"
                                    ? "ok"
                                    : layer.status === "not_published"
                                      ? "neutral"
                                      : "warn"
                                }
                              >
                                {layer.status}
                              </DsBadge>
                            </td>
                            <td className="ds-num">{primaryRows(layer)}</td>
                            <td>{layer.scope}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="ds-table-hint">
                    Scroll the table horizontally to see every column.
                  </p>
                  <p className="ds-note">{provenance.notes}</p>
                </>
              ) : (
                <div className="ds-pane">
                  <div className="ds-pane__title">Unavailable</div>
                  <div className="ds-pane__body">
                    <p>No provenance published in this build.</p>
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="ds-section" id="notes">
            <div className="ds-section__head">
              <p className="ds-label">08 · Notes</p>
              <h2>Notes and folio</h2>
            </div>
            <div className="ds-section__body">
              <p className="ds-note">
                No production page, contract or generated file is changed. This
                specimen is noindex and unlinked.
              </p>
              <details className="ds-details" open>
                <summary>Open note</summary>
                <div className="ds-details__body">
                  The density control changes padding and type size. It never
                  removes a column, a row or a source.
                </div>
              </details>
              <details className="ds-details">
                <summary>Closed method note</summary>
                <div className="ds-details__body">
                  A closed disclosure is for method or caveats only. A
                  contracted data table is never placed inside one.
                </div>
              </details>
            </div>
          </section>

          <div className="ds-folio">
            <span>fitba · design specimen 001</span>
            <span>
              Season {season} · dataset {datasetShort} · generated {generated}
            </span>
            <span>No production changes</span>
          </div>
        </div>
      </div>
    </div>
  );
}
