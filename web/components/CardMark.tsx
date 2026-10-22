export function CardMark({ color }: { color: "yellow" | "red" }) {
  const label = color === "yellow" ? "Yellow cards" : "Red cards";
  return (
    <span
      className={`card-mark card-mark-${color}`}
      role="img"
      aria-label={label}
      title={label}
    />
  );
}
