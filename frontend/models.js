/** Model catalog and camera-to-model assignments. */
(function (global) {
  "use strict";

  const API = "/api/v1";
  let modelsCache = [];

  async function request(url, options) {
    const response = await fetch(url, options);
    const text = await response.text();
    if (!response.ok) {
      try {
        throw new Error(JSON.parse(text).detail || text || "HTTP " + response.status);
      } catch (error) {
        if (error instanceof SyntaxError) throw new Error(text || "HTTP " + response.status);
        throw error;
      }
    }
    return text ? JSON.parse(text) : null;
  }

  async function loadModels(force) {
    if (!force && modelsCache.length) return modelsCache;
    const data = await request(API + "/models");
    modelsCache = data.items || [];
    return modelsCache;
  }

  function statusText(model) {
    if (!model.enabled) return "отключена";
    return model.exists ? "готова" : "файл не найден";
  }

  async function renderModels() {
    const table = document.getElementById("model-table");
    const msg = document.getElementById("model-list-msg");
    if (!table) return;
    try {
      const models = await loadModels(true);
      table.innerHTML = "";
      models.forEach(function (model) {
        const row = document.createElement("tr");
        [model.id, model.name, model.code, model.task, model.backend, model.path].forEach(function (value) {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.appendChild(cell);
        });
        const state = document.createElement("td");
        state.textContent = statusText(model);
        if (model.enabled && !model.exists) state.className = "model-file-missing";
        row.appendChild(state);
        const actions = document.createElement("td");
        actions.className = "actions";
        const edit = document.createElement("button");
        edit.type = "button";
        edit.className = "btn btn-secondary model-edit-btn";
        edit.dataset.id = String(model.id);
        edit.textContent = "Изменить";
        actions.appendChild(edit);
        if (!model.builtin) {
          const remove = document.createElement("button");
          remove.type = "button";
          remove.className = "btn btn-danger model-delete-btn";
          remove.dataset.id = String(model.id);
          remove.textContent = "Удалить";
          actions.appendChild(remove);
        }
        row.appendChild(actions);
        table.appendChild(row);
      });
      if (msg) msg.textContent = models.length ? "Всего моделей: " + models.length : "Моделей пока нет";
    } catch (error) {
      if (msg) msg.textContent = error.message;
    }
  }

  function openModelModal(model) {
    const modal = document.getElementById("model-modal");
    const form = document.getElementById("model-form");
    if (!modal || !form) return;
    form.reset();
    document.getElementById("model-edit-id").value = model ? String(model.id) : "";
    document.getElementById("model-form-title").textContent = model ? "Изменить модель" : "Добавить модель";
    if (model) {
      form.name.value = model.name;
      form.code.value = model.code;
      form.task.value = model.task;
      form.backend.value = model.backend;
      form.path.value = model.path;
      form.enabled.checked = !!model.enabled;
    }
    document.getElementById("model-form-msg").textContent = "";
    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeModelModal() {
    const modal = document.getElementById("model-modal");
    if (!modal) return;
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  async function populateCameraModelSelect(cameraId) {
    const select = document.getElementById("camera-models");
    if (!select) return;
    const models = await loadModels(false);
    let selected = new Set();
    if (cameraId) {
      const data = await request(API + "/cameras/" + cameraId + "/models");
      selected = new Set((data.items || []).map(function (item) { return Number(item.model_id); }));
    }
    select.innerHTML = "";
    models.forEach(function (model) {
      const option = document.createElement("option");
      option.value = String(model.id);
      option.textContent = model.name + " · " + model.task + (model.enabled ? "" : " (отключена)");
      option.selected = selected.has(Number(model.id));
      select.appendChild(option);
    });
  }

  function selectedCameraModelIds() {
    const select = document.getElementById("camera-models");
    return select ? Array.from(select.selectedOptions).map(function (option) { return Number(option.value); }) : [];
  }

  async function saveCameraModels(cameraId) {
    return request(API + "/cameras/" + cameraId + "/models", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_ids: selectedCameraModelIds() }),
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const table = document.getElementById("model-table");
    const form = document.getElementById("model-form");
    document.getElementById("add-model-btn")?.addEventListener("click", function () { openModelModal(null); });
    document.getElementById("model-modal-close")?.addEventListener("click", closeModelModal);
    document.getElementById("model-modal-backdrop")?.addEventListener("click", closeModelModal);
    document.getElementById("model-cancel-btn")?.addEventListener("click", closeModelModal);
    document.querySelector('[data-tab="models"]')?.addEventListener("click", function () { renderModels(); });

    table?.addEventListener("click", async function (event) {
      const edit = event.target.closest(".model-edit-btn");
      const remove = event.target.closest(".model-delete-btn");
      if (edit) {
        const model = (await loadModels(false)).find(function (item) { return String(item.id) === edit.dataset.id; });
        if (model) openModelModal(model);
      } else if (remove && confirm("Удалить модель? Назначения камерам тоже будут удалены.")) {
        await request(API + "/models/" + remove.dataset.id, { method: "DELETE" });
        modelsCache = [];
        await renderModels();
      }
    });

    form?.addEventListener("submit", async function (event) {
      event.preventDefault();
      const data = new FormData(form);
      const id = document.getElementById("model-edit-id").value;
      const payload = {
        name: String(data.get("name") || "").trim(),
        code: String(data.get("code") || "").trim(),
        task: data.get("task"),
        backend: data.get("backend"),
        path: String(data.get("path") || "").trim(),
        enabled: data.get("enabled") === "on",
        config: {},
      };
      const msg = document.getElementById("model-form-msg");
      try {
        await request(API + "/models" + (id ? "/" + id : ""), {
          method: id ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        modelsCache = [];
        closeModelModal();
        await renderModels();
      } catch (error) {
        if (msg) msg.textContent = error.message;
      }
    });
  });

  global.DF_models = {
    populateCameraModelSelect: populateCameraModelSelect,
    saveCameraModels: saveCameraModels,
    renderModels: renderModels,
  };
})(window);
