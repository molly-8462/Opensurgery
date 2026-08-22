document.querySelectorAll(".search").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const input = form.querySelector("input[type='search']");
    const query = input?.value.trim() || "";
    window.location.href = query ? `search.html?q=${encodeURIComponent(query)}` : "directory.html";
  });
});

const contents = document.querySelector(".contents");
const hideContents = document.querySelector(".contents__heading button");

hideContents?.addEventListener("click", () => {
  contents?.classList.toggle("is-collapsed");
  hideContents.textContent = contents?.classList.contains("is-collapsed") ? "show" : "hide";
});

const photoToggle = document.querySelector(".photo-toggle");

photoToggle?.addEventListener("click", () => {
  const willShow = photoToggle.getAttribute("aria-pressed") !== "true";
  photoToggle.setAttribute("aria-pressed", String(willShow));
  photoToggle.lastChild.textContent = willShow ? " Hide surgical photos" : " Show surgical photos";
  document.body.classList.toggle("photos-visible", willShow);
});

const editForm = document.querySelector("#edit-form");

if (editForm) {
  let hasUnsavedChanges = false;
  const formStatus = editForm.querySelector(".form-status");
  const portraitInput = editForm.querySelector("#portrait-file");
  const portraitInitials = editForm.querySelector(".portrait-upload__initials");
  const portraitRights = editForm.querySelector("[name='portrait_rights']");

  editForm.addEventListener("input", () => {
    hasUnsavedChanges = true;
  });

  editForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!editForm.reportValidity()) return;
    hasUnsavedChanges = false;
    if (formStatus) formStatus.textContent = "Submitting proposal…";
  });

  portraitInput?.addEventListener("change", () => {
    const [file] = portraitInput.files;
    if (portraitRights) portraitRights.required = Boolean(file);
    if (!file || !portraitInitials) return;
    const preview = new FileReader();
    preview.addEventListener("load", () => {
      portraitInitials.textContent = "";
      portraitInitials.style.backgroundImage = `url(${preview.result})`;
      portraitInitials.style.backgroundSize = "cover";
      portraitInitials.style.backgroundPosition = "center";
    });
    preview.readAsDataURL(file);
  });

  window.addEventListener("beforeunload", (event) => {
    if (!hasUnsavedChanges) return;
    event.preventDefault();
    event.returnValue = "";
  });
}

let menuButton = document.querySelector(".menu-button");
if (!menuButton && document.querySelector(".site-header")) {
  menuButton = document.createElement("button");
  menuButton.className = "menu-button";
  menuButton.type = "button";
  menuButton.setAttribute("aria-label", "Open navigation");
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.innerHTML = "<span></span><span></span><span></span>";
  document.querySelector(".site-header").firstElementChild?.replaceWith(menuButton);
}
if (menuButton) {
  const drawer = document.createElement("aside");
  drawer.className = "nav-drawer";
  drawer.id = "site-navigation";
  drawer.setAttribute("aria-hidden", "true");
  drawer.innerHTML = `<div class="nav-drawer__top"><a class="wordmark" href="home.html"><span class="wordmark__symbol">O</span><span><strong>OpenSurgery</strong><small>Community surgeon guide</small></span></a><button type="button" aria-label="Close navigation">×</button></div><nav aria-label="Main navigation"><strong>Explore</strong><a href="home.html">Home</a><a href="directory.html">Surgeon directory</a><a href="procedures.html">Procedure guides</a><a href="search.html">Search</a><strong>Contribute</strong><a href="add-surgeon.html">Add a surgeon</a><a href="write-review.html">Write a review</a><a href="pending.html">Pending edits</a><a href="guidelines.html">Community guidelines</a><strong>Your space</strong><a href="account.html">Account dashboard</a><a href="messages.html">Messages</a><a href="settings.html">Settings</a></nav><footer><a href="policies.html">Policies</a></footer>`;
  const backdrop = document.createElement("button");
  backdrop.className = "nav-backdrop";
  backdrop.type = "button";
  backdrop.setAttribute("aria-label", "Close navigation");
  document.body.append(drawer, backdrop);
  menuButton.setAttribute("aria-controls", drawer.id);
  const setDrawer = (open) => {
    drawer.classList.toggle("is-open", open);
    backdrop.classList.toggle("is-open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    menuButton.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("drawer-open", open);
    if (open) drawer.querySelector("button")?.focus();
  };
  menuButton.addEventListener("click", () => setDrawer(true));
  drawer.querySelector("button")?.addEventListener("click", () => setDrawer(false));
  backdrop.addEventListener("click", () => setDrawer(false));
  window.addEventListener("keydown", (event) => { if (event.key === "Escape") setDrawer(false); });
}

const API_BASE = "/api/v1";
let signedInUser = null;
try { signedInUser = JSON.parse(localStorage.getItem("opensurgery_user")); } catch (_) { signedInUser = null; }
const apiRequest = async (path, options = {}) => {
  const headers = { ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...(options.headers || {}) };
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "same-origin" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "The request could not be completed.");
  return body;
};
if (signedInUser?.displayName) {
  document.querySelectorAll(".account-links").forEach((nav) => {
    nav.innerHTML = `<a href="messages.html">Messages</a><a href="account.html">${signedInUser.displayName}</a>`;
  });
  document.querySelectorAll("[data-account-display]").forEach((node) => { node.textContent = signedInUser.displayName; });
}

document.querySelectorAll("[data-auth-form]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const status = form.querySelector(".form-status");
    const data = new FormData(form);
    if (form.dataset.authForm === "create" && data.get("password") !== data.get("confirm_password")) {
      if (status) status.textContent = "The passwords do not match.";
      return;
    }
    const endpoint = form.dataset.authForm === "create" ? "/auth/register" : "/auth/login";
    const payload = form.dataset.authForm === "create"
      ? { email: data.get("email"), display_name: data.get("display_name"), password: data.get("password"), approximate_region: data.get("region") || null }
      : { identity: data.get("identity"), password: data.get("password") };
    try {
      const result = await apiRequest(endpoint, { method: "POST", body: JSON.stringify(payload) });
      localStorage.setItem("opensurgery_user", JSON.stringify({ displayName: result.user.display_name }));
      if (status) status.textContent = "Success. Opening your account…";
      window.setTimeout(() => { window.location.href = "account.html"; }, 350);
    } catch (error) { if (status) status.textContent = error.message; }
  });
});

document.querySelector(".dashboard-signout")?.addEventListener("click", async () => {
  await apiRequest("/auth/logout", { method: "POST" }).catch(() => {});
  localStorage.removeItem("opensurgery_user");
  window.location.href = "home.html";
});

document.querySelectorAll("[data-demo-form]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const type = form.dataset.demoForm;
    if (["reset", "settings", "review"].includes(type)) return;
    if (!form.reportValidity()) return;
    const messages = { contact: "Message prepared successfully. No email was sent because support delivery is not configured." };
    const status = form.querySelector(".form-status");
    if (status) status.textContent = messages[type] || "Saved.";
  });
});

const queryParams = new URLSearchParams(window.location.search);
const searchInput = document.querySelector("[data-search-input]");
const searchQuery = queryParams.get("q");
if (searchInput && searchQuery) searchInput.value = searchQuery;
const searchSummary = document.querySelector("[data-search-summary]");
if (searchSummary && searchQuery) searchSummary.textContent = `Searching for “${searchQuery}”…`;

const profileName = queryParams.get("user");
if (profileName) {
  document.querySelectorAll("[data-profile-name]").forEach((node) => { node.textContent = profileName; });
  document.querySelectorAll("[data-profile-initial]").forEach((node) => { node.textContent = profileName.charAt(0).toUpperCase(); });
}
const messageDialog = document.querySelector(".message-dialog");
document.querySelector(".message-user-button")?.addEventListener("click", () => messageDialog?.showModal());
messageDialog?.addEventListener("close", async () => {
  if (messageDialog.returnValue === "send") {
    const status = messageDialog.querySelector(".form-status");
    messageDialog.showModal();
    if (!signedInUser) { if (status) status.textContent = "Log in before sending a message."; return; }
    const fields = messageDialog.querySelectorAll("input, textarea");
    try { await apiRequest("/messages", { method: "POST", body: JSON.stringify({ recipient: queryParams.get("user"), body: `${fields[0].value}\n\n${fields[1].value}` }) }); if (status) status.textContent = "Message sent."; }
    catch (error) { if (status) status.textContent = error.message; }
  }
});

document.querySelectorAll(".photo-slot.has-photo").forEach((button) => {
  button.addEventListener("click", () => {
    document.body.classList.add("photos-visible");
    if (photoToggle) { photoToggle.setAttribute("aria-pressed", "true"); photoToggle.lastChild.textContent = " Hide surgical photos"; }
  });
});

document.querySelectorAll(".load-more").forEach((button) => {
  if (button.closest(".reviews-page")) return;
  button.addEventListener("click", () => { button.textContent = "All published reviews are loaded"; button.disabled = true; });
});
document.querySelector(".review-controls button")?.addEventListener("click", (event) => { event.currentTarget.textContent = "Filters applied"; });

document.querySelectorAll(".reply-button, [data-add-topic]").forEach((button) => {
  button.addEventListener("click", () => {
    const topic = document.querySelector("#new-topic");
    if (!topic) return;
    let composer = topic.querySelector(".topic-composer");
    if (!composer) {
      composer = document.createElement("form");
      composer.className = "topic-composer";
      composer.innerHTML = `<label>Topic title<input type="text" required></label><label>Comment<textarea rows="6" required></textarea></label><button class="primary-button">Post topic</button><p class="form-status"></p>`;
      topic.append(composer);
      composer.addEventListener("submit", async (event) => {
        event.preventDefault(); if (!composer.reportValidity()) return;
        if (!signedInUser) { composer.querySelector(".form-status").textContent = "Log in before posting a topic."; return; }
        const slug = selectedSurgeonSlug();
        if (!slug) { composer.querySelector(".form-status").textContent = "No surgeon was selected."; return; }
        try { await apiRequest(`/surgeons/${slug}/talk`, { method: "POST", body: JSON.stringify({ title: composer.querySelector("input").value, body: composer.querySelector("textarea").value }) }); composer.querySelector(".form-status").textContent = "Topic posted."; }
        catch (error) { composer.querySelector(".form-status").textContent = error.message; }
      });
    }
    topic.scrollIntoView({ behavior: "smooth" });
    composer.querySelector("input")?.focus();
  });
});

document.querySelectorAll(".undo-revision, .restore-revision").forEach((button) => {
  button.addEventListener("click", () => { button.textContent = "Restore proposal created"; button.disabled = true; });
});
document.querySelector("[data-copy-link]")?.addEventListener("click", async (event) => {
  try { await navigator.clipboard.writeText(window.location.href); event.currentTarget.textContent = "Link copied"; }
  catch (_) { event.currentTarget.textContent = "Use the address bar to copy"; }
});

const directoryForm = document.querySelector("[data-directory-filters]");
if (directoryForm) {
  const country = queryParams.get("country");
  if (country && directoryForm.elements.country) directoryForm.elements.country.value = country;
  const applyDirectoryFilters = () => {
    const data = new FormData(directoryForm);
    const name = String(data.get("name") || "").toLowerCase();
    const procedure = String(data.get("procedure") || "");
    const selectedCountry = String(data.get("country") || "");
    const longterm = data.get("longterm") === "on";
    let visible = 0;
    document.querySelectorAll(".directory-results article").forEach((card) => {
      const matches = (!name || card.dataset.name.toLowerCase().includes(name)) && (!procedure || card.dataset.procedure === procedure) && (!selectedCountry || card.dataset.country === selectedCountry) && (!longterm || card.dataset.longterm === "true");
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    const summary = document.querySelector(".listing-summary strong");
    if (summary) summary.textContent = `${visible} surgeon profile${visible === 1 ? "" : "s"}`;
  };
  directoryForm.addEventListener("submit", (event) => { event.preventDefault(); applyDirectoryFilters(); });
  applyDirectoryFilters();
}

const surgeonPage = document.querySelector("[data-surgeon-page]");
if (surgeonPage) {
  const slug = queryParams.get("surgeon") || surgeonPage.dataset.surgeonPage;
  if (!slug) throw new Error("A surgeon slug is required for this page.");
  apiRequest(`/surgeons/${encodeURIComponent(slug)}`).then((record) => {
    const values = { "[data-surgeon-name]": record.name, "[data-surgeon-initials]": record.initials, "[data-surgeon-country]": record.country, "[data-surgeon-detail]": `${record.specialty} · ${[record.city, record.region, record.country].filter(Boolean).join(", ")}`, "[data-surgeon-procedure]": record.procedures.map((x) => x.name).join(", "), "[data-surgeon-reviews]": record.review_count, "[data-surgeon-overview]": record.article_body };
    Object.entries(values).forEach(([selector, value]) => { const node = document.querySelector(selector); if (node) node.textContent = value; });
    document.querySelectorAll("[data-surgeon-link]").forEach((link) => { link.href = surgeonUrl(record.slug); });
    document.querySelectorAll("[data-surgeon-reviews-link]").forEach((link) => { link.href = surgeonUrl(record.slug, "reviews"); });
    document.querySelectorAll("[data-surgeon-talk-link]").forEach((link) => { link.href = surgeonUrl(record.slug, "talk"); });
    document.title = `${record.name} — OpenSurgery`;
  }).catch((error) => { surgeonPage.querySelector("[data-surgeon-overview]").textContent = error.message; });
}

const showInlineMenu = (button, items) => {
  const existing = document.querySelector(".prototype-menu");
  if (existing) {
    const sameOwner = existing.dataset.owner === button.dataset.menuOwner;
    existing.remove();
    button.setAttribute("aria-expanded", "false");
    if (sameOwner) return;
  }
  if (!button.dataset.menuOwner) button.dataset.menuOwner = `menu-${Math.random().toString(36).slice(2)}`;
  const menu = document.createElement("div");
  menu.className = "prototype-menu";
  menu.dataset.owner = button.dataset.menuOwner;
  menu.setAttribute("role", "menu");
  items.forEach(({ label, href }) => {
    const link = document.createElement("a");
    link.href = href;
    link.textContent = label;
    link.setAttribute("role", "menuitem");
    menu.append(link);
  });
  button.setAttribute("aria-expanded", "true");
  button.insertAdjacentElement("afterend", menu);
  menu.querySelector("a")?.focus();
};

document.querySelectorAll(".language-button").forEach((button) => {
  button.setAttribute("aria-haspopup", "menu");
  button.setAttribute("aria-expanded", "false");
  button.addEventListener("click", () => showInlineMenu(button, [{ label: "English", href: window.location.pathname + window.location.search }]));
});

document.querySelectorAll(".more-button").forEach((button) => {
  button.setAttribute("aria-haspopup", "menu");
  button.setAttribute("aria-expanded", "false");
  button.addEventListener("click", () => showInlineMenu(button, [
    { label: "View history", href: document.querySelector("a[href*='history.html']")?.href || "history.html" },
    { label: "Community guidelines", href: "guidelines.html" },
  ]));
});

const resultTabs = document.querySelectorAll(".result-tabs button");
resultTabs.forEach((button) => button.addEventListener("click", () => {
  resultTabs.forEach((tab) => { tab.classList.remove("is-active"); tab.setAttribute("aria-selected", "false"); });
  button.classList.add("is-active");
  button.setAttribute("aria-selected", "true");
  const category = button.textContent.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll(".search-result-list article").forEach((result) => {
    const type = result.querySelector(":scope > span")?.textContent.toLowerCase() || "";
    const matches = category === "all" || type.includes(category.replace(/s$/, ""));
    result.hidden = !matches;
    if (matches) visible += 1;
  });
  const summary = document.querySelector("[data-search-summary]");
  if (summary) summary.textContent = `${visible} ${category === "all" ? "matching results" : `${category} result${visible === 1 ? "" : "s"}`}.`;
}));

const historyFilters = document.querySelector(".history-filters");
historyFilters?.querySelector("button")?.addEventListener("click", () => {
  const data = new FormData(historyFilters);
  const fromDate = String(data.get("from_date") || "");
  const editor = String(data.get("editor") || "").trim().toLowerCase();
  const changeType = String(data.get("change_type") || "All changes").toLowerCase();
  let visible = 0;
  document.querySelectorAll(".history-list .revision").forEach((revision) => {
    const revisionEditor = revision.querySelector(".revision-meta a")?.textContent.toLowerCase() || "";
    const revisionType = revision.querySelector(".revision-meta span:last-child")?.textContent.toLowerCase() || "";
    const time = revision.querySelector(".revision-title a")?.textContent || "";
    const parsedDate = new Date(time.replace(" at ", " "));
    const matchesDate = !fromDate || (!Number.isNaN(parsedDate.valueOf()) && parsedDate >= new Date(`${fromDate}T00:00:00`));
    const matches = matchesDate && (!editor || revisionEditor.includes(editor)) && (changeType === "all changes" || revisionType === changeType);
    revision.hidden = !matches;
    if (matches) visible += 1;
  });
  const pagination = document.querySelector(".history-pagination span");
  if (pagination) pagination.textContent = `Showing ${visible} matching revision${visible === 1 ? "" : "s"}`;
});

document.querySelector(".history-pagination button:last-child")?.addEventListener("click", (event) => {
  event.currentTarget.textContent = "Older revisions require the history API";
  event.currentTarget.disabled = true;
});

document.querySelectorAll(".pending-shell button, .proposal-list button").forEach((button) => {
  button.addEventListener("click", () => {
    const proposal = button.closest("article");
    const destination = button.textContent.includes("Review") ? proposal?.querySelector("a[href*='revision.html']") : proposal?.querySelector("a[href*='talk.html']");
    if (destination) window.location.href = destination.href;
  });
});

document.querySelectorAll(".conversation-list button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".conversation-list button").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    const person = button.querySelector("strong")?.textContent || "Community member";
    const headerName = document.querySelector(".conversation > header strong");
    const profileLink = document.querySelector(".conversation > header a");
    if (headerName) headerName.textContent = person;
    if (profileLink) profileLink.href = `profile.html?user=${encodeURIComponent(person)}`;
  });
});

document.querySelectorAll(".topic-heading button[aria-label='Topic tools']").forEach((button) => {
  button.setAttribute("aria-haspopup", "menu");
  button.setAttribute("aria-expanded", "false");
  button.addEventListener("click", () => showInlineMenu(button, [
    { label: "Reply to topic", href: "#new-topic" },
    { label: "Talk guidelines", href: "policies.html#talk-policy" },
  ]));
});

document.querySelectorAll(".talk-actions button").forEach((button) => {
  if (!button.textContent.toLowerCase().startsWith("tools")) return;
  button.setAttribute("aria-haspopup", "menu");
  button.setAttribute("aria-expanded", "false");
  button.addEventListener("click", () => showInlineMenu(button, [
    { label: "View talk history", href: "talk-history.html" },
    { label: "Talk guidelines", href: "policies.html#talk-policy" },
  ]));
});

document.querySelector(".review-detail-footer button")?.addEventListener("click", (event) => {
  event.currentTarget.textContent = "Thanks";
  event.currentTarget.disabled = true;
  event.currentTarget.setAttribute("aria-pressed", "true");
});

document.querySelectorAll("button").forEach((button) => {
  const label = button.textContent.trim().toLowerCase();
  if (label === "watch" || label === "subscribe") {
    button.addEventListener("click", () => {
      const active = button.getAttribute("aria-pressed") === "true";
      button.setAttribute("aria-pressed", String(!active));
      button.textContent = active ? (label === "watch" ? "Watch" : "subscribe") : (label === "watch" ? "Watching" : "subscribed");
    });
  }
  if (label === "save draft" || label.includes("preview")) {
    button.addEventListener("click", () => {
      const form = button.closest("form");
      const status = form?.querySelector(".form-status");
      if (status) status.textContent = label === "save draft" ? "Draft saving is not available yet." : "Preview is ready; submitted data remains in the form.";
    });
  }
});

document.querySelectorAll(".secondary-button").forEach((button) => {
  if (button.textContent.includes("Add another source")) button.addEventListener("click", () => {
    const sources = document.querySelector("#edit-sources");
    if (!sources) return;
    const label = document.createElement("label");
    label.textContent = "Additional source URL";
    label.innerHTML += '<input type="url" placeholder="https://example.org/source" required>';
    button.before(label);
  });
});

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
const surgeonRouteMatch = window.location.pathname.match(/^\/surgeons\/([^/]+)(?:\/(reviews|talk|edit|history))?\/?$/);
const surgeonRouteSlug = surgeonRouteMatch ? decodeURIComponent(surgeonRouteMatch[1]) : null;
const surgeonRouteSection = surgeonRouteMatch?.[2] || "info";
const surgeonSectionFiles = { info: "index.html", reviews: "reviews.html", talk: "talk.html", edit: "edit.html", history: "history.html" };
const pageName = surgeonRouteMatch ? surgeonSectionFiles[surgeonRouteSection] : (window.location.pathname.split("/").pop() || "home.html");
const selectedSurgeonSlug = () => surgeonRouteSlug || queryParams.get("surgeon");
const surgeonUrl = (slug, section = "info") => `/surgeons/${encodeURIComponent(slug)}${section === "info" ? "" : `/${section}`}`;
const finishSurgeonLoad = (error) => {
  const shell = document.querySelector("[data-surgeon-shell]");
  if (!shell) return;
  shell.removeAttribute("aria-busy");
  const status = shell.querySelector(".profile-load-status");
  if (error && status) {
    shell.dataset.loadError = "true";
    status.textContent = error.message || "The surgeon page could not be loaded.";
    status.setAttribute("role", "alert");
  } else status?.remove();
};

const renderSurgeonCards = (container, surgeons, directoryRows = false) => {
  container.innerHTML = surgeons.map((surgeon) => directoryRows ? `
    <article data-name="${escapeHtml(surgeon.name)}" data-country="${escapeHtml(surgeon.country)}">
      <div class="directory-avatar">${escapeHtml(surgeon.initials)}</div><div>
        <h2><a href="${surgeonUrl(surgeon.slug)}">${escapeHtml(surgeon.name)}</a></h2>
        <p>${escapeHtml(surgeon.specialty)} · ${escapeHtml([surgeon.city, surgeon.region, surgeon.country].filter(Boolean).join(", "))}</p>
        <ul>${surgeon.procedures.map((procedure) => `<li>${escapeHtml(procedure.name)}</li>`).join("")}</ul>
        <span>${surgeon.review_count} published review${surgeon.review_count === 1 ? "" : "s"}</span>
      </div><a class="row-action" href="${surgeonUrl(surgeon.slug)}">View profile →</a>
    </article>` : `
    <article class="surgeon-card"><div class="surgeon-card__initials">${escapeHtml(surgeon.initials)}</div><div>
      <h3><a href="${surgeonUrl(surgeon.slug)}">${escapeHtml(surgeon.name)}</a></h3>
      <p>${escapeHtml([surgeon.city, surgeon.region, surgeon.country].filter(Boolean).join(", "))}</p>
      <div class="surgeon-card__meta"><span>${escapeHtml(surgeon.procedures[0]?.name || "Profile")}</span><span>${surgeon.review_count} reviews</span></div>
    </div></article>`).join("");
};

if (pageName === "home.html") {
  const cards = document.querySelector(".surgeon-card-grid");
  if (cards) apiRequest("/surgeons").then((data) => renderSurgeonCards(cards, data.items.slice(0, 3))).catch(() => { cards.innerHTML = "<p>Directory data is temporarily unavailable.</p>"; });
}

if (pageName === "index.html") {
  const slug = selectedSurgeonSlug();
  const profile = document.querySelector("[data-surgeon-profile]");
  if (!slug) {
    window.location.replace("directory.html");
  } else
  apiRequest(`/surgeons/${encodeURIComponent(slug)}`).then((surgeon) => {
    document.title = `${surgeon.name} — OpenSurgery`;
    const title = document.querySelector(".article-header h1"); if (title) title.textContent = surgeon.name;
    const subtitle = document.querySelector(".article-header .subtitle"); if (subtitle) subtitle.textContent = `${surgeon.specialty || "Surgeon"} · ${[surgeon.city, surgeon.region, surgeon.country].filter(Boolean).join(", ")}`;
    document.querySelectorAll(".article-navigation a, .edit-section, .portrait-placeholder, .article-footer a[href*='history.html']").forEach((link) => {
      if (link.href.includes("index.html")) link.href = surgeonUrl(slug);
      if (link.href.includes("reviews.html")) link.href = surgeonUrl(slug, "reviews");
      if (link.href.includes("talk.html")) link.href = surgeonUrl(slug, "talk");
      if (link.href.includes("edit.html")) link.href = surgeonUrl(slug, "edit");
      if (link.href.includes("history.html")) link.href = surgeonUrl(slug, "history");
    });
    const reviewCount = document.querySelector(".article-navigation a[href*='reviews.html'] .count"); if (reviewCount) reviewCount.textContent = surgeon.review_count;
    const countryLink = document.querySelector(".breadcrumb a[href*='country=']");
    if (countryLink) { countryLink.textContent = surgeon.country || "Directory"; countryLink.href = `directory.html?country=${encodeURIComponent(surgeon.country || "")}`; }
    const note = document.querySelector(".prototype-note");
    if (note) note.innerHTML = `<strong>Community-maintained profile:</strong> Verify current practice information directly with the clinician or practice.`;
    const infobox = document.querySelector(".infobox");
    if (infobox) {
      infobox.querySelector("header strong").textContent = surgeon.name;
      infobox.querySelector("header small").textContent = surgeon.specialty || "Specialty not listed";
      infobox.setAttribute("aria-label", `${surgeon.name} profile summary`);
      const portrait = infobox.querySelector(".portrait-placeholder span"); if (portrait) portrait.textContent = surgeon.initials;
      const cells = infobox.querySelectorAll("tbody td");
      if (cells[0]) cells[0].textContent = surgeon.profile.practice || "Practice not listed";
      if (cells[1]) cells[1].textContent = [surgeon.city, surgeon.region, surgeon.country].filter(Boolean).join(", ");
      if (cells[2]) cells[2].textContent = surgeon.specialty || "Not listed";
      if (cells[3]) cells[3].textContent = surgeon.procedures.map((item) => item.name).join(", ") || "Not listed";
      if (cells[4]) cells[4].textContent = (surgeon.profile.languages || []).join(", ") || "Not listed";
      if (cells[5]) cells[5].innerHTML = surgeon.website_url ? `<a href="${escapeHtml(surgeon.website_url)}" rel="noopener noreferrer">Practice website</a>` : "Not listed";
    }
    const intro = document.querySelector("#intro");
    if (intro) intro.innerHTML = surgeon.article_body.split("\n\n").map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");
    const practice = document.querySelector("#practice");
    if (practice) practice.innerHTML = `<h2>Practice <a class="edit-section" href="${surgeonUrl(slug, "edit")}#edit-practice">edit</a></h2><p>${escapeHtml(surgeon.profile.practice_summary || `${surgeon.name} is associated with ${surgeon.profile.practice || "a practice that is not yet listed"}.`)}</p>`;
    const procedures = document.querySelector("#procedures");
    if (procedures) procedures.innerHTML = `<h2>Procedures and techniques <a class="edit-section" href="${surgeonUrl(slug, "edit")}#edit-procedures">edit</a></h2><p>These procedures are linked to this community-maintained profile. Availability and technique should be confirmed directly with the practice.</p>${surgeon.procedures.length ? surgeon.procedures.map((item) => `<h3>${escapeHtml(item.name)}</h3>`).join("") : "<p>No procedures are currently listed.</p>"}`;
    const patientInfo = document.querySelector("#patient-information");
    if (patientInfo) patientInfo.innerHTML = `<h2>Patient information <a class="edit-section" href="edit.html?surgeon=${encodeURIComponent(slug)}#edit-patient-information">edit</a></h2><p>Community members have published <a href="reviews.html?surgeon=${encodeURIComponent(slug)}"><strong>${surgeon.review_count} review${surgeon.review_count === 1 ? "" : "s"} of ${escapeHtml(surgeon.name)}</strong></a>. Reviews are first-person accounts and are maintained separately from this article.</p><div class="review-callout"><div><strong>Have experience with this surgeon?</strong><span>Your review can help others understand the consultation and recovery process.</span></div><a href="write-review.html?surgeon=${encodeURIComponent(slug)}">Write a review</a></div>`;
    const references = document.querySelector("#references");
    if (references) references.innerHTML = `<h2>References</h2><p>Sources are stored with the profile's revision and proposal history. <a href="${surgeonUrl(slug, "history")}">View edit history</a>.</p>`;
    const external = document.querySelector("#external-links");
    if (external) external.innerHTML = `<h2>External links</h2>${surgeon.website_url ? `<ul><li><a href="${escapeHtml(surgeon.website_url)}" rel="noopener noreferrer">Practice website</a></li></ul>` : "<p>No external website is currently listed.</p>"}`;
    finishSurgeonLoad();
  }).catch((error) => {
    document.title = "Surgeon profile unavailable — OpenSurgery";
    const header = document.querySelector(".article-header h1");
    if (header) header.textContent = "Surgeon profile unavailable";
    const intro = document.querySelector("#intro");
    if (intro) intro.innerHTML = `<p>${escapeHtml(error.message)}</p><p><a href="directory.html">Return to the surgeon directory</a>.</p>`;
    document.querySelectorAll(".article-body > :not(#intro), .prototype-note, .mobile-contents, .article-footer").forEach((node) => { node.hidden = true; });
    finishSurgeonLoad();
  });
}

if (pageName === "directory.html") {
  const results = document.querySelector(".directory-results");
  const form = document.querySelector("[data-directory-filters]");
  const loadDirectory = async () => {
    const data = new FormData(form); const params = new URLSearchParams();
    if (data.get("name")) params.set("q", data.get("name"));
    if (data.get("country")) params.set("country", data.get("country"));
    if (data.get("procedure")) params.set("procedure", data.get("procedure"));
    const response = await apiRequest(`/surgeons?${params}`); renderSurgeonCards(results, response.items, true);
    const summary = document.querySelector(".listing-summary strong"); if (summary) summary.textContent = `${response.total} surgeon profile${response.total === 1 ? "" : "s"}`;
  };
  form?.addEventListener("submit", (event) => { event.preventDefault(); loadDirectory().catch(() => {}); });
  if (results) loadDirectory().catch(() => { results.innerHTML = "<p>Directory data is temporarily unavailable.</p>"; });
}

if (pageName === "reviews.html") {
  const slug = selectedSurgeonSlug();
  if (!slug) window.location.replace("directory.html"); else
  Promise.all([apiRequest(`/surgeons/${slug}`), apiRequest(`/surgeons/${slug}/reviews`)]).then(([surgeon, data]) => {
    document.title = `Reviews of ${surgeon.name} — OpenSurgery`;
    document.querySelectorAll(".title-row h1").forEach((node) => { node.textContent = surgeon.name; });
    const subtitle = document.querySelector(".article-header .subtitle"); if (subtitle) subtitle.textContent = `${surgeon.specialty || "Surgeon"} · ${[surgeon.city, surgeon.region, surgeon.country].filter(Boolean).join(", ")}`;
    document.querySelectorAll(".article-navigation a").forEach((link) => {
      if (link.href.includes("index.html")) link.href = surgeonUrl(slug);
      if (link.href.includes("reviews.html")) link.href = surgeonUrl(slug, "reviews");
      if (link.href.includes("talk.html")) link.href = surgeonUrl(slug, "talk");
      if (link.href.includes("write-review.html")) link.href = `write-review.html?surgeon=${encodeURIComponent(slug)}`;
    });
    const sidebarTotal = document.querySelector(".review-sidebar > strong"); if (sidebarTotal) sidebarTotal.textContent = `${data.total} review${data.total === 1 ? "" : "s"}`;
    const sidebarBreakdown = document.querySelector(".review-sidebar dl"); if (sidebarBreakdown) sidebarBreakdown.hidden = true;
    const procedureFilter = document.querySelector(".review-controls select");
    if (procedureFilter) procedureFilter.innerHTML = '<option>All procedures</option>' + surgeon.procedures.map((item) => `<option value="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</option>`).join("");
    const reviewTabCount = document.querySelector(".article-navigation a[href*='reviews.html'] .count"); if (reviewTabCount) reviewTabCount.textContent = data.total;
    document.querySelectorAll(".review-group").forEach((group, index) => {
      if (index) { group.hidden = true; return; }
      const header = group.querySelector(".review-group__header span"); if (header) header.textContent = `${data.total} reviews`;
      group.querySelectorAll(".review-row").forEach((row) => row.remove());
      const loadMore = group.querySelector(".load-more");
      const appendReviews = (items) => items.forEach((review) => loadMore?.insertAdjacentHTML("beforebegin", `<article class="review-row"><a class="review-row__body" href="review.html?review=${encodeURIComponent(review.slug)}"><div class="review-byline"><span class="user-avatar">${escapeHtml(review.reviewer[0])}</span><div><strong>${escapeHtml(review.reviewer)}</strong><span>${escapeHtml(review.updated_at.slice(0,10))}</span></div></div><dl class="review-meta"><div><dt>Procedure</dt><dd>${escapeHtml(review.procedure)}</dd></div><div><dt>Technique</dt><dd>${escapeHtml(review.technique)}</dd></div></dl><p>${escapeHtml(review.narrative.slice(0,220))}…</p><span class="read-more">Read full review →</span></a></article>`));
      appendReviews(data.items);
      if (loadMore) {
        loadMore.hidden = !data.has_more;
        loadMore.textContent = "Load more reviews";
        loadMore.addEventListener("click", async () => {
          loadMore.disabled = true;
          try {
            const next = await apiRequest(`/surgeons/${encodeURIComponent(slug)}/reviews?offset=${group.querySelectorAll(".review-row").length}&limit=${data.limit}`);
            appendReviews(next.items); loadMore.hidden = !next.has_more;
          } catch (error) { loadMore.textContent = error.message; }
          finally { loadMore.disabled = false; }
        });
      }
    });
    finishSurgeonLoad();
  }).catch(finishSurgeonLoad);
}

if (pageName === "review.html") {
  const slug = queryParams.get("review");
  if (slug) apiRequest(`/reviews/${encodeURIComponent(slug)}`).then((review) => {
    document.querySelector(".review-detail-header h1").textContent = review.title;
    document.querySelector(".review-detail-header p").innerHTML = `First-person experience by <a href="profile.html?user=${encodeURIComponent(review.reviewer)}">${escapeHtml(review.reviewer)}</a>`;
    document.querySelector(".review-detail-content article").innerHTML = review.narrative.split("\n\n").map((text) => `<p>${escapeHtml(text)}</p>`).join("");
    const surgeonLink = document.querySelector(".breadcrumb a:nth-of-type(2)");
    if (surgeonLink) { surgeonLink.textContent = review.surgeon.name; surgeonLink.href = surgeonUrl(review.surgeon.slug); }
    const reviewsLink = document.querySelector(".breadcrumb a[href*='reviews.html']"); if (reviewsLink) reviewsLink.href = `reviews.html?surgeon=${encodeURIComponent(review.surgeon.slug)}`;
  });
}

if (pageName === "history.html") {
  const slug = selectedSurgeonSlug();
  if (!slug) window.location.replace("directory.html"); else
  Promise.all([apiRequest(`/surgeons/${slug}`), apiRequest(`/surgeons/${slug}/history`)]).then(([surgeon, data]) => {
    document.title = `Revision history of ${surgeon.name} — OpenSurgery`;
    document.querySelector(".history-page h1").textContent = `${surgeon.name} revision history`;
    const subtitle = document.querySelector(".history-page .subtitle"); if (subtitle) subtitle.textContent = `${surgeon.name} · Info page`;
    document.querySelectorAll(".article-navigation a, .breadcrumb a").forEach((link) => {
      if (link.href.includes("index.html")) link.href = surgeonUrl(slug);
      if (link.href.includes("reviews.html")) link.href = surgeonUrl(slug, "reviews");
      if (link.href.includes("talk.html")) link.href = surgeonUrl(slug, "talk");
      if (link.href.includes("edit.html")) link.href = surgeonUrl(slug, "edit");
      if (link.href.includes("history.html")) link.href = surgeonUrl(slug, "history");
    });
    const list = document.querySelector("#history-list"); list.innerHTML = data.items.map((revision) => `<article class="revision"><div class="revision-main"><div class="revision-title"><a href="revision.html?surgeon=${encodeURIComponent(slug)}&revision=${revision.revision_number}">${escapeHtml(new Date(revision.published_at).toLocaleString())}</a></div><p>${escapeHtml(revision.summary)}</p><div class="revision-meta"><a href="profile.html?user=${encodeURIComponent(revision.editor)}">${escapeHtml(revision.editor)}</a><span>${escapeHtml(revision.change_type)}</span></div></div><div class="revision-actions"><a href="revision.html?surgeon=${encodeURIComponent(slug)}&revision=${revision.revision_number}">view version</a></div></article>`).join("");
    finishSurgeonLoad();
  }).catch(finishSurgeonLoad);
}

if (pageName === "revision.html") {
  const slug = selectedSurgeonSlug(); const number = queryParams.get("revision");
  if (number) Promise.all([apiRequest(`/surgeons/${slug}`), apiRequest(`/surgeons/${slug}/revisions/${number}`)]).then(([surgeon, revision]) => {
    document.querySelector(".revision-page h1").textContent = surgeon.name;
    document.querySelectorAll("[data-revision-number]").forEach((node) => { node.textContent = revision.revision_number; });
    const date = document.querySelector("[data-revision-date]"); if (date) date.textContent = new Date(revision.published_at).toLocaleString();
    const summary = document.querySelector("[data-revision-summary]"); if (summary) summary.textContent = revision.summary;
    const body = document.querySelector(".revision-page .article-body");
    if (body) body.innerHTML = revision.article_body.split("\n\n").map((text) => `<p>${escapeHtml(text)}</p>`).join("");
    finishSurgeonLoad();
  }).catch(finishSurgeonLoad);
}

if (pageName === "talk.html") {
  const slug = selectedSurgeonSlug();
  if (!slug) window.location.replace("directory.html"); else
  Promise.all([apiRequest(`/surgeons/${slug}`), apiRequest(`/surgeons/${slug}/talk`)]).then(([surgeon, data]) => {
    document.title = `Talk: ${surgeon.name} — OpenSurgery`;
    const title = document.querySelector(".talk-page .title-row h1"); if (title) title.innerHTML = `<span class="namespace">Talk:</span> ${escapeHtml(surgeon.name)}`;
    const subtitle = document.querySelector(".talk-page .subtitle"); if (subtitle) subtitle.textContent = `Discussion about improvements to the ${surgeon.name} information page`;
    const introNotice = document.querySelector(".talk-notice--intro strong"); if (introNotice) introNotice.textContent = `This is the discussion page for improving the ${surgeon.name} article.`;
    const breadcrumbSurgeon = document.querySelector(".talk-page .breadcrumb a:nth-of-type(2)"); if (breadcrumbSurgeon) { breadcrumbSurgeon.textContent = surgeon.name; breadcrumbSurgeon.href = surgeonUrl(slug); }
    document.querySelectorAll(".article-navigation a").forEach((link) => {
      if (link.href.includes("index.html")) link.href = surgeonUrl(slug);
      if (link.href.includes("reviews.html")) link.href = surgeonUrl(slug, "reviews");
      if (link.href.includes("talk.html")) link.href = surgeonUrl(slug, "talk");
    });
    const firstTopic = document.querySelector(".talk-topic"); if (!firstTopic) return;
    document.querySelectorAll(".talk-topic:not(#new-topic)").forEach((node) => node.remove());
    const toolbar = document.querySelector(".discussion-toolbar");
    data.items.forEach((topic) => toolbar.insertAdjacentHTML("afterend", `<section class="talk-topic" id="${escapeHtml(topic.slug)}"><header class="topic-heading"><h2>${escapeHtml(topic.title)}</h2></header><div class="comment-thread">${topic.comments.map((comment) => `<article class="comment"><div class="comment-marker">${escapeHtml(comment.author[0])}</div><div><p>${escapeHtml(comment.body)}</p><footer><a href="profile.html?user=${encodeURIComponent(comment.author)}">${escapeHtml(comment.author)}</a> <time>${escapeHtml(new Date(comment.created_at).toLocaleString())}</time></footer></div></article>`).join("")}</div></section>`));
    finishSurgeonLoad();
  }).catch(finishSurgeonLoad);
}

if (pageName === "procedures.html") {
  apiRequest("/procedures").then((data) => {
    document.querySelectorAll(".guide-items").forEach((node) => { node.innerHTML = ""; });
    data.items.forEach((procedure) => {
      const section = [...document.querySelectorAll(".guide-section")].find((node) => node.id === procedure.category.toLowerCase());
      section?.querySelector(".guide-items")?.insertAdjacentHTML("beforeend", `<article><h3>${escapeHtml(procedure.name)}</h3><p>${escapeHtml(procedure.description)}</p><div><a href="directory.html?procedure=${encodeURIComponent(procedure.slug)}">Find surgeons</a></div></article>`);
    });
  });
}

if (pageName === "profile.html") {
  const user = queryParams.get("user");
  if (user) apiRequest(`/users/${encodeURIComponent(user)}`).then((profile) => {
    document.querySelectorAll("[data-profile-name]").forEach((node) => { node.textContent = profile.display_name; });
    document.querySelectorAll("[data-profile-initial]").forEach((node) => { node.textContent = profile.display_name[0]; });
    const bio = document.querySelector(".profile-about > p"); if (bio) bio.textContent = profile.bio || "This member has not added a bio.";
  });
}

if (pageName === "practice.html") {
  apiRequest("/practices/northbank-reconstructive-center").then((practice) => {
    document.querySelectorAll(".practice-shell h1").forEach((node) => { node.textContent = practice.name; });
    const content = document.querySelector("[data-practice-content]");
    if (content) content.innerHTML = `<h2>Locations</h2>${practice.locations.map((location) => `<p><strong>${escapeHtml([location.city, location.region].filter(Boolean).join(", "))}</strong><br>${escapeHtml(location.accessibility || "Accessibility information not listed.")}</p>`).join("")}<h2>Linked surgeons</h2>${practice.surgeons.map((surgeon) => `<p><a href="${surgeonUrl(surgeon.slug)}">${escapeHtml(surgeon.name)}</a></p>`).join("")}`;
  });
}

if (pageName === "pending.html") {
  apiRequest("/proposals").then((data) => {
    const list = document.querySelector(".proposal-list"); list.innerHTML = data.items.map((proposal) => `<article><span>${escapeHtml(proposal.state)}</span><h2>${escapeHtml(proposal.summary)}</h2><p><a href="${surgeonUrl(proposal.surgeon.slug)}">${escapeHtml(proposal.surgeon.name)}</a> · Proposed by ${escapeHtml(proposal.author)}</p></article>`).join("");
    apiRequest("/me").then((user) => {
      if (!["trusted_editor", "moderator", "admin"].includes(user.role)) return;
      apiRequest("/moderation/surgeons").then((submissions) => {
        submissions.items.forEach((item) => list.insertAdjacentHTML("beforeend", `<article data-surgeon-submission="${item.id}"><span>New profile</span><h2>${escapeHtml(item.name)}</h2><p>${escapeHtml(item.specialty)} · ${escapeHtml([item.city, item.region, item.country_code].filter(Boolean).join(", "))} · Submitted by ${escapeHtml(item.submitter)}</p><blockquote>${escapeHtml(item.article_body)}</blockquote>${item.sources.map((source) => `<p><a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">Review source</a> — ${escapeHtml(source.note)}</p>`).join("")}<div><button class="primary-button" type="button" data-approve-surgeon>Approve profile</button></div></article>`));
        list.querySelectorAll("[data-approve-surgeon]").forEach((button) => button.addEventListener("click", async () => {
          const article = button.closest("[data-surgeon-submission]");
          try {
            const result = await apiRequest(`/moderation/surgeons/${article.dataset.surgeonSubmission}/approve`, { method: "POST" });
            article.innerHTML = `<span>Published</span><h2>Profile approved</h2><p><a href="${surgeonUrl(result.slug)}">Open the published profile</a></p>`;
          } catch (error) { button.insertAdjacentHTML("afterend", `<p class="form-status">${escapeHtml(error.message)}</p>`); }
        }));
      });
    }).catch(() => {});
  });
}

if (pageName === "search.html") {
  const list = document.querySelector(".search-result-list");
  const query = queryParams.get("q") || "";
  Promise.all([apiRequest(`/surgeons?q=${encodeURIComponent(query)}`), apiRequest("/procedures")]).then(([surgeons, procedures]) => {
    const matchingProcedures = procedures.items.filter((item) => !query || `${item.name} ${item.description}`.toLowerCase().includes(query.toLowerCase()));
    list.innerHTML = surgeons.items.map((item) => `<article><span>Surgeon</span><h2><a href="${surgeonUrl(item.slug)}">${escapeHtml(item.name)}</a></h2><p>${escapeHtml(item.specialty || "Surgeon profile")}</p></article>`).join("") + matchingProcedures.map((item) => `<article><span>Procedure</span><h2><a href="procedures.html#${encodeURIComponent(item.category.toLowerCase())}">${escapeHtml(item.name)}</a></h2><p>${escapeHtml(item.description)}</p></article>`).join("");
    const summary = document.querySelector("[data-search-summary]"); if (summary) summary.textContent = `${surgeons.total + matchingProcedures.length} matching results.`;
  });
}

if (pageName === "write-review.html") {
  const form = document.querySelector("[data-demo-form='review']");
  const selects = form?.querySelectorAll("select");
  if (form && selects?.length) {
    let procedureRecords = [];
    const populateTechniques = () => {
      const procedure = procedureRecords.find((item) => item.slug === selects[1].value);
      const options = procedure?.techniques || [];
      selects[2].innerHTML = '<option value="">Unknown or not listed</option>' + options.map((item) => `<option value="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</option>`).join("");
    };
    Promise.all([apiRequest("/surgeons"), apiRequest("/procedures")]).then(([surgeons, procedures]) => {
      procedureRecords = procedures.items;
      selects[0].innerHTML = surgeons.items.map((item) => `<option value="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</option>`).join("");
      const requestedSurgeon = queryParams.get("surgeon"); if (requestedSurgeon && surgeons.items.some((item) => item.slug === requestedSurgeon)) selects[0].value = requestedSurgeon;
      selects[1].innerHTML = procedures.items.map((item) => `<option value="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</option>`).join("");
      populateTechniques();
    });
    selects[1].addEventListener("change", populateTechniques);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!signedInUser) { form.querySelector(".form-status").textContent = "Log in before submitting a review."; return; }
      const data = new FormData(form);
      const complicationValues = { "None reported": "none_reported", "Complication reported": "complication_reported", "Revision reported": "revision_reported", "Prefer not to say": "prefer_not_to_say" };
      try {
        const uploadedMedia = [];
        for (const name of ["early_photo", "long_term_photo"]) {
          const file = form.elements[name]?.files?.[0];
          if (!file) continue;
          const upload = new FormData(); upload.append("file", file);
          const media = await apiRequest("/media", { method: "POST", body: upload });
          uploadedMedia.push({ name, id: media.id });
        }
        const month = String(data.get("surgery_month") || "");
        const longTerm = uploadedMedia.find((item) => item.name === "long_term_photo");
        const result = await apiRequest("/reviews", { method: "POST", body: JSON.stringify({ surgeon_slug: data.get("surgeon_slug"), procedure_slug: data.get("procedure_slug"), technique_slug: data.get("technique_slug") || null, surgery_date: month ? `${month}-01` : null, surgery_date_precision: "month", location_text: data.get("location") || null, title: data.get("title"), narrative: data.get("narrative"), complications_status: complicationValues[data.get("complications_status")] || "prefer_not_to_say", media_ids: uploadedMedia.map((item) => item.id), designated_long_term_media_id: longTerm && data.get("long_term_confirmed") ? longTerm.id : null }) });
        form.querySelector(".form-status").textContent = `Review saved with status: ${result.state}.`;
      } catch (error) { form.querySelector(".form-status").textContent = error.message; }
    });
  }
}

if (pageName === "add-surgeon.html") {
  const form = document.querySelector("[data-surgeon-create]");
  const procedureSelect = form?.elements.procedure_slugs;
  if (procedureSelect) apiRequest("/procedures").then((data) => {
    procedureSelect.innerHTML = data.items.map((item) => `<option value="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</option>`).join("");
  }).catch((error) => { form.querySelector(".form-status").textContent = error.message; });
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (!signedInUser) { form.querySelector(".form-status").innerHTML = '<a href="login.html">Log in</a> before submitting a surgeon.'; return; }
    const data = new FormData(form);
    const payload = {
      display_name: data.get("display_name"), aliases: data.get("aliases") || null,
      specialty: data.get("specialty"), city: data.get("city"), region: data.get("region") || null,
      country_code: data.get("country_code"), website_url: data.get("website_url") || null,
      practice_name: data.get("practice_name") || null, article_body: data.get("article_body"),
      procedure_slugs: data.getAll("procedure_slugs"), source_url: data.get("source_url"),
      source_note: data.get("source_note"),
    };
    try {
      const result = await apiRequest("/surgeons", { method: "POST", body: JSON.stringify(payload) });
      form.reset();
      form.querySelector(".form-status").textContent = `Profile submitted for review with status: ${result.status}.`;
    } catch (error) { form.querySelector(".form-status").textContent = error.message; }
  });
}

if (["index.html", "surgeon.html"].includes(pageName)) {
  apiRequest("/me").then((user) => {
    if (!["trusted_editor", "moderator", "admin"].includes(user.role)) return;
    const slug = selectedSurgeonSlug();
    if (!slug) return;
    const container = document.querySelector(".article-navigation nav:last-child, .dynamic-surgeon__content aside");
    if (!container || container.querySelector("[data-remove-surgeon]")) return;
    const button = document.createElement("button"); button.type = "button"; button.dataset.removeSurgeon = ""; button.textContent = "Remove profile";
    container.append(button);
    button.addEventListener("click", async () => {
      const reason = window.prompt("Why should this profile be removed? This will be recorded in the audit log.");
      if (!reason || reason.trim().length < 10) return;
      try {
        await apiRequest(`/moderation/surgeons/${encodeURIComponent(slug)}/remove`, { method: "POST", body: JSON.stringify({ reason: reason.trim(), status: "removed" }) });
        window.location.href = "directory.html";
      } catch (error) { window.alert(error.message); }
    });
  }).catch(() => {});
}

if (pageName === "messages.html") {
  const list = document.querySelector(".conversation-list"); const thread = document.querySelector(".message-thread");
  if (!signedInUser) list.innerHTML = '<p><a href="login.html">Log in</a> to view messages.</p>';
  else apiRequest("/conversations").then((data) => {
    list.innerHTML = data.items.map((item) => `<button type="button" data-conversation="${item.id}"><span class="user-avatar">${escapeHtml(item.member[0])}</span><span><strong>${escapeHtml(item.member)}</strong><small>${escapeHtml(item.last_message.slice(0,80))}</small></span></button>`).join("") || "<p>No conversations yet.</p>";
    list.querySelectorAll("button").forEach((button) => button.addEventListener("click", async () => {
      document.querySelector(".message-composer").dataset.conversation = button.dataset.conversation;
      const data = await apiRequest(`/conversations/${button.dataset.conversation}/messages`);
      thread.innerHTML = data.items.map((message) => `<article class="message ${message.mine ? "message--sent" : "message--received"}"><p>${escapeHtml(message.body)}</p><time>${escapeHtml(new Date(message.created_at).toLocaleString())}</time></article>`).join("");
      document.querySelector(".conversation > header strong").textContent = button.querySelector("strong").textContent;
    }));
  }).catch((error) => { list.innerHTML = `<p>${escapeHtml(error.message)}</p>`; });
  const composer = document.querySelector(".message-composer");
  composer?.addEventListener("submit", async (event) => {
    event.preventDefault(); const conversation = composer.dataset.conversation;
    if (!conversation) { composer.querySelector(".form-status").textContent = "Select a conversation first."; return; }
    try { await apiRequest(`/conversations/${conversation}/messages`, { method: "POST", body: JSON.stringify({ body: composer.querySelector("textarea").value }) }); composer.querySelector("textarea").value = ""; composer.querySelector(".form-status").textContent = "Reply sent."; }
    catch (error) { composer.querySelector(".form-status").textContent = error.message; }
  });
}

if (pageName === "settings.html") {
  const form = document.querySelector(".settings-shell form");
  if (!signedInUser) form.querySelector(".form-status").innerHTML = '<a href="login.html">Log in</a> to manage settings.';
  else apiRequest("/me").then((user) => {
    form.elements.display_name.value = user.display_name; form.elements.bio.value = user.bio || ""; form.elements.approximate_region.value = user.approximate_region || "";
    ["allow_messages","allow_new_accounts","email_message_notifications","email_watch_notifications"].forEach((name) => { form.elements[name].checked = Boolean(user[name]); });
  });
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try { await apiRequest("/me", { method: "PATCH", body: JSON.stringify({ bio: form.elements.bio.value || null, approximate_region: form.elements.approximate_region.value || null, allow_messages: form.elements.allow_messages.checked, allow_new_accounts: form.elements.allow_new_accounts.checked, email_message_notifications: form.elements.email_message_notifications.checked, email_watch_notifications: form.elements.email_watch_notifications.checked }) }); form.querySelector(".form-status").textContent = "Settings saved."; }
    catch (error) { form.querySelector(".form-status").textContent = error.message; }
  });
  const exportButton = [...form.querySelectorAll("button")].find((button) => button.textContent.includes("Export my data"));
  exportButton?.addEventListener("click", async () => {
    try { const data = await apiRequest("/me/export"); const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })); link.download = "opensurgery-account-export.json"; link.click(); URL.revokeObjectURL(link.href); }
    catch (error) { form.querySelector(".form-status").textContent = error.message; }
  });
  const deleteButton = [...form.querySelectorAll("button")].find((button) => button.textContent.includes("Delete account"));
  deleteButton?.addEventListener("click", async () => {
    if (!window.confirm("Permanently deactivate this account and anonymize its profile?")) return;
    try { await apiRequest("/me", { method: "DELETE" }); localStorage.removeItem("opensurgery_user"); window.location.href = "home.html"; }
    catch (error) { form.querySelector(".form-status").textContent = error.message; }
  });
}

if (pageName === "forgot-password.html") {
  const form = document.querySelector("[data-demo-form='reset']");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try { const result = await apiRequest("/auth/password-reset", { method: "POST", body: JSON.stringify({ email: form.elements.email.value }) }); form.querySelector(".form-status").textContent = result.message; }
    catch (error) { form.querySelector(".form-status").textContent = error.message; }
  });
}

if (pageName === "edit.html") {
  const slug = selectedSurgeonSlug(); const form = document.querySelector("#edit-form");
  if (!slug) window.location.replace("directory.html"); else
  Promise.all([apiRequest(`/surgeons/${slug}`), apiRequest("/procedures")]).then(([surgeon, procedures]) => {
    document.title = `Edit ${surgeon.name} — OpenSurgery`;
    document.querySelector(".edit-page h1").textContent = `Edit ${surgeon.name}`;
    form.elements.overview.value = surgeon.article_body;
    const mobileTitle = document.querySelector(".mobile-editor-title strong"); if (mobileTitle) mobileTitle.textContent = `Edit ${surgeon.name}`;
    const initials = document.querySelector(".portrait-upload__initials"); if (initials) initials.textContent = surgeon.initials;
    const values = { sidebar_practice: surgeon.profile.practice || "", sidebar_practice_url: surgeon.profile.practice_url || surgeon.website_url || "", city: surgeon.city || "", region: surgeon.region || "", country: surgeon.country || "", specialty: surgeon.specialty || "", languages: (surgeon.profile.languages || []).join(", "), website: surgeon.website_url || surgeon.profile.website_url || "" };
    Object.entries(values).forEach(([name, value]) => { if (form.elements[name]) form.elements[name].value = value; });
    form.elements.practice_description.value = surgeon.profile.practice_summary || "";
    form.elements.procedure_description.value = "";
    form.elements.patient_information.value = surgeon.profile.patient_information || "";
    const selectedSlugs = new Set(surgeon.procedures.map((item) => item.slug));
    const procedureOptions = procedures.items.map((item) => `<option value="${escapeHtml(item.slug)}">${escapeHtml(item.name)}</option>`).join("");
    form.elements.procedures.innerHTML = procedureOptions;
    form.elements.sidebar_procedures.innerHTML = procedureOptions;
    [form.elements.procedures, form.elements.sidebar_procedures].forEach((select) => [...select.options].forEach((option) => { option.selected = selectedSlugs.has(option.value); }));
    document.querySelectorAll(".breadcrumb a[href*='index.html'], .article-navigation a[href*='index.html']").forEach((link) => { link.href = surgeonUrl(slug); link.textContent = link.closest(".breadcrumb") ? surgeon.name : "← Return to Info"; });
    document.querySelectorAll("a[href*='history.html']").forEach((link) => { link.href = surgeonUrl(slug, "history"); });
    finishSurgeonLoad();
  }).catch(finishSurgeonLoad);
  form?.addEventListener("submit", async (event) => {
    event.preventDefault(); if (!signedInUser) { form.querySelector(".form-status").textContent = "Log in before submitting a proposal."; return; }
    const selectedProcedures = [...form.elements.sidebar_procedures.selectedOptions].map((option) => option.value);
    const articleSections = ["overview", "practice_description", "procedure_description", "patient_information"].map((name) => form.elements[name]?.value.trim()).filter(Boolean);
    try { const result = await apiRequest(`/surgeons/${slug}/proposals`, { method: "POST", body: JSON.stringify({ proposed_article_body: articleSections.join("\n\n"), edit_summary: form.elements.edit_summary.value, source_url: form.elements.source_url.value, source_note: form.elements.source_note.value, procedure_slugs: selectedProcedures, profile: { practice: form.elements.sidebar_practice.value, practice_url: form.elements.sidebar_practice_url.value, city: form.elements.city.value, region: form.elements.region.value, country: form.elements.country.value, specialty: form.elements.specialty.value, languages: form.elements.languages.value.split(",").map((item) => item.trim()).filter(Boolean), website_url: form.elements.website.value } }) }); form.querySelector(".form-status").textContent = `Proposal saved with status: ${result.state}.`; }
    catch (error) { form.querySelector(".form-status").textContent = error.message; }
  });
}
