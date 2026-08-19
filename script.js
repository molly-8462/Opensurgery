document.querySelector(".search")?.addEventListener("submit", (event) => {
  event.preventDefault();
});

const contents = document.querySelector(".contents");
const hideContents = document.querySelector(".contents__heading button");

hideContents?.addEventListener("click", () => {
  contents?.classList.toggle("is-collapsed");
  hideContents.textContent = contents?.classList.contains("is-collapsed") ? "show" : "hide";
});
