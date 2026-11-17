document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-open-modal]").forEach(btn => btn.addEventListener("click", () => {
    const modal = document.getElementById(btn.dataset.openModal);
    if (modal) { modal.classList.add("open"); document.body.classList.add("modal-open"); }
  }));
  document.querySelectorAll("[data-close-modal]").forEach(btn => btn.addEventListener("click", () => {
    btn.closest(".modal-backdrop")?.classList.remove("open"); document.body.classList.remove("modal-open");
  }));
  document.querySelectorAll(".modal-backdrop").forEach(backdrop => backdrop.addEventListener("click", event => {
    if (event.target === backdrop) { backdrop.classList.remove("open"); document.body.classList.remove("modal-open"); }
  }));

  const form = document.getElementById("garment-form");
  const fileInput = document.getElementById("garment-image");
  const cameraInput = document.getElementById("camera-image");
  const message = document.getElementById("recognition-message");
  const preview = document.getElementById("image-preview");
  const previewImage = document.getElementById("preview-image");

  async function handlePhoto(file) {
    if (!file || !form) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      if (message) message.textContent = "Choose a JPG, PNG or WEBP image.";
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      if (message) message.textContent = "This image is larger than 8 MB. Choose a smaller photo.";
      return;
    }
    if (preview && previewImage) {
      previewImage.src = URL.createObjectURL(file);
      preview.hidden = false;
    }
    if (message) message.textContent = "Preparing your photo and suggesting garment details…";
    const data = new FormData(); data.append("image", file);
    try {
      const response = await fetch("/garments/recognise", { method: "POST", body: data });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Photo processing failed");
      if (result.name) form.elements.name.value = result.name;
      if (result.category) form.elements.category.value = result.category;
      if (result.subcategory) {
        const sub = form.elements.subcategory;
        const option = [...sub.options].find(o => o.value.toLowerCase() === result.subcategory.toLowerCase());
        if (option) sub.value = option.value;
      }
      if (result.color) form.elements.color.value = result.color;
      if (result.season) form.elements.season.value = result.season;
      if (result.image) {
        let hidden = document.getElementById("recognised-image");
        if (!hidden) {
          hidden = document.createElement("input"); hidden.type = "hidden";
          hidden.name = "recognised_image"; hidden.id = "recognised-image"; form.appendChild(hidden);
        }
        hidden.value = result.image;
      }
      if (message) message.textContent = result.name
        ? "Suggested details are ready. Check them, make corrections if needed, then add the garment."
        : (result.message || "Photo prepared. Choose the garment details below.");
    } catch (error) {
      if (message) message.textContent = error.message + " You can still complete the details manually.";
    }
  }
  fileInput?.addEventListener("change", () => handlePhoto(fileInput.files?.[0]));
  cameraInput?.addEventListener("change", () => {
    const file = cameraInput.files?.[0];
    if (file && fileInput) {
      const transfer = new DataTransfer(); transfer.items.add(file); fileInput.files = transfer.files;
      handlePhoto(file);
    }
  });

  const dateInput = document.querySelector('input[type="date"]');
  if (dateInput && !dateInput.value) dateInput.min = new Date().toISOString().slice(0, 10);
});
