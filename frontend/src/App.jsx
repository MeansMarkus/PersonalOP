import { useMemo, useState } from "react";

const PROMPTS = [
  "Find backend software internships in NYC for summer 2027 and create my application checklist.",
  "Build a weekly networking plan for fintech engineering leads and alumni at 10 companies.",
  "Generate a prep plan for Stripe intern interviews including behavioral and debugging rounds."
];

const OP_MODES = [
  {
    id: "internships",
    label: "Internships",
    badge: "Primary",
    description: "Source matching roles, prioritize by fit, and keep your tracker current.",
    example:
      "Find backend software internships in NYC for summer 2027 and create my application checklist."
  },
  {
    id: "networking",
    label: "Networking",
    badge: "Growth",
    description: "Map target people, generate outreach tasks, and follow up automatically.",
    example:
      "Build a weekly networking plan for fintech engineering leads and alumni at 10 companies."
  },
  {
    id: "skills",
    label: "Skill Sprint",
    badge: "Prep",
    description: "Turn role requirements into a daily skill-building and project roadmap.",
    example:
      "Create a 4-week backend interview prep sprint focused on APIs, SQL, and system design."
  },
  {
    id: "interview",
    label: "Interview Ops",
    badge: "Execution",
    description: "Prepare focused question banks, mock sessions, and post-interview follow-up.",
    example:
      "Generate a prep plan for Stripe intern interviews including behavioral and debugging rounds."
  }
];

export default function App() {
  const [selectedMode, setSelectedMode] = useState(OP_MODES[0]);
  const [goal, setGoal] = useState(PROMPTS[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const canSubmit = useMemo(() => goal.trim().length >= 5 && !loading, [goal, loading]);

  async function onSubmit(event) {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/v1/tasks/plan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ goal: goal.trim() })
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const payload = await response.json();
      setResult(payload);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unexpected request error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-mist text-ink">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6 lg:py-12">
        <header className="rounded-3xl border border-white/70 bg-white/80 p-6 shadow-lg shadow-blue-100 backdrop-blur sm:p-8">
          <p className="font-heading text-xs uppercase tracking-[0.28em] text-tide">PersonalOP</p>
          <h1 className="mt-3 max-w-3xl font-heading text-3xl leading-tight sm:text-5xl">
            Turn one natural-language task into an executable plan
          </h1>
          <p className="mt-4 max-w-2xl font-body text-sm text-slate-700 sm:text-base">
            This first MVP slice accepts a single prompt, classifies the task, and returns a structured plan you can
            build on later.
          </p>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {OP_MODES.map((mode) => {
            const isActive = selectedMode.id === mode.id;

            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => {
                  setSelectedMode(mode);
                  if (!goal.trim()) {
                    setGoal(mode.example);
                  }
                }}
                className={`group rounded-2xl border p-4 text-left transition ${
                  isActive
                    ? "border-tide bg-white shadow-md shadow-blue-100"
                    : "border-slate-200 bg-white/80 hover:-translate-y-0.5 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-heading text-lg">{mode.label}</h3>
                  <span
                    className={`rounded-full px-2.5 py-1 font-body text-[11px] uppercase tracking-wide ${
                      isActive ? "bg-blue-100 text-tide" : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {mode.badge}
                  </span>
                </div>
                <p className="mt-2 font-body text-sm text-slate-600">{mode.description}</p>
              </button>
            );
          })}
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-md sm:p-8">
            <h2 className="font-heading text-2xl">Describe the task you want handled</h2>
            <p className="mt-2 font-body text-sm text-slate-600">
              Write one sentence in plain English. The backend will turn it into a task type, focus area, and action
              plan.
            </p>

            <form className="mt-5 space-y-4" onSubmit={onSubmit}>
              <label className="block">
                <span className="mb-2 block font-body text-sm text-slate-700">Natural-language task input</span>
                <textarea
                  className="h-32 w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 font-body text-sm outline-none transition focus:border-tide focus:ring-2 focus:ring-blue-200"
                  placeholder={selectedMode.example}
                  value={goal}
                  onChange={(event) => setGoal(event.target.value)}
                />
              </label>

              <div className="flex flex-wrap gap-2">
                {PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => {
                      setGoal(prompt);
                    }}
                    className="rounded-full border border-slate-300 bg-white px-3 py-1.5 font-body text-xs text-slate-700 transition hover:border-tide hover:text-tide"
                  >
                    Try example
                  </button>
                ))}
              </div>

              <button
                type="submit"
                disabled={!canSubmit}
                className="inline-flex items-center justify-center rounded-xl bg-coral px-5 py-3 font-heading text-sm uppercase tracking-wide text-white transition hover:brightness-95 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {loading ? "Analyzing..." : "Analyze Task"}
              </button>
            </form>

            {error ? (
              <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 font-body text-sm text-red-700">
                {error}
              </p>
            ) : null}

            {result ? (
              <div className="mt-6 grid gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 sm:grid-cols-2">
                <div>
                  <p className="font-body text-xs uppercase tracking-wide text-moss">Task type</p>
                  <p className="mt-1 font-heading text-base text-emerald-900">{result.intake.task_type}</p>
                </div>
                <div>
                  <p className="font-body text-xs uppercase tracking-wide text-moss">Focus area</p>
                  <p className="mt-1 font-heading text-base text-emerald-900">{result.intake.focus_area}</p>
                </div>
                <div className="sm:col-span-2">
                  <p className="font-body text-xs uppercase tracking-wide text-moss">Keywords</p>
                  <p className="mt-1 font-body text-sm text-emerald-900">
                    {result.intake.keywords.length > 0 ? result.intake.keywords.join(", ") : "No direct match yet"}
                  </p>
                </div>
                <div className="sm:col-span-2">
                  <p className="font-body text-xs uppercase tracking-wide text-moss">Next best action</p>
                  <p className="mt-1 font-body text-sm text-emerald-900">{result.intake.next_best_action}</p>
                </div>
              </div>
            ) : null}
          </article>

          <aside className="rounded-3xl border border-slate-200 bg-white p-6 shadow-md sm:p-8">
            <h2 className="font-heading text-2xl">Parsed execution plan</h2>
            <p className="mt-2 font-body text-sm text-slate-600">The planner converts your sentence into a simple task brief.</p>

            {!result ? (
              <div className="mt-5 space-y-3">
                {OP_MODES.map((mode) => (
                  <div key={mode.id} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-body text-sm">
                    <p className="font-semibold text-slate-800">{mode.label}</p>
                    <p className="mt-1 text-slate-600">{mode.description}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-5 space-y-3">
                <p className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-body text-sm text-slate-700">
                  {result.summary}
                </p>
                <ol className="space-y-3">
                  {result.steps.map((step) => (
                    <li key={step.id} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-body text-sm">
                      <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-tide text-xs text-white">
                        {step.id}
                      </span>
                      {step.description}
                    </li>
                  ))}
                </ol>
                <p className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-body text-sm text-slate-600">
                  Task ID: <span className="break-all font-mono text-slate-800">{result.task_id}</span>
                </p>
              </div>
            )}
          </aside>
        </section>
      </div>
    </main>
  );
}
