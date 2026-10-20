
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
  check_in: "2026-11-10",
  check_out: "2026-11-13",
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
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatLabel(value) {
  return String(value).replaceAll("_", " ");
}

function getPlaces(liveData) {
  if (Array.isArray(liveData)) return liveData;
  if (Array.isArray(liveData?.places)) return liveData.places;
  return [];
}

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [placesLoading, setPlacesLoading] = useState(false);
  const [error, setError] = useState("");
  const [placesError, setPlacesError] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: ["days", "travelers", "budget"].includes(name)
        ? Number(value)
        : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setPlacesError("");
    setResult(null);

    if (form.check_out <= form.check_in) {
      setError("Check-out date must be after check-in date.");
      setLoading(false);
      return;
    }

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
      check_in: form.check_in,
      check_out: form.check_out,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const message =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail
                  .map((item) => item.msg || JSON.stringify(item))
                  .join(", ")
              : JSON.stringify(data.detail || data) ||
                "Unable to generate travel plan.";

        throw new Error(message);
      }

      setResult(data);

      // Fetch live tourist places separately from the verified backend route.
      setPlacesLoading(true);

      try {
        const placesUrl =
          `${API_BASE_URL}/api/live/places?city=` +
          encodeURIComponent(form.destination.trim());

        const placesResponse = await fetch(placesUrl);
        const placesData = await placesResponse.json().catch(() => ({}));

        if (!placesResponse.ok) {
          throw new Error(
            placesData.detail || "Could not load live tourist places."
          );
        }

        setResult((previous) => ({
          ...previous,
          tool_data: {
            ...(previous?.tool_data || {}),
            live_places: placesData,
          },
        }));
      } catch (placesErr) {
        setPlacesError(
          placesErr.message || "Could not load live tourist places."
        );
      } finally {
        setPlacesLoading(false);
      }
    } catch (err) {
      setError(
        err.message ||
          "Could not connect to the backend. Check FastAPI and CORS settings."
      );
    } finally {
      setLoading(false);
    }
  }

  function downloadItinerary() {
    if (!result) return;

    const content = [
      `Travel Plan: ${result.source} to ${result.destination}`,
      `Duration: ${result.days} days`,
      `Travelers: ${result.travelers}`,
      `Budget: ${formatCurrency(result.budget)}`,
      `Check-in: ${form.check_in}`,
      `Check-out: ${form.check_out}`,
      "",
      "ITINERARY",
      result.itinerary || "No itinerary available.",
      "",
      "BUDGET BREAKDOWN",
      JSON.stringify(result.budget_breakdown || {}, null, 2),
      "",
      "LIVE TOURIST PLACES",
      JSON.stringify(result.tool_data?.live_places || {}, null, 2),
      "",
      "Prices may be estimates. Live availability and bookings are not guaranteed.",
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
  const liveData = result?.tool_data?.live_places;
  const places = getPlaces(liveData);

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
            Create a personalized itinerary and explore map-based tourist
            places with AI-powered planning.
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
                    value={form.budget}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>

              <div className="field-row">
                <div className="field">
                  <label htmlFor="check_in">Check-in</label>
                  <input
                    id="check_in"
                    name="check_in"
                    type="date"
                    value={form.check_in}
                    onChange={handleChange}
                    required
                  />
                </div>

                <div className="field">
                  <label htmlFor="check_out">Check-out</label>
                  <input
                    id="check_out"
                    name="check_out"
                    type="date"
                    value={form.check_out}
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
                {loading ? "Creating your trip..." : "✦ Generate travel plan"}
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
                <small>Check the FastAPI terminal for details.</small>
              </div>
            )}

            {loading && (
              <div className="panel loading-panel">
                <span className="large-spinner" />
                <h2>Planning your adventure...</h2>
                <p>Generating your itinerary and collecting travel data.</p>
              </div>
            )}

            {!result && !loading && !error && (
              <div className="panel empty-state">
                <div className="empty-illustration">✈</div>
                <h2>Your next adventure starts here</h2>
                <p>
                  Enter your trip details to generate a personalized travel
                  plan and budget estimate.
                </p>
                <div className="feature-list">
                  <span>✓ Day-by-day itinerary</span>
                  <span>✓ Budget breakdown</span>
                  <span>✓ Live tourist places</span>
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
                                  {item?.amount == null
                                    ? "Unavailable"
                                    : formatCurrency(item.amount)}
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
                          Some essential prices are missing. This is a partial
                          estimate, not the final trip cost.
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

                <section className="panel content-panel">
                  <div className="section-heading">
                    <span className="section-icon">📍</span>
                    <div>
                      <h2>Live Tourist Places</h2>
                      <p>
                        {liveData?.provider || "OpenStreetMap"} ·{" "}
                        {liveData?.status || "Waiting for data"}
                      </p>
                    </div>
                  </div>

                  {placesLoading && <p>Loading live tourist places...</p>}

                  {placesError && (
                    <p className="warning-message">{placesError}</p>
                  )}

                  {!placesLoading && places.length === 0 && !placesError && (
                    <p>No tourist places were returned for this destination.</p>
                  )}

                  {places.length > 0 && (
                    <>
                      <p className="places-note">
                        {liveData?.count ?? places.length} map records found.
                        Tourist suitability and current access are not
                        independently verified.
                      </p>

                      <div className="places-grid">
                        {places.map((place, index) => {
                          const latitude = place.latitude ?? place.lat;
                          const longitude =
                            place.longitude ?? place.lon ?? place.lng;

                          const mapUrl =
                            place.osm_url ||
                            (latitude != null && longitude != null
                              ? `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=16/${latitude}/${longitude}`
                              : null);

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
                                {place.description ||
                                  place.display_name ||
                                  "No description available."}
                              </p>

                              {mapUrl && (
                                <a
                                  href={mapUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  View on OpenStreetMap ↗
                                </a>
                              )}

                              {place.verified_tourist_attraction === false && (
                                <p className="place-warning">
                                  Tourist suitability has not been
                                  independently verified.
                                </p>
                              )}
                            </article>
                          );
                        })}
                      </div>
                    </>
                  )}
                </section>

                <section className="panel content-panel">
                  <div className="section-heading">
                    <span className="section-icon">⚙</span>
                    <div>
                      <h2>Travel tool diagnostics</h2>
                      <p>Data returned by connected tools</p>
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
