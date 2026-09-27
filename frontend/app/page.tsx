"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  GitBranch,
  Lightbulb,
  RefreshCw,
  ShieldAlert,
  Target,
  Trash2,
  Zap,
} from "lucide-react";

import Graph from "../components/Graph";

const API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

const STORAGE_KEY = "shadow-session-v4";
const LEGACY_STORAGE_KEYS = ["shadow-session-v3", "shadow-session-v2"];

// Keep form and panel styling self-contained in this page.
// This prevents the UI from breaking when global CSS classes are missing.
const fieldClass =
  "w-full box-border rounded-xl border border-[#293548] bg-[#080c12] px-3.5 py-3 text-sm text-white outline-none placeholder:text-[#536176] transition focus:border-[#8067ff] focus:ring-2 focus:ring-[#8067ff]/15";

const textareaClass =
  "w-full box-border rounded-xl border border-[#293548] bg-[#080c12] px-3.5 py-3 text-sm leading-5 text-white outline-none placeholder:text-[#536176] resize-y transition focus:border-[#8067ff] focus:ring-2 focus:ring-[#8067ff]/15";

const panelClass =
  "rounded-2xl border border-[#202b3b] bg-[#0b1017] shadow-[0_12px_40px_rgba(0,0,0,0.18)]";

type Tab =
  | "analysis"
  | "stress"
  | "counterfactual"
  | "interventions"
  | "perspectives"
  | "report"
  | "feedback";

type SessionData = {
  decision: string;
  objective: string;
  domain: string;
  context: string;
  parsed: any;
  result: any;
  tab: Tab;
};

const TABS: { id: Tab; label: string }[] = [
  { id: "analysis", label: "Analysis" },
  { id: "stress", label: "Stress" },
  { id: "counterfactual", label: "Counterfactual" },
  { id: "interventions", label: "Interventions" },
  { id: "perspectives", label: "Perspectives" },
  { id: "report", label: "Report" },
  { id: "feedback", label: "Feedback" },
];

export default function Page() {
  const [decision, setDecision] = useState("");
  const [objective, setObjective] = useState("");
  const [domain, setDomain] = useState("");
  const [context, setContext] = useState("");

  const [parsed, setParsed] = useState<any>(null);
  const [result, setResult] = useState<any>(null);

  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("analysis");
  const [hydrated, setHydrated] = useState(false);
  const [error, setError] = useState("");

  const variables = useMemo<Record<string, number>>(() => ({}), []);

  /*
   * =========================================================
   * RESTORE
   * =========================================================
   */

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);

      if (saved) {
        const session: Partial<SessionData> = JSON.parse(saved);

        setDecision(session.decision ?? "");
        setObjective(session.objective ?? "");
        setDomain(session.domain ?? "");
        setContext(session.context ?? "");
        setParsed(session.parsed ?? null);
        setResult(session.result ?? null);

        const validTabs: Tab[] = [
          "analysis",
          "stress",
          "counterfactual",
          "interventions",
          "perspectives",
          "report",
          "feedback",
        ];

        if (
          session.tab &&
          validTabs.includes(session.tab as Tab)
        ) {
          setTab(session.tab as Tab);
        }
      }
    } catch (err) {
      console.error("Failed to restore SHADOW session:", err);
    } finally {
      setHydrated(true);
    }
  }, []);

  /*
   * =========================================================
   * PERSIST
   * =========================================================
   */

  useEffect(() => {
    if (!hydrated) return;

    const session: SessionData = {
      decision,
      objective,
      domain,
      context,
      parsed,
      result,
      tab,
    };

    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(session),
      );
    } catch (err) {
      console.error("Failed to persist SHADOW session:", err);
    }
  }, [
    hydrated,
    decision,
    objective,
    domain,
    context,
    parsed,
    result,
    tab,
  ]);

  /*
   * =========================================================
   * API HELPER
   * =========================================================
   */

  const post = useCallback(
    async (path: string, body: unknown) => {
      const response = await fetch(`${API}${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const text = await response.text();

      let data: any = null;

      try {
        data = text ? JSON.parse(text) : null;
      } catch {
        data = text;
      }

      if (!response.ok) {
        throw new Error(
          typeof data === "string"
            ? data
            : data?.detail ||
                `Request failed with status ${response.status}`,
        );
      }

      return data;
    },
    [],
  );

  /*
   * =========================================================
   * ANALYZE
   * =========================================================
   */

  async function analyzeDecision() {
    if (!decision.trim() || loading) return;

    setLoading(true);
    setError("");
    setResult(null);
    setParsed(null);

    try {
      const parsedDecision = await post("/api/parse", {
        decision: decision.trim(),
        objective: objective.trim() || null,
        domain: domain.trim() || null,

        context: {
          notes: context.trim(),
        },

        constraints: [],
        variables,
      });

      setParsed(parsedDecision);

      const simulation = await post("/api/simulate", {
        parsed: parsedDecision,
        variable_overrides: variables,
        shocks: {},
      });

      setResult(simulation);
      setTab("analysis");
    } catch (err) {
      console.error("SHADOW analysis error:", err);

      setError(
        err instanceof Error
          ? err.message
          : "Could not connect to the SHADOW backend.",
      );
    } finally {
      setLoading(false);
    }
  }

  /*
   * =========================================================
   * CLEAR
   * =========================================================
   */

  function resetAnalysis() {
    // Full reset: clear the current analysis, all form inputs,
    // and every persisted session version so stale data cannot return.
    try {
      localStorage.removeItem(STORAGE_KEY);
      for (const key of LEGACY_STORAGE_KEYS) {
        localStorage.removeItem(key);
      }
    } catch (err) {
      console.error("Failed to clear SHADOW session:", err);
    }

    setLoading(false);
    setError("");
    setParsed(null);
    setResult(null);
    setTab("analysis");
    setDecision("");
    setObjective("");
    setDomain("");
    setContext("");
  }

  function clearSession() {
    resetAnalysis();
  }

  return (
    <main
      className="min-h-screen bg-[#05070b] text-white"
      style={{
        backgroundImage:
          "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
        backgroundSize: "28px 28px",
      }}
    >
      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="sticky top-0 z-30 border-b border-[#202a38] bg-[#070a0e]/95 backdrop-blur-xl">
        <div className="max-w-[1540px] mx-auto h-16 px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#9179ff] to-[#4f36d3] flex items-center justify-center font-black">
              S
            </div>

            <div>
              <div className="font-bold">SHADOW</div>

              <div className="text-[9px] text-[#7d8ba0] tracking-[.3em]">
                DECISION INTELLIGENCE ENGINE
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-[#8794a8]">
            <span className="w-2 h-2 rounded-full bg-[#45e4a0]" />

            <span>ENGINE READY</span>

            <span className="rounded-full border border-[#293548] bg-[#0b1017] px-2.5 py-1 text-[9px] font-semibold">
              DOMAIN AGNOSTIC
            </span>

            {result && (
              <button
                onClick={clearSession}
                className="flex items-center gap-1 hover:text-white transition"
              >
                <Trash2 size={13} />
                Clear
              </button>
            )}
          </div>
        </div>
      </header>

      {/* =====================================================
          MAIN
      ===================================================== */}

      <div className="max-w-[1540px] mx-auto p-6">
        {/* HERO */}

        <section className="py-8">
          <div className="text-xs tracking-[.28em] text-[#8976ff] font-bold">
            SEE · STRESS-TEST · SIMULATE · DECIDE
          </div>

          <h1 className="text-5xl font-black mt-2 tracking-tight">
            Before you act,
            <br />
            <span className="text-[#8873ff]">
              see the cascade.
            </span>
          </h1>

          <p className="text-[#8491a5] max-w-2xl mt-4 leading-6">
            Turn a real-world decision into a structured
            scenario, model dependencies, attack assumptions,
            explore counterfactuals and identify interventions.
          </p>
        </section>

        {/* =================================================
            CONTENT
        ================================================= */}

        <div className="grid lg:grid-cols-[390px_1fr] gap-5">
          {/* =================================================
              INPUT
          ================================================= */}

          <aside className={`${panelClass} p-5 h-fit`}>
            <div className="flex items-center gap-2 font-bold">
              <BrainCircuit
                size={17}
                className="text-[#8b75ff]"
              />

              New decision
            </div>

            {/* DECISION */}

            <FieldLabel>DECISION</FieldLabel>

            <textarea
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              placeholder="Describe the decision you are considering..."
              className={`${textareaClass} mt-2 min-h-[128px]`}
            />

            {/* OBJECTIVE */}

            <FieldLabel>
              OBJECTIVE (OPTIONAL)
            </FieldLabel>

            <input
              value={objective}
              onChange={(e) =>
                setObjective(e.target.value)
              }
              placeholder="What outcome are you trying to achieve?"
              className={`${fieldClass} mt-2`}
            />

            {/* DOMAIN */}

            <FieldLabel>
              DOMAIN (OPTIONAL)
            </FieldLabel>

            <input
              value={domain}
              onChange={(e) =>
                setDomain(e.target.value)
              }
              placeholder="e.g. logistics, energy, healthcare..."
              className={`${fieldClass} mt-2`}
            />

            {/* CONTEXT */}

            <FieldLabel>CONTEXT / DATA</FieldLabel>

            <textarea
              value={context}
              onChange={(e) =>
                setContext(e.target.value)
              }
              placeholder="Known facts, assumptions, constraints, data notes..."
              className={`${textareaClass} mt-2 min-h-[112px]`}
            />

            {/* ERROR */}

            {error && (
              <div className="mt-4 p-3 rounded-xl border border-red-900/50 bg-red-950/20 text-xs text-red-400">
                {error}
              </div>
            )}

            {/* ANALYZE */}

            <button
              onClick={analyzeDecision}
              disabled={
                loading ||
                !decision.trim()
              }
              className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#8064ff] to-[#5e3ed8] px-4 py-3 text-sm font-bold text-white shadow-lg shadow-[#6046e5]/20 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-45"
            >
              {loading ? (
                <>
                  <RefreshCw
                    size={16}
                    className="animate-spin"
                  />

                  Building scenario...
                </>
              ) : (
                <>
                  <Zap size={16} />

                  Analyze decision
                </>
              )}
            </button>

            {(result || decision || objective || domain || context) && (
              <button
                type="button"
                onClick={resetAnalysis}
                disabled={loading}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl border border-[#293548] bg-[#0a0f16] px-4 py-2.5 text-sm font-semibold text-[#aab4c4] transition hover:border-[#8067ff] hover:text-white disabled:cursor-not-allowed disabled:opacity-45"
              >
                <RefreshCw size={15} />
                Reset analysis
              </button>
            )}

            {/* DISCLAIMER */}

            <div className="mt-4 p-3 rounded-xl bg-[#0a0f16] border border-[#202a38] text-[11px] leading-5 text-[#7e8ba0]">
              Unknown facts remain explicit assumptions.
              SHADOW does not silently turn missing
              information into facts.
            </div>
          </aside>

          {/* =================================================
              RESULTS
          ================================================= */}

          <section>
            {!result ? (
              <Welcome />
            ) : (
              <>
                {/* METRICS */}

                <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                  <Metric
                    title="IMPACT"
                    value={result.impact_score}
                  />

                  <Metric
                    title="RISK"
                    value={result.risk_score}
                  />

                  <Metric
                    title="CASCADE"
                    value={`${result.cascade_depth ?? 0} levels`}
                    raw
                  />

                  <Metric
                    title="AFFECTED"
                    value={`${result.affected_entities ?? 0} nodes`}
                    raw
                  />
                </div>

                {/* TABS */}

                <div className="flex gap-1 border-b border-[#202a38] mt-5 overflow-x-auto">
                  {TABS.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setTab(item.id)}
                      className={`px-4 py-3 text-xs font-semibold whitespace-nowrap transition ${
                        tab === item.id
                          ? "text-white border-b-2 border-[#7d61ff]"
                          : "text-[#748196] hover:text-white"
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>

                {/* CONTENT */}

                {tab === "analysis" && (
                  <Analysis result={result} />
                )}

                {tab === "stress" && (
                  <Stress result={result} />
                )}

                {tab === "counterfactual" && (
                  <Counterfactual result={result} />
                )}

                {tab === "interventions" && (
                  <Interventions result={result} />
                )}

                {tab === "perspectives" && (
                  <Perspectives result={result} />
                )}

                {tab === "report" && (
                  <Report result={result} />
                )}

                {tab === "feedback" && (
                  <Feedback
                    result={result}
                    post={post}
                  />
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

/* =========================================================
   FIELD LABEL
========================================================= */

function FieldLabel({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <label className="block text-[10px] tracking-widest text-[#748196] mt-5">
      {children}
    </label>
  );
}

/* =========================================================
   WELCOME
========================================================= */

function Welcome() {
  const items = [
    ["Parse", "Extract entities & assumptions"],
    ["Simulate", "Propagate dependencies"],
    ["Stress", "Attack fragile assumptions"],
  ];

  return (
    <div className={`${panelClass} min-h-[520px] flex items-center justify-center text-center p-6 sm:p-10`}>
      <div className="max-w-xl">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-[#17122d] border border-[#382c72] flex items-center justify-center">
          <GitBranch className="text-[#8b75ff]" />
        </div>

        <h2 className="text-3xl font-black mt-6">
          Model a decision, not a demo.
        </h2>

        <p className="text-[#7e8ba0] mt-3 leading-7">
          Enter any real scenario. SHADOW builds its
          dependency graph from the supplied decision and
          context instead of relying on a predefined
          industry scenario.
        </p>

        <div className="grid grid-cols-3 gap-3 mt-8 text-left">
          {items.map(([title, description]) => (
            <div
              key={title}
              className="p-4 rounded-xl bg-[#0b1017] border border-[#202a38]"
            >
              <b className="text-sm">
                {title}
              </b>

              <div className="text-xs text-[#748196] mt-2">
                {description}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* =========================================================
   METRIC
========================================================= */

function Metric({
  title,
  value,
  raw = false,
}: {
  title: string;
  value: any;
  raw?: boolean;
}) {
  const display =
    typeof value === "number"
      ? value.toFixed(2)
      : value ?? "—";

  return (
    <div className={`${panelClass} rounded-xl p-4`}>
      <div className="text-[10px] tracking-widest text-[#718096]">
        {title}
      </div>

      <div className="text-2xl font-black mt-2">
        {display}

        {!raw && (
          <span className="text-xs text-[#718096]">
            {" "}
            /100
          </span>
        )}
      </div>
    </div>
  );
}

/* =========================================================
   ANALYSIS
========================================================= */

function Analysis({
  result,
}: {
  result: any;
}) {
  return (
    <div className="space-y-5 mt-5">
      <div className={`${panelClass} overflow-hidden`}>
        <div className="p-4 border-b border-[#202a38] flex items-center justify-between">
          <div>
            <b>Dynamic consequence graph</b>

            <div className="text-xs text-[#718096] mt-1">
              Generated from the supplied scenario.
            </div>
          </div>

          <span className="rounded-full border border-[#382c72] bg-[#120e26] px-2.5 py-1 text-[9px] font-semibold text-[#8d7aff]">
            SIMULATION
          </span>
        </div>

        <div className="h-[470px]">
          <Graph graph={result?.graph} />
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <Card
          title="Uncertainty"
          icon={<AlertTriangle />}
        >
          <div className="text-2xl font-black">
            {result?.uncertainty?.p10 ?? "—"} —{" "}
            {result?.uncertainty?.p90 ?? "—"}
          </div>

          <p className="text-xs text-[#718096] mt-2">
            10th–90th percentile modeled impact range.
          </p>
        </Card>

        <Card
          title="Critical paths"
          icon={<GitBranch />}
        >
          <div className="text-2xl font-black">
            {result?.critical_paths?.length ?? 0}
          </div>

          <p className="text-xs text-[#718096] mt-2">
            Dependency chains detected by the graph engine.
          </p>
        </Card>

        <Card
          title="Explanation"
          icon={<Lightbulb />}
        >
          <p className="text-sm leading-6 text-[#aab4c4]">
            {result?.explanation ||
              "No explanation was returned by the simulation."}
          </p>
        </Card>
      </div>
    </div>
  );
}

/* =========================================================
   STRESS
========================================================= */

function Stress({
  result,
}: {
  result: any;
}) {
  const tests = Array.isArray(
    result?.stress_tests,
  )
    ? result.stress_tests
    : [];

  if (!tests.length) {
    return <EmptyState text="No stress tests were returned." />;
  }

  return (
    <div className="grid md:grid-cols-2 gap-4 mt-5">
      {tests.map((test: any, index: number) => (
        <Card
          key={test.id ?? index}
          title={
            test.title ??
            `Stress test ${index + 1}`
          }
          icon={<ShieldAlert />}
        >
          <div className="text-3xl font-black">
            {Number(
              test.impact_score ?? 0,
            ).toFixed(1)}

            <span className="text-xs text-[#718096]">
              {" "}
              impact
            </span>
          </div>

          <div className="mt-4 text-xs text-[#aab4c4] leading-5">
            {Array.isArray(test.findings)
              ? test.findings.join(" ")
              : test.findings ||
                "No findings returned."}
          </div>

          {Array.isArray(
            test.critical_path,
          ) &&
            test.critical_path.length > 0 && (
              <div className="mt-4 text-[10px] text-[#718096]">
                Critical path:{" "}
                {test.critical_path.join(
                  " → ",
                )}
              </div>
            )}
        </Card>
      ))}
    </div>
  );
}

/* =========================================================
   COUNTERFACTUAL
========================================================= */

function Counterfactual({
  result,
}: {
  result: any;
}) {
  const base = Number(
    result?.impact_score ?? 0,
  );

  const risk = Number(
    result?.risk_score ?? 0,
  );

  const rows = [
    {
      name: "Baseline",
      impact: base,
      risk,
      description:
        "Current modeled scenario.",
    },
    {
      name: "Reduced scope",
      impact: Math.max(0, base * 0.75),
      risk: Math.max(0, risk * 0.75),
      description:
        "Illustrative reduction in modeled exposure.",
    },
    {
      name: "Additional redundancy",
      impact: Math.max(0, base * 0.6),
      risk: Math.max(0, risk * 0.6),
      description:
        "Illustrative reduction through added resilience.",
    },
  ];

  return (
    <div className={`${panelClass} mt-5 overflow-hidden`}>
      <div className="p-5 border-b border-[#202a38]">
        <b>Counterfactual workspace</b>

        <p className="text-xs text-[#718096] mt-1">
          Compare alternate modeled assumptions
          against the baseline.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-[#718096] bg-[#0a0f16]">
            <tr>
              <th className="p-4 text-left">
                Scenario
              </th>

              <th className="text-left">
                Impact
              </th>

              <th className="text-left">
                Risk
              </th>

              <th className="text-left">
                Description
              </th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row) => (
              <tr
                key={row.name}
                className="border-t border-[#202a38]"
              >
                <td className="p-4 font-semibold">
                  {row.name}
                </td>

                <td>
                  {row.impact.toFixed(1)}
                </td>

                <td>
                  {row.risk.toFixed(1)}
                </td>

                <td className="pr-4 text-xs text-[#718096]">
                  {row.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-4 text-[10px] text-[#718096] border-t border-[#202a38]">
        These values are illustrative transformations
        of the current model output, not independently
        simulated alternative scenarios.
      </div>
    </div>
  );
}

/* =========================================================
   INTERVENTIONS
========================================================= */

function Interventions({
  result,
}: {
  result: any;
}) {
  const interventions = Array.isArray(
    result?.interventions,
  )
    ? result.interventions
    : [];

  if (!interventions.length) {
    return (
      <EmptyState text="No interventions were returned." />
    );
  }

  return (
    <div className="grid md:grid-cols-2 gap-4 mt-5">
      {interventions.map(
        (item: any, index: number) => (
          <Card
            key={item.id ?? index}
            title={
              item.title ??
              `Intervention ${index + 1}`
            }
            icon={<Target />}
          >
            <p className="text-sm text-[#aab4c4] leading-6">
              {item.rationale ||
                "No rationale provided."}
            </p>

            <div className="grid grid-cols-3 gap-2 mt-4 text-xs">
              <Stat
                a="Impact ↓"
                b={`${Number(
                  item.estimated_impact_reduction ??
                    0,
                ).toFixed(0)}%`}
              />

              <Stat
                a="Feasibility"
                b={`${Number(
                  item.feasibility ?? 0,
                ).toFixed(0)}%`}
              />

              <Stat
                a="Score"
                b={Number(
                  item.score ?? 0,
                ).toFixed(0)}
              />
            </div>
          </Card>
        ),
      )}
    </div>
  );
}

/* =========================================================
   PERSPECTIVES
========================================================= */

function Perspectives({
  result,
}: {
  result: any;
}) {
  const perspectives = Array.isArray(
    result?.perspectives,
  )
    ? result.perspectives
    : [];

  if (!perspectives.length) {
    return (
      <EmptyState text="No perspectives were returned." />
    );
  }

  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mt-5">
      {perspectives.map(
        (item: any, index: number) => (
          <Card
            key={item.name ?? index}
            title={
              item.name ??
              `Perspective ${index + 1}`
            }
            icon={<Activity />}
          >
            <div className="text-3xl font-black">
              {Number(
                item.score ?? 0,
              ).toFixed(0)}
            </div>

            <p className="text-xs text-[#7d8aa0] mt-2 leading-5">
              {Array.isArray(item.findings)
                ? item.findings.join(" ")
                : item.findings ||
                  "No findings returned."}
            </p>
          </Card>
        ),
      )}
    </div>
  );
}

/* =========================================================
   REPORT
========================================================= */

function Report({
  result,
}: {
  result: any;
}) {
  const metrics = Array.isArray(
    result?.metrics,
  )
    ? result.metrics
    : [];

  return (
    <div className={`${panelClass} mt-5 p-5 sm:p-6`}>
      <div className="flex justify-between gap-4">
        <div>
          <div className="text-xs tracking-widest text-[#8873ff]">
            DECISION REPORT
          </div>

          <h2 className="text-2xl font-black mt-2">
            SHADOW analysis
          </h2>
        </div>

        <span className="h-fit rounded-full border border-[#293548] bg-[#080c12] px-3 py-1.5 text-[10px] font-semibold text-[#aab4c4]">
          HUMAN REVIEW REQUIRED
        </span>
      </div>

      <p className="text-[#aab4c4] mt-5 leading-7">
        {result?.explanation ||
          "No report explanation was returned."}
      </p>

      {metrics.length > 0 && (
        <div className="grid md:grid-cols-3 gap-3 mt-6">
          {metrics.map(
            (metric: any, index: number) => (
              <Stat
                key={metric.name ?? index}
                a={metric.name ?? "Metric"}
                b={`${metric.value ?? "—"} ${
                  metric.unit ?? ""
                }`}
              />
            ),
          )}
        </div>
      )}
    </div>
  );
}

/* =========================================================
   FEEDBACK
========================================================= */

function Feedback({
  result,
  post,
}: {
  result: any;
  post: (
    path: string,
    body: unknown,
  ) => Promise<any>;
}) {
  const feedbackKey = `shadow-feedback-${
    result?.scenario_id ?? "current"
  }`;

  const [actual, setActual] = useState("");
  const [notes, setNotes] = useState("");

  const [done, setDone] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  /*
   * Restore feedback for this scenario.
   */

  useEffect(() => {
    try {
      const saved = localStorage.getItem(
        feedbackKey,
      );

      if (!saved) {
        setActual("");
        setNotes("");
        setDone(false);
        return;
      }

      const data = JSON.parse(saved);

      setActual(data.actual ?? "");
      setNotes(data.notes ?? "");
      setDone(Boolean(data.done));
    } catch {
      setActual("");
      setNotes("");
      setDone(false);
    }
  }, [feedbackKey]);

  async function recordOutcome() {
    setError("");
    setDone(false);

    if (!actual.trim()) {
      setError(
        "Enter the actual numeric result.",
      );
      return;
    }

    const numericValue = Number(actual);

    if (!Number.isFinite(numericValue)) {
      setError(
        "Actual result must be a valid number.",
      );
      return;
    }

    if (!result?.scenario_id) {
      setError(
        "This scenario has no scenario ID.",
      );
      return;
    }

    setSaving(true);

    try {
      await post("/api/feedback", {
        scenario_id: result.scenario_id,

        predicted: {
          impact: Number(
            result.impact_score ?? 0,
          ),
          risk: Number(
            result.risk_score ?? 0,
          ),
        },

        actual: {
          metric: numericValue,
        },

        notes: notes.trim(),
      });

      localStorage.setItem(
        feedbackKey,
        JSON.stringify({
          actual,
          notes,
          done: true,
        }),
      );

      setDone(true);
    } catch (err) {
      console.error(
        "Feedback error:",
        err,
      );

      setError(
        err instanceof Error
          ? err.message
          : "Could not record the outcome.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={`${panelClass} mt-5 max-w-2xl p-5 sm:p-6`}>
      <div className="flex items-center gap-2">
        <RefreshCw
          size={17}
          className="text-[#8873ff]"
        />

        <b>Outcome feedback</b>
      </div>

      <p className="text-xs text-[#718096] mt-2">
        Record what actually happened so the
        prediction can be evaluated later.
      </p>

      <input
        type="number"
        step="any"
        value={actual}
        onChange={(e) => {
          setActual(e.target.value);
          setDone(false);
          setError("");
        }}
        placeholder="Actual metric, e.g. 120"
        className={`${fieldClass} mt-5`}
      />

      <textarea
        value={notes}
        onChange={(e) => {
          setNotes(e.target.value);
          setDone(false);
          setError("");
        }}
        placeholder="What happened? What assumptions were wrong?"
        className={`${textareaClass} mt-3 min-h-[112px]`}
      />

      {error && (
        <div className="mt-3 p-3 rounded-xl border border-red-900/50 bg-red-950/20 text-xs text-red-400">
          {error}
        </div>
      )}

      {done && (
        <div className="mt-3 p-3 rounded-xl border border-green-900/50 bg-green-950/20 text-xs text-green-400">
          Outcome recorded successfully.
        </div>
      )}

      <button
        className="mt-4 rounded-xl bg-gradient-to-r from-[#8064ff] to-[#5e3ed8] px-4 py-2.5 text-sm font-bold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        onClick={recordOutcome}
        disabled={saving}
      >
        {saving
          ? "Recording..."
          : done
            ? "Recorded"
            : "Record outcome"}
      </button>
    </div>
  );
}

/* =========================================================
   CARD
========================================================= */

function Card({
  title,
  icon,
  children,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={`${panelClass} p-5`}>
      <div className="flex items-center gap-2 text-sm font-bold mb-4">
        {icon}
        <span>{title}</span>
      </div>

      {children}
    </div>
  );
}

/* =========================================================
   STAT
========================================================= */

function Stat({
  a,
  b,
}: {
  a: string;
  b: ReactNode;
}) {
  return (
    <div className="rounded-xl bg-[#0a0f16] border border-[#202a38] p-3">
      <div className="text-[10px] text-[#718096]">
        {a}
      </div>

      <b className="text-sm">
        {b}
      </b>
    </div>
  );
}

/* =========================================================
   EMPTY STATE
========================================================= */

function EmptyState({
  text,
}: {
  text: string;
}) {
  return (
    <div className={`${panelClass} mt-5 p-8 text-center text-sm text-[#718096]`}>
      {text}
    </div>
  );
}