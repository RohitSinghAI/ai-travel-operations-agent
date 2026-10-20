
import React from "react";

export default function LiveTouristPlaces({ livePlaces }) {
  const places = Array.isArray(livePlaces?.places)
    ? livePlaces.places
    : [];

  const isLive = livePlaces?.status === "live";

  if (!livePlaces) {
    return null;
  }

  return (
    <section className="my-8">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Explore Tourist Places
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Places mapped for your destination
          </p>
        </div>

        <span
          className={`rounded-full px-3 py-1 text-sm font-medium ${
            isLive
              ? "bg-green-100 text-green-700"
              : "bg-amber-100 text-amber-700"
          }`}
        >
          {isLive ? "Live data" : "Data unavailable"}
        </span>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Places found</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {places.length}
          </p>
        </div>

        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">Data provider</p>
          <p className="mt-1 text-sm font-semibold text-gray-800">
            {livePlaces.provider || "Not available"}
          </p>
        </div>
      </div>

      {!places.length ? (
        <div className="rounded-xl border border-dashed p-8 text-center">
          <p className="font-medium text-gray-700">
            No tourist places available
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Try again later or check another destination.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {places.map((place, index) => {
            const mapUrl =
              place.osm_url ||
              `https://www.openstreetmap.org/?mlat=${encodeURIComponent(
                place.latitude
              )}&mlon=${encodeURIComponent(place.longitude)}#map=16/${encodeURIComponent(
                place.latitude
              )}/${encodeURIComponent(place.longitude)}`;

            return (
              <article
                key={`${place.name}-${place.latitude}-${place.longitude}-${index}`}
                className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {place.name}
                  </h3>

                  <span className="shrink-0 rounded-lg bg-blue-50 px-2 py-1 text-xs font-medium capitalize text-blue-700">
                    {place.category || "Place"}
                  </span>
                </div>

                <p className="mb-4 text-sm leading-6 text-gray-600">
                  {place.description ||
                    "Place information from OpenStreetMap."}
                </p>

                {Number.isFinite(Number(place.latitude)) &&
                  Number.isFinite(Number(place.longitude)) && (
                    <p className="mb-4 text-xs text-gray-500">
                      Coordinates: {place.latitude}, {place.longitude}
                    </p>
                  )}

                <a
                  href={mapUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
                >
                  View on OpenStreetMap ↗
                </a>

                <p className="mt-4 border-t pt-3 text-xs text-amber-700">
                  {place.verified_tourist_attraction === true
                    ? "Marked as verified by the data provider."
                    : "Tourist suitability and current visitor access have not been independently verified."}
                </p>
              </article>
            );
          })}
        </div>
      )}

      <p className="mt-4 text-xs text-gray-500">
        Map data © OpenStreetMap contributors. Places and access information
        may be incomplete or outdated.
      </p>
    </section>
  );
}
