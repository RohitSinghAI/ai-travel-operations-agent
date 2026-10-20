import { useState } from "react";
import LiveTouristPlaces from "./components/LiveTouristPlaces.jsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const initialForm = {
  source: "Hyderabad",
  destination: "Goa",
  days: 3,
  travelers: 2,
  budget: 15000,
  check_in: "2026-11-10",
  check_out: "2026-11-13",
  preferences: "beaches, local food",
};

const destinations = [
  {
    name: "Goa",
    category: "Beach escape",
    description:
      "Discover scenic beaches, Portuguese heritage and local cuisine.",
    image:
      "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=900&q=80",
  },
  {
    name: "Manali",
    category: "Mountain retreat",
    description:
      "Explore mountain landscapes, pine forests and peaceful valleys.",
    image:
      "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=900&q=80",
  },
  {
    name: "Jaipur",
    category: "Culture & heritage",
    description:
      "Experience historic forts, colorful markets and Rajasthani food.",
    image:
      "https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?auto=format&fit=crop&w=900&q=80",
  },
];

const inputClass =
  "mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-100";

function Field({ label, children }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      {children}
    </label>
  );
}

function formatErrorDetail(data, status) {
  if (typeof data === "string" && data.trim()) return data;

  const detail = data?.detail ?? data?.message ?? data?.error;
  if (typeof detail === "string") return detail;
  if (detail != null) {
    try {
      return JSON.stringify(detail, null, 2);
    } catch {
      return String(detail);
    }
  }

  return `Request failed (${status}). The server did not return an error message.`;
}


export default function App() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  };

  const generatePlan = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    if (new Date(form.check_out) <= new Date(form.check_in)) {
      setError("Check-out date must be after the check-in date.");
      setLoading(false);
      return;
    }

    try {
      // Vite proxies /plan to the FastAPI backend on port 8000.
      const response = await fetch("/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          days: Number(form.days),
          travelers: Number(form.travelers),
          budget: Number(form.budget),

          // Convert comma-separated text into a list
          preferences: form.preferences
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });

      const contentType = response.headers.get("content-type") || "";
      let data;

      if (contentType.includes("application/json")) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        throw new Error(formatErrorDetail(data, response.status));
      }

      if (data == null || typeof data !== "object") {
        throw new Error("The backend returned an unexpected response.");
      }

      setResult(data);
    } catch (err) {
      console.error("Travel plan request failed:", err);
      setError(
        err instanceof TypeError
          ? "Cannot connect to the backend. Confirm FastAPI is running at http://127.0.0.1:8000 and the Vite /plan proxy is configured."
          : err.message || "Something went wrong while generating your trip."
      );
    } finally {
      setLoading(false);
    }
  };

  const livePlacesData =
    result?.tool_data?.live_places ??
    result?.live_places ??
    null;
  const itinerary =
    result?.itinerary ??
    result?.plan ??
    result?.travel_plan ??
    null;

  return (
    <div className="min-h-screen text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 lg:px-8">
          <a href="#" className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-600 text-2xl text-white shadow-lg shadow-indigo-200">
              ✈
            </span>
            <span>
              <span className="block text-lg font-black tracking-tight">
                Travel<span className="text-indigo-600">AI</span>
              </span>
              <span className="block text-xs text-slate-500">
                Smart Travel Planner
              </span>
            </span>
          </a>

          <div className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a className="transition hover:text-indigo-600" href="#planner">
              Plan a trip
            </a>
            <a
              className="transition hover:text-indigo-600"
              href="#destinations"
            >
              Destinations
            </a>
            <a className="transition hover:text-indigo-600" href="#results">
              Your itinerary
            </a>
          </div>

          <a
            href="#planner"
            className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-200 transition hover:bg-indigo-700"
          >
            Start planning →
          </a>
        </nav>
      </header>

      <main>
        <section className="relative overflow-hidden bg-slate-950">
          <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-slate-950/90 to-indigo-950/50" />
          <div className="absolute -right-20 -top-32 h-96 w-96 rounded-full bg-indigo-500/20 blur-3xl" />

          <div className="relative mx-auto grid max-w-7xl items-center gap-10 px-5 py-16 md:py-24 lg:grid-cols-[1.15fr_0.85fr] lg:px-8">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-xs font-semibold tracking-wide text-indigo-200">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                YOUR PERSONAL AI TRAVEL ASSISTANT
              </span>

              <h1 className="mt-7 max-w-2xl text-4xl font-black leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl">
                Your next adventure,
                <span className="block text-indigo-400">
                  intelligently planned.
                </span>
              </h1>

              <p className="mt-6 max-w-xl text-base leading-8 text-slate-300 sm:text-lg">
                Plan memorable trips with AI-powered itineraries, destination
                discovery and budget estimates—all in one place.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <a
                  href="#planner"
                  className="rounded-xl bg-indigo-500 px-6 py-3.5 font-bold text-white transition hover:bg-indigo-400"
                >
                  Create my trip <span className="ml-2">→</span>
                </a>
                <a
                  href="#destinations"
                  className="rounded-xl border border-white/20 px-6 py-3.5 font-semibold text-white transition hover:bg-white/10"
                >
                  Explore destinations
                </a>
              </div>

              <div className="mt-10 flex flex-wrap gap-x-7 gap-y-3 text-sm text-slate-300">
                <span>✓ Personalized itinerary</span>
                <span>✓ Budget planning</span>
                <span>✓ Place discovery</span>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-md">
              <img
                src="https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1000&q=85"
                alt="Beautiful mountain lake travel destination"
                className="h-80 w-full rounded-3xl object-cover shadow-2xl sm:h-96"
              />
              <div className="absolute -bottom-5 left-4 right-4 rounded-2xl border border-white/60 bg-white/95 p-4 shadow-xl backdrop-blur sm:left-8 sm:right-8">
                <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
                  Your next journey
                </p>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <div>
                    <p className="font-bold">Made for your budget</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Destinations · Activities · Planning
                    </p>
                  </div>
                  <span className="text-3xl">🌍</span>
                </div>
              </div>
            </div>
          </div>
        </section>


        <section
          id="planner"
          className="mx-auto max-w-7xl scroll-mt-24 px-5 py-16 lg:px-8"
        >
          <div className="mb-8">
            <p className="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">
              Start your journey
            </p>
            <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
              Plan your perfect trip
            </h2>
            <p className="mt-3 max-w-2xl leading-7 text-slate-500">
              Tell us where you want to go. Customize your travel details and
              generate a plan using your connected AI backend.
            </p>
          </div>

          <div className="grid items-start gap-8 lg:grid-cols-[0.85fr_1.15fr]">
            <form
              onSubmit={generatePlan}
              className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8"
            >
              <div className="mb-7 flex items-center gap-3">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-xl">
                  🧭
                </span>
                <div>
                  <h3 className="text-xl font-extrabold">Trip details</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Customize your journey
                  </p>
                </div>
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Starting city">
                  <input
                    required
                    name="source"
                    value={form.source}
                    onChange={updateField}
                    placeholder="e.g. Hyderabad"
                    className={inputClass}
                  />
                </Field>

                <Field label="Destination city">
                  <input
                    required
                    name="destination"
                    value={form.destination}
                    onChange={updateField}
                    placeholder="e.g. Goa"
                    className={inputClass}
                  />
                </Field>

                <Field label="Duration (days)">
                  <input
                    required
                    type="number"
                    min="1"
                    max="30"
                    name="days"
                    value={form.days}
                    onChange={updateField}
                    className={inputClass}
                  />
                </Field>

                <Field label="Travelers">
                  <input
                    required
                    type="number"
                    min="1"
                    max="50"
                    name="travelers"
                    value={form.travelers}
                    onChange={updateField}
                    className={inputClass}
                  />
                </Field>

                <Field label="Total budget (₹)">
                  <input
                    required
                    type="number"
                    min="1"
                    name="budget"
                    value={form.budget}
                    onChange={updateField}
                    className={inputClass}
                  />
                </Field>

                <Field label="Check-in">
                  <input
                    required
                    type="date"
                    name="check_in"
                    value={form.check_in}
                    onChange={updateField}
                    className={inputClass}
                  />
                </Field>

                <Field label="Check-out">
                  <input
                    required
                    type="date"
                    name="check_out"
                    value={form.check_out}
                    min={form.check_in}
                    onChange={updateField}
                    className={inputClass}
                  />
                </Field>

                <Field label="Travel preferences">
                  <input
                    name="preferences"
                    value={form.preferences}
                    onChange={updateField}
                    placeholder="Beaches, food, adventure"
                    className={inputClass}
                  />
                </Field>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-7 flex w-full items-center justify-center gap-3 rounded-xl bg-indigo-600 px-5 py-4 font-bold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                    Creating your itinerary...
                  </>
                ) : (
                  <>✦ Generate travel plan</>
                )}
              </button>

              <p className="mt-4 text-center text-xs leading-6 text-slate-500">
                Prices may be estimates or sample data. Live availability and
                bookings are not guaranteed.
              </p>
            </form>

            <div id="results" className="scroll-mt-24">
              {!result && !loading && !error && (
                <div className="flex min-h-[440px] flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center">
                  <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-indigo-50 text-4xl">
                    🗺️
                  </div>
                  <h3 className="mt-6 text-2xl font-extrabold">
                    Your adventure starts here
                  </h3>
                  <p className="mt-3 max-w-sm leading-7 text-slate-500">
                    Enter your trip details and generate a personalized travel
                    plan with your AI backend.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {[
                      "Day-by-day itinerary",
                      "Budget breakdown",
                      "Live places",
                    ].map((item) => (
                      <span
                        key={item}
                        className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-600"
                      >
                        ✓ {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {loading && (
                <div className="flex min-h-[440px] flex-col items-center justify-center rounded-3xl border border-slate-200 bg-white p-8 text-center">
                  <div className="h-12 w-12 animate-spin rounded-full border-4 border-indigo-100 border-t-indigo-600" />
                  <h3 className="mt-5 text-xl font-bold">
                    Planning your adventure...
                  </h3>
                  <p className="mt-2 text-sm text-slate-500">
                    Your backend is preparing the trip details.
                  </p>
                </div>
              )}

              {error && (
                <div
                  role="alert"
                  className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800"
                >
                  <h3 className="font-bold">Unable to generate your trip</h3>
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">
                    {error}
                  </p>
                  <p className="mt-3 text-xs">
                    Check the FastAPI terminal for the detailed traceback and
                    confirm the /plan endpoint is available.
                  </p>
                </div>
              )}

              {result && (
                <div className="space-y-5">
                  <div className="rounded-3xl bg-indigo-600 p-6 text-white sm:p-8">
                    <p className="text-sm font-semibold text-indigo-200">
                      YOUR TRAVEL PLAN
                    </p>
                    <h3 className="mt-3 text-2xl font-black">
                      {form.source} → {form.destination}
                    </h3>
                    <p className="mt-3 text-sm text-indigo-100">
                      {form.days} days · {form.travelers} travelers · ₹
                      {Number(form.budget).toLocaleString("en-IN")} budget
                    </p>
                  </div>
                  <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-7">
                    <h3 className="text-xl font-extrabold">
                      Generated itinerary
                    </h3>

                    <div className="mt-5 space-y-4 text-sm leading-7 text-slate-600">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1: ({ children }) => (
                            <h1 className="mb-4 text-2xl font-black text-slate-900">
                              {children}
                            </h1>
                          ),
                          h2: ({ children }) => (
                            <h2 className="mb-3 mt-6 text-xl font-bold text-slate-900">
                              {children}
                            </h2>
                          ),
                          h3: ({ children }) => (
                            <h3 className="mb-2 mt-4 text-lg font-bold text-slate-800">
                              {children}
                            </h3>
                          ),
                          p: ({ children }) => (
                            <p className="mb-3 leading-7">{children}</p>
                          ),
                          ul: ({ children }) => (
                            <ul className="mb-4 list-disc space-y-2 pl-6">
                              {children}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="mb-4 list-decimal space-y-2 pl-6">
                              {children}
                            </ol>
                          ),
                          li: ({ children }) => <li>{children}</li>,
                          strong: ({ children }) => (
                            <strong className="font-bold text-slate-900">
                              {children}
                            </strong>
                          ),
                          table: ({ children }) => (
                            <div className="my-4 overflow-x-auto">
                              <table className="w-full border-collapse text-left text-sm">
                                {children}
                              </table>
                            </div>
                          ),
                          th: ({ children }) => (
                            <th className="border border-slate-200 bg-slate-50 p-3 font-bold text-slate-800">
                              {children}
                            </th>
                          ),
                          td: ({ children }) => (
                            <td className="border border-slate-200 p-3">{children}</td>
                          ),
                          hr: () => <hr className="my-6 border-slate-200" />,
                        }}
                      >
                        {typeof itinerary === "string"
                          ? itinerary
                          : JSON.stringify(itinerary ?? result, null, 2)}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {result.budget_breakdown && (
                    <div className="rounded-3xl border border-slate-200 bg-white p-5 sm:p-7">
                      <h3 className="text-xl font-extrabold">
                        Budget breakdown
                      </h3>
                      <pre className="mt-4 overflow-x-auto whitespace-pre-wrap break-words font-sans text-sm leading-7 text-slate-600">
                        {JSON.stringify(result.budget_breakdown, null, 2)}
                      </pre>
                    </div>
                  )}

                  <LiveTouristPlaces
                    liveData={livePlacesData}
                    loading={false}
                    error=""
                  />
                </div>
              )}
            </div>
          </div>
        </section>

        <section
          id="destinations"
          className="mx-auto max-w-7xl scroll-mt-24 px-5 pb-16 lg:px-8"
        >
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">
                Find your inspiration
              </p>
              <h2 className="mt-3 text-3xl font-black tracking-tight">
                Popular destinations
              </h2>
              <p className="mt-2 text-slate-500">
                Explore ideas for your next adventure.
              </p>
            </div>
            <span className="rounded-full bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-700">
              Explore India
            </span>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {destinations.map((destination) => (
              <article
                key={destination.name}
                className="group overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-xl"
              >
                <div className="relative overflow-hidden">
                  <img
                    src={destination.image}
                    alt={destination.name}
                    loading="lazy"
                    className="h-56 w-full object-cover transition duration-500 group-hover:scale-105"
                  />
                  <span className="absolute left-4 top-4 rounded-full bg-white/95 px-3 py-2 text-xs font-bold text-slate-700">
                    {destination.category}
                  </span>
                </div>
                <div className="p-5">
                  <h3 className="text-xl font-extrabold">
                    {destination.name}
                  </h3>
                  <p className="mt-2 text-sm leading-7 text-slate-500">
                    {destination.description}
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setForm((previous) => ({
                        ...previous,
                        destination: destination.name,
                      }));
                      document
                        .getElementById("planner")
                        ?.scrollIntoView({ behavior: "smooth" });
                    }}
                    className="mt-5 font-bold text-indigo-600 transition hover:text-indigo-800"
                  >
                    Plan this trip →
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <p className="font-bold text-slate-800">
            Travel<span className="text-indigo-600">AI</span>
          </p>
          <p>
            Built with React, Tailwind CSS, FastAPI, LangGraph, Groq and MCP.
          </p>
          <p>Live data and prices may require verification.</p>
        </div>
      </footer>
    </div>
  );
}
