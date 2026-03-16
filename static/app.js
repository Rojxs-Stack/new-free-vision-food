const cameraBtn = document.getElementById("cameraBtn");
const galleryBtn = document.getElementById("galleryBtn");
const cameraInput = document.getElementById("cameraInput");
const galleryInput = document.getElementById("galleryInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const preview = document.getElementById("preview");
const statusEl = document.getElementById("status");
const resultBox = document.getElementById("resultBox");
const jsonOutput = document.getElementById("jsonOutput");
const prettyResult = document.getElementById("prettyResult");

let selectedFile = null;

cameraBtn.addEventListener("click", () => {
  cameraInput.click();
});

galleryBtn.addEventListener("click", () => {
  galleryInput.click();
});

function setSelectedFile(file) {
  if (!file) return;

  selectedFile = file;

  const imageUrl = URL.createObjectURL(file);
  preview.src = imageUrl;
  preview.style.display = "block";

  resultBox.classList.add("hidden");
  prettyResult.innerHTML = "";
  jsonOutput.textContent = "";
  statusEl.textContent = "Imagen seleccionada.";
}

cameraInput.addEventListener("change", () => {
  const file = cameraInput.files[0];
  setSelectedFile(file);
});

galleryInput.addEventListener("change", () => {
  const file = galleryInput.files[0];
  setSelectedFile(file);
});

function renderPrettyResult(data) {
  if (!data.is_food) {
    prettyResult.innerHTML = `<p>${data.message || "Eso no es comida"}</p>`;
    return;
  }

  prettyResult.innerHTML = `
    <div class="result-grid">
      <div class="result-item"><strong>Comida</strong>${data.food_name}</div>
      <div class="result-item"><strong>Porción</strong>${data.estimated_portion}</div>
      <div class="result-item"><strong>Calorías</strong>${data.calories}</div>
      <div class="result-item"><strong>Proteínas</strong>${data.protein_g} g</div>
      <div class="result-item"><strong>Carbohidratos</strong>${data.carbs_g} g</div>
      <div class="result-item"><strong>Grasas</strong>${data.fat_g} g</div>
      <div class="result-item"><strong>Fibra</strong>${data.fiber_g} g</div>
      <div class="result-item"><strong>Azúcar</strong>${data.sugar_g} g</div>
      <div class="result-item"><strong>Confianza</strong>${data.confidence}%</div>
    </div>
  `;
}

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    statusEl.textContent = "Primero sacá o subí una imagen.";
    return;
  }

  try {
    statusEl.textContent = "Analizando...";
    resultBox.classList.add("hidden");
    prettyResult.innerHTML = "";
    jsonOutput.textContent = "";

    const formData = new FormData();
    formData.append("file", selectedFile);

    const response = await fetch("/analyze-food", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || "Error al analizar la imagen");
    }

    renderPrettyResult(data);
    jsonOutput.textContent = JSON.stringify(data, null, 2);
    resultBox.classList.remove("hidden");
    statusEl.textContent = data.is_food
      ? "Análisis completado."
      : "La imagen no es comida.";
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  }
});
