import { PageProvenance } from "@/components/PageProvenance";

export function ContractPage({
  surface,
  state = "full",
  children,
}: {
  surface: string;
  state?: "full" | "empty" | "no-fixture" | "redirect";
  children: React.ReactNode;
}) {
  return (
    <div
      className="contract-page"
      data-contract-page={surface}
      data-contract-state={state}
    >
      {children}
      {state === "full" ? <PageProvenance surface={surface} /> : null}
    </div>
  );
}
