import Link from "next/link";

import { SourceTrustPolicyAdminClient } from "./source-trust-policy-admin";

export default function SourceTrustPolicyAdminPage(): JSX.Element {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Admin</p>
        <h1>Source Trust Policy Console</h1>
        <p>
          Manage trust-policy routing against <code>/admin/source-trust-policy</code> (list, upsert, enable toggle).
        </p>
        <Link href="/admin/cockpit" className="inline-link">
          Open moderator cockpit
        </Link>
        <Link href="/" className="inline-link">
          Back to catalogue
        </Link>
      </section>

      <SourceTrustPolicyAdminClient />
    </main>
  );
}
