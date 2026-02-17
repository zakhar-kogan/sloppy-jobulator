import { Suspense } from "react";

import { PublicCatalogueClient } from "./public-catalogue-client";

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <h1>Sloppy Jobulator</h1>
        <p>Search and browse moderated research opportunities.</p>
      </section>

      <Suspense fallback={<section className="catalogue-shell">Loading catalogue...</section>}>
        <PublicCatalogueClient />
      </Suspense>
    </main>
  );
}
