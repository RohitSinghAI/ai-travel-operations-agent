import { useMemo, useState } from "react";
import "./LiveTouristPlaces.css";

const CATEGORIES = [
  "all",
  "beach",
  "attraction",
  "museum",
  "park",
  "viewpoint",
];

function normalizeCategory(value) {
  return String(value || "other").trim().toLowerCase();
}

function formatCategory(value) {
  return normalizeCategory(value)
    .split(/[\s_-]+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function getMapUrl(place) {
  if (place.osm_url) return place.osm_url;

  const lat = place.latitude ?? place.lat;
  const lon = place.longitude ?? place.lon ?? place.lng;

  if (lat == null || lon == null) return null;

  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=16/${lat}/${lon}`;
}

export default function LiveTouristPlaces({
  liveData,
  loading = false,
  error = "",
}) {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");

  const places = Array.isArray(liveData)
    ? liveData
    : Array.isArray(liveData?.places)
      ? liveData.places
      : [];

  const availableCategories = useMemo(() => {
    const found = [...new Set(places.map((place) => normalizeCategory(place.category)))];
    return [
      "all",
      ...CATEGORIES.filter(
        (category) => category !== "all" && found.includes(category)
      ),
      ...found.filter((category) => !CATEGORIES.includes(category)),
    ];
  }, [places]);

  const filteredPlaces = useMemo(() => {
    const query = search.trim().toLowerCase();

    return places.filter((place) => {
      const category = normalizeCategory(place.category);
      const matchesCategory =
        activeCategory === "all" || category === activeCategory;

      const searchableText = [
        place.name,
        place.category,
        place.description,
        place.display_name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return matchesCategory && searchableText.includes(query);
    });
  }, [places, search, activeCategory]);

  if (loading) {
    return (
      <section className="panel content-panel live-places-section">
        <div className="live-places-loading" role="status" aria-live="polite">
          <span className="live-places-spinner" />
          <div>
            <h3>Loading tourist places...</h3>
            <p>Fetching map records for your destination.</p>
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel content-panel live-places-section">
        <div className="live-places-error" role="alert">
          <span className="live-places-empty-icon">⚠️</span>
          <h3>Could not load tourist places</h3>
          <p>{typeof error === "string" ? error : JSON.stringify(error)}</p>
        </div>
      </section>
    );
  }

  if (!liveData) {
    return (
      <section className="panel content-panel live-places-section">
        <div className="live-places-empty">
          <span className="live-places-empty-icon">📍</span>
          <h3>Live places not loaded yet</h3>
          <p>Generate a travel plan to discover places at your destination.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel content-panel live-places-section">
      <div className="live-places-header">
        <div className="live-places-heading">
          <span className="live-places-heading-icon">📍</span>

          <div>
            <div className="live-places-title-row">
              <h2>Explore Tourist Places</h2>
              <span className="live-places-live-badge">
                <span className="live-places-live-dot" />
                {liveData.status === "live" ? "LIVE DATA" : "MAP DATA"}
              </span>
            </div>

            <p>
              Discover places and open their locations on OpenStreetMap.
            </p>
          </div>
        </div>

        <div className="live-places-count">
          <strong>{liveData.count ?? places.length}</strong>
          <span>places found</span>
        </div>
      </div>

      <div className="live-places-toolbar">
        <label className="live-places-search">
          <span aria-hidden="true">⌕</span>
          <input
            type="search"
            placeholder="Search places, museums, beaches..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search tourist places"
          />

          {search && (
            <button
              type="button"
              className="live-places-clear"
              onClick={() => setSearch("")}
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </label>

        <div
          className="live-places-filters"
          role="group"
          aria-label="Filter places by category"
        >
          {availableCategories.map((category) => (
            <button
              type="button"
              key={category}
              className={`live-places-filter ${
                activeCategory === category ? "active" : ""
              }`}
              onClick={() => setActiveCategory(category)}
              aria-pressed={activeCategory === category}
            >
              {category === "all" ? "All places" : formatCategory(category)}
            </button>
          ))}
        </div>
      </div>

      {filteredPlaces.length === 0 ? (
        <div className="live-places-empty">
          <span className="live-places-empty-icon">🔎</span>
          <h3>No places found</h3>
          <p>Try another search or select a different category.</p>

          <button
            type="button"
            className="live-places-reset"
            onClick={() => {
              setSearch("");
              setActiveCategory("all");
            }}
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="live-places-grid">
          {filteredPlaces.map((place, index) => {
            const mapUrl = getMapUrl(place);
            const category = normalizeCategory(place.category);
            const lat = place.latitude ?? place.lat;
            const lon = place.longitude ?? place.lon ?? place.lng;

            return (
              <article
                className="live-place-card"
                key={place.id || place.osm_id || place.osm_url || `${place.name}-${index}`}
              >
                <div className={`live-place-art live-place-art-${category.replace(/[^a-z0-9_-]/g, "")}`}>
                  <span className="live-place-art-icon">
                    {category === "beach"
                      ? "🏖️"
                      : category === "museum"
                        ? "🏛️"
                        : category === "park"
                          ? "🌳"
                          : category === "viewpoint"
                            ? "🌄"
                            : category === "attraction"
                              ? "🏛️"
                              : "📍"}
                  </span>

                  <span className="live-place-number">
                    {(index + 1).toString().padStart(2, "0")}
                  </span>

                  <span className="live-place-category">
                    {formatCategory(category)}
                  </span>
                </div>

                <div className="live-place-content">
                  <h3>{place.name || "Unnamed place"}</h3>

                  <p className="live-place-address">
                    <span aria-hidden="true">⌖</span>
                    {place.display_name || "Location listed on OpenStreetMap"}
                  </p>

                  <p className="live-place-description">
                    {place.description ||
                      "View the map record for more location details."}
                  </p>

                  {lat != null && lon != null && (
                    <p className="live-place-coordinates">
                      {Number(lat).toFixed(4)}, {Number(lon).toFixed(4)}
                    </p>
                  )}

                  <div className="live-place-footer">
                    <span className="live-place-source">OpenStreetMap</span>

                    {mapUrl ? (
                      <a
                        className="live-place-map-link"
                        href={mapUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        View map <span aria-hidden="true">↗</span>
                      </a>
                    ) : (
                      <span className="live-place-no-map">Map unavailable</span>
                    )}
                  </div>

                  {place.verified_tourist_attraction === false && (
                    <p className="live-place-disclaimer">
                      Tourist suitability and current access are not
                      independently verified.
                    </p>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="live-places-footer-note">
        <span aria-hidden="true">ⓘ</span>
        <p>
          Data provider: {liveData.provider || "OpenStreetMap"}. Map records do
          not confirm opening hours, entry fees or current visitor access.
          Please verify these before travelling.
        </p>
      </div>

      <p className="live-places-attribution">
        Map data ©{" "}
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noopener noreferrer"
        >
          OpenStreetMap contributors
        </a>
      </p>
    </section>
  );
}
