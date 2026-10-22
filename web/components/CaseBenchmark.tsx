import type { CaseBenchmark as Benchmark } from "@/lib/data";

function cell(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function CaseBenchmark({ benchmark }: { benchmark: Benchmark }) {
  return (
    <section className="card case-benchmark" data-contract="case.benchmark">
      <div className="section-head">
        <div>
          <p className="eyebrow">Benchmark</p>
          <h2>{benchmark.title}</h2>
        </div>
        <span className="badge badge-neutral">League performance only</span>
      </div>
      <div className="table-wrap">
        <table className="league-table">
          <thead>
            <tr>
              {benchmark.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {benchmark.rows.map((row, index) => (
              <tr key={index}>
                {benchmark.columns.map((column) => (
                  <td key={column}>{cell(row[column])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">{benchmark.note}</p>
    </section>
  );
}
