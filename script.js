document.querySelector(".search")?.addEventListener("submit", (event) => {
  event.preventDefault();
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
