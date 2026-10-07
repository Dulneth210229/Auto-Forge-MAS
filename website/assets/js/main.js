/* ==========================================================================
   AutoForge website - behaviour
   Shared on every page: theme, mobile menu, search, reveal, back-to-top.
   Page-specific renderers run only when their container exists.
   Content comes from window.SITE (assets/js/data.js).
   ========================================================================== */
(function () {
  "use strict";

  var SITE = window.SITE || { members: [], supervisors: [], documents: [], presentations: [], milestones: [], project: {} };
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  var ICON = {
    mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
    eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    ext: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 4h6v6"/><path d="M20 4 10 14"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/></svg>',
    clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>'
  };

  /* -------------------------------------------------------------- storage */
  function store(key, val) {
    try {
      if (val === undefined) return window.localStorage.getItem(key);
      window.localStorage.setItem(key, val);
    } catch (e) { /* storage unavailable - ignore */ }
    return null;
  }

  /* ---------------------------------------------------------------- theme */
  function initTheme() {
    var btn = $("#theme-toggle");
    if (!btn) return;
    function current() { return document.documentElement.getAttribute("data-theme") || "light"; }
    function sync() {
      var dark = current() === "dark";
      btn.setAttribute("aria-pressed", dark ? "true" : "false");
      btn.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
    }
    sync();
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      store("af-theme", next);
      sync();
    });
  }

  /* ----------------------------------------------------------- mobile nav */
  function initMenu() {
    var btn = $("#menu-toggle"), nav = $("#site-nav");
    if (!btn || !nav) return;
    function set(open) {
      nav.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    }
    btn.addEventListener("click", function () { set(!nav.classList.contains("is-open")); });
    nav.addEventListener("click", function (e) { if (e.target.closest("a")) set(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") set(false); });
    window.addEventListener("resize", function () { if (window.innerWidth > 960) set(false); });
  }

  /* --------------------------------------------------------------- search */
  var PAGES = [
    { t: "Home", u: "index.html", d: "Overview, abstract and key results of AutoForge" },
    { t: "Abstract", u: "index.html#abstract", d: "What AutoForge is and why it matters" },
    { t: "Key results", u: "index.html#results", d: "RAG ablation, security precision and recall, checkpoint recovery, QA" },
    { t: "Domain", u: "domain.html", d: "Literature survey, research gap, problem, objectives, methodology, technologies" },
    { t: "Literature survey", u: "domain.html#literature", d: "ChatDev, MetaGPT, SWE-agent, OpenHands, AgentCoder, HULA" },
    { t: "Research gap", u: "domain.html#gap", d: "No stage-by-stage human approval with durable resume" },
    { t: "Research problem", u: "domain.html#problem", d: "Controlled, reviewable LLM-assisted software development" },
    { t: "Research objectives", u: "domain.html#objectives", d: "O1 versioned artifacts, O2 durable resume, O3 verified pipeline" },
    { t: "Methodology", u: "domain.html#methodology", d: "Design-science, seven agents, LangGraph, evaluation plan" },
    { t: "Technologies used", u: "domain.html#technologies", d: "FastAPI, LangGraph, MongoDB, ChromaDB, Ollama, React, Docker, Playwright" },
    { t: "Milestones", u: "milestones.html", d: "Proposal, progress presentations, final assessment, viva" },
    { t: "Documents", u: "documents.html", d: "Project charter, proposal, check lists, research paper, final reports" },
    { t: "Presentations", u: "presentations.html", d: "Proposal, Progress Presentation 1 and 2, final slides" },
    { t: "About us", u: "about.html", d: "Team members, supervisors, contributions" },
    { t: "Contact us", u: "contact.html", d: "Emails, phone numbers and a general email template" }
  ];

  function buildIndex() {
    var idx = PAGES.slice();
    (SITE.members || []).forEach(function (m) {
      idx.push({ t: m.name, u: "about.html#" + m.id, d: m.studentId + " - " + m.component + " " + (m.agents || []).join(" ") + " " + m.email });
    });
    (SITE.supervisors || []).forEach(function (s) { idx.push({ t: s.name, u: "about.html#supervisors", d: s.role }); });
    (SITE.documents || []).forEach(function (x) { idx.push({ t: x.title, u: "documents.html#" + x.id, d: x.group + " - " + x.description }); });
    (SITE.presentations || []).forEach(function (x) { idx.push({ t: x.title, u: "presentations.html#" + x.id, d: x.description }); });
    (SITE.milestones || []).forEach(function (x) { idx.push({ t: x.title + " (milestone)", u: "milestones.html?m=" + x.id, d: x.summary }); });
    return idx;
  }

  function initSearch() {
    var dlg = $("#search"), input = $("#search-input"), list = $("#search-results");
    if (!dlg || !input || !list) return;
    var index = buildIndex(), focused = -1, lastFocus = null;

    function open() {
      lastFocus = document.activeElement;
      dlg.classList.add("is-open");
      dlg.setAttribute("aria-hidden", "false");
      input.value = "";
      render("");
      setTimeout(function () { input.focus(); }, 20);
    }
    function close() {
      dlg.classList.remove("is-open");
      dlg.setAttribute("aria-hidden", "true");
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    function render(q) {
      q = q.trim().toLowerCase();
      var terms = q.split(/\s+/).filter(Boolean);
      var hits = index.filter(function (r) {
        var hay = (r.t + " " + r.d).toLowerCase();
        return terms.every(function (w) { return hay.indexOf(w) !== -1; });
      }).slice(0, 12);
      if (!q) hits = PAGES.filter(function (p) { return p.u.indexOf("#") === -1; });
      focused = -1;
      if (!hits.length) { list.innerHTML = '<li class="search__empty">No results for "' + esc(q) + '"</li>'; return; }
      list.innerHTML = hits.map(function (r) {
        return '<li><a href="' + esc(r.u) + '">' + esc(r.t) + "<small>" + esc(r.d) + "</small></a></li>";
      }).join("");
    }
    function move(step) {
      var links = $$("a", list);
      if (!links.length) return;
      focused = (focused + step + links.length) % links.length;
      links.forEach(function (a, i) { a.classList.toggle("is-focused", i === focused); });
      links[focused].scrollIntoView({ block: "nearest" });
    }

    $$("[data-open-search]").forEach(function (b) { b.addEventListener("click", open); });
    $$("[data-close-search]").forEach(function (b) { b.addEventListener("click", close); });
    list.addEventListener("click", function (e) { if (e.target.closest("a")) close(); });
    input.addEventListener("input", function () { render(input.value); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
      else if (e.key === "Enter") {
        var links = $$("a", list), target = links[focused >= 0 ? focused : 0];
        if (target) { e.preventDefault(); close(); window.location.href = target.getAttribute("href"); }
      }
    });
    document.addEventListener("keydown", function (e) {
      var typing = /input|textarea|select/i.test((e.target && e.target.tagName) || "");
      if ((e.key === "k" && (e.ctrlKey || e.metaKey)) || (e.key === "/" && !typing)) { e.preventDefault(); open(); }
      else if (e.key === "Escape" && dlg.classList.contains("is-open")) close();
    });
  }

  /* -------------------------------------------------- reveal + to-top */
  function initReveal() {
    var els = $$(".reveal");
    if (!("IntersectionObserver" in window)) { els.forEach(function (el) { el.classList.add("is-visible"); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("is-visible"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    els.forEach(function (el) { io.observe(el); });
  }
  function initToTop() {
    var btn = $("#to-top");
    if (!btn) return;
    window.addEventListener("scroll", function () { btn.classList.toggle("is-visible", window.scrollY > 600); }, { passive: true });
    btn.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
  }
  function initYear() { $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); }); }

  /* -------------------------------------------- OneDrive link handling */
  function hasLink(item) { return !!(item && item.url && String(item.url).trim()); }
  function embedUrl(item) {
    if (!item) return "";
    if (item.embed) return item.embed;
    if (!hasLink(item)) return "";
    try {
      var u = new URL(item.url);
      var host = u.hostname.toLowerCase();
      if (/sharepoint\.com$/.test(host)) { u.searchParams.set("action", "embedview"); return u.toString(); }
      if (host === "onedrive.live.com") {
        u.pathname = u.pathname.replace(/^\/(redir|view\.aspx|edit\.aspx|\?)/i, "/embed");
        if (u.pathname.indexOf("/embed") !== 0) u.pathname = "/embed";
        return u.toString();
      }
      if (/docs\.google\.com$/.test(host)) return item.url.replace(/\/(edit|view)(\?.*)?$/, "/preview");
      if (/drive\.google\.com$/.test(host)) return item.url.replace(/\/view(\?.*)?$/, "/preview");
      if (/\.pdf($|\?)/i.test(u.pathname)) return item.url;
    } catch (e) { /* invalid URL */ }
    return "";
  }

  function actionButtons(item) {
    if (!hasLink(item)) {
      return '<span class="badge badge--muted">Link coming soon</span>';
    }
    var canView = !!embedUrl(item);
    var html = "";
    if (canView) html += '<button type="button" class="btn btn--sm" data-view="' + esc(item.id) + '">' + ICON.eye + "View</button>";
    html += '<a class="btn btn--sm btn--ghost" href="' + esc(item.url) + '" target="_blank" rel="noopener">' + ICON.ext + "Open in OneDrive</a>";
    return html;
  }

  function findItem(id) {
    var all = (SITE.documents || []).concat(SITE.presentations || []);
    for (var i = 0; i < all.length; i++) if (all[i].id === id) return all[i];
    return null;
  }

  /* --------------------------------------------------------------- viewer */
  function initViewer() {
    var v = $("#viewer");
    if (!v) return;
    var frame = $("#viewer-frame"), title = $("#viewer-title"), openLink = $("#viewer-open"), lastFocus = null;

    function open(item) {
      lastFocus = document.activeElement;
      title.textContent = item.title;
      openLink.href = item.url;
      var src = embedUrl(item);
      frame.innerHTML =
        '<div class="viewer__hint"><div><p><strong>Loading the preview...</strong></p>' +
        "<p>If it does not appear, the file may not allow embedding. Use <em>Open in OneDrive</em> instead.</p></div></div>" +
        '<iframe title="' + esc(item.title) + '" src="' + esc(src) + '" allowfullscreen loading="lazy"></iframe>';
      v.classList.add("is-open");
      v.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      $("#viewer-close").focus();
    }
    function close() {
      v.classList.remove("is-open");
      v.setAttribute("aria-hidden", "true");
      frame.innerHTML = "";
      document.body.style.overflow = "";
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    document.addEventListener("click", function (e) {
      var b = e.target.closest("[data-view]");
      if (b) { var item = findItem(b.getAttribute("data-view")); if (item) open(item); }
      if (e.target.closest("[data-close-viewer]")) close();
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && v.classList.contains("is-open")) close(); });
  }

  /* ------------------------------------------------------------ documents */
  function renderDocuments() {
    var root = $("#documents-list");
    if (!root) return;
    var docs = SITE.documents || [];
    var groups = [];
    docs.forEach(function (d) { if (groups.indexOf(d.group) === -1) groups.push(d.group); });

    var bar = $("#documents-filter");
    if (bar) {
      bar.innerHTML = ['All'].concat(groups).map(function (g, i) {
        return '<button type="button" data-filter="' + esc(i === 0 ? "*" : g) + '" aria-pressed="' + (i === 0) + '">' + esc(g) + "</button>";
      }).join("");
      bar.addEventListener("click", function (e) {
        var b = e.target.closest("button[data-filter]");
        if (!b) return;
        $$("button", bar).forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        var f = b.getAttribute("data-filter");
        $$("[data-group]", root).forEach(function (sec) { sec.hidden = !(f === "*" || sec.getAttribute("data-group") === f); });
      });
    }

    root.innerHTML = groups.map(function (g) {
      var items = docs.filter(function (d) { return d.group === g; });
      var ready = items.filter(hasLink).length;
      return '<section data-group="' + esc(g) + '">' +
        '<div class="doc-group-title"><h2>' + esc(g) + "</h2><span>" + ready + " of " + items.length + " available</span></div>" +
        '<div class="grid grid--2">' + items.map(function (d) {
          return '<article class="card card--hover doc-card" id="' + esc(d.id) + '">' +
            '<div class="doc-card__top"><div class="doc-card__type">' + esc(d.type || "PDF") + "</div>" +
            (hasLink(d) ? '<span class="badge badge--ok">Available</span>' : '<span class="badge badge--muted">Pending</span>') + "</div>" +
            "<h3>" + esc(d.title) + "</h3><p>" + esc(d.description) + "</p>" +
            (d.date ? '<span class="muted mono" style="font-size:.8rem">Submitted: ' + esc(d.date) + "</span>" : "") +
            '<div class="doc-card__actions">' + actionButtons(d) + "</div></article>";
        }).join("") + "</div></section>";
    }).join("");
  }

  /* -------------------------------------------------------- presentations */
  function renderPresentations() {
    var root = $("#presentations-list");
    if (!root) return;
    root.innerHTML = (SITE.presentations || []).map(function (p, i) {
      return '<article class="card deck" id="' + esc(p.id) + '">' +
        '<div class="deck__cover"><span class="deck__label">Slides</span><span class="deck__num">' + String(i + 1).padStart(2, "0") + "</span></div>" +
        '<div class="deck__body"><div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">' +
        '<h3 style="margin:0">' + esc(p.title) + "</h3>" +
        (hasLink(p) ? '<span class="badge badge--ok">Available</span>' : '<span class="badge badge--muted">Pending</span>') + "</div>" +
        "<p>" + esc(p.description) + "</p>" +
        (p.date ? '<span class="muted mono" style="font-size:.8rem">Presented: ' + esc(p.date) + "</span>" : "") +
        '<div class="doc-card__actions">' + actionButtons(p) + "</div></div></article>";
    }).join("");
  }

  /* ------------------------------------------------------------ milestones */
  var STATUS = {
    "completed": { cls: "badge--ok", label: "Completed" },
    "in-progress": { cls: "badge--warn", label: "In progress" },
    "upcoming": { cls: "badge--muted", label: "Upcoming" }
  };
  function badge(status) { var s = STATUS[status] || STATUS.upcoming; return '<span class="badge ' + s.cls + '">' + s.label + "</span>"; }
  function tbc(v) { return v ? esc(v) : '<span class="tbc">To be confirmed</span>'; }

  function renderMilestones() {
    var select = $("#milestone-select"), detail = $("#milestone-detail"), tl = $("#milestone-timeline");
    if (!select || !detail) return;
    var ms = SITE.milestones || [];
    select.innerHTML = ms.map(function (m, i) {
      return '<option value="' + esc(m.id) + '">' + (i + 1) + ". " + esc(m.title) + " - " + (STATUS[m.status] || STATUS.upcoming).label + "</option>";
    }).join("");

    if (tl) {
      tl.innerHTML = ms.map(function (m) {
        return '<li class="is-' + esc(m.status) + '" data-ms="' + esc(m.id) + '"><span class="timeline__dot"></span>' +
          '<button type="button" data-pick="' + esc(m.id) + '"><span class="timeline__title">' + esc(m.title) + "</span>" +
          '<span class="timeline__meta">' + (m.date ? esc(m.date) : "Date to be confirmed") + " &middot; " + (STATUS[m.status] || STATUS.upcoming).label + "</span></button></li>";
      }).join("");
      tl.addEventListener("click", function (e) {
        var b = e.target.closest("[data-pick]");
        if (b) { select.value = b.getAttribute("data-pick"); show(select.value, true); }
      });
    }

    function deliverableRow(id) {
      var it = findItem(id);
      if (!it) return "";
      return '<li style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:10px 0;border-bottom:1px solid var(--line);margin:0">' +
        "<span>" + esc(it.title) + "</span><span class=\"doc-card__actions\">" + actionButtons(it) + "</span></li>";
    }

    function show(id, push) {
      var m = null;
      ms.forEach(function (x) { if (x.id === id) m = x; });
      if (!m) m = ms[0];
      if (!m) return;
      detail.innerHTML =
        '<article class="card">' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">' +
        '<div><span class="card__kicker">Milestone ' + (ms.indexOf(m) + 1) + " of " + ms.length + "</span><h2 style=\"font-size:1.7rem;margin:0\">" + esc(m.title) + "</h2></div>" + badge(m.status) + "</div>" +
        '<div class="ms-facts">' +
        '<div class="ms-fact"><span>Date</span><strong>' + tbc(m.date) + "</strong></div>" +
        '<div class="ms-fact"><span>Marks allocated</span><strong>' + tbc(m.marks) + "</strong></div>" +
        '<div class="ms-fact"><span>Status</span><strong>' + (STATUS[m.status] || STATUS.upcoming).label + "</strong></div></div>" +
        "<p>" + esc(m.summary) + "</p>" +
        "<h3 style=\"margin-top:20px\">What is assessed</h3>" +
        '<ul class="check-list">' + (m.assessed || []).map(function (a) { return "<li>" + esc(a) + "</li>"; }).join("") + "</ul></article>" +
        '<aside class="card"><h3>Related documents</h3>' +
        ((m.deliverables || []).length
          ? '<ul style="list-style:none;padding:0;margin:0">' + m.deliverables.map(deliverableRow).join("") + "</ul>"
          : '<p class="muted">No document is submitted for this assessment. It is assessed in person.</p>') +
        "</aside>";
      if (tl) $$("li", tl).forEach(function (li) { li.classList.toggle("is-selected", li.getAttribute("data-ms") === m.id); });
      if (push && window.history && history.replaceState) {
        try { history.replaceState(null, "", "?m=" + encodeURIComponent(m.id)); } catch (e) { /* ignore */ }
      }
    }

    select.addEventListener("change", function () { show(select.value, true); });
    var initial = null;
    try { initial = new URLSearchParams(window.location.search).get("m"); } catch (e) { /* ignore */ }
    if (initial && ms.some(function (x) { return x.id === initial; })) select.value = initial;
    else {
      var current = ms.filter(function (x) { return x.status === "in-progress"; })[0];
      if (current) select.value = current.id;
    }
    show(select.value, false);

    var counts = $("#milestone-counts");
    if (counts) {
      var done = ms.filter(function (x) { return x.status === "completed"; }).length;
      counts.textContent = done + " of " + ms.length + " completed";
      var bar = $("#milestone-progress");
      if (bar) bar.style.width = Math.round((done / Math.max(ms.length, 1)) * 100) + "%";
    }
  }

  /* --------------------------------------------------------------- people */
  function emailLink(email) {
    if (!email) return '<span class="member__email muted">' + ICON.mail + "Email to be added</span>";
    return '<a class="member__email" href="mailto:' + esc(email) + '">' + ICON.mail + esc(email) + "</a>";
  }

  function renderMembers() {
    var root = $("#members-list");
    if (root) {
      root.innerHTML = (SITE.members || []).map(function (m) {
        var links = [];
        if (m.links && m.links.github) links.push('<a href="' + esc(m.links.github) + '" target="_blank" rel="noopener">GitHub</a>');
        if (m.links && m.links.linkedin) links.push('<a href="' + esc(m.links.linkedin) + '" target="_blank" rel="noopener">LinkedIn</a>');
        return '<article class="card card--hover member reveal" id="' + esc(m.id) + '">' +
          '<div class="member__photo"><img src="' + esc(m.photo) + '" alt="Photo of ' + esc(m.name) + '" width="400" height="400" loading="lazy"></div>' +
          '<div class="member__body">' +
          '<div><h3 class="member__name">' + esc(m.name) + '</h3><span class="member__id">' + esc(m.studentId) + "</span></div>" +
          '<div class="member__component">' + esc(m.component) + "</div>" +
          '<div class="tags">' + (m.agents || []).map(function (a) { return '<span class="tag">' + esc(a) + "</span>"; }).join("") + "</div>" +
          '<p class="member__summary" style="margin:0">' + esc(m.summary) + "</p>" +
          '<div><strong style="font-size:.86rem">Achievements</strong><ul class="check-list" style="margin-top:8px">' +
          (m.highlights || []).map(function (h) { return "<li>" + esc(h) + "</li>"; }).join("") + "</ul></div>" +
          '<div style="margin-top:auto;display:flex;flex-direction:column;gap:6px">' + emailLink(m.email) +
          (links.length ? '<div style="display:flex;gap:14px;font-size:.9rem">' + links.join("") + "</div>" : "") + "</div>" +
          "</div></article>";
      }).join("");
    }

    var sup = $("#supervisors-list");
    if (sup) {
      sup.innerHTML = (SITE.supervisors || []).map(function (s) {
        return '<article class="card reveal"><div class="person-mini"><img src="' + esc(s.photo) + '" alt="Photo of ' + esc(s.name) + '" width="56" height="56" loading="lazy">' +
          "<div><strong>" + esc(s.name) + "</strong><span>" + esc(s.role) + "</span></div></div>" +
          '<div style="margin-top:14px">' + emailLink(s.email) + "</div></article>";
      }).join("");
    }

    var strip = $("#team-strip");
    if (strip) {
      strip.innerHTML = (SITE.members || []).map(function (m) {
        return '<a class="card card--hover reveal" href="about.html#' + esc(m.id) + '" style="text-decoration:none;color:inherit">' +
          '<div class="person-mini"><img src="' + esc(m.photo) + '" alt="" width="56" height="56" loading="lazy">' +
          "<div><strong>" + esc(m.name) + "</strong><span>" + esc(m.studentId) + "</span></div></div>" +
          '<p style="margin:14px 0 0;font-size:.92rem;color:var(--ink-2)">' + esc(m.component) + "</p></a>";
      }).join("");
    }

    var contacts = $("#member-contacts");
    if (contacts) {
      contacts.innerHTML = (SITE.members || []).concat(SITE.supervisors || []).map(function (p) {
        return "<tr><td><strong>" + esc(p.name) + "</strong>" + (p.studentId ? '<br><span class="muted mono" style="font-size:.8rem">' + esc(p.studentId) + "</span>" : "") +
          "</td><td>" + esc(p.role || (p.agents || []).join(", ")) + "</td><td>" +
          (p.email ? '<a href="mailto:' + esc(p.email) + '">' + esc(p.email) + "</a>" : '<span class="muted">To be added</span>') + "</td></tr>";
      }).join("");
    }

    var recipient = $("#contact-to");
    if (recipient) {
      recipient.innerHTML = '<option value="all">Whole research team</option>' +
        (SITE.members || []).concat(SITE.supervisors || []).filter(function (p) { return p.email; }).map(function (p) {
          return '<option value="' + esc(p.email) + '">' + esc(p.name) + "</option>";
        }).join("");
    }
  }

  /* ------------------------------------------------------- home pipeline */
  function initPipeline() {
    var card = $("#pipeline");
    if (!card) return;
    var stages = $$(".stage", card), foot = $("#pipeline-foot"), i = 0, timer = null;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    function activate(n) {
      i = n;
      stages.forEach(function (s, k) {
        s.classList.toggle("is-active", k === n);
        s.classList.toggle("is-done", k < n);
        s.setAttribute("aria-pressed", k === n ? "true" : "false");
      });
      if (foot) foot.innerHTML = stages[n].getAttribute("data-detail");
    }
    function tick() { activate((i + 1) % stages.length); }
    function start() { if (!reduce && !timer) timer = setInterval(tick, 2600); }
    function stop() { clearInterval(timer); timer = null; }
    stages.forEach(function (s, k) {
      s.addEventListener("click", function () { stop(); activate(k); });
    });
    card.addEventListener("mouseenter", stop);
    card.addEventListener("mouseleave", start);
    card.addEventListener("focusin", stop);
    activate(0);
    start();
  }

  /* -------------------------------------------------------- domain toc */
  function initToc() {
    var toc = $("#toc");
    if (!toc || !("IntersectionObserver" in window)) return;
    var links = $$("a", toc), map = {};
    links.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          links.forEach(function (a) { a.classList.remove("is-active"); });
          var a = map[en.target.id];
          if (a) a.classList.add("is-active");
        }
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    Object.keys(map).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
  }

  /* ------------------------------------------------------------- contact */
  function initContact() {
    var form = $("#contact-form");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var name = $("#cf-name").value.trim(), from = $("#cf-email").value.trim(),
          subject = $("#cf-subject").value.trim(), msg = $("#cf-message").value.trim(), to = $("#contact-to").value;
        var status = $("#cf-status");
        if (!name || !subject || !msg) { status.textContent = "Please fill in your name, a subject and a message."; return; }
        var all = (SITE.members || []).map(function (m) { return m.email; }).filter(Boolean).join(",");
        var recipients = to === "all" ? all : to;
        var body = "Dear AutoForge team,\n\n" + msg + "\n\nKind regards,\n" + name + (from ? "\n" + from : "");
        window.location.href = "mailto:" + recipients + "?subject=" + encodeURIComponent("[" + (SITE.project.groupId || "AutoForge") + "] " + subject) + "&body=" + encodeURIComponent(body);
        status.textContent = "Your email app should open with the message ready to send.";
      });
    }
    $$("[data-copy]").forEach(function (b) {
      b.addEventListener("click", function () {
        var src = document.getElementById(b.getAttribute("data-copy"));
        if (!src) return;
        var text = src.textContent, done = function () { var old = b.textContent; b.textContent = "Copied"; setTimeout(function () { b.textContent = old; }, 1600); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
        else { fallbackCopy(text); done(); }
      });
    });
    function fallbackCopy(text) {
      var ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) { /* ignore */ }
      document.body.removeChild(ta);
    }
  }

  /* ---------------------------------------------- counts on documents */
  function renderCounts() {
    $$("[data-count]").forEach(function (el) {
      var key = el.getAttribute("data-count"), list = SITE[key] || [];
      el.textContent = list.filter(hasLink).length + " of " + list.length;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initMenu();
    initSearch();
    renderDocuments();
    renderPresentations();
    renderMilestones();
    renderMembers();
    renderCounts();
    initViewer();
    initPipeline();
    initToc();
    initContact();
    initReveal();
    initToTop();
    initYear();
    if (window.location.hash) {
      var target = document.getElementById(window.location.hash.slice(1));
      if (target) setTimeout(function () { target.scrollIntoView(); }, 60);
    }
  });
})();
