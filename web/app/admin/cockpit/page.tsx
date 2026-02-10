import Link from "next/link";

import { ModeratorCockpitClient } from "./moderator-cockpit-client";

export default function ModeratorCockpitPage(): JSX.Element {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Admin + Moderation</p>
        <h1>Operator Cockpit</h1>
        <p>
          Candidate queue actions (`approve/reject/merge/override`) plus operator visibility for modules and jobs.
        </p>
        <p>
          <Link href="/admin/source-trust-policy" className="inline-link">
            Open source trust policy console
          </Link>
        </p>
        <p>
          <Link href="/" className="inline-link">
            Back to catalogue
          </Link>
        </p>
      </section>

      <ModeratorCockpitClient />
    </main>
  );
}
