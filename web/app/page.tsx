import Link from "next/link";
import { Suspense } from "react";

import { PublicCatalogueClient } from "./public-catalogue-client";

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Public Catalogue</p>
        <h1>Research Opportunities, De-duplicated</h1>
        <p>
          Search and browse moderated opportunities with filters, sorting, and posting previews. Results come from the
          live `GET /postings` API contract.
        </p>

        <div className="actions">
          <Link className="inline-link" href="/admin/cockpit">
            Open moderator cockpit
          </Link>
        </div>
      </section>

      <Suspense fallback={<section className="catalogue-shell">Loading catalogue...</section>}>
        <PublicCatalogueClient />
      </Suspense>
    </main>
  );
}
