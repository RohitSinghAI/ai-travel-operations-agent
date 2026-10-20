import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import LiveTouristPlaces from "./components/LiveTouristPlaces.jsx";

const INITIAL_FORM = {
  source: "Hyderabad",
  destination: "Goa",
  days: 3,
  travelers: 2,
  budget: 15000,
  check_in: "2026-11-10",
  check_out: "2026-11-13",
  preferences: "beaches, local food",
};

const DESTINATIONS = [
  {
    name: "Goa",
    tag: "BEACHES & SUNSETS",
    description: "Coastal escapes, seafood and colorful heritage streets.",
    image:
      "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=1000&q=85",
  },
  {
    name: "Manali",
    tag: "MOUNTAINS & NATURE",
    description: "Mountain views, pine forests and fresh alpine air.",
    image:
      "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=1000&q=85",
  },
  {
    name: "Jaipur",
    tag: "CULTURE & HERITAGE",
    description: "Historic forts, vibrant markets and local traditions.",
    image:
      "https://images.unsplash.com/photo-1599661046827-dacff0c0f09a?auto=format&fit=crop&w=1000&q=85",
  },
];

const inputClass =
  "mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-4 focus:ring-violet-100";

function Field({ label, children }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {label}
      {children}
    </label>
  );
}

function readError(data, status) {
  if (typeof data === "string" && data.trim()) return data;
  const detail = data?.detail ?? data?.message ?? data?.error;
  if (typeof detail === "string") return detail;
  if (detail != null) return JSON.stringify(detail, null, 2);
  return `Request failed (${status}). The server did not return an error message.`;
}

function Money({ value }) {
  if (value == null || value === "") return <>Not available</>;
  const number = Number(value);
  return Number.isFinite(number)
    ? <>₹{number.toLocaleString("en-IN")}</>
    : <>{String(value)}</>;
}

function MarkdownContent({ content }) {
  const markdown =
    typeof content === "string"
      ? content
      : JSON.stringify(content ?? {}, null, 2);

  return (
    <div className="space-y-3 text-sm leading-7 text-slate-600">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mb-3 mt-5 text-2xl font-black text-slate-900">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-3 mt-6 text-xl font-extrabold text-slate-900">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-2 mt-4 text-lg font-bold text-slate-900">{children}</h3>
          ),
          p: ({ children }) => <p className="leading-7">{children}</p>,
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-6">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-1 pl-6">{children}</ol>,
          strong: ({ children }) => <strong className="font-bold text-slate-900">{children}</strong>,
          hr: () => <hr className="my-5 border-slate-200" />,
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-slate-200 bg-slate-50 p-3 font-bold text-slate-800">{children}</th>
          ),
          td: ({ children }) => <td className="border border-slate-200 p-3">{children}</td>,
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}

export default function App() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("itinerary");

  const livePlacesData = result?.tool_data?.live_places ?? result?.live_places ?? null;
  const itinerary = result?.itinerary ?? result?.plan ?? result?.travel_plan ?? null;

  const budgetItems = useMemo(() => {
    const items = result?.budget_breakdown?.line_items;
    if (!items || typeof items !== "object") return [];
    return Object.entries(items);
  }, [result]);

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((old) => ({ ...old, [name]: value }));
  };

  const generatePlan = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    if (new Date(form.check_out) <= new Date(form.check_in)) {
      setError("Check-out date must be after check-in date.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          days: Number(form.days),
          travelers: Number(form.travelers),
          budget: Number(form.budget),
          preferences: form.preferences
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });

      const contentType = response.headers.get("content-type") || "";
      const data = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

      if (!response.ok) throw new Error(readError(data, response.status));
      if (!data || typeof data !== "object") {
        throw new Error("The backend returned an unexpected response.");
      }

      setResult(data);
      setActiveTab("itinerary");
      setTimeout(() => {
        document.getElementById("trip-results")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 80);
    } catch (err) {
      console.error("Travel plan request failed:", err);
      setError(
        err instanceof TypeError
          ? "Cannot connect to FastAPI. Check that the backend is running on port 8000 and Vite proxies /plan."
          : err.message || "Something went wrong while planning your trip."
      );
    } finally {
      setLoading(false);
    }
  };

  const chooseDestination = (name) => {
    setForm((old) => ({ ...old, destination: name }));
    document.getElementById("planner")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-[#f7f7fb] text-slate-900">
      <header className="sticky top-0 z-40 border-b border-white/70 bg-white/90 backdrop-blur-xl">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
          <a href="#" className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-violet-600 text-xl text-white shadow-lg shadow-violet-200">✈</span>
            <span>
              <span className="block text-lg font-black tracking-tight">Travel<span className="text-violet-600">AI</span></span>
              <span className="block text-xs text-slate-500">Your journey, reimagined</span>
            </span>
          </a>

          <div className="hidden items-center gap-7 text-sm font-semibold text-slate-600 md:flex">
            <a href="#planner" className="transition hover:text-violet-600">Trip planner</a>
            <a href="#discover" className="transition hover:text-violet-600">Discover</a>
            <a href="#trip-results" className="transition hover:text-violet-600">My itinerary</a>
          </div>

          <a href="#planner" className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-violet-700">
            Plan a trip <span className="ml-1">↗</span>
          </a>
        </nav>
      </header>

      <main>
        <section className="relative isolate overflow-hidden bg-[#151126]">
          <div className="absolute inset-0 -z-10">
            <img
              src="https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=2000&q=90"
              alt=""
              className="h-full w-full object-cover opacity-35"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[#151126] via-[#151126]/90 to-violet-950/40" />
          </div>

          <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 py-16 sm:px-6 md:py-24 lg:grid-cols-[1.1fr_.9fr] lg:px-8">
            <div className="text-white">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-bold tracking-[.16em] text-violet-100">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                SMART TRAVEL, POWERED BY AI
              </span>
              <h1 className="mt-7 max-w-3xl text-4xl font-black leading-[1.08] tracking-tight sm:text-6xl">
                Less planning.
                <span className="block text-violet-300">More exploring.</span>
              </h1>
              <p className="mt-6 max-w-xl text-base leading-8 text-white/75 sm:text-lg">
                Build a personalized itinerary, explore map-listed places and keep your trip budget in view—all in one travel workspace.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <a href="#planner" className="rounded-xl bg-violet-500 px-6 py-3.5 font-bold text-white shadow-lg shadow-violet-950/30 transition hover:bg-violet-400">
                  Build my itinerary <span className="ml-2">→</span>
                </a>
                <a href="#discover" className="rounded-xl border border-white/25 bg-white/5 px-6 py-3.5 font-bold text-white transition hover:bg-white/10">
                  Explore destinations
                </a>
              </div>
              <div className="mt-10 flex flex-wrap gap-x-6 gap-y-3 text-sm text-white/70">
                <span>✓ Day-by-day planning</span>
                <span>✓ Budget visibility</span>
                <span>✓ Map-linked places</span>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-lg">
              <img
                src="https://images.unsplash.com/photo-1530789253388-582c481c54b0?auto=format&fit=crop&w=1200&q=85"
                alt="Traveler looking across a scenic landscape"
                className="h-72 w-full rounded-[2rem] object-cover shadow-2xl ring-1 ring-white/20 sm:h-[410px]"
              />
              <div className="absolute -bottom-5 left-4 right-4 rounded-2xl border border-white/70 bg-white/95 p-4 shadow-xl sm:left-8 sm:right-8">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-violet-600">Made around you</p>
                    <p className="mt-1 font-extrabold">Your next trip starts here</p>
                    <p className="mt-1 text-xs text-slate-500">Destination · Experiences · Budget</p>
                  </div>
                  <span className="grid h-12 w-12 place-items-center rounded-2xl bg-violet-50 text-2xl">🧭</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="planner" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6 lg:px-8">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[.2em] text-violet-600">Your next chapter</p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">Design your getaway</h2>
              <p className="mt-3 max-w-2xl leading-7 text-slate-500">Share a few details and let your connected travel-planning backend build a first draft.</p>
            </div>
            <span className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600">PERSONALIZED TRIP BUILDER</span>
          </div>

          <div className="grid items-start gap-6 lg:grid-cols-[.88fr_1.12fr]">
            <form onSubmit={generatePlan} className="rounded-[1.75rem] border border-slate-200/80 bg-white p-5 shadow-sm sm:p-7">
              <div className="mb-6 flex items-center gap-3">
                <span className="grid h-12 w-12 place-items-center rounded-2xl bg-violet-50 text-xl">🗺️</span>
                <div>
                  <h3 className="text-xl font-black">Trip details</h3>
                  <p className="mt-1 text-sm text-slate-500">Your trip, your preferences</p>
                </div>
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <Field label="Starting city">
                  <input required name="source" value={form.source} onChange={updateField} placeholder="Hyderabad" className={inputClass} />
                </Field>
                <Field label="Destination">
                  <input required name="destination" value={form.destination} onChange={updateField} placeholder="Goa" className={inputClass} />
                </Field>
                <Field label="Duration (days)">
                  <input required type="number" min="1" max="30" name="days" value={form.days} onChange={updateField} className={inputClass} />
                </Field>
                <Field label="Travelers">
                  <input required type="number" min="1" max="50" name="travelers" value={form.travelers} onChange={updateField} className={inputClass} />
                </Field>
                <Field label="Total budget (₹)">
                  <input required type="number" min="1" name="budget" value={form.budget} onChange={updateField} className={inputClass} />
                </Field>
                <Field label="Travel preferences">
                  <input name="preferences" value={form.preferences} onChange={updateField} placeholder="Beaches, food, nature" className={inputClass} />
                </Field>
                <Field label="Check-in date">
                  <input required type="date" name="check_in" value={form.check_in} onChange={updateField} className={inputClass} />
                </Field>
                <Field label="Check-out date">
                  <input required type="date" name="check_out" min={form.check_in} value={form.check_out} onChange={updateField} className={inputClass} />
                </Field>
              </div>

              <button type="submit" disabled={loading} className="mt-7 flex w-full items-center justify-center gap-3 rounded-xl bg-violet-600 px-5 py-4 font-extrabold text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60">
                {loading ? (
                  <>
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                    Creating your itinerary...
                  </>
                ) : (
                  <>✦ Generate my travel plan</>
                )}
              </button>
              <p className="mt-4 text-center text-xs leading-6 text-slate-500">
                Estimates and map records may need independent verification. This form does not book or reserve travel.
              </p>
            </form>

            <div id="trip-results" className="min-w-0 scroll-mt-24">
              {!result && !loading && !error && (
                <div className="flex min-h-[450px] flex-col items-center justify-center rounded-[1.75rem] border border-dashed border-slate-300 bg-white p-8 text-center">
                  <span className="grid h-20 w-20 place-items-center rounded-3xl bg-violet-50 text-4xl">🌍</span>
                  <h3 className="mt-6 text-2xl font-black">A great trip begins with an idea</h3>
                  <p className="mt-3 max-w-sm leading-7 text-slate-500">Fill in your trip details to see your itinerary, budget information and map-listed places here.</p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {["Itinerary", "Budget", "Places"].map((item) => (
                      <span key={item} className="rounded-full bg-slate-100 px-3 py-2 text-xs font-bold text-slate-600">✓ {item}</span>
                    ))}
                  </div>
                </div>
              )}

              {loading && (
                <div className="flex min-h-[450px] flex-col items-center justify-center rounded-[1.75rem] border border-slate-200 bg-white p-8 text-center">
                  <span className="h-12 w-12 animate-spin rounded-full border-4 border-violet-100 border-t-violet-600" />
                  <h3 className="mt-5 text-xl font-black">Crafting your journey</h3>
                  <p className="mt-2 text-sm text-slate-500">Waiting for your travel-planning backend...</p>
                </div>
              )}

              {error && (
                <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800">
                  <h3 className="font-extrabold">We couldn't create this trip</h3>
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6">{error}</p>
                  <p className="mt-3 text-xs">Check the FastAPI terminal and the Vite /plan proxy configuration.</p>
                </div>
              )}

              {result && (
                <div className="space-y-5">
                  <div className="overflow-hidden rounded-[1.75rem] bg-slate-900 p-6 text-white sm:p-7">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-bold uppercase tracking-[.2em] text-violet-300">Your trip overview</p>
                        <h3 className="mt-3 text-2xl font-black sm:text-3xl">{form.source} <span className="text-violet-300">→</span> {form.destination}</h3>
                        <p className="mt-3 text-sm text-white/70">{form.days} days · {form.travelers} travelers · {form.check_in} to {form.check_out}</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/10 p-4">
                        <p className="text-xs text-white/60">Your budget</p>
                        <p className="mt-1 text-2xl font-black"><Money value={form.budget} /></p>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-2">
                    {[
                      ["itinerary", "✦ Itinerary"],
                      ["budget", "₹ Budget"],
                      ["places", "⌖ Tourist places"],
                    ].map(([tab, label]) => (
                      <button key={tab} type="button" onClick={() => setActiveTab(tab)} className={`rounded-xl px-4 py-2.5 text-sm font-bold transition ${activeTab === tab ? "bg-violet-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"}`}>
                        {label}
                      </button>
                    ))}
                  </div>

                  {activeTab === "itinerary" && (
                    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                      <p className="text-xs font-black uppercase tracking-[.18em] text-violet-600">The plan</p>
                      <h3 className="mt-2 text-xl font-black">Your itinerary</h3>
                      <div className="mt-5">
                        <MarkdownContent content={itinerary ?? result} />
                      </div>
                    </section>
                  )}

                  {activeTab === "budget" && (
                    <section className="rounded-[1.75rem] border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-black uppercase tracking-[.18em] text-violet-600">Trip finances</p>
                          <h3 className="mt-2 text-xl font-black">Budget breakdown</h3>
                          <p className="mt-1 text-sm text-slate-500">Amounts are shown as returned by your backend.</p>
                        </div>
                        <span className="rounded-xl bg-violet-50 px-4 py-2 text-sm font-extrabold text-violet-700">Budget: <Money value={result.budget_breakdown?.user_budget ?? form.budget} /></span>
                      </div>

                      {budgetItems.length > 0 ? (
                        <div className="mt-6 grid gap-3 sm:grid-cols-2">
                          {budgetItems.map(([key, item]) => (
                            <article key={key} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
                              <div className="flex items-start justify-between gap-3">
                                <p className="text-sm font-bold capitalize text-slate-600">{key.replaceAll("_", " ")}</p>
                                <span className="grid h-9 w-9 place-items-center rounded-xl bg-white text-lg shadow-sm">
                                  {key === "transport" ? "🚆" : key === "accommodation" ? "🛏️" : key === "food" ? "🍽️" : key === "activities" ? "🎟️" : "💳"}
                                </span>
                              </div>
                              <p className="mt-3 text-2xl font-black text-slate-900"><Money value={item?.amount} /></p>
                              <p className="mt-2 text-xs leading-5 text-slate-500">{item?.source || "No source details provided."}</p>
                            </article>
                          ))}
                        </div>
                      ) : (
                        <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
                          The backend did not return a line-item budget breakdown.
                          <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(result.budget_breakdown ?? { budget: form.budget }, null, 2)}</pre>
                        </div>
                      )}

                      {result.budget_breakdown?.essential_prices_complete === false && (
                        <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
                          <strong>Price verification needed.</strong> Some essential prices are unavailable or estimated. Confirm transport, accommodation and activity prices before travelling.
                        </div>
                      )}
                    </section>
                  )}

                  {activeTab === "places" && (
                    <LiveTouristPlaces liveData={livePlacesData} loading={false} error="" />
                  )}

                  {result.review_notes && (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
                      <strong>Planning notes</strong>
                      <div className="mt-2">
                        {Array.isArray(result.review_notes)
                          ? result.review_notes.map((note, index) => <p key={index}>{typeof note === "string" ? note : JSON.stringify(note)}</p>)
                          : typeof result.review_notes === "string"
                            ? result.review_notes
                            : JSON.stringify(result.review_notes)}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>

        <section id="discover" className="mx-auto max-w-7xl scroll-mt-24 px-4 pb-20 sm:px-6 lg:px-8">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[.2em] text-violet-600">A little inspiration</p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">Where will you go next?</h2>
              <p className="mt-3 text-slate-500">Choose a destination to fill the planner.</p>
            </div>
            <span className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600">EXPLORE INDIA</span>
          </div>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {DESTINATIONS.map((destination) => (
              <article key={destination.name} className="group overflow-hidden rounded-[1.75rem] border border-slate-200 bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-xl">
                <div className="relative overflow-hidden">
                  <img src={destination.image} alt={destination.name} loading="lazy" className="h-60 w-full object-cover transition duration-500 group-hover:scale-105" />
                  <span className="absolute left-4 top-4 rounded-full bg-white/95 px-3 py-2 text-[10px] font-black tracking-widest text-slate-800">{destination.tag}</span>
                </div>
                <div className="p-5">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-xl font-black">{destination.name}</h3>
                    <span className="text-xl text-violet-600">↗</span>
                  </div>
                  <p className="mt-2 text-sm leading-7 text-slate-500">{destination.description}</p>
                  <button type="button" onClick={() => chooseDestination(destination.name)} className="mt-5 rounded-xl bg-violet-50 px-4 py-2.5 text-sm font-extrabold text-violet-700 transition hover:bg-violet-100">
                    Plan this destination →
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <p className="font-black text-slate-900">Travel<span className="text-violet-600">AI</span></p>
          <p>React · Tailwind CSS · FastAPI · LangGraph · Groq · MCP</p>
          <p>Live prices and visitor access must be verified.</p>
        </div>
      </footer>
    </div>
  );
}
