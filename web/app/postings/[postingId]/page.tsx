import Link from "next/link";
import { notFound } from "next/navigation";

import { forwardPublicRequest } from "../../../lib/public-api-core";
import { buildPostingDetailPath } from "../../../lib/public-proxy-paths";

type PostingStatus = "active" | "stale" | "archived" | "closed";

type PostingDetail = {
  id: string;
  title: string;
  canonical_url: string;
  organization_name: string;
  status: PostingStatus;
  country: string | null;
  city: string | null;
  region: string | null;
  remote: boolean;
  tags: string[];
  description_text: string | null;
  application_url: string | null;
  deadline: string | null;
  published_at: string | null;
  updated_at: string;
};

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "-";
  }
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString();
}

function asPostingDetail(payload: unknown): PostingDetail | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const row = payload as Partial<PostingDetail>;
  if (
    typeof row.id !== "string" ||
    typeof row.title !== "string" ||
    typeof row.organization_name !== "string" ||
    typeof row.canonical_url !== "string" ||
    typeof row.status !== "string"
  ) {
    return null;
  }
  return {
    id: row.id,
    title: row.title,
    canonical_url: row.canonical_url,
    organization_name: row.organization_name,
    status: row.status as PostingStatus,
    country: typeof row.country === "string" ? row.country : null,
    city: typeof row.city === "string" ? row.city : null,
    region: typeof row.region === "string" ? row.region : null,
    remote: Boolean(row.remote),
    tags: Array.isArray(row.tags) ? row.tags.filter((item): item is string => typeof item === "string") : [],
    description_text: typeof row.description_text === "string" ? row.description_text : null,
    application_url: typeof row.application_url === "string" ? row.application_url : null,
    deadline: typeof row.deadline === "string" ? row.deadline : null,
    published_at: typeof row.published_at === "string" ? row.published_at : null,
    updated_at: typeof row.updated_at === "string" ? row.updated_at : ""
  };
}

export default async function PostingDetailPage({
  params
}: {
  params: Promise<{ postingId: string }>;
}): Promise<JSX.Element> {
  const { postingId } = await params;
  const response = await forwardPublicRequest(buildPostingDetailPath(postingId), { method: "GET" });

  if (response.status === 404) {
    notFound();
  }
  if (response.status !== 200) {
    throw new Error("Failed to load posting detail.");
  }

  const posting = asPostingDetail(response.payload);
  if (!posting) {
    throw new Error("Posting detail response is invalid.");
  }

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Public Catalogue</p>
        <h1>{posting.title}</h1>
        <p>
          {posting.organization_name}
          {posting.country ? ` · ${posting.country}` : ""}
          {posting.region ? ` · ${posting.region}` : ""}
          {posting.city ? ` · ${posting.city}` : ""}
          {posting.remote ? " · remote" : ""}
        </p>
        <p className="status">Status: {posting.status}</p>
        <p className="status">Published: {formatTimestamp(posting.published_at)}</p>
        <p className="status">Updated: {formatTimestamp(posting.updated_at)}</p>
        <p className="status">Deadline: {formatTimestamp(posting.deadline)}</p>
        <div className="actions">
          <a className="inline-link" href={posting.canonical_url} target="_blank" rel="noreferrer">
            Open source
          </a>
          {posting.application_url ? (
            <a className="inline-link" href={posting.application_url} target="_blank" rel="noreferrer">
              Apply
            </a>
          ) : null}
          <Link className="inline-link" href="/">
            Back to catalogue
          </Link>
          <Link className="inline-link" href={`/?organization_name=${encodeURIComponent(posting.organization_name)}`}>
            More from this org
          </Link>
          {posting.tags[0] ? (
            <Link className="inline-link" href={`/?tag=${encodeURIComponent(posting.tags[0])}`}>
              Related by tag
            </Link>
          ) : null}
        </div>
      </section>

      <section className="catalogue-shell">
        <article className="card detail-card">
          {posting.description_text ? <p>{posting.description_text}</p> : <p className="status">No description provided.</p>}
          {posting.tags.length > 0 ? (
            <div className="tag-row">
              {posting.tags.map((tag) => (
                <span key={`${posting.id}-${tag}`} className="badge">
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </article>
      </section>
    </main>
  );
}
