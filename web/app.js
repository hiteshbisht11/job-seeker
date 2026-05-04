// Job Seeker — upload + per-resume matching frontend (no auth).
//
// Flow:
//   1. Land on upload screen
//   2. Pick PDF → POST /api/match (multipart)
//   3. Render scored jobs returned by the server

(() => {
  const state = {
    profile: null,
    jobs: [],
    selectedFile: null,
    filter: { scope: "all", priority: "all", search: "", sort: "fit-desc" },
  };

  document.addEventListener("DOMContentLoaded", () => {
    bindUI();
    showScreen("welcome");
  });

  function bindUI() {
    document.getElementById("getStartedBtn").addEventListener("click", () => showScreen("upload"));
    document.getElementById("backToWelcomeBtn").addEventListener("click", () => showScreen("welcome"));

    document.getElementById("reuploadBtn").addEventListener("click", () => {
      // Reset file selection so re-uploading the same file still triggers change
      const input = document.getElementById("resumeInput");
      input.value = "";
      state.selectedFile = null;
      document.getElementById("fileName").textContent = "";
      document.getElementById("dropLabel").textContent = "Click or drop a PDF here";
      document.getElementById("analyzeBtn").disabled = true;
      showUploadError("");
      showScreen("upload");
    });

    const fileInput = document.getElementById("resumeInput");
    const dropZone  = document.getElementById("dropZone");
    fileInput.addEventListener("change", e => setFile(e.target.files[0]));
    ["dragover","dragenter"].forEach(evt => dropZone.addEventListener(evt, e => {
      e.preventDefault(); dropZone.classList.add("border-indigo-500","bg-indigo-50/50");
    }));
    ["dragleave","drop"].forEach(evt => dropZone.addEventListener(evt, e => {
      e.preventDefault(); dropZone.classList.remove("border-indigo-500","bg-indigo-50/50");
    }));
    dropZone.addEventListener("drop", e => {
      const f = e.dataTransfer?.files?.[0];
      if (f) setFile(f);
    });

    document.getElementById("analyzeBtn").addEventListener("click", analyzeResume);

    document.getElementById("searchInput").addEventListener("input", e => {
      state.filter.search = e.target.value.trim().toLowerCase();
      renderJobs();
    });
    document.getElementById("sortSelect").addEventListener("change", e => {
      state.filter.sort = e.target.value;
      renderJobs();
    });
    document.querySelectorAll("#scopeFilters [data-scope]").forEach(btn =>
      btn.addEventListener("click", () => {
        state.filter.scope = btn.dataset.scope;
        document.querySelectorAll("#scopeFilters [data-scope]").forEach(b => b.classList.toggle("chip-active", b.dataset.scope === state.filter.scope));
        renderJobs();
      }));
    document.querySelectorAll("#priorityFilters [data-priority]").forEach(btn =>
      btn.addEventListener("click", () => {
        state.filter.priority = btn.dataset.priority;
        document.querySelectorAll("#priorityFilters [data-priority]").forEach(b => b.classList.toggle("chip-active", b.dataset.priority === state.filter.priority));
        renderJobs();
      }));

    document.getElementById("modal").addEventListener("click", e => {
      if (e.target.id === "modal") closeModal();
    });
    document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
  }

  // ---- Resume upload ------------------------------------------------------
  function setFile(file) {
    if (!file) return;
    if (file.type !== "application/pdf") {
      showUploadError("Please pick a PDF file.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      showUploadError("File is over 5 MB.");
      return;
    }
    state.selectedFile = file;
    document.getElementById("fileName").textContent = file.name;
    document.getElementById("dropLabel").textContent = "Click to change file";
    document.getElementById("analyzeBtn").disabled = false;
    showUploadError("");
  }

  async function analyzeResume() {
    if (!state.selectedFile) return;
    const btn = document.getElementById("analyzeBtn");
    btn.disabled = true;
    document.getElementById("uploadProgress").classList.remove("hidden");
    showUploadError("");

    const fd = new FormData();
    fd.append("resume", state.selectedFile);
    try {
      const res = await fetch("/api/match", { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      state.profile = data.profile;
      state.jobs = data.jobs;
      showScreen("dashboard");
      renderDashboard();
    } catch (e) {
      showUploadError(e.message || "Upload failed.");
    } finally {
      btn.disabled = false;
      document.getElementById("uploadProgress").classList.add("hidden");
    }
  }

  // ---- Screen switcher ----------------------------------------------------
  function showScreen(name) {
    for (const s of ["welcome", "upload", "dashboard"]) {
      document.getElementById(`screen-${s}`).classList.toggle("hidden", s !== name);
    }
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  function showUploadError(msg) {
    const el = document.getElementById("uploadError");
    el.textContent = msg;
    el.classList.toggle("hidden", !msg);
  }

  // ---- Dashboard rendering ------------------------------------------------
  function renderDashboard() {
    const subtitleParts = [
      `${state.profile.skills.length} skills detected`,
      `${state.profile.years_experience} yrs experience`,
    ];
    if (state.profile.name_hint) subtitleParts.unshift(state.profile.name_hint);
    document.getElementById("dashSubtitle").textContent = subtitleParts.join(" · ");

    document.getElementById("profileSkills").innerHTML =
      state.profile.skills.map(s => `<span class="pill-skill-have mr-1 mb-1">${escape(s)}</span>`).join(" ")
      || "<span class='text-slate-400 text-xs'>(none detected)</span>";
    renderStats();
    renderJobs();
  }

  function renderStats() {
    const total   = state.jobs.length;
    const high    = state.jobs.filter(j => j.priority === "High").length;
    const med     = state.jobs.filter(j => j.priority === "Medium").length;
    const stretch = state.jobs.filter(j => j.priority === "Stretch").length;
    const remote  = state.jobs.filter(j => j.scope === "Worldwide Remote").length;
    const india   = state.jobs.filter(j => j.scope === "India").length;

    document.getElementById("statsBar").innerHTML = [
      stat("Total roles",     total,   "bg-slate-100 text-slate-800"),
      stat("High priority",   high,    "bg-emerald-100 text-emerald-800"),
      stat("Medium",          med,     "bg-amber-100 text-amber-800"),
      stat("Stretch",         stretch, "bg-rose-100 text-rose-800"),
      stat("India",           india,   "bg-blue-100 text-blue-800"),
      stat("Remote (global)", remote,  "bg-indigo-100 text-indigo-800"),
    ].join("");
    document.getElementById("cnt-all").textContent    = total;
    document.getElementById("cnt-india").textContent  = india;
    document.getElementById("cnt-remote").textContent = remote;
  }

  function stat(label, value, cls) {
    return `<div class="rounded-lg p-3 ${cls}">
      <div class="text-2xl font-bold leading-none">${value}</div>
      <div class="text-xs mt-1 font-medium opacity-80">${label}</div>
    </div>`;
  }

  function filterJobs() {
    const { scope, priority, search, sort } = state.filter;
    let out = state.jobs.slice();
    if (scope === "india")  out = out.filter(j => j.scope === "India");
    if (scope === "remote") out = out.filter(j => j.scope === "Worldwide Remote");
    if (priority !== "all") out = out.filter(j => j.priority === priority);
    if (search) {
      out = out.filter(j =>
        (j.company + " " + j.role + " " + j.key_requirements + " " + j.why_fit + " " + j.location + " " + j.category)
        .toLowerCase().includes(search));
    }
    out.sort((a, b) => {
      switch (sort) {
        case "fit-desc":     return b.fit_score - a.fit_score;
        case "fit-asc":      return a.fit_score - b.fit_score;
        case "company-asc":  return a.company.localeCompare(b.company);
      }
    });
    return out;
  }

  function fitColor(score) {
    if (score >= 75) return "bg-emerald-500 text-white";
    if (score >= 60) return "bg-emerald-100 text-emerald-800 border border-emerald-300";
    if (score >= 45) return "bg-amber-100 text-amber-800 border border-amber-300";
    return "bg-rose-100 text-rose-800 border border-rose-300";
  }

  function renderJobs() {
    const jobs = filterJobs();
    const grid = document.getElementById("jobsGrid");
    document.getElementById("emptyState").classList.toggle("hidden", jobs.length > 0);
    grid.innerHTML = jobs.map((j, i) => jobCard(j, i)).join("");
    grid.querySelectorAll("[data-job-idx]").forEach(card => {
      card.addEventListener("click", e => {
        if (e.target.closest("a, button")) return;
        openModal(jobs[+card.dataset.jobIdx]);
      });
    });
  }

  function jobCard(j, idx) {
    const compBand = j.comp_band_inr ? `<span class="text-xs text-emerald-700 font-medium">💰 ${escape(j.comp_band_inr)}</span>` : "";
    const matched = (j.matched_skills || []).slice(0, 6).map(s => `<span class="pill-skill-have">${escape(s)}</span>`).join(" ");
    return `
      <div class="job-card" data-job-idx="${idx}">
        <div class="flex items-start gap-3">
          <div class="fit-badge ${fitColor(j.fit_score)}">${j.fit_score}</div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="priority-pill priority-${j.priority}">${j.priority}</span>
              <span class="text-xs text-slate-500">${escape(j.scope)}</span>
            </div>
            <div class="font-semibold text-base mt-1 truncate">${escape(j.company)}</div>
            <div class="text-sm text-slate-700 line-clamp-2">${escape(j.role)}</div>
          </div>
        </div>
        <div class="text-xs text-slate-500 flex flex-wrap gap-x-3 gap-y-1">
          <span>📍 ${escape(j.location)}</span>
          <span>👤 ${escape(j.experience)}</span>
          ${compBand}
        </div>
        <div class="flex flex-wrap gap-1">${matched}</div>
        <div class="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
          <a href="${j.primary_link}" target="_blank" rel="noopener" class="text-xs px-2.5 py-1.5 rounded-md bg-indigo-600 text-white hover:bg-indigo-700">Careers ↗</a>
          <a href="${j.search_link}"  target="_blank" rel="noopener" class="text-xs px-2.5 py-1.5 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50">Search ↗</a>
        </div>
      </div>`;
  }

  function openModal(j) {
    const compBand = j.comp_band_inr ? `<div><dt class="text-xs uppercase tracking-wide text-slate-500">Comp band</dt><dd class="font-medium text-emerald-700">${escape(j.comp_band_inr)}</dd></div>` : "";
    const matched = (j.matched_skills || []).map(s => `<span class="pill-skill-have">${escape(s)}</span>`).join(" ") || "<span class='text-slate-400 text-xs'>none</span>";
    const missing = (j.missing_skills || []).map(s => `<span class="pill-skill-miss">${escape(s)}</span>`).join(" ") || "<span class='text-slate-400 text-xs'>none</span>";
    const b = j.breakdown || {};

    document.getElementById("modalContent").innerHTML = `
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-start gap-3">
          <div class="fit-badge ${fitColor(j.fit_score)}">${j.fit_score}</div>
          <div>
            <span class="priority-pill priority-${j.priority}">${j.priority}</span>
            <span class="text-xs text-slate-500 ml-2">${escape(j.scope)}</span>
            <h2 class="text-xl font-bold mt-2">${escape(j.company)}</h2>
            <p class="text-slate-700">${escape(j.role)}</p>
          </div>
        </div>
        <button onclick="document.getElementById('modal').classList.add('hidden')"
                class="text-slate-400 hover:text-slate-700 text-2xl leading-none">×</button>
      </div>

      <dl class="grid grid-cols-2 gap-4 mt-5 text-sm">
        <div><dt class="text-xs uppercase tracking-wide text-slate-500">Location</dt><dd class="font-medium">${escape(j.location)}</dd></div>
        <div><dt class="text-xs uppercase tracking-wide text-slate-500">Experience</dt><dd class="font-medium">${escape(j.experience)}</dd></div>
        <div><dt class="text-xs uppercase tracking-wide text-slate-500">Category</dt><dd class="font-medium">${escape(j.category)}</dd></div>
        ${compBand}
      </dl>

      <div class="mt-5">
        <h3 class="text-xs uppercase tracking-wide text-slate-500 mb-2">Matched skills</h3>
        <div class="flex flex-wrap gap-1">${matched}</div>
      </div>
      <div class="mt-3">
        <h3 class="text-xs uppercase tracking-wide text-slate-500 mb-2">Skills the role expects but I didn't detect</h3>
        <div class="flex flex-wrap gap-1">${missing}</div>
      </div>

      <div class="mt-5">
        <h3 class="text-xs uppercase tracking-wide text-slate-500 mb-2">Score breakdown</h3>
        <div class="grid grid-cols-4 gap-2 text-sm">
          ${scoreCell("Skill recall",  b.skill_recall, 50)}
          ${scoreCell("Breadth",       b.skill_breadth, 15)}
          ${scoreCell("Experience",    b.experience, 20)}
          ${scoreCell("Title fit",     b.title, 15)}
        </div>
      </div>

      <div class="mt-5">
        <h3 class="text-xs uppercase tracking-wide text-slate-500 mb-1">Why this is curated</h3>
        <p class="text-sm leading-relaxed">${escape(j.why_fit)}</p>
      </div>

      <div class="mt-6 flex items-center gap-2">
        <a href="${j.primary_link}" target="_blank" rel="noopener" class="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700">Open careers page ↗</a>
        <a href="${j.search_link}"  target="_blank" rel="noopener" class="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50">Open job search ↗</a>
      </div>`;
    document.getElementById("modal").classList.remove("hidden");
  }
  function closeModal() { document.getElementById("modal").classList.add("hidden"); }
  function scoreCell(label, value, max) {
    const v = value ?? 0;
    return `<div class="rounded-md border border-slate-200 p-2 text-center">
      <div class="text-base font-semibold">${v} / ${max}</div>
      <div class="text-[10px] uppercase tracking-wide text-slate-500 mt-0.5">${label}</div>
    </div>`;
  }

  function escape(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
  }
})();
