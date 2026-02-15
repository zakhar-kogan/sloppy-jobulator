import Link from "next/link";

import { URLNormalizationOverridesAdminClient } from "./url-normalization-overrides-admin";

export default function URLNormalizationOverridesPage(): JSX.Element {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Admin</p>
        <h1>URL Normalization Overrides</h1>
        <p>
          Manage per-domain URL normalization behavior against <code>/admin/url-normalization-overrides</code> (list,
          upsert, enable toggle).
        </p>
        <p>
          <Link href="/admin/cockpit" className="inline-link">
            Back to operator cockpit
          </Link>
        </p>
      </section>

      <URLNormalizationOverridesAdminClient />
    </main>
  );
}
