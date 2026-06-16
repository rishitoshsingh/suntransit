export default function AboutModal({ onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card glass" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>

        <div className="modal-section">
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <img src="/logo.png" alt="SunTransit" style={{ height: 48, width: "auto", objectFit: "contain" }} />
            <div>
              <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: ".2px" }}>SunTransit</div>
              <div style={{ fontSize: 12, color: "var(--text-dim)", fontWeight: 500 }}>transit intelligence</div>
            </div>
          </div>
          <p className="modal-text">
            Real-time transit intelligence for <strong>Valley Metro</strong> (Phoenix, AZ) and the{" "}
            <strong>Massachusetts Bay Transportation Authority (MBTA)</strong> (Boston, MA).
            Tracks live bus positions, detects bunching, computes stop and route delay
            trends, and visualises performance as an H3 hex heatmap, all powered by a
            Kafka + Spark + PostgreSQL pipeline running on a personal server.
          </p>
        </div>

        <div className="modal-divider" />

        <div className="modal-section">
          <div className="modal-label">Tech stack</div>
          <div className="modal-tags">
            {["Kafka", "Apache Spark", "PostgreSQL", "Redis", "FastAPI", "React", "MapLibre GL", "H3", "Docker"].map((t) => (
              <span key={t} className="modal-tag">{t}</span>
            ))}
          </div>
        </div>

        <div className="modal-divider" />

        <div className="modal-section">
          <div className="modal-label">Built by</div>
          <p className="modal-text" style={{ marginBottom: 14 }}>
            <strong>Rishitosh Kumar Singh</strong>
          </p>
          <a href="https://github.com/rishitoshsingh/suntransit" target="_blank" rel="noopener noreferrer" className="modal-star">
            <StarIcon /> Star this project on GitHub
          </a>

          <div className="modal-links">
            <a href="https://github.com/rishitoshsingh/suntransit" target="_blank" rel="noopener noreferrer" className="modal-link">
              <GitHubIcon /> Source code
            </a>
            <a href="https://rishitoshsingh.is-a.dev/suntransit/" target="_blank" rel="noopener noreferrer" className="modal-link">
              <LinkIcon /> Project page
            </a>
            <a href="https://rishitoshsingh.is-a.dev/" target="_blank" rel="noopener noreferrer" className="modal-link">
              <LinkIcon /> Portfolio
            </a>
            <a href="https://github.com/rishitoshsingh" target="_blank" rel="noopener noreferrer" className="modal-link">
              <GitHubIcon /> GitHub
            </a>
            <a href="https://linkedin.com/in/rishitoshsingh" target="_blank" rel="noopener noreferrer" className="modal-link">
              <LinkedInIcon /> LinkedIn
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function StarIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.295 24 12c0-6.63-5.37-12-12-12" />
    </svg>
  );
}

function LinkedInIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}
