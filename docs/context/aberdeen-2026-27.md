# Aberdeen 2026-27: context diary

Qualitative context for reading the data. This is **not** a data source. Nothing
in this diary feeds normalized values, role assignments or published statistics.
Entries are dated; add a citation where one exists.

## 2026-10-21 — A rebuilt squad without a settled shape

Aberdeen have just completed a substantial squad rebuild. The transfer register
shows the scale of the turnover. The team has not yet settled on a shape: it has
used 3-5-2, 3-4-3, 4-4-2 and 5-4-1, and has switched between shapes mid-game.
The unresolved question is the balance of the middle: two centre-backs or three,
or something in between with a holding midfielder dropping into the back line.
The centre-back ratings have been poor and the goalkeeper has been making a high
volume of saves. That combination is a large part of the current fan
frustration and the pressure on the manager.

This is the motivating context for the role and shape layer. The platform should
show:

- the kick-off formation and starting roles in every match, with starts and
  substitute minutes separated;
- the matchday sequence of shapes, so the churn is visible rather than flattened
  into a season total;
- results, goals conceded, goalkeeper saves and centre-back ratings by shape;
- the 2-vs-3-centre-back split and whether a holding midfielder started;
- the difference between what the team sheet says at kick-off and any reported
  mid-game switch. Mid-game switches are recorded in
  `reference/shape_notes.yaml` only when a source supports them; they are never
  inferred from substitutions.

The shape view is descriptive, not causal. A handful of matches in one shape is
not proof, and the shape is not randomly assigned. The point is to make the
tactical problem visible and testable.

## 2026-10-21 — Multi-position players, not one label

A player is not one position. The rebuild has produced players who cover a
back four and a back five, a double pivot and a single holding role, or a wide
midfield and a wing. The role layer must therefore publish an eligibility set:
primary, secondary and stretch slots. Equal weight is given to starts across
the last three seasons; the current Aberdeen role only overrides the display
label when it is clearly and obviously different. The squad filter is broad —
defenders, midfielders, attackers, left/centre/right — because a full-back is
both a defender and a midfielder, a DM is a midfielder, and a winger is an
attacker. The full match-by-match history is a capped, on-demand backfill; it is
not refetched daily or weekly, because a player does not change position on that
timescale.

The principle is wider than Aberdeen: formations are fluid and players are
increasingly utility players, inverted full-backs or inside forwards, up to the
total positional fluidity associated with Atalanta. The slot/eligibility model
is the general case. At Aberdeen it shows up in the central midfield/defence
balance and in the wide players. Olusanya is the worked example: he led the line
for lesser teams but is not a natural finisher; at Aberdeen he is used as an
inside forward / No. 10 to get to the byline or in behind, win first and second
balls and stretch the defence, while Nisbet and Mouloua hold the pure CF slots
because they are better finishers. That is a tactical note and a current-usage
story, not a reason to erase his career centre-forward record.

Lewis Mayo is the other side of the same coin: he wears number 8 for Aberdeen
and the manager intends to use him in central midfield, while at Kilmarnock he
played centre-back because the team needed him there. The observed team-sheet
starts still show centre-back; central midfield is the intended current usage.
The inference panel should say that plainly rather than pretending the
intention is an observed start.

Mitchell Frame is similar: he is a right back by trade, but the 2025-26
Aberdeen team sheets place him on the left (left back / left wing-back), with
Devlin or Lobban on the right of the same line. The history should show the
observed left-side starts and the tactical note should record right back as his
natural side. Do not overwrite the grid with the trade position.
