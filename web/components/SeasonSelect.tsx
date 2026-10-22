"use client";

export function SeasonSelect({
  seasons,
  current,
  selected,
  onSelect,
}: {
  seasons: string[];
  current: string;
  selected: string;
  onSelect: (season: string) => void;
}) {
  return (
    <div
      className="season-bar"
      role="tablist"
      aria-label="Match seasons"
      data-contract="matches.season-select"
    >
      {seasons.map((season) => (
        <button
          key={season}
          type="button"
          role="tab"
          aria-selected={season === selected}
          className={`season-pill${season === selected ? " is-active" : ""}`}
          onClick={() => onSelect(season)}
        >
          {season}
          {season === current ? (
            <span className="season-current"> current</span>
          ) : null}
        </button>
      ))}
    </div>
  );
}
