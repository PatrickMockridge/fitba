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


def _minute_label(event: dict[str, Any]) -> str:
    minute = event.get("minute")
    if minute is None:
        return "an unrecorded minute"
    extra = event.get("extra_minute")
    return f"{int(minute)}+{int(extra)}" if extra else str(int(minute))


def _goal_side(event: dict[str, Any], home_name: str) -> str:
    if event.get("beneficiary_side") in {"home", "away"}:
        return str(event["beneficiary_side"])
    if event.get("side") in {"home", "away"}:
        return str(event["side"])
    return (
        "home"
        if str(event.get("team_name") or "").casefold() == str(home_name).casefold()
        else "away"
    )


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
    ordered = sorted(
        goals,
        key=lambda item: (_minute(item), int(item.get("extra_minute") or 0)),
    )
    for event in ordered:
        side = _goal_side(event, home_name)
        if side == "home":
            home += 1
        else:
            away += 1
        sequence.append(
            {
                "minute": _minute(event),
                "minute_label": _minute_label(event),
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


def _goal_bullet(item: dict[str, Any], index: int) -> str:
    scorer = item.get("player") or "an unrecorded scorer"
    assist = f", assisted by {item['assist']}" if item.get("assist") else ""
    score = f"{item['home']}-{item['away']}"
    minute = item.get("minute_label") or str(item.get("minute") or "")
    if item.get("own_goal"):
        return f"An own goal by {scorer} made it {score} on {minute} minutes."
    if item.get("penalty"):
        return f"{scorer} scored a penalty on {minute} minutes{assist}, making it {score}."
    if index == 0:
        return f"{scorer} opened the scoring on {minute} minutes{assist}, making it {score}."
    return f"{scorer} scored on {minute} minutes{assist}, making it {score}."


def build_summary(
    *,
    fixture: dict[str, Any],
    events: list[dict[str, Any]],
    stats: dict[str, Any] | None,
    xg: dict[str, Any] | None,
    late_goal_minute: int = 85,
    events_available: bool | None = None,
    goals_complete: bool | None = None,
    status: str | None = None,
    home_penalties: int | None = None,
    away_penalties: int | None = None,
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
            "events_available": False,
            "goals_complete": False,
            "reconciliation": None,
            "note": "The result is not published for this fixture.",
        }

    available = bool(events) if events_available is None else bool(events_available)
    goals = _goal_events(events)
    sequence = _score_sequence(goals, home)
    red_cards = [event for event in events if event.get("is_red_card")]
    shootout_available = home_penalties is not None and away_penalties is not None
    home_pens = int(home_penalties) if home_penalties is not None else None
    away_pens = int(away_penalties) if away_penalties is not None else None

    comeback_side: str | None = None
    for item in sequence:
        if item["side"] == "home" and item["away"] - item["home"] >= 2:
            comeback_side = "home"
        if item["side"] == "away" and item["home"] - item["away"] >= 2:
            comeback_side = "away"

    winner_side = "home" if home_goals > away_goals else "away"
    margin = abs(int(home_goals) - int(away_goals))
    decisive_late = False
    if margin == 1 and sequence:
        last = sequence[-1]
        before_home = last["home"] - (1 if last["side"] == "home" else 0)
        before_away = last["away"] - (1 if last["side"] == "away" else 0)
        was_level_or_behind = (
            before_home <= before_away if winner_side == "home" else before_away <= before_home
        )
        decisive_late = (
            last["side"] == winner_side
            and last["minute"] >= late_goal_minute
            and was_level_or_behind
        )

    score = f"{max(home_goals, away_goals)}-{min(home_goals, away_goals)}"
    if (
        shootout_available
        and home_pens is not None
        and away_pens is not None
        and home_pens != away_pens
    ):
        penalty_winner = "home" if home_pens > away_pens else "away"
        penalty_loser = "away" if penalty_winner == "home" else "home"
        penalty_winner_name = home if penalty_winner == "home" else away
        penalty_loser_name = home if penalty_loser == "home" else away
        penalty_score = (
            f"{home_pens}-{away_pens}" if penalty_winner == "home" else f"{away_pens}-{home_pens}"
        )
        headline = (
            f"{penalty_winner_name} beat {penalty_loser_name} {penalty_score} on penalties "
            f"after a {home_goals}-{away_goals} draw"
        )
    elif status == "PEN" and not shootout_available:
        headline = (
            f"{home} and {away} drew {home_goals}-{away_goals}; the shoot-out result is unavailable"
        )
    elif home_goals == away_goals:
        headline = f"{home} and {away} draw {home_goals}-{away_goals}"
    else:
        winner = home if home_goals > away_goals else away
        loser = away if winner == home else home
        if comeback_side == winner_side:
            headline = f"{winner} come back to beat {loser} {score}"
        elif decisive_late:
            headline = f"{winner} win it late against {loser}"
        elif red_cards:
            headline = f"Ten-man {winner} beat {loser} {score}"
        else:
            headline = f"{winner} beat {loser} {score}"

    event_final = (sequence[-1]["home"], sequence[-1]["away"]) if sequence else (0, 0)
    reconciled = event_final == (home_goals, away_goals)
    bullets: list[dict[str, Any]] = []

    if not available:
        bullets.append(
            {
                "text": "The event feed is unavailable; the final score is authoritative.",
                "basis": "unknown",
            }
        )
    elif not sequence:
        bullets.append(
            {
                "text": (
                    "The event feed records no goals."
                    if home_goals == 0 and away_goals == 0
                    else (
                        f"The event feed does not reconcile with the final score "
                        f"{home_goals}-{away_goals}; only recorded goals are listed."
                    )
                ),
                "basis": "measured",
            }
        )
    else:
        for index, item in enumerate(sequence):
            bullets.append({"text": _sentence(_goal_bullet(item, index)), "basis": "measured"})
        if not reconciled:
            bullets.append(
                {
                    "text": (
                        f"The event feed records {len(goals)} "
                        f"{'goal' if len(goals) == 1 else 'goals'} but does not "
                        f"reconcile with the final score {home_goals}-{away_goals}; "
                        "only recorded goals are listed."
                    ),
                    "basis": "measured",
                }
            )

    for card in red_cards:
        player = card.get("player_name") or "A player"
        minute = _minute_label(card)
        if card.get("is_second_yellow"):
            text = f"{player} was sent off for a second yellow card on {minute} minutes."
        else:
            text = f"{player} was sent off on {minute} minutes."
        bullets.append({"text": _sentence(text), "basis": "measured"})

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

    complete = (
        bool(goals_complete) if goals_complete is not None else (reconciled if available else False)
    )
    reconciliation = (
        {
            "event_goals": len(goals),
            "event_score": {"home": event_final[0], "away": event_final[1]},
            "final_score": {"home": home_goals, "away": away_goals},
            "matched": reconciled,
        }
        if available
        else {
            "event_goals": None,
            "event_score": None,
            "final_score": {"home": home_goals, "away": away_goals},
            "matched": None,
        }
    )

    return {
        "headline": _sentence(headline),
        "basis": "measured" if events or stats else "unknown",
        "bullets": bullets,
        "events_available": available,
        "goals_complete": complete,
        "reconciliation": reconciliation,
        "note": (
            "The read describes measured events and model output. It is not a "
            "result prediction and not a verdict on performance."
        ),
    }


__all__ = ["BANNED", "build_summary"]
