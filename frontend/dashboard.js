/** Левая колонка отделов: раскрывается и показывает рабочие зоны. */
window.DF_zoneIndex = window.DF_zoneIndex || {};
window.DF_zoneIndexReady = false;

window.DF_setZoneIndex = function (summary) {
  const byId = {};
  (summary.departments || []).forEach(function (department) {
    if (department.id == null) return;
    byId[String(department.id)] = department.zones || [];
  });
  window.DF_zoneIndex = byId;
  window.DF_zoneIndexReady = true;
};

window.DF_attachZones = function (items, done) {
  function apply() {
    (items || []).forEach(function (item) {
      if (!item.zones) item.zones = window.DF_zoneIndex[String(item.id)] || [];
    });
    done(items);
  }
  if (window.DF_zoneIndexReady) {
    apply();
    return;
  }
  fetch("/api/v1/dashboard/summary")
    .then(function (response) { return response.json(); })
    .then(function (summary) {
      window.DF_setZoneIndex(summary);
      apply();
    })
    .catch(function () { done(items); });
};

function dfFmtDuration(seconds) {
  const minutes = Math.max(0, Math.round((Number(seconds) || 0) / 60));
  const hours = Math.floor(minutes / 60);
  return hours + "ч " + String(minutes % 60).padStart(2, "0") + "м";
}

function dfFmtPersonHours(seconds) {
  return ((Number(seconds) || 0) / 3600).toLocaleString("ru-RU", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

function dfUtilization(work, idle) {
  const total = (Number(work) || 0) + (Number(idle) || 0);
  return total ? Math.round(((Number(work) || 0) / total) * 100) : 0;
}

function dfZoneKey(zone) {
  return String(zone.camera_id) + ":" + String(zone.roi_index);
}

window.DF_fillDeptNav = function (nav, items, selectedId, onSelect, zoneState) {
  if (!nav) return;
  const selectedZoneKey = zoneState && zoneState.key ? String(zoneState.key) : "";
  nav.replaceChildren();
  (items || []).forEach(function (item) {
    const selected = String(selectedId) === String(item.id);
    const wrap = document.createElement("details");
    wrap.className = "dept-nav-item";
    if (selected) wrap.open = true;
    const summaryEl = document.createElement("summary");
    summaryEl.className =
      "dept-nav-btn" + (selected && !selectedZoneKey ? " active" : "");
    const label = document.createElement("span");
    label.textContent = item.name;
    summaryEl.appendChild(label);
    if (item.count) {
      const meta = document.createElement("small");
      meta.textContent = item.count;
      summaryEl.appendChild(meta);
    }
    summaryEl.addEventListener("click", function (event) {
      if (selected && selectedZoneKey) {
        event.preventDefault();
        onSelect(item.id);
        return;
      }
      if (selected) return;
      event.preventDefault();
      onSelect(item.id);
    });
    wrap.appendChild(summaryEl);
    const list = document.createElement("div");
    list.className = "dept-zone-list";
    const zones = item.zones || [];
    if (!zones.length) {
      const empty = document.createElement("p");
      empty.className = "dept-zone-empty";
      empty.textContent = item.emptyText || "Нет рабочих зон";
      list.appendChild(empty);
    } else {
      zones.forEach(function (zone) {
        const zKey = dfZoneKey(zone);
        const zSelected = selectedZoneKey === zKey;
        const clickable = !!(zoneState && zoneState.onSelect);
        const zBtn = document.createElement(clickable ? "button" : "div");
        if (clickable) zBtn.type = "button";
        zBtn.className = "dept-zone-btn" + (zSelected ? " active" : "");
        const zName = document.createElement("span");
        zName.textContent = zone.name || "Зона";
        zBtn.appendChild(zName);
        if (zone.camera_name) {
          const zCam = document.createElement("small");
          zCam.textContent = zone.camera_name;
          zBtn.appendChild(zCam);
        }
        if (clickable) {
          zBtn.addEventListener("click", function () {
            if (zSelected) {
              onSelect(item.id);
              return;
            }
            zoneState.onSelect(item.id, zKey, zone);
          });
        }
        list.appendChild(zBtn);
      });
    }
    wrap.appendChild(list);
    nav.appendChild(wrap);
  });
};

/** Главная сводка: один API-запрос, фильтр по отделу на клиенте. */
(function () {
  const API = "/api/v1/dashboard/summary";
  const byId = (id) => document.getElementById(id);
  let summary = null;
  let selectedId = "";
  let selectedZoneKey = "";

  const formatDuration = dfFmtDuration;
  const formatPersonHours = dfFmtPersonHours;
  const utilization = dfUtilization;

  function text(id, value) {
    const element = byId(id);
    if (element) element.textContent = value;
  }

  function deptKey(department) {
    return department.id == null ? "none" : String(department.id);
  }

  function ensureSelected() {
    const departments = (summary && summary.departments) || [];
    if (!departments.some(function (item) { return deptKey(item) === selectedId; })) {
      selectedId = departments.length ? deptKey(departments[0]) : "";
      selectedZoneKey = "";
    }
    if (!selectedZoneKey) return;
    const department = departments.find(function (item) {
      return deptKey(item) === selectedId;
    });
    const found = department && (department.zones || []).some(function (zone) {
      return dfZoneKey(zone) === selectedZoneKey;
    });
    if (!found) selectedZoneKey = "";
  }

  function viewFromSelection() {
    if (!summary) return null;
    ensureSelected();
    const department = (summary.departments || []).find(function (item) {
      return deptKey(item) === selectedId;
    });
    if (!department) {
      return {
        scope: "dept",
        name: null,
        cameraName: "",
        data: {
          date: summary.date,
          department_count: 0,
          camera_count: 0,
          enabled_camera_count: 0,
          zone_count: 0,
          work_seconds: 0,
          idle_seconds: 0,
          person_seconds: 0,
          packages: 0,
          departments: [],
        },
      };
    }
    const zone = selectedZoneKey
      ? (department.zones || []).find(function (item) {
          return dfZoneKey(item) === selectedZoneKey;
        })
      : null;
    if (zone) {
      return {
        scope: "zone",
        name: zone.name,
        cameraName: zone.camera_name || "",
        data: {
          date: summary.date,
          department_count: 1,
          camera_count: 1,
          enabled_camera_count: 1,
          zone_count: 1,
          work_seconds: zone.work_seconds,
          idle_seconds: zone.idle_seconds,
          person_seconds: zone.person_seconds,
          packages: 0,
          departments: [
            Object.assign({}, department, {
              camera_count: 1,
              enabled_camera_count: 1,
              zone_count: 1,
              work_seconds: zone.work_seconds,
              idle_seconds: zone.idle_seconds,
              person_seconds: zone.person_seconds,
              zones: [zone],
            }),
          ],
        },
      };
    }
    return {
      scope: "dept",
      name: department.name,
      cameraName: "",
      data: {
        date: summary.date,
        department_count: department.id == null ? 0 : 1,
        camera_count: department.camera_count,
        enabled_camera_count: department.enabled_camera_count,
        zone_count: department.zone_count,
        work_seconds: department.work_seconds,
        idle_seconds: department.idle_seconds,
        person_seconds: department.person_seconds,
        packages: department.packages,
        departments: [department],
      },
    };
  }

  function renderNav() {
    const nav = byId("dashboard-dept-nav");
    if (!nav || !summary) return;
    ensureSelected();
    window.DF_fillDeptNav(
      nav,
      (summary.departments || []).map(function (department) {
        return {
          id: deptKey(department),
          name: department.name,
          count: department.zone_count + " зон",
          zones: department.zones || [],
        };
      }),
      selectedId,
      function (id) {
        selectedId = id;
        selectedZoneKey = "";
        render();
      },
      {
        key: selectedZoneKey,
        onSelect: function (deptId, zoneKey) {
          selectedId = deptId;
          selectedZoneKey = zoneKey;
          render();
        },
      }
    );
  }

  function renderDepartments(items, filtered) {
    const container = byId("dashboard-departments");
    if (!container) return;
    container.replaceChildren();

    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-dashboard";
      empty.textContent = "Добавьте цехи и камеры — здесь появится оперативная сводка.";
      container.appendChild(empty);
      return;
    }

    items.forEach(function (department, index) {
      const card = document.createElement("details");
      card.className = "department-card";
      if (filtered || index < 2) card.open = true;

      const summaryEl = document.createElement("summary");
      const titleRow = document.createElement("div");
      titleRow.className = "department-title-row";
      const title = document.createElement("h3");
      title.textContent = department.name;
      const number = document.createElement("span");
      number.className = "department-index";
      number.textContent = String(index + 1).padStart(2, "0");
      titleRow.append(title, number);

      const meta = document.createElement("div");
      meta.className = "department-meta";
      const cameras = document.createElement("span");
      cameras.textContent = "Камеры ";
      const camerasValue = document.createElement("b");
      camerasValue.textContent =
        department.enabled_camera_count + " / " + department.camera_count;
      cameras.appendChild(camerasValue);
      const zones = document.createElement("span");
      zones.textContent = "Зоны ";
      const zonesValue = document.createElement("b");
      zonesValue.textContent = department.zone_count;
      zones.appendChild(zonesValue);
      const ratio = document.createElement("span");
      ratio.textContent = "Работа ";
      const ratioValue = document.createElement("b");
      ratioValue.textContent =
        utilization(department.work_seconds, department.idle_seconds) + "%";
      ratio.appendChild(ratioValue);
      meta.append(cameras, zones, ratio);

      const progress = document.createElement("div");
      progress.className = "department-progress";
      const progressValue = document.createElement("i");
      progressValue.style.width =
        utilization(department.work_seconds, department.idle_seconds) + "%";
      progress.appendChild(progressValue);
      summaryEl.append(titleRow, meta, progress);
      card.appendChild(summaryEl);

      const zoneList = document.createElement("div");
      zoneList.className = "zone-list";
      if (!department.zones.length) {
        const noZones = document.createElement("p");
        noZones.className = "zone-row";
        noZones.textContent = "Рабочие зоны ещё не настроены";
        zoneList.appendChild(noZones);
      } else {
        department.zones.forEach(function (zone) {
          const row = document.createElement("div");
          row.className = "zone-row";
          const name = document.createElement("span");
          name.className = "zone-name";
          const strong = document.createElement("b");
          strong.textContent = zone.name;
          const camera = document.createElement("small");
          camera.textContent = zone.camera_name;
          name.append(strong, camera);
          const values = document.createElement("span");
          values.className = "zone-values";
          values.textContent =
            formatDuration(zone.work_seconds) + " · " + formatPersonHours(zone.person_seconds) + " чел·ч";
          row.append(name, values);
          zoneList.appendChild(row);
        });
      }
      card.appendChild(zoneList);
      container.appendChild(card);
    });
  }

  function renderAiReport(view, ratio) {
    const list = byId("dashboard-ai-report");
    if (!list) return;
    const data = view.data;
    const scope = view.name || "Производство";
    const lines = [];
    if (!data.zone_count) {
      lines.push("Рабочие зоны не настроены — сводка пустая.");
    } else {
      if (ratio >= 80) {
        lines.push(scope + ": загрузка " + ratio + "% — смена идёт стабильно.");
      } else if (ratio >= 50) {
        lines.push(
          scope + ": загрузка " + ratio + "% — простой " + formatDuration(data.idle_seconds) + "."
        );
      } else {
        lines.push(
          scope + ": загрузка " + ratio + "% — простой больше работы. Проверьте зоны."
        );
      }
      if (view.scope !== "zone") {
        let worst = null;
        (data.departments || []).forEach(function (department) {
          (department.zones || []).forEach(function (zone) {
            if (!worst || zone.idle_seconds > worst.idle_seconds) {
              worst = { name: zone.name, dept: department.name, idle_seconds: zone.idle_seconds };
            }
          });
        });
        if (worst && worst.idle_seconds > 0) {
          lines.push(
            "Больше всего простоя: " + worst.name + " (" + worst.dept + ") — " +
              formatDuration(worst.idle_seconds) + "."
          );
        }
        const off = (Number(data.camera_count) || 0) - (Number(data.enabled_camera_count) || 0);
        if (off > 0) {
          lines.push("Выключено камер: " + off + " из " + data.camera_count + ".");
        }
      }
      if (view.scope === "zone") {
        lines.push(
          "Упаковки считаются по камере, не по зоне. Чел·часы: " +
            formatPersonHours(data.person_seconds) + "."
        );
      } else {
        lines.push(
          "Упаковок: " + Number(data.packages || 0).toLocaleString("ru-RU") +
            ". Чел·часы: " + formatPersonHours(data.person_seconds) + "."
        );
      }
    }
    list.replaceChildren();
    lines.forEach(function (line) {
      const item = document.createElement("li");
      item.textContent = line;
      list.appendChild(item);
    });
  }

  function render() {
    const view = viewFromSelection();
    if (!view) return;
    const data = view.data;
    const title = byId("dashboard-title");
    if (title) {
      title.innerHTML = view.name
        ? view.name + " <span>сегодня</span>"
        : "Производство <span>сегодня</span>";
    }
    text("dash-work-kpi", formatDuration(data.work_seconds));
    text("dash-cameras", data.camera_count);
    text("dash-cameras-note", view.scope === "zone" ? view.cameraName || "камера" : data.enabled_camera_count + " включено");
    text("dash-zones", data.zone_count);
    text("dash-person-hours", formatPersonHours(data.person_seconds));
    text("dash-idle-kpi", formatDuration(data.idle_seconds));
    text("dash-packages", view.scope === "zone" ? "—" : Number(data.packages || 0).toLocaleString("ru-RU"));
    text("dash-zones-title", view.scope === "zone" ? "Зона" : "Зоны");
    text(
      "dashboard-date",
      new Date(data.date + "T00:00:00").toLocaleDateString("ru-RU", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    );

    const ratio = utilization(data.work_seconds, data.idle_seconds);
    text("dash-utilization", ratio);
    text("dash-work", formatDuration(data.work_seconds));
    text("dash-idle", formatDuration(data.idle_seconds));
    const bar = byId("dash-utilization-bar");
    if (bar) bar.style.width = ratio + "%";
    renderNav();
    renderDepartments(data.departments || [], view.scope === "dept");
    renderAiReport(view, ratio);
  }

  async function loadDashboard() {
    const refresh = byId("dashboard-refresh");
    const state = byId("dash-load-state");
    if (refresh) refresh.classList.add("loading");
    if (state) {
      state.classList.remove("error");
      state.lastChild.textContent = " Обновление…";
    }
    try {
      const response = await fetch(API);
      if (!response.ok) throw new Error((await response.text()) || "HTTP " + response.status);
      summary = await response.json();
      window.DF_setZoneIndex(summary);
      ensureSelected();
      render();
      if (state) state.lastChild.textContent = " Данные из БД";
    } catch (error) {
      if (state) {
        state.classList.add("error");
        state.lastChild.textContent = " Нет данных";
      }
      const container = byId("dashboard-departments");
      if (container) {
        const message = document.createElement("p");
        message.className = "empty-dashboard";
        message.textContent = "Не удалось загрузить сводку: " + error.message;
        container.replaceChildren(message);
      }
    } finally {
      if (refresh) refresh.classList.remove("loading");
    }
  }

  function openTab(tab) {
    const button = document.querySelector('.nav-tab[data-tab="' + tab + '"]');
    if (button) button.click();
  }

  document.querySelectorAll("[data-open-tab]").forEach(function (element) {
    element.addEventListener("click", function (event) {
      event.preventDefault();
      openTab(element.dataset.openTab);
    });
  });

  const refresh = byId("dashboard-refresh");
  if (refresh) refresh.addEventListener("click", loadDashboard);

  function updateClock() {
    text(
      "nav-clock",
      new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
    );
  }

  updateClock();
  setInterval(updateClock, 30000);
  loadDashboard();
  setInterval(function () {
    const dashboard = byId("tab-dashboard");
    if (dashboard && dashboard.classList.contains("active")) loadDashboard();
  }, 60000);
  window.DF_loadDashboard = loadDashboard;
})();
