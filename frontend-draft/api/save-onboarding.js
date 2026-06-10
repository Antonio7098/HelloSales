/**
 * /api/save-onboarding — persists a user's onboarding answers to git.
 * /Oliviercontribution.
 *
 * Vercel serverless function. On onboarding completion the frontend POSTs the
 * user's full answer set here; we commit it as users/<profileId>.json to the
 * git-backed data store (MarketersTerminal/hello-sales-data) via the GitHub
 * Contents API. This gives genuine per-user persistence without a database.
 *
 * Env required (set in Vercel project settings):
 *   GITHUB_TOKEN — a token with write access to the data repo.
 *
 * Body: { profileId, name, email, companyName, role, responses, progress }
 */

const OWNER = "MarketersTerminal";
const REPO = "hello-sales-data";
const BRANCH = "main";

function slug(s) {
  return String(s || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "method_not_allowed" });
    return;
  }

  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    res.status(500).json({ ok: false, error: "GITHUB_TOKEN not configured" });
    return;
  }

  let body = req.body;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      body = {};
    }
  }
  body = body || {};

  const profileId = body.profileId || slug(body.email) || `anon-${Date.now()}`;
  const path = `users/${slug(profileId)}.json`;

  const record = {
    profile_id: profileId,
    name: body.name ?? null,
    email: body.email ?? null,
    company_name: body.companyName ?? null,
    role: body.role ?? null,
    progress: body.progress ?? null,
    responses: Array.isArray(body.responses) ? body.responses : [],
    answered_count: Array.isArray(body.responses)
      ? body.responses.filter((r) => (r.response_value ?? "").toString().trim() !== "").length
      : 0,
    saved_at: new Date().toISOString(),
  };

  const apiBase = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${path}`;
  const ghHeaders = {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "User-Agent": "hello-sales-onboarding",
    "X-GitHub-Api-Version": "2022-11-28",
  };

  try {
    // Look up existing file SHA (required to update an existing file).
    let sha;
    const head = await fetch(`${apiBase}?ref=${BRANCH}`, { headers: ghHeaders });
    if (head.status === 200) {
      const existing = await head.json();
      sha = existing.sha;
    }

    const content = Buffer.from(JSON.stringify(record, null, 2) + "\n", "utf8").toString("base64");
    const put = await fetch(apiBase, {
      method: "PUT",
      headers: { ...ghHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({
        message: `onboarding: ${record.company_name || profileId} (${record.answered_count} answers)`,
        content,
        branch: BRANCH,
        ...(sha ? { sha } : {}),
        committer: { name: "Hello Sales Bot", email: "onboarding@hellosales.app" },
      }),
    });

    if (!put.ok) {
      const detail = await put.text();
      res.status(502).json({ ok: false, error: "github_write_failed", detail: detail.slice(0, 300) });
      return;
    }

    const result = await put.json();
    res.status(200).json({
      ok: true,
      path,
      commit: result?.commit?.sha ?? null,
      answered: record.answered_count,
    });
  } catch (err) {
    res.status(500).json({ ok: false, error: "exception", detail: String(err).slice(0, 300) });
  }
}
