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
    if (formStatus) formStatus.textContent = "Proposal ready for review. This prototype has not sent data to a server.";
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

const revisionNumberElements = document.querySelectorAll("[data-revision-number]");

if (revisionNumberElements.length) {
  const revisions = {
    "124": { date: "12 May 2026 at 09:17", editor: "JuniperNorth", summary: "Clarified that buttonhole is listed in current clinic materials and added an archived source." },
    "123": { date: "9 May 2026 at 01:34", editor: "RiverNorth", summary: "Specified that accessibility information applies to the Portland clinic’s main entrance." },
    "122": { date: "22 April 2026 at 18:51", editor: "MapleSignal", summary: "Added Spanish to languages reported by the clinic and included a supporting source." },
    "121": { date: "4 April 2026 at 12:08", editor: "CedarKeys", summary: "Updated the procedure citation to an archived clinic page." },
    "120": { date: "30 March 2026 at 22:16", editor: "ModHarbor", summary: "Reverted unsourced changes to practice location and website." },
    "119": { date: "18 March 2026 at 07:42", editor: "AshAndPine", summary: "Reorganized the practice section and corrected a typographical error." },
  };
  const requested = new URLSearchParams(window.location.search).get("revision") || "123";
  const revision = revisions[requested] || revisions["123"];
  revisionNumberElements.forEach((element) => { element.textContent = requested in revisions ? requested : "123"; });
  const date = document.querySelector("[data-revision-date]");
  const editor = document.querySelector("[data-revision-editor]");
  const summary = document.querySelector("[data-revision-summary]");
  if (date) date.textContent = revision.date;
  if (editor) editor.textContent = revision.editor;
  if (summary) summary.textContent = revision.summary;
  const editorLink = document.querySelector("[data-revision-editor]");
  if (editorLink) editorLink.href = `profile.html?user=${encodeURIComponent(revision.editor)}`;
  const permanentLink = document.querySelector("[data-permanent-link]");
  if (permanentLink) permanentLink.href = `revision.html?revision=${encodeURIComponent(requested in revisions ? requested : "123")}`;
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
  drawer.innerHTML = `<div class="nav-drawer__top"><a class="wordmark" href="home.html"><span class="wordmark__symbol">O</span><span><strong>OpenSurgery</strong><small>Community surgeon guide</small></span></a><button type="button" aria-label="Close navigation">×</button></div><nav aria-label="Main navigation"><strong>Explore</strong><a href="home.html">Home</a><a href="directory.html">Surgeon directory</a><a href="procedures.html">Procedure guides</a><a href="search.html">Search</a><strong>Contribute</strong><a href="write-review.html">Write a review</a><a href="pending.html">Pending edits</a><a href="guidelines.html">Community guidelines</a><strong>Your space</strong><a href="account.html">Account dashboard</a><a href="messages.html">Messages</a><a href="settings.html">Settings</a></nav><footer><a href="policies.html">Policies</a><a href="contact.html">Contact</a></footer>`;
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

let signedInUser = null;
try { signedInUser = JSON.parse(localStorage.getItem("opensurgery_user")); } catch (_) { signedInUser = null; }
if (signedInUser?.displayName) {
  document.querySelectorAll(".account-links").forEach((nav) => {
    nav.innerHTML = `<a href="messages.html">Messages</a><a href="account.html">${signedInUser.displayName}</a>`;
  });
  document.querySelectorAll("[data-account-display]").forEach((node) => { node.textContent = signedInUser.displayName; });
}

document.querySelectorAll("[data-auth-form]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const status = form.querySelector(".form-status");
    const data = new FormData(form);
    if (form.dataset.authForm === "create" && data.get("password") !== data.get("confirm_password")) {
      if (status) status.textContent = "The passwords do not match.";
      return;
    }
    const displayName = String(data.get("display_name") || data.get("email") || "JuniperNorth").split("@")[0];
    localStorage.setItem("opensurgery_user", JSON.stringify({ displayName }));
    if (status) status.textContent = "Success. Opening your account…";
    window.setTimeout(() => { window.location.href = "account.html"; }, 350);
  });
});

document.querySelector(".dashboard-signout")?.addEventListener("click", () => {
  localStorage.removeItem("opensurgery_user");
  window.location.href = "home.html";
});

document.querySelectorAll("[data-demo-form]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const type = form.dataset.demoForm;
    const messages = { reset: "Reset instructions would be sent now when the email service is connected.", settings: "Settings saved in this frontend demonstration.", review: "Review submitted for moderation in this frontend demonstration.", contact: "Message prepared successfully. No email was sent from this frontend demonstration." };
    const status = form.querySelector(".form-status");
    if (status) status.textContent = messages[type] || "Saved.";
  });
});

const queryParams = new URLSearchParams(window.location.search);
const searchInput = document.querySelector("[data-search-input]");
const searchQuery = queryParams.get("q");
if (searchInput && searchQuery) searchInput.value = searchQuery;
const searchSummary = document.querySelector("[data-search-summary]");
if (searchSummary && searchQuery) searchSummary.textContent = `Showing prototype matches for “${searchQuery}”.`;

const profileName = queryParams.get("user");
if (profileName) {
  document.querySelectorAll("[data-profile-name]").forEach((node) => { node.textContent = profileName; });
  document.querySelectorAll("[data-profile-initial]").forEach((node) => { node.textContent = profileName.charAt(0).toUpperCase(); });
}
const messageDialog = document.querySelector(".message-dialog");
document.querySelector(".message-user-button")?.addEventListener("click", () => messageDialog?.showModal());
messageDialog?.addEventListener("close", () => {
  if (messageDialog.returnValue === "send") {
    const status = messageDialog.querySelector(".form-status");
    if (status) status.textContent = "Message sent in this frontend demonstration.";
    messageDialog.showModal();
  }
});

document.querySelectorAll(".photo-slot.has-photo").forEach((button) => {
  button.addEventListener("click", () => {
    document.body.classList.add("photos-visible");
    if (photoToggle) { photoToggle.setAttribute("aria-pressed", "true"); photoToggle.lastChild.textContent = " Hide surgical photos"; }
  });
});

document.querySelectorAll(".load-more").forEach((button) => {
  button.addEventListener("click", () => { button.textContent = "More reviews will load when the API is connected"; button.disabled = true; });
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
      composer.addEventListener("submit", (event) => { event.preventDefault(); if (composer.reportValidity()) composer.querySelector(".form-status").textContent = "Topic ready to post when the community API is connected."; });
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

const surgeonRecords = {
  adrian: { name: "Adrian Lee", initials: "AL", country: "Canada", detail: "Craniofacial surgeon · Toronto, Ontario, Canada", procedure: "Facial feminization surgery and facial revision", reviews: "21", overview: "Adrian Lee is a fictional craniofacial surgeon included to demonstrate a directory profile." },
  samira: { name: "Samira Khan", initials: "SK", country: "United Kingdom", detail: "Plastic surgeon · Manchester, United Kingdom", procedure: "Chest masculinization and breast augmentation", reviews: "17", overview: "Samira Khan is a fictional plastic surgeon included to demonstrate a directory profile." },
  narin: { name: "Narin Chai", initials: "NC", country: "Thailand", detail: "Gender-affirming surgeon · Bangkok, Thailand", procedure: "Vaginoplasty and revision surgery", reviews: "52", overview: "Narin Chai is a fictional gender-affirming surgeon included to demonstrate a directory profile." }
};
const surgeonPage = document.querySelector("[data-surgeon-page]");
if (surgeonPage) {
  const record = surgeonRecords[queryParams.get("surgeon")] || surgeonRecords.adrian;
  const values = { "[data-surgeon-name]": record.name, "[data-surgeon-initials]": record.initials, "[data-surgeon-country]": record.country, "[data-surgeon-detail]": record.detail, "[data-surgeon-procedure]": record.procedure, "[data-surgeon-reviews]": record.reviews, "[data-surgeon-overview]": record.overview };
  Object.entries(values).forEach(([selector, value]) => { const node = document.querySelector(selector); if (node) node.textContent = value; });
  document.title = `${record.name} — OpenSurgery`;
}

const contactSubject = queryParams.get("subject");
const contactSubjectInput = document.querySelector(".contact-shell input[type='text']");
if (contactSubject && contactSubjectInput) contactSubjectInput.value = contactSubject;

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
  if (label === "report review") button.addEventListener("click", () => { window.location.href = "contact.html?subject=Report%20review"; });
  if (label === "save draft" || label.includes("preview")) {
    button.addEventListener("click", () => {
      const form = button.closest("form");
      const status = form?.querySelector(".form-status");
      if (status) status.textContent = label === "save draft" ? "Draft saved in this browser demonstration." : "Preview is ready; submitted data remains in the form.";
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
  if (button.textContent.includes("Export my data")) button.addEventListener("click", () => {
    const blob = new Blob([JSON.stringify({ prototype: true, account: signedInUser?.displayName || "JuniperNorth" }, null, 2)], { type: "application/json" });
    const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "opensurgery-account-export.json"; link.click(); URL.revokeObjectURL(link.href);
  });
  if (button.textContent.includes("Delete account")) button.addEventListener("click", () => {
    const status = button.closest("form")?.querySelector(".form-status");
    if (status) status.textContent = "Account deletion requires password confirmation in the production service.";
  });
});

document.querySelectorAll(".contact-layout > nav button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".contact-layout > nav button").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    const select = document.querySelector(".contact-layout select");
    if (select) select.value = button.textContent.replace("Report a ", "").replace("Surgeon correction", "Surgeon correction").replace("Privacy request", "Privacy request").replace("General question", "General question").replace("safety issue", "Safety issue");
  });
});
