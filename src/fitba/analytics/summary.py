"""Deterministic match summaries from events, score and measured stats.

The summary is a stock-phrase generator, not a language model. It records what
the feed says, labels model output as model output, and says when a data class
is missing. It never predicts a result, awards a "deserved" verdict or blames a
player.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

BANNED = (
    "deserved",
    "dominated",
    "lucky",
    "should have won",
    "bottled",
    "collapse",
    "disgrace",
    "hero",
    "villain",
)


def _minute(event: dict[str, Any]) -> int:
    return int(event.get("minute") or 0) + int(event.get("extra_minute") or 0)


def _goal_side(event: dict[str, Any], home_name: str) -> str:
    side = (
        "home"
        if str(event.get("team_name") or "").casefold() == str(home_name).casefold()
        else "away"
    )
    if event.get("is_own_goal"):
        return "away" if side == "home" else "home"
    return side


def _goal_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event.get("is_goal") and not event.get("is_shootout") and event.get("minute") is not None
    ]


def _score_sequence(goals: list[dict[str, Any]], home_name: str) -> list[dict[str, Any]]:
    home = 0
    away = 0
    sequence: list[dict[str, Any]] = []
    for event in sorted(goals, key=_minute):
        side = _goal_side(event, home_name)
        if side == "home":
            home += 1
        else:
            away += 1
        sequence.append(
            {
                "minute": _minute(event),
                "side": side,
                "player": event.get("player_name"),
                "assist": event.get("assist_name"),
                "own_goal": bool(event.get("is_own_goal")),
                "penalty": bool(event.get("is_penalty")),
                "home": home,
                "away": away,
            }
        )
    return sequence


def _sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    lowered = cleaned.casefold()
    for phrase in BANNED:
        if phrase in lowered:
            raise ValueError(f"banned summary phrase: {phrase}")
    return cleaned


def build_summary(
    *,
    fixture: dict[str, Any],
    events: list[dict[str, Any]],
    stats: dict[str, Any] | None,
    xg: dict[str, Any] | None,
    late_goal_minute: int = 85,
) -> dict[str, Any]:
    home = str(fixture.get("home_team_name") or "Home")
    away = str(fixture.get("away_team_name") or "Away")
    home_goals = fixture.get("home_goals")
    away_goals = fixture.get("away_goals")
    if home_goals is None or away_goals is None:
        return {
            "headline": f"{home} v {away}: result unavailable",
            "basis": "unknown",
            "bullets": [],
            "note": "The result is not published for this fixture.",
        }

    goals = _goal_events(events)
    sequence = _score_sequence(goals, home)
    red_cards = [event for event in events if event.get("is_red_card")]
    shootout = [event for event in events if event.get("is_shootout")]
    comeback = False
    for item in sequence:
        if item["side"] == "home" and item["away"] - item["home"] >= 2:
            comeback = "home"
        if item["side"] == "away" and item["home"] - item["away"] >= 2:
            comeback = "away"
    if (home_goals > away_goals and comeback == "home") or (
        away_goals > home_goals and comeback == "away"
    ):
        comeback = True
    else:
        comeback = False

    late_goals = [item for item in sequence if item["minute"] >= late_goal_minute]
    score = f"{max(home_goals, away_goals)}-{min(home_goals, away_goals)}"
    if home_goals == away_goals:
        headline = f"{home} and {away} draw {home_goals}-{away_goals}"
    else:
        winner = home if home_goals > away_goals else away
        loser = away if winner == home else home
        winner_side = "home" if winner == home else "away"
        if shootout:
            headline = f"{winner} beat {loser} on penalties after a {home_goals}-{away_goals} draw"
        elif comeback:
            headline = f"{winner} come back to beat {loser} {score}"
        elif late_goals and late_goals[-1]["side"] == winner_side:
            headline = f"{winner} win it late against {loser}"
        elif red_cards:
            headline = f"Ten-man {winner} beat {loser} {score}"
        else:
            headline = f"{winner} beat {loser} {score}"

    event_final = (sequence[-1]["home"], sequence[-1]["away"]) if sequence else (0, 0)
    reconciled = event_final == (home_goals, away_goals)
    bullets: list[dict[str, Any]] = []
    if not reconciled:
        bullets.append(
            {
                "text": (
                    f"The event feed records {len(goals)} goals; the final score "
                    f"is {home_goals}-{away_goals}. The score is authoritative."
                ),
                "basis": "measured",
            }
        )
    if sequence:
        first = sequence[0]
        scorer = first.get("player") or "an unrecorded scorer"
        assist = f", assisted by {first['assist']}" if first.get("assist") else ""
        if first.get("own_goal"):
            opening = f"An own goal by {scorer} opened the scoring on {first['minute']} minutes."
        elif first.get("penalty"):
            opening = f"{scorer} scored a penalty on {first['minute']} minutes{assist}."
        else:
            opening = f"{scorer} opened the scoring on {first['minute']} minutes{assist}."
        bullets.append({"text": _sentence(opening), "basis": "measured"})
        equalisers = [
            item for item in sequence[1:] if item["home"] == item["away"] and item["home"] > 0
        ]
        if equalisers:
            item = equalisers[0]
            bullets.append(
                {
                    "text": _sentence(
                        f"{item.get('player') or 'The equaliser'} made it "
                        f"{item['home']}-{item['away']} on {item['minute']} minutes."
                    ),
                    "basis": "measured",
                }
            )
        if late_goals:
            item = late_goals[-1]
            bullets.append(
                {
                    "text": _sentence(
                        f"The last goal came on {item['minute']} minutes, "
                        f"making it {item['home']}-{item['away']}."
                    ),
                    "basis": "measured",
                }
            )
    else:
        bullets.append(
            {
                "text": "The event feed records no goals for this fixture.",
                "basis": "measured" if events else "unknown",
            }
        )

    if red_cards:
        first = red_cards[0]
        bullets.append(
            {
                "text": _sentence(
                    f"{first.get('player_name') or 'A player'} was sent off "
                    f"on {_minute(first)} minutes."
                ),
                "basis": "measured",
            }
        )
    if any(event.get("is_own_goal") for event in goals):
        bullets.append({"text": "The score includes an own goal.", "basis": "measured"})
    if any(event.get("is_penalty") for event in goals):
        bullets.append({"text": "The score includes a penalty.", "basis": "measured"})

    if stats:
        for key, label in (
            ("shots", "Shots"),
            ("shots_on_target", "Shots on target"),
            ("possession", "Possession"),
        ):
            home_value = (stats.get("home") or {}).get(key)
            away_value = (stats.get("away") or {}).get(key)
            if home_value is None or away_value is None:
                continue
            suffix = "%" if key == "possession" else ""
            bullets.append(
                {
                    "text": _sentence(
                        f"{label}: {home} {home_value}{suffix}, {away} {away_value}{suffix}."
                    ),
                    "basis": "measured",
                }
            )
    else:
        bullets.append(
            {
                "text": (
                    "Team statistics are unavailable for this fixture; the score "
                    "and event record are shown."
                ),
                "basis": "unknown",
            }
        )
    if xg and xg.get("home") is not None and xg.get("away") is not None:
        bullets.append(
            {
                "text": _sentence(
                    f"fxG: {home} {xg['home']} ({xg.get('home_low')}-{xg.get('home_high')}), "
                    f"{away} {xg['away']} ({xg.get('away_low')}-{xg.get('away_high')})."
                ),
                "basis": "inferred",
            }
        )

    return {
        "headline": _sentence(headline),
        "basis": "measured" if events or stats else "unknown",
        "bullets": bullets,
        "reconciliation": {
            "event_goals": len(goals),
            "event_score": {"home": event_final[0], "away": event_final[1]},
            "final_score": {"home": home_goals, "away": away_goals},
            "matched": reconciled,
        },
        "note": (
            "The read describes measured events and model output. It is not a "
            "result prediction and not a verdict on performance."
        ),
    }


__all__ = ["BANNED", "build_summary"]
