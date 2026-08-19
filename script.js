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
