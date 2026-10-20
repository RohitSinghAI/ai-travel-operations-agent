
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import API_BASE_URL from "./api.js";
import "./App.css";

const initialForm = {
  source: "Hyderabad",
  destination: "Goa",
  days: 3,
  travelers: 2,
  budget: 15000,
  preferences: "beaches, local food",
};

function formatCurrency(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  const amount = Number(value);
  if (!Number.isFinite(amount)) return "Not available";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatLabel(value) {
  return value.replaceAll("_", " ");
}

function App() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const payload = {
      source: form.source.trim(),
      destination: form.destination.trim(),
      days: Number(form.days),
      travelers: Number(form.travelers),
      budget: Number(form.budget),
      preferences: form.preferences
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };

    try {
      const response = await fetch(`${API_BASE_URL}/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const message =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((item) => item.msg || JSON.stringify(item)).join(", ")
              : JSON.stringify(data.detail || data) ||
                "Unable to generate the travel plan.";

        throw new Error(message);
      }

      setResult(data);
    } catch (err) {
      setError(
        err.message ||
          "Could not connect to the backend. Check whether FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  }

  function downloadItinerary() {
    if (!result) return;

    const breakdown = result.budget_breakdown || {};

    const content = [
      `Travel Plan: ${result.source} to ${result.destination}`,
      `Duration: ${result.days} days`,
      `Travelers: ${result.travelers}`,
      `Budget: ${formatCurrency(result.budget)}`,
      "",
      "ITINERARY",
      result.itinerary || "No itinerary available.",
      "",
      "BUDGET BREAKDOWN",
      JSON.stringify(breakdown, null, 2),
      "",
      "TRAVEL TOOL DATA",
      JSON.stringify(result.tool_data || {}, null, 2),
      "",
      "DISCLAIMER: Prices may be estimates or sample data. Live availability and bookings are not guaranteed.",
    ].join("\n");

    const blob = new Blob([content], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "travel-itinerary.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  const breakdown = result?.budget_breakdown;
  const lineItems = breakdown?.line_items || {};

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Travel AI home">
          <span className="brand-icon">✈</span>
          <span>
            Travel<span className="brand-accent">AI</span>
          </span>
        </a>

        <span className="status-pill">
          <span className="status-dot" />
          AI Travel Planner
        </span>
      </header>

      <main className="page-container">
        <section className="hero">
          <p className="eyebrow">YOUR PERSONAL TRAVEL ASSISTANT</p>
          <h1>Plan your next adventure.</h1>
          <p className="hero-description">
            Create a personalized itinerary and estimate your travel costs
            with AI-powered planning.
          </p>
        </section>

        <div className="dashboard-grid">
          <aside className="panel form-panel">
            <div className="panel-heading">
              <span className="heading-icon">⌁</span>
              <div>
                <h2>Trip details</h2>
                <p>Customize your journey</p>
              </div>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="source">Starting city</label>
                <input
                  id="source"
                  name="source"
                  value={form.source}
                  onChange={handleChange}
                  minLength={2}
                  maxLength={100}
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="destination">Destination city</label>
                <input
                  id="destination"
                  name="destination"
                  value={form.destination}
                  onChange={handleChange}
                  minLength={2}
                  maxLength={100}
                  required
                />
              </div>

              <div className="field-row">
                <div className="field">
                  <label htmlFor="days">Duration (days)</label>
                  <input
                    id="days"
                    name="days"
                    type="number"
                    min="1"
                    max="30"
                    value={form.days}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="field">
                  <label htmlFor="travelers">Travelers</label>
                  <input
                    id="travelers"
                    name="travelers"
                    type="number"
                    min="1"
                    max="50"
                    value={form.travelers}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>

              <div className="field">
                <label htmlFor="budget">Total budget (INR)</label>
                <div className="budget-input">
                  <span>₹</span>
                  <input
                    id="budget"
                    name="budget"
                    type="number"
                    min="1"
                    step="100"
                    value={form.budget}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>

              <div className="field">
                <label htmlFor="preferences">Travel preferences</label>
                <textarea
                  id="preferences"
                  name="preferences"
                  rows="3"
                  value={form.preferences}
                  onChange={handleChange}
                  placeholder="Beaches, food, nature..."
                />
                <small>Separate preferences with commas.</small>
              </div>

              <button
                className="primary-button"
                type="submit"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    Creating your trip...
                  </>
                ) : (
                  <>✦ Generate travel plan</>
                )}
              </button>

              <div className="disclaimer">
                <span>ⓘ</span>
                <p>
                  Prices may be estimates or sample data. Live availability
                  and bookings are not guaranteed.
                </p>
              </div>
            </form>
          </aside>

          <section className="results-column">
            {error && (
              <div className="error-banner" role="alert">
                <strong>Something went wrong</strong>
                <p>{error}</p>
                <small>
                  Check the FastAPI terminal and API response for details.
                </small>
              </div>
            )}

            {loading && (
              <div className="panel loading-panel">
                <span className="large-spinner" />
                <h2>Planning your adventure...</h2>
                <p>
                  Collecting travel options, estimating costs and preparing
                  your itinerary.
                </p>
              </div>
            )}

            {!result && !loading && !error && (
              <div className="panel empty-state">
                <div className="empty-illustration">✈</div>
                <h2>Your next adventure starts here</h2>
                <p>
                  Enter your trip details and generate a personalized travel
                  plan with an estimated budget.
                </p>
                <div className="feature-list">
                  <span>✓ Day-by-day itinerary</span>
                  <span>✓ Budget breakdown</span>
                  <span>✓ Travel tool information</span>
                </div>
              </div>
            )}

            {result && (
              <>
                <section className="panel trip-summary">
                  <div className="result-title-row">
                    <div>
                      <p className="eyebrow">YOUR TRIP OVERVIEW</p>
                      <h2>
                        {result.source} <span>→</span> {result.destination}
                      </h2>
                    </div>
                    <button
                      className="secondary-button"
                      onClick={downloadItinerary}
                      type="button"
                    >
                      ↓ Download
                    </button>
                  </div>

                  <div className="stats-grid">
                    <div className="stat-card">
                      <span>Duration</span>
                      <strong>{result.days} days</strong>
                    </div>
                    <div className="stat-card">
                      <span>Travelers</span>
                      <strong>{result.travelers}</strong>
                    </div>
                    <div className="stat-card">
                      <span>Your budget</span>
                      <strong>{formatCurrency(result.budget)}</strong>
                    </div>
                  </div>
                </section>

                <section className="panel content-panel">
                  <div className="section-heading">
                    <span className="section-icon">✦</span>
                    <div>
                      <h2>Your AI itinerary</h2>
                      <p>Your personalized travel plan</p>
                    </div>
                  </div>

                  <article className="markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {result.itinerary || "No itinerary was returned."}
                    </ReactMarkdown>
                  </article>
                </section>

                <section className="panel content-panel">
                  <div className="section-heading">
                    <span className="section-icon">₹</span>
                    <div>
                      <h2>Budget breakdown</h2>
                      <p>Estimated costs in Indian rupees</p>
                    </div>
                  </div>

                  {breakdown ? (
                    <>
                      <div className="budget-total">
                        <span>Estimated trip total</span>
                        <strong>
                          {formatCurrency(breakdown.estimated_total)}
                        </strong>
                      </div>

                      <div className="budget-table-wrapper">
                        <table className="budget-table">
                          <thead>
                            <tr>
                              <th>Expense</th>
                              <th>Estimated cost</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(lineItems).map(([key, item]) => (
                              <tr key={key}>
                                <td>
                                  <span className="expense-name">
                                    {formatLabel(key)}
                                  </span>
                                  {item?.source && (
                                    <small className="expense-source">
                                      {item.source}
                                    </small>
                                  )}
                                </td>
                                <td className="amount-cell">
                                  {key === "contingency" &&
                                  item?.rate !== undefined
                                    ? `${formatCurrency(item.amount)} (${Math.round(item.rate * 100)}%)`
                                    : formatCurrency(item?.amount)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="budget-footer">
                        <span>Budget remaining</span>
                        <strong
                          className={
                            Number(breakdown.budget_remaining) < 0
                              ? "negative"
                              : "positive"
                          }
                        >
                          {formatCurrency(breakdown.budget_remaining)}
                        </strong>
                      </div>

                      {breakdown.essential_prices_complete === false && (
                        <p className="warning-message">
                          Some essential prices are missing. The total may be
                          incomplete.
                        </p>
                      )}

                      {breakdown.warnings?.length > 0 && (
                        <div className="warnings">
                          <strong>Things to keep in mind</strong>
                          <ul>
                            {breakdown.warnings.map((warning, index) => (
                              <li key={`${index}-${warning}`}>{warning}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  ) : (
                    <p>No structured budget breakdown was returned.</p>
                  )}
                </section>

                {/* Live Tourist Places */}
                {result.tool_data?.live_places && (
                  <section className="panel content-panel">
                    <div className="section-heading">
                      <span className="section-icon">📍</span>
                      <div>
                        <h2>Live Tourist Places</h2>
                        <p>
                          Provider:{" "}
                          {result.tool_data.live_places.provider || "Not specified"}
                          {" · "}
                          Status:{" "}
                          {result.tool_data.live_places.status || "Not specified"}
                        </p>
                      </div>
                    </div>

                    {(() => {
                      const liveData = result.tool_data.live_places;
                      const places = Array.isArray(liveData)
                        ? liveData
                        : Array.isArray(liveData.places)
                          ? liveData.places
                          : [];

                      if (places.length === 0) {
                        return (
                          <p>
                            No tourist places were returned for this destination.
                          </p>
                        );
                      }

                      return (
                        <div className="places-grid">
                          {places.map((place, index) => {
                            const latitude =
                              place.latitude ?? place.lat ?? place.coordinates?.lat;
                            const longitude =
                              place.longitude ?? place.lon ?? place.lng ?? place.coordinates?.lon;

                            return (
                              <article
                                className="place-card"
                                key={place.id || place.name || index}
                              >
                                <span className="place-category">
                                  {formatLabel(place.category || "Tourist place")}
                                </span>

                                <h3>{place.name || "Unnamed place"}</h3>

                                <p>
                                  {place.description || "No description available."}
                                </p>

                                {latitude != null && longitude != null && (
                                  <a
                                    href={`https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=16/${latitude}/${longitude}`}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    View on OpenStreetMap ↗
                                  </a>
                                )}

                                {place.verified_tourist_attraction === false && (
                                  <p className="place-warning">
                                    Tourist suitability has not been independently
                                    verified.
                                  </p>
                                )}
                              </article>
                            );
                          })}
                        </div>
                      );
                    })()}
                  </section>
                )}

                <section className="panel content-panel">
                  <div className="section-heading">
                    <span className="section-icon">⚙</span>
                    <div>
                      <h2>Travel tool diagnostics</h2>
                      <p>Data returned by the connected tools</p>
                    </div>
                  </div>

                  {result.tool_data &&
                  Object.keys(result.tool_data).length > 0 ? (
                    <div className="tool-list">
                      {Object.entries(result.tool_data).map(([name, data]) => (
                        <details className="tool-item" key={name}>
                          <summary>
                            <span>{formatLabel(name)}</span>
                            <span
                              className={
                                data?.error ? "tool-error" : "tool-success"
                              }
                            >
                              {data?.error ? "Error" : "Response received"}
                            </span>
                          </summary>
                          <pre>{JSON.stringify(data, null, 2)}</pre>
                        </details>
                      ))}
                    </div>
                  ) : (
                    <p>No tool diagnostics were returned.</p>
                  )}
                </section>

                {result.review_notes && (
                  <p className="review-note">
                    <strong>Review:</strong> {result.review_notes}
                  </p>
                )}
              </>
            )}
          </section>
        </div>

        <footer className="footer">
          Built with React, FastAPI, LangGraph, Groq and MCP
        </footer>
      </main>
    </div>
  );
}

export default App;
