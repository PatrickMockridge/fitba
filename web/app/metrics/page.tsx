import { ContractPage } from "@/components/ContractPage";
import {
  getManifest,
  getMetricsAudit,
  getMetricsRegistry,
  getValidationReport,
} from "@/lib/data";

export const metadata = {
  title: "Metrics and audit · fitba",
  description:
    "Every published number: its definition, formula, source, coverage, verification and audit status.",
};

function badge(status: string) {
  if (status === "pass") return "badge badge-ok";
  if (status === "fail") return "badge badge-warn";
  return "badge badge-neutral";
}

function formulaOf(formula: string | Record<string, string>) {
  if (typeof formula === "string") return <span>{formula}</span>;
  return (
    <dl className="metric-formula">
      {Object.entries(formula).map(([field, rule]) => (
        <div key={field}>
          <dt>{field}</dt>
          <dd>
            <code>{rule}</code>
          </dd>
        </div>
      ))}
    </dl>
  );
}

function valueOf(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") {
    return <code className="metric-value">{JSON.stringify(value)}</code>;
  }
  return <code>{String(value)}</code>;
}

export default function MetricsPage() {
  const manifest = getManifest();
  const registry = getMetricsRegistry();
  const audit = getMetricsAudit();
  const validation = getValidationReport();

  if (!registry || !audit) {
    return (
      <ContractPage surface="metrics" state="empty">
        <section className="page-head" data-contract="metrics.hero">
          <p className="eyebrow">Metrics and audit</p>
          <h1>Metrics and audit</h1>
          <p className="lede">
            No metric registry is published in this build. Run{" "}
            <code>uv run fitba publish</code> to generate the registry and audit.
          </p>
        </section>
      </ContractPage>
    );
  }

  const auditById = new Map(audit.metrics.map((entry) => [entry.id, entry]));
  const parameterAuditById = new Map(audit.parameters.map((entry) => [entry.id, entry]));
  const groups = new Map<string, typeof registry.metrics>();
  for (const metric of registry.metrics) {
    const group = groups.get(metric.home_surface) ?? [];
    group.push(metric);
    groups.set(metric.home_surface, group);
  }
  const parameterGroups = new Map<string, typeof registry.parameters>();
  for (const parameter of registry.parameters) {
    const domain = parameter.config_path.split(".")[0];
    const group = parameterGroups.get(domain) ?? [];
    group.push(parameter);
    parameterGroups.set(domain, group);
  }
  const metricsBlock = manifest?.metrics;
  const validationBlock = manifest?.validation;

  return (
    <ContractPage surface="metrics">
      <section className="page-head" data-contract="metrics.hero">
        <p className="eyebrow">Metrics and audit</p>
        <h1>Metrics and audit</h1>
        <p className="lede">
          Every published number has a registry entry: a definition, formula,
          inputs, basis, source layer, coverage tier and verification mode. The
          audit is regenerated from the published payloads on every publish.
        </p>
        <p className="fine-print">
          Registry {registry.registry_version}, reviewed {registry.reviewed}.
          Dataset <code>{audit.dataset_version}</code>, audited{" "}
          {new Date(audit.audited_at).toLocaleString("en-GB", {
            timeZone: "UTC",
            dateStyle: "medium",
            timeStyle: "short",
          })}{" "}
          UTC.
        </p>
      </section>

      <div className="grid metrics-summary" data-contract="metrics.summary">
        <div className="stat-tile">
          <span className="stat-label">Metrics</span>
          <span className="stat-value">
            {audit.summary.metrics_passed}/{audit.summary.metrics_total}
          </span>
          <span className="stat-note">
            {audit.summary.metrics_failed} failed
          </span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Parameters</span>
          <span className="stat-value">
            {audit.summary.parameters_passed}/{audit.summary.parameters_total}
          </span>
          <span className="stat-note">
            {audit.summary.parameters_failed} failed
          </span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Audit</span>
          <span className="stat-value">
            <span className={badge(audit.status)}>{audit.status}</span>
          </span>
          <span className="stat-note">
            {audit.summary.provenance_only} provenance-only
          </span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Validation</span>
          <span className="stat-value">
            <span className={badge(validation?.status ?? "not_run")}>
              {validation?.status ?? "not run"}
            </span>
          </span>
          <span className="stat-note">
            {validation?.checks.length ?? 0} checks · {validation?.errors ?? 0} errors
          </span>
        </div>
      </div>

      <section className="card" data-contract="metrics.audit">
        <div className="section-head">
          <div>
            <p className="eyebrow">Audit trail</p>
            <h2>Registry and audit artefacts</h2>
          </div>
        </div>
        <dl className="audit-facts">
          <div>
            <dt>Registry version</dt>
            <dd>{registry.registry_version}</dd>
          </div>
          <div>
            <dt>Registry checksum</dt>
            <dd>
              <code className="checksum">{registry.checksum}</code>
            </dd>
          </div>
          <div>
            <dt>Audit status</dt>
            <dd>
              <span className={badge(audit.status)}>{audit.status}</span>
            </dd>
          </div>
          <div>
            <dt>Audit checksum</dt>
            <dd>
              <code className="checksum">
                {metricsBlock?.audit_checksum ?? "—"}
              </code>
            </dd>
          </div>
          <div>
            <dt>Rows checked</dt>
            <dd className="num">{audit.summary.rows_checked}</dd>
          </div>
          <div>
            <dt>Fields checked</dt>
            <dd className="num">{audit.summary.fields_checked}</dd>
          </div>
          <div>
            <dt>Allowlist</dt>
            <dd>{audit.allowlist.status}</dd>
          </div>
          <div>
            <dt>Expires</dt>
            <dd>{audit.allowlist.expires ?? "—"}</dd>
          </div>
        </dl>
        <p className="fine-print">
          A pass proves the published values reproduce from the corpus where the
          mode is <code>recompute</code>, agree across payloads where it is{" "}
          <code>cross_surface</code>, and are present with an active source
          layer where it is <code>provenance_only</code>. It does not prove
          upstream provider accuracy or that a curated fact is true.
        </p>
        {validationBlock ? (
          <p className="fine-print">
            Validation: {validationBlock.status}, {validationBlock.checks}{" "}
            checks, {validationBlock.errors} errors,{" "}
            {validationBlock.warnings} warnings. Report checksum{" "}
            <code className="checksum">{validationBlock.checksum}</code>.
          </p>
        ) : null}
        {audit.errors.length ? (
          <ul>
            {audit.errors.slice(0, 10).map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="card" data-contract="metrics.registry">
        <div className="section-head">
          <div>
            <p className="eyebrow">Registry</p>
            <h2>Metric definitions</h2>
          </div>
          <span className="badge badge-neutral">
            {registry.metrics.length} metrics
          </span>
        </div>
        {[...groups.entries()].map(([surface, metrics]) => (
          <div key={surface} className="metric-group">
            <h3>
              <a href={surface}>{surface}</a>
            </h3>
            <div className="table-wrap">
              <table className="league-table metric-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Definition</th>
                    <th>Formula</th>
                    <th>Basis</th>
                    <th>Source</th>
                    <th>Coverage</th>
                    <th>Verification</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((metric) => {
                    const entry = auditById.get(metric.id);
                    return (
                      <tr
                        key={metric.id}
                        id={`metric-${metric.id.replaceAll(".", "-")}`}
                        data-contract="metrics.registry"
                      >
                        <td>
                          <code>{metric.id}</code>
                          <span className="fine-print">{metric.label}</span>
                        </td>
                        <td>{metric.description}</td>
                        <td>{formulaOf(metric.formula)}</td>
                        <td>{metric.basis}</td>
                        <td>{metric.source_layer}</td>
                        <td>{metric.coverage_tier}</td>
                        <td>
                          {metric.verification}
                          {entry ? (
                            <span className="fine-print">
                              {entry.rows_checked} rows ·{" "}
                              {entry.numeric_leaves} numeric leaves
                            </span>
                          ) : null}
                        </td>
                        <td>
                          <span className={badge(entry?.status ?? "not_run")}>
                            {entry?.status ?? "not run"}
                          </span>
                          {entry?.provenance_only ? (
                            <span className="fine-print">
                              present, not recomputed
                            </span>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </section>

      <section className="card" data-contract="metrics.parameters">
        <div className="section-head">
          <div>
            <p className="eyebrow">Parameters</p>
            <h2>Config-backed thresholds and weights</h2>
          </div>
          <span className="badge badge-neutral">
            {registry.parameters.length} parameters
          </span>
        </div>
        {[...parameterGroups.entries()].map(([domain, parameters]) => (
          <div key={domain} className="metric-group">
            <h3>{domain}</h3>
            <div className="table-wrap">
              <table className="league-table metric-table">
                <thead>
                  <tr>
                    <th>Parameter</th>
                    <th>Value</th>
                    <th>Unit</th>
                    <th>Used by</th>
                    <th>Config</th>
                    <th>Verification</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {parameters.map((parameter) => {
                    const entry = parameterAuditById.get(parameter.id);
                    return (
                      <tr
                        key={parameter.id}
                        id={`parameter-${parameter.id.replaceAll(".", "-")}`}
                        data-contract="metrics.parameters"
                      >
                        <td>
                          <code>{parameter.id}</code>
                          <span className="fine-print">{parameter.label}</span>
                        </td>
                        <td>{valueOf(parameter.value)}</td>
                        <td>{parameter.unit}</td>
                        <td>{parameter.used_by.join(", ")}</td>
                        <td>
                          <code>{parameter.config_path}</code>
                        </td>
                        <td>{parameter.verification}</td>
                        <td>
                          <span className={badge(entry?.status ?? "not_run")}>
                            {entry?.status ?? "not run"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </section>

      <section className="card" data-contract="metrics.method">
        <div className="section-head">
          <div>
            <p className="eyebrow">Method</p>
            <h2>Verification modes</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table className="league-table">
            <thead>
              <tr>
                <th>Mode</th>
                <th>What it proves</th>
                <th>What it does not prove</th>
                <th className="num">Metrics</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <code>recompute</code>
                </td>
                <td>Re-derived from published rows using the registered formula.</td>
                <td>Upstream provider accuracy.</td>
                <td className="num">
                  {audit.summary.verification_modes.recompute ?? 0}
                </td>
              </tr>
              <tr>
                <td>
                  <code>cross_surface</code>
                </td>
                <td>The same fact agrees across two payloads.</td>
                <td>Formula correctness.</td>
                <td className="num">
                  {audit.summary.verification_modes.cross_surface ?? 0}
                </td>
              </tr>
              <tr>
                <td>
                  <code>config_match</code>
                </td>
                <td>The registry parameter equals config.</td>
                <td>The config is analytically right.</td>
                <td className="num">
                  {audit.summary.verification_modes.config_match ?? 0}
                </td>
              </tr>
              <tr>
                <td>
                  <code>source_checksum</code>
                </td>
                <td>The curated source file is unchanged since audit.</td>
                <td>The source fact is true.</td>
                <td className="num">
                  {audit.summary.verification_modes.source_checksum ?? 0}
                </td>
              </tr>
              <tr>
                <td>
                  <code>provenance_only</code>
                </td>
                <td>
                  The value is present and its declared layer is active with
                  rows.
                </td>
                <td>Independent recomputation.</td>
                <td className="num">
                  {audit.summary.verification_modes.provenance_only ?? 0}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="fine-print">
          Coverage tiers: <code>event</code>, <code>match</code>,{" "}
          <code>curated</code>, <code>value_only</code>, <code>derived</code>{" "}
          and <code>unknown</code>. The most detailed tier an input supports is
          declared; a derived or inferred value is never labelled measured.
        </p>
        <p className="fine-print">
          A number is any value, rate, percentage, count, rank, range,
          confidence, coverage label, threshold or weight. Changing a formula,
          denominator, rounding mode, source, coverage tier, confidence rule or
          parameter needs owner approval, a metric/registry version bump and an
          entry in the metric changelog.
        </p>
      </section>

      <section className="card" data-contract="metrics.links">
        <div className="section-head">
          <div>
            <p className="eyebrow">Related</p>
            <h2>Sources, method and build status</h2>
          </div>
        </div>
        <ul className="link-list">
          <li>
            <a href="/status/">Build status and coverage</a>
          </li>
          <li>
            <a href="/methodology/">Methodology</a>
          </li>
          <li>
            <a href="/sources/">Sources and provenance</a>
          </li>
          <li>
            <a href="/about/">About the project</a>
          </li>
        </ul>
      </section>
    </ContractPage>
  );
}
