"""Canonical current-season team match stats.

The current season uses API-Football because it is the same source as the
fixture pages and the xG shot model. Historical seasons use football-data,
whose league rows are the only complete historical source. The source travels
with each row; no page silently mixes the two within a season.
"""

from __future__ import annotations

from typing import Any

from fitba.ingest.xg_enrichment import enrichment_by_match_team

CURRENT_SEASON = "2026-27"

# Feature-parquet field -> the club_match_rows stat key.
API_STAT_MAP = {
    "shots": "shots",
    "shots_on_target": "shots_on_target",
    "corners": "corners",
    "fouls": "fouls",
    "yellow_cards": "yellow",
    "red_cards": "red",
}


def current_season_stats(
    season: str = CURRENT_SEASON,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Return API-Football team stats keyed by (match_id, team_id)."""
    return enrichment_by_match_team(season)


def overlay_current_stats(
    rows: list[dict[str, Any]],
    *,
    season: str = CURRENT_SEASON,
) -> list[dict[str, Any]]:
    """Overlay API team counts on club-perspective rows for ``season``.

    Rows from other seasons are returned unchanged. A missing API stat keeps
    the football-data value; the caller's source field says which was used.
    """
    stats = current_season_stats(season)
    if not stats:
        return rows
    output: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["stats_source"] = "football_data_uk"
        if str(item.get("season")) == season:
            match_id = str(item.get("match_id") or "")
            # club_match_rows stores the opponent, not our own id.
            team_id = str(item.get("team_id") or "")
            features = stats.get((match_id, team_id)) or {}
            for feature, key in API_STAT_MAP.items():
                for_side = features.get(feature)
                if for_side is not None:
                    item[f"{key}_for"] = int(for_side)
            opponent_id = str(item.get("opponent_id") or "")
            opponent = stats.get((match_id, opponent_id)) or {}
            for feature, key in API_STAT_MAP.items():
                against = opponent.get(feature)
                if against is not None:
                    item[f"{key}_against"] = int(against)
            if features:
                item["stats_source"] = "api_football"
        output.append(item)
    return output


__all__ = ["API_STAT_MAP", "CURRENT_SEASON", "current_season_stats", "overlay_current_stats"]
