// Colapsar / expandir el panel "Nueva actividad"
const panelToggle = document.getElementById("panelToggle");
const panelBody = document.getElementById("panelBody");

if (panelToggle && panelBody) {
  panelToggle.addEventListener("click", () => {
    const expanded = panelToggle.getAttribute("aria-expanded") === "true";
    panelToggle.setAttribute("aria-expanded", String(!expanded));
    panelBody.style.display = expanded ? "none" : "flex";
  });
}

// Colapsar / expandir el panel "Registro Completo (Actividades)"
const registryToggle = document.getElementById("registryToggle");
const registryBody = document.getElementById("registryBody");

if (registryToggle && registryBody) {
  registryToggle.addEventListener("click", () => {
    const expanded = registryToggle.getAttribute("aria-expanded") === "true";
    registryToggle.setAttribute("aria-expanded", String(!expanded));
    registryBody.style.display = expanded ? "none" : "block";
  });
}

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

if (dropzone && fileInput) {
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
}

// Control de Modales (Editar / Eliminar)
function openEditModal(id, title, category, date, duration, description) {
  const modal = document.getElementById("editModal");
  const form = document.getElementById("editForm");
  
  form.action = `/activities/${id}/edit`;
  document.getElementById("edit_title").value = title;
  document.getElementById("edit_category").value = category;
  document.getElementById("edit_date").value = date;
  document.getElementById("edit_duration").value = duration;
  document.getElementById("edit_description").value = description;
  
  modal.classList.add("active");
}

function openDeleteModal(id, title) {
  const modal = document.getElementById("deleteModal");
  const form = document.getElementById("deleteForm");
  
  form.action = `/activities/${id}/delete`;
  document.getElementById("deleteTargetTitle").textContent = title;
  
  modal.classList.add("active");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
  }
}