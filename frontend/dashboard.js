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

/** Главная сводка + настраиваемая доска виджетов. */
(function () {
  const API = "/api/v1/dashboard/summary";
  const LAYOUT_KEY = "df_dashboard_layout_v1";
  const byId = (id) => document.getElementById(id);
  let summary = null;
  let selectedId = "";
  let selectedZoneKey = "";
  let layout = [];
  let drag = null;
  let resize = null;

  const WIDGET_DEFS = {
    work: { title: "Работа", desc: "Время работы за смену", w: 2, h: 1 },
    cameras: { title: "Камеры", desc: "Количество и статус", w: 2, h: 1 },
    zones: { title: "Рабочие зоны", desc: "ROI под контролем", w: 2, h: 1 },
    person_hours: { title: "Чел·часы", desc: "По зонам присутствия", w: 2, h: 1 },
    people_zone: { title: "Люди в зоне", desc: "Счётчик присутствия people-zone", w: 2, h: 1 },
    idle: { title: "Простой", desc: "Время простоя за смену", w: 2, h: 1 },
    packages: { title: "Упаковки", desc: "Обнаружено сегодня", w: 2, h: 1 },
    structure: { title: "Цехи и зоны", desc: "Структура и показатели", w: 8, h: 4 },
    utilization: { title: "Работа / простой", desc: "Загрузка смены", w: 4, h: 4 },
    ai_report: { title: "ИИ отчёт", desc: "Анализ по данным БД", w: 4, h: 4 },
  };

  const DEFAULT_LAYOUT = [
    { id: "w1", type: "work", x: 0, y: 0, w: 2, h: 1 },
    { id: "w2", type: "cameras", x: 2, y: 0, w: 2, h: 1 },
    { id: "w3", type: "zones", x: 4, y: 0, w: 2, h: 1 },
    { id: "w4", type: "person_hours", x: 6, y: 0, w: 2, h: 1 },
    { id: "w5", type: "idle", x: 8, y: 0, w: 2, h: 1 },
    { id: "w6", type: "packages", x: 10, y: 0, w: 2, h: 1 },
    { id: "w7", type: "structure", x: 0, y: 1, w: 8, h: 4 },
    { id: "w8", type: "utilization", x: 8, y: 1, w: 4, h: 4 },
    { id: "w9", type: "ai_report", x: 8, y: 5, w: 4, h: 3 },
  ];

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

  function layoutStorageKey() {
    return LAYOUT_KEY + ":" + selectedId + ":" + selectedZoneKey;
  }

  function cloneLayout(items) {
    return (items || []).map(function (item) {
      return Object.assign({}, item);
    });
  }

  function loadLayout() {
    try {
      const raw = localStorage.getItem(layoutStorageKey());
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length) return parsed;
      }
    } catch (error) {
      /* ponytail: bad layout JSON → default */
    }
    return cloneLayout(DEFAULT_LAYOUT);
  }

  function saveLayout() {
    localStorage.setItem(layoutStorageKey(), JSON.stringify(layout));
  }

  function nextWidgetId() {
    return "w" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
  }

  function findFreeSpot(w, h) {
    let y = 0;
    while (y < 40) {
      for (let x = 0; x <= 12 - w; x += 1) {
        const clash = layout.some(function (item) {
          return !(
            x + w <= item.x ||
            x >= item.x + item.w ||
            y + h <= item.y ||
            y >= item.y + item.h
          );
        });
        if (!clash) return { x: x, y: y };
      }
      y += 1;
    }
    return { x: 0, y: layout.reduce(function (max, item) {
      return Math.max(max, item.y + item.h);
    }, 0) };
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
          people_zone_workers: 0,
          people_zone_person_seconds: 0,
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
          people_zone_workers: zone.people_zone_workers,
          people_zone_person_seconds: zone.people_zone_person_seconds,
          packages: 0,
          departments: [
            Object.assign({}, department, {
              camera_count: 1,
              enabled_camera_count: 1,
              zone_count: 1,
              work_seconds: zone.work_seconds,
              idle_seconds: zone.idle_seconds,
              person_seconds: zone.person_seconds,
              people_zone_workers: zone.people_zone_workers,
              people_zone_person_seconds: zone.people_zone_person_seconds,
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
        people_zone_workers: department.people_zone_workers,
        people_zone_person_seconds: department.people_zone_person_seconds,
        packages: department.packages,
        departments: [department],
      },
    };
  }

  function aiLines(view, ratio) {
    const data = view.data;
    const scope = view.name || "Производство";
    const lines = [];
    if (!data.zone_count) {
      lines.push("Рабочие зоны не настроены — сводка пустая.");
      return lines;
    }
    if (ratio >= 80) {
      lines.push(scope + ": загрузка " + ratio + "% — смена идёт стабильно.");
    } else if (ratio >= 50) {
      lines.push(scope + ": загрузка " + ratio + "% — простой " + formatDuration(data.idle_seconds) + ".");
    } else {
      lines.push(scope + ": загрузка " + ratio + "% — простой больше работы. Проверьте зоны.");
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
      lines.push(
        "Упаковок: " + Number(data.packages || 0).toLocaleString("ru-RU") +
          ". Чел·часы: " + formatPersonHours(data.person_seconds) + "."
      );
    } else {
      lines.push("Чел·часы зоны: " + formatPersonHours(data.person_seconds) + ".");
    }
    return lines;
  }

  function buildDepartmentsPanel(container, departments, filtered) {
    container.replaceChildren();
    if (!departments.length) {
      const empty = document.createElement("p");
      empty.className = "empty-dashboard";
      empty.textContent = "Добавьте цехи и камеры — здесь появится оперативная сводка.";
      container.appendChild(empty);
      return;
    }
    departments.forEach(function (department, index) {
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
      camerasValue.textContent = department.enabled_camera_count + " / " + department.camera_count;
      cameras.appendChild(camerasValue);
      const zones = document.createElement("span");
      zones.textContent = "Зоны ";
      const zonesValue = document.createElement("b");
      zonesValue.textContent = department.zone_count;
      zones.appendChild(zonesValue);
      const ratio = document.createElement("span");
      ratio.textContent = "Работа ";
      const ratioValue = document.createElement("b");
      ratioValue.textContent = utilization(department.work_seconds, department.idle_seconds) + "%";
      ratio.appendChild(ratioValue);
      meta.append(cameras, zones, ratio);
      const progress = document.createElement("div");
      progress.className = "department-progress";
      const progressValue = document.createElement("i");
      progressValue.style.width = utilization(department.work_seconds, department.idle_seconds) + "%";
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

  function fillKpiBody(body, type, view, ratio) {
    const data = view.data;
    body.replaceChildren();
    if (type === "work") {
      body.innerHTML =
        '<span class="kpi-label">Работа</span><strong>' + formatDuration(data.work_seconds) +
        '</strong><small>за текущую смену</small>';
      return;
    }
    if (type === "cameras") {
      body.innerHTML =
        '<span class="kpi-label">Камеры</span><strong>' + data.camera_count +
        '</strong><small>' + (view.scope === "zone" ? (view.cameraName || "камера") : data.enabled_camera_count + " включено") +
        "</small>";
      return;
    }
    if (type === "zones") {
      body.innerHTML =
        '<span class="kpi-label">Рабочие зоны</span><strong>' + data.zone_count +
        '</strong><small>ROI под контролем</small>';
      return;
    }
    if (type === "person_hours") {
      body.innerHTML =
        '<span class="kpi-label">Чел·часы</span><strong>' + formatPersonHours(data.person_seconds) +
        '</strong><small>по рабочим зонам</small>';
      return;
    }
    if (type === "people_zone") {
      body.innerHTML =
        '<span class="kpi-label">Люди в зоне</span><strong>' +
        Number(data.people_zone_workers || 0) +
        '</strong><small>сейчас · ' +
        formatPersonHours(data.people_zone_person_seconds) +
        ' чел·ч за смену</small>';
      return;
    }
    if (type === "idle") {
      body.innerHTML =
        '<span class="kpi-label">Простой</span><strong>' + formatDuration(data.idle_seconds) +
        '</strong><small>за текущую смену</small>';
      return;
    }
    if (type === "packages") {
      body.innerHTML =
        '<span class="kpi-label">Упаковки</span><strong>' +
        (view.scope === "zone" ? "—" : Number(data.packages || 0).toLocaleString("ru-RU")) +
        '</strong><small>обнаружено сегодня</small>';
      return;
    }
    if (type === "structure") {
      const wrap = document.createElement("div");
      wrap.className = "widget-structure";
      const head = document.createElement("div");
      head.className = "panel-heading";
      head.innerHTML =
        '<div><p class="panel-kicker">Структура производства</p><h2>' +
        (view.scope === "zone" ? "Зона" : "Цехи и зоны") + "</h2></div>";
      const grid = document.createElement("div");
      grid.className = "department-grid";
      buildDepartmentsPanel(grid, data.departments || [], view.scope === "dept");
      wrap.append(head, grid);
      body.appendChild(wrap);
      return;
    }
    if (type === "utilization") {
      const wrap = document.createElement("div");
      wrap.className = "widget-utilization";
      wrap.innerHTML =
        '<div class="panel-heading"><div><p class="panel-kicker">Баланс смены</p><h2>Работа / простой</h2></div></div>' +
        '<div class="utilization-number"><strong>' + ratio + '</strong><span>%</span></div>' +
        '<div class="utilization-track" aria-hidden="true"><i style="width:' + ratio + '%"></i></div>' +
        '<div class="utilization-legend">' +
        '<span><i class="legend-work"></i>Работа <b>' + formatDuration(data.work_seconds) + "</b></span>" +
        '<span><i class="legend-idle"></i>Простой <b>' + formatDuration(data.idle_seconds) + "</b></span>" +
        "</div>" +
        '<button type="button" class="dashboard-link" data-open-tab="stats">Открыть подробную статистику</button>';
      body.appendChild(wrap);
      return;
    }
    if (type === "ai_report") {
      const wrap = document.createElement("div");
      wrap.className = "widget-ai";
      const head = document.createElement("div");
      head.className = "panel-heading";
      head.innerHTML = '<div><p class="panel-kicker">Анализ смены</p><h2>ИИ отчёт</h2></div>';
      const list = document.createElement("ul");
      list.className = "ai-report-list";
      aiLines(view, ratio).forEach(function (line) {
        const item = document.createElement("li");
        item.textContent = line;
        list.appendChild(item);
      });
      wrap.append(head, list);
      body.appendChild(wrap);
    }
  }

  function renderWidgetContent(node, view, ratio) {
    const body = node.querySelector(".widget-body");
    if (!body) return;
    fillKpiBody(body, node.dataset.widgetType, view, ratio);
  }

  function createWidgetNode(item) {
    const def = WIDGET_DEFS[item.type];
    if (!def) return null;
    const node = document.createElement("article");
    node.className = "widget-card" + (item.type === "work" ? " widget-card-accent" : "");
    node.dataset.widgetId = item.id;
    node.dataset.widgetType = item.type;
    node.style.gridColumn = (item.x + 1) + " / span " + item.w;
    node.style.gridRow = (item.y + 1) + " / span " + item.h;
    const toolbar = document.createElement("div");
    toolbar.className = "widget-toolbar";
    toolbar.innerHTML =
      '<button type="button" class="widget-handle" aria-label="Переместить" title="Переместить">⠿</button>' +
      '<span class="widget-title">' + def.title + "</span>" +
      '<button type="button" class="widget-btn widget-btn-close" data-action="close" title="Закрыть">×</button>';
    const body = document.createElement("div");
    body.className = "widget-body";
    ["n", "s", "e", "w", "ne", "nw", "se", "sw"].forEach(function (edge) {
      const handle = document.createElement("div");
      handle.className = "widget-resize widget-resize-" + edge;
      handle.dataset.edge = edge;
      handle.addEventListener("pointerdown", function (event) {
        startResize(event, item.id, edge);
      });
      node.appendChild(handle);
    });
    node.append(toolbar, body);
    toolbar.querySelector(".widget-handle").addEventListener("pointerdown", function (event) {
      startDrag(event, item.id);
    });
    toolbar.querySelector("[data-action=close]").addEventListener("click", function (event) {
      event.stopPropagation();
      removeWidget(item.id);
    });
    return node;
  }

  function renderBoard() {
    const board = byId("dashboard-board");
    const view = viewFromSelection();
    if (!board || !view) return;
    const ratio = utilization(view.data.work_seconds, view.data.idle_seconds);
    board.replaceChildren();
    layout.forEach(function (item) {
      const node = createWidgetNode(item);
      if (!node) return;
      renderWidgetContent(node, view, ratio);
      board.appendChild(node);
    });
    board.querySelectorAll("[data-open-tab]").forEach(function (element) {
      element.addEventListener("click", function (event) {
        event.preventDefault();
        openTab(element.dataset.openTab);
      });
    });
  }

  function renderHeader(view) {
    const data = view.data;
    const title = byId("dashboard-title");
    if (title) {
      title.innerHTML = view.name
        ? view.name + " <span>сегодня</span>"
        : "Производство <span>сегодня</span>";
    }
    text(
      "dashboard-date",
      new Date(data.date + "T00:00:00").toLocaleDateString("ru-RU", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    );
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
        layout = loadLayout();
        render();
      },
      {
        key: selectedZoneKey,
        onSelect: function (deptId, zoneKey) {
          selectedId = deptId;
          selectedZoneKey = zoneKey;
          layout = loadLayout();
          render();
        },
      }
    );
  }

  function render() {
    const view = viewFromSelection();
    if (!view) return;
    renderHeader(view);
    renderNav();
    renderBoard();
  }

  function removeWidget(id) {
    layout = layout.filter(function (item) { return item.id !== id; });
    saveLayout();
    renderBoard();
    renderCatalog();
  }

  function applyGrid(node, item) {
    node.style.gridColumn = (item.x + 1) + " / span " + item.w;
    node.style.gridRow = (item.y + 1) + " / span " + item.h;
  }

  function widgetNode(id) {
    return document.querySelector('[data-widget-id="' + id + '"]');
  }

  function addWidget(type) {
    const def = WIDGET_DEFS[type];
    if (!def) return;
    if (layout.some(function (item) { return item.type === type; })) return;
    const spot = findFreeSpot(def.w, def.h);
    layout.push({
      id: nextWidgetId(),
      type: type,
      x: spot.x,
      y: spot.y,
      w: def.w,
      h: def.h,
    });
    saveLayout();
    renderBoard();
    renderCatalog();
    closeCatalog();
  }

  function resetLayout() {
    layout = cloneLayout(DEFAULT_LAYOUT);
    saveLayout();
    renderBoard();
    renderCatalog();
    closeCatalog();
  }

  function renderCatalog() {
    const list = byId("widget-catalog-list");
    if (!list) return;
    list.replaceChildren();
    Object.keys(WIDGET_DEFS).forEach(function (type) {
      const def = WIDGET_DEFS[type];
      const exists = layout.some(function (item) { return item.type === type; });
      const row = document.createElement("button");
      row.type = "button";
      row.className = "widget-catalog-item" + (exists ? " is-added" : "");
      row.disabled = exists;
      row.innerHTML = "<strong>" + def.title + "</strong><span>" + def.desc + "</span>";
      row.addEventListener("click", function () { addWidget(type); });
      list.appendChild(row);
    });
  }

  function openCatalog() {
    renderCatalog();
    const modal = byId("widget-catalog");
    if (modal) modal.hidden = false;
  }

  function closeCatalog() {
    const modal = byId("widget-catalog");
    if (modal) modal.hidden = true;
  }

  function boardMetrics() {
    const board = byId("dashboard-board");
    if (!board) return null;
    const rect = board.getBoundingClientRect();
    const gap = parseFloat(getComputedStyle(board).gap) || 10;
    const cols = 12;
    return {
      left: rect.left,
      top: rect.top,
      gap: gap,
      cols: cols,
      colStep: (rect.width - gap * (cols - 1)) / cols + gap,
      rowStep: 72 + gap,
    };
  }

  function boardPos(clientX, clientY) {
    const m = boardMetrics();
    if (!m) return { gx: 0, gy: 0, x: 0, y: 0 };
    const gx = (clientX - m.left) / m.colStep;
    const gy = (clientY - m.top) / m.rowStep;
    return {
      gx: gx,
      gy: gy,
      x: Math.max(0, Math.min(m.cols - 1, Math.floor(gx))),
      y: Math.max(0, Math.floor(gy)),
    };
  }

  function startDrag(event, id) {
    if (resize) return;
    const item = layout.find(function (entry) { return entry.id === id; });
    if (!item) return;
    drag = { id: id };
    event.preventDefault();
    event.stopPropagation();
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerEnd);
  }

  function startResize(event, id, edge) {
    const item = layout.find(function (entry) { return entry.id === id; });
    if (!item) return;
    resize = {
      id: id,
      edge: edge,
      x: item.x,
      y: item.y,
      w: item.w,
      h: item.h,
    };
    event.preventDefault();
    event.stopPropagation();
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerEnd);
  }

  function onPointerMove(event) {
    const pos = boardPos(event.clientX, event.clientY);
    if (resize) {
      const item = layout.find(function (entry) { return entry.id === resize.id; });
      if (!item) return;
      const edge = resize.edge;
      let x = resize.x;
      let y = resize.y;
      let w = resize.w;
      let h = resize.h;
      // ponytail: snap edge to nearest cell so shrink doesn't wait for a full tile
      if (edge.indexOf("e") !== -1) {
        w = Math.max(1, Math.min(12 - resize.x, Math.round(pos.gx) - resize.x));
      }
      if (edge.indexOf("s") !== -1) {
        h = Math.max(1, Math.round(pos.gy) - resize.y);
      }
      if (edge.indexOf("w") !== -1) {
        const right = resize.x + resize.w;
        x = Math.max(0, Math.min(right - 1, Math.round(pos.gx)));
        w = right - x;
      }
      if (edge.indexOf("n") !== -1) {
        const bottom = resize.y + resize.h;
        y = Math.max(0, Math.min(bottom - 1, Math.round(pos.gy)));
        h = bottom - y;
      }
      item.x = x;
      item.y = y;
      item.w = w;
      item.h = Math.max(1, h);
      const node = widgetNode(item.id);
      if (node) applyGrid(node, item);
      return;
    }
    if (!drag) return;
    const item = layout.find(function (entry) { return entry.id === drag.id; });
    if (!item) return;
    item.x = Math.max(0, Math.min(12 - item.w, pos.x));
    item.y = Math.max(0, pos.y);
    const node = widgetNode(item.id);
    if (node) applyGrid(node, item);
  }

  function onPointerEnd() {
    if (drag || resize) saveLayout();
    drag = null;
    resize = null;
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerEnd);
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
      layout = loadLayout();
      render();
      if (state) state.lastChild.textContent = " Данные из БД";
    } catch (error) {
      if (state) {
        state.classList.add("error");
        state.lastChild.textContent = " Нет данных";
      }
      const board = byId("dashboard-board");
      if (board) {
        board.replaceChildren();
        const message = document.createElement("p");
        message.className = "empty-dashboard";
        message.textContent = "Не удалось загрузить сводку: " + error.message;
        board.appendChild(message);
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

  const addBtn = byId("dashboard-add-widget");
  if (addBtn) addBtn.addEventListener("click", openCatalog);

  const catalogClose = byId("widget-catalog-close");
  if (catalogClose) catalogClose.addEventListener("click", closeCatalog);

  const catalogReset = byId("widget-catalog-reset");
  if (catalogReset) catalogReset.addEventListener("click", resetLayout);

  const catalog = byId("widget-catalog");
  if (catalog) {
    catalog.addEventListener("click", function (event) {
      if (event.target === catalog) closeCatalog();
    });
  }

  function updateClock() {
    text(
      "nav-clock",
      new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
    );
  }

  updateClock();
  setInterval(updateClock, 30000);
  layout = loadLayout();
  loadDashboard();
  setInterval(function () {
    const dashboard = byId("tab-dashboard");
    if (dashboard && dashboard.classList.contains("active")) loadDashboard();
  }, 60000);
  window.DF_loadDashboard = loadDashboard;
})();
