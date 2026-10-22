export function ContractPage({
  surface,
  state = "full",
  children,
}: {
  surface: string;
  state?: "full" | "empty" | "no-fixture";
  children: React.ReactNode;
}) {
  return (
    <div
      className="contract-page"
      data-contract-page={surface}
      data-contract-state={state}
    >
      {children}
    </div>
  );
}
