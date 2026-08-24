// Colapsar / expandir el panel "Nueva actividad"
const panelToggle = document.getElementById("panelToggle");
const panelBody = document.getElementById("panelBody");

panelToggle.addEventListener("click", () => {
  const expanded = panelToggle.getAttribute("aria-expanded") === "true";
  panelToggle.setAttribute("aria-expanded", String(!expanded));
  panelBody.style.display = expanded ? "none" : "flex";
});

// Zona de arrastrar y soltar archivo
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("attachment");
const filenameLabel = document.getElementById("dropzoneFilename");

function showFilename(file) {
  if (!file) {
    filenameLabel.hidden = true;
    filenameLabel.textContent = "";
    return;
  }
  filenameLabel.hidden = false;
  filenameLabel.textContent = `Archivo seleccionado: ${file.name}`;
}

dropzone.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  showFilename(fileInput.files[0]);
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);

["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);

dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) {
    fileInput.files = e.dataTransfer.files;
    showFilename(file);
  }
});
