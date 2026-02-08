const sampleRows = [
  {
    title: "Research Assistant in Computational Biology",
    org: "Example University",
    status: "active"
  },
  {
    title: "PhD Scholarship in Robotics",
    org: "Sample Institute of Technology",
    status: "active"
  }
];

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <h1>Research Opportunities, De-duplicated</h1>
        <p>
          Bootstrap catalogue UI connected to v1 API contracts. Search, filter, and moderation surfaces follow in
          upcoming phases.
        </p>

        <div className="controls">
          <div className="control">
            <label htmlFor="search">Search</label>
            <input id="search" placeholder="keyword, organization, field" />
          </div>
          <div className="control">
            <label htmlFor="sector">Sector</label>
            <select id="sector" defaultValue="all">
              <option value="all">All sectors</option>
              <option value="academia">Academia</option>
              <option value="industry">Industry</option>
            </select>
          </div>
          <div className="control">
            <label htmlFor="degree">Degree</label>
            <select id="degree" defaultValue="all">
              <option value="all">All levels</option>
              <option value="bachelors">Bachelors</option>
              <option value="masters">Masters</option>
              <option value="phd">PhD</option>
            </select>
          </div>
        </div>
      </section>

      <section className="grid" aria-label="posting list">
        {sampleRows.map((row) => (
          <article className="card" key={row.title}>
            <h3>{row.title}</h3>
            <p>{row.org}</p>
            <span className="badge">{row.status}</span>
          </article>
        ))}
      </section>
    </main>
  );
}
