/** Статистика: рабочие ROI-зоны или общая зона (чел·часы). */
(function () {
  const API = "/api/v1";
  const t = (key, vars) => (window.DF_I18N ? window.DF_I18N.t(key, vars) : key);

  const PEOPLE_COLORS = ["#3d3d3d", "#5ba8e0", "#2e7d32", "#1b5e20"];
  const ROI_PEOPLE_COLORS = ["#3d3d3d", "#5ba8e0", "#2e7d32"];
  const ROI_MAX_WORKERS = 2;
  let serverToday = "";

  async function request(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error((await res.text()) || "HTTP " + res.status);
    return res.json();
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function effectiveToday() {
    return serverToday || todayStr();
  }

  function todayStr() {
    const d = new Date();
    return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
  }

  function addDays(dateStr, delta) {
    const p = dateStr.split("-").map(Number);
    const d = new Date(p[0], p[1] - 1, p[2]);
    d.setDate(d.getDate() + delta);
    return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
  }

  function fmtDuration(sec) {
    const total = Math.max(0, Math.floor(sec || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) return h + "ч " + m + "м";
    if (m > 0) return m + "м";
    return s + "с";
  }

  function fmtPersonHours(sec) {
    const total = Math.max(0, Number(sec) || 0);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    return h + ":" + pad2(m);
  }

  function zoneDisplayName(z) {
    const name = z && z.roi_name ? String(z.roi_name).trim() : "";
    return name || t("statsZoneLabel", { n: z.roi_index });
  }

  function fmtDateRu(dateStr) {
    const p = dateStr.split("-").map(Number);
    if (p.length !== 3) return dateStr;
    const d = new Date(p[0], p[1] - 1, p[2]);
    return d.toLocaleDateString([], {
      weekday: "short",
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }

  function fmtHm(ts) {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function renderPeopleTimeline(container, data) {
    if (!container || !data) return;
    const rangeStart = data.range_start || 0;
    const rangeEnd = data.range_end || rangeStart + 1;
    const span = Math.max(1, rangeEnd - rangeStart);

    const wrap = document.createElement("div");
    wrap.className = "people-timeline";

    const title = document.createElement("div");
    title.className = "people-timeline-title";
    title.textContent = t("statsPeopleZoneName");
    wrap.appendChild(title);

    const bar = document.createElement("div");
    bar.className = "people-timeline-bar";
    (data.segments || []).forEach(function (seg) {
      const start = Math.max(rangeStart, seg.start);
      const end = Math.min(rangeEnd, seg.end);
      if (end <= start) return;
      const left = ((start - rangeStart) / span) * 100;
      const width = ((end - start) / span) * 100;
      const block = document.createElement("div");
      block.className = "people-timeline-seg";
      const workers = Math.min(3, Math.max(0, seg.workers || 0));
      block.style.left = left + "%";
      block.style.width = width + "%";
      block.style.background = PEOPLE_COLORS[workers] || PEOPLE_COLORS[0];
      block.title = fmtHm(start) + "–" + fmtHm(end) + " · " + workers + "/3";
      bar.appendChild(block);
    });
    wrap.appendChild(bar);

    const axis = document.createElement("div");
    axis.className = "people-timeline-axis";
    const opts = window.DF_DAY_VIEW_OPTS || { viewStartHour: 7, viewEndHour: 19 };
    axis.innerHTML =
      pad2(opts.viewStartHour) +
      ":00" +
      '<span class="people-timeline-axis-end">' +
      pad2(opts.viewEndHour) +
      ":00</span>";
    wrap.appendChild(axis);

    const legend = document.createElement("div");
    legend.className = "people-timeline-legend";
    [0, 1, 2, 3].forEach(function (n) {
      const item = document.createElement("span");
      item.className = "people-timeline-legend-item";
      item.innerHTML =
        '<i style="background:' + PEOPLE_COLORS[n] + '"></i> ' + t("statsWorkers" + n);
      legend.appendChild(item);
    });
    wrap.appendChild(legend);

    container.innerHTML = "";
    container.appendChild(wrap);
  }

  function renderRoiZoneTimeline(container, zone, rangeStart, rangeEnd) {
    if (!container || !zone) return;
    const span = Math.max(1, rangeEnd - rangeStart);
    const maxW = Math.min(ROI_MAX_WORKERS, zone.max_workers || ROI_MAX_WORKERS);
    const name =
      zone.roi_name && String(zone.roi_name).trim()
        ? String(zone.roi_name).trim()
        : t("statsZoneLabel", { n: zone.roi_index || 1 });

    const wrap = document.createElement("div");
    wrap.className = "people-timeline";

    const title = document.createElement("div");
    title.className = "people-timeline-title";
    title.textContent = name;
    wrap.appendChild(title);

    const bar = document.createElement("div");
    bar.className = "people-timeline-bar";
    (zone.segments || []).forEach(function (seg) {
      const start = Math.max(rangeStart, seg.start);
      const end = Math.min(rangeEnd, seg.end);
      if (end <= start) return;
      const left = ((start - rangeStart) / span) * 100;
      const width = ((end - start) / span) * 100;
      const block = document.createElement("div");
      block.className = "people-timeline-seg";
      const workers = Math.min(maxW, Math.max(0, seg.workers || 0));
      block.style.left = left + "%";
      block.style.width = width + "%";
      block.style.background = ROI_PEOPLE_COLORS[workers] || ROI_PEOPLE_COLORS[0];
      block.title = fmtHm(start) + "–" + fmtHm(end) + " · " + workers + "/" + maxW;
      bar.appendChild(block);
    });
    wrap.appendChild(bar);

    const axis = document.createElement("div");
    axis.className = "people-timeline-axis";
    const opts = window.DF_DAY_VIEW_OPTS || { viewStartHour: 7, viewEndHour: 19 };
    axis.innerHTML =
      pad2(opts.viewStartHour) +
      ":00" +
      '<span class="people-timeline-axis-end">' +
      pad2(opts.viewEndHour) +
      ":00</span>";
    wrap.appendChild(axis);

    const legend = document.createElement("div");
    legend.className = "people-timeline-legend";
    for (let n = 0; n <= maxW; n++) {
      const item = document.createElement("span");
      item.className = "people-timeline-legend-item";
      item.innerHTML =
        '<i style="background:' + ROI_PEOPLE_COLORS[n] + '"></i> ' + t("statsWorkers" + n);
      legend.appendChild(item);
    }
    wrap.appendChild(legend);
    container.appendChild(wrap);
  }

  window.DF_initStats = function () {
    const tab = document.getElementById("tab-stats");
    if (!tab || tab.dataset.statsReady === "1") return;
    tab.dataset.statsReady = "1";

    const deptSelect = document.getElementById("stats-department-select");
    const camSelect = document.getElementById("stats-camera-select");
    const fromInput = document.getElementById("stats-from-date");
    const toInput = document.getElementById("stats-to-date");
    const chipsEl = document.getElementById("stats-period-chips");
    const modeChipsEl = document.getElementById("stats-mode-chips");
    const tableHead = document.getElementById("stats-table-head");
    const detailHead = document.getElementById("stats-detail-head");
    const tableBody = document.getElementById("stats-table-body");
    const summaryEl = document.getElementById("stats-summary");
    const detailSection = document.getElementById("stats-day-detail");
    const detailTitle = document.getElementById("stats-day-detail-title");
    const zonesTableBody = document.getElementById("stats-zones-table-body");
    const timelineEl = document.getElementById("stats-day-timeline");

    if (!deptSelect || !camSelect || !tableBody) return;

    let allCameras = [];
    let statDates = [];
    let currentDays = [];
    let selectedDate = null;
    let activePeriod = "7";
    let activeMode = "roi";

    const PERIODS = [
      { id: "7", days: 7 },
      { id: "14", days: 14 },
      { id: "30", days: 30 },
      { id: "all", days: 0 },
    ];

    const MODES = [
      { id: "roi", labelKey: "statsModeRoi" },
      { id: "people", labelKey: "statsModePeople" },
    ];

    function isPeopleMode() {
      return activeMode === "people";
    }

    function statsApiBase() {
      return isPeopleMode() ? "/people-zone-stats/" : "/roi-stats/";
    }

    function tableColspan() {
      return isPeopleMode() ? 6 : 8;
    }

    function updateTableHead() {
      if (!tableHead) return;
      if (isPeopleMode()) {
        tableHead.innerHTML =
          "<tr><th>" +
          t("date") +
          "</th><th>" +
          t("statsPersonHours") +
          "</th><th>" +
          t("statsWorkers0") +
          "</th><th>" +
          t("statsWorkers1") +
          "</th><th>" +
          t("statsWorkers2") +
          "</th><th>" +
          t("statsWorkers3") +
          "</th></tr>";
      } else {
        tableHead.innerHTML =
          "<tr><th>" +
          t("date") +
          "</th><th>" +
          t("statsWork") +
          "</th><th>" +
          t("statsIdle") +
          "</th><th>" +
          t("statsPersonHours") +
          "</th><th>" +
          t("statsWorkers0") +
          "</th><th>" +
          t("statsWorkers1") +
          "</th><th>" +
          t("statsWorkers2") +
          "</th><th>" +
          t("statsZones") +
          "</th></tr>";
      }
    }

    function updateDetailHead() {
      if (!detailHead) return;
      if (isPeopleMode()) {
        detailHead.innerHTML =
          "<tr><th>" +
          t("statsPersonHours") +
          "</th><th>" +
          t("statsWorkers0") +
          "</th><th>" +
          t("statsWorkers1") +
          "</th><th>" +
          t("statsWorkers2") +
          "</th><th>" +
          t("statsWorkers3") +
          "</th></tr>";
      } else {
        detailHead.innerHTML =
          "<tr><th>" +
          t("statsZone") +
          "</th><th>" +
          t("statsWork") +
          "</th><th>" +
          t("statsIdle") +
          "</th><th>" +
          t("statsPersonHours") +
          "</th><th>" +
          t("statsWorkers0") +
          "</th><th>" +
          t("statsWorkers1") +
          "</th><th>" +
          t("statsWorkers2") +
          "</th></tr>";
      }
    }

    function renderModeChips() {
      if (!modeChipsEl) return;
      modeChipsEl.innerHTML = "";
      MODES.forEach(function (m) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "period-chip" + (activeMode === m.id ? " active" : "");
        btn.textContent = t(m.labelKey);
        btn.dataset.mode = m.id;
        btn.addEventListener("click", function () {
          if (activeMode === m.id) return;
          activeMode = m.id;
          updateTableHead();
          updateDetailHead();
          renderModeChips();
          clearDetail();
          const camId = camSelect.value;
          if (camId) {
            loadStatDates(camId).then(loadStats);
          } else {
            tableBody.innerHTML =
              '<tr><td colspan="' +
              tableColspan() +
              '" class="help-text">' +
              t("statsSelectFilters") +
              "</td></tr>";
          }
        });
        modeChipsEl.appendChild(btn);
      });
    }

    function renderChips() {
      if (!chipsEl) return;
      chipsEl.innerHTML = "";
      PERIODS.forEach(function (p) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "period-chip" + (activePeriod === p.id ? " active" : "");
        btn.textContent =
          p.id === "all" ? t("statsPeriodAll") : t("statsPeriodDays", { n: p.days });
        btn.dataset.period = p.id;
        btn.addEventListener("click", function () {
          activePeriod = p.id;
          applyPeriod(p.id);
          renderChips();
          loadStats();
        });
        chipsEl.appendChild(btn);
      });
    }

    function applyPeriod(periodId) {
      const today = effectiveToday();
      const p = PERIODS.find(function (x) {
        return x.id === periodId;
      });
      if (!p) return;
      if (periodId === "all" && statDates.length) {
        if (fromInput) fromInput.value = statDates[0];
        if (toInput) toInput.value = statDates[statDates.length - 1] || today;
        return;
      }
      const days = p.days || 7;
      if (fromInput) fromInput.value = addDays(today, -(days - 1));
      if (toInput) toInput.value = today;
    }

    function camerasForDepartment(deptValue) {
      if (!deptValue) return [];
      if (deptValue === "none") {
        return allCameras.filter(function (cam) {
          return !cam.department_id;
        });
      }
      const deptId = Number(deptValue);
      return allCameras.filter(function (cam) {
        return cam.department_id === deptId;
      });
    }

    function populateCameraSelect(preserveId) {
      const deptValue = deptSelect.value;
      camSelect.innerHTML = "";
      const cameras = camerasForDepartment(deptValue);

      if (!deptValue) {
        camSelect.disabled = true;
        const opt0 = document.createElement("option");
        opt0.value = "";
        opt0.textContent = t("statsSelectDepartmentFirst");
        camSelect.appendChild(opt0);
        return;
      }

      camSelect.disabled = false;
      const opt0 = document.createElement("option");
      opt0.value = "";
      opt0.textContent = t("selectCamera");
      camSelect.appendChild(opt0);

      if (!cameras.length) {
        const optEmpty = document.createElement("option");
        optEmpty.value = "";
        optEmpty.textContent = t("statsNoCamerasInDept");
        optEmpty.disabled = true;
        camSelect.appendChild(optEmpty);
        camSelect.disabled = true;
        return;
      }

      cameras.forEach(function (cam) {
        const opt = document.createElement("option");
        opt.value = String(cam.id);
        opt.textContent = cam.id + " — " + cam.name;
        camSelect.appendChild(opt);
      });

      if (preserveId && cameras.some(function (c) { return String(c.id) === String(preserveId); })) {
        camSelect.value = String(preserveId);
      }
    }

    async function loadDepartments() {
      const [deptData, camData] = await Promise.all([
        request(API + "/departments"),
        request(API + "/cameras"),
      ]);
      allCameras = camData.items || [];
      const prevDept = deptSelect.value;
      const prevCam = camSelect.value;

      deptSelect.innerHTML = "";
      const opt0 = document.createElement("option");
      opt0.value = "";
      opt0.textContent = t("selectDepartment");
      deptSelect.appendChild(opt0);

      (deptData.items || []).forEach(function (dept) {
        const opt = document.createElement("option");
        opt.value = String(dept.id);
        opt.textContent = dept.name + " (" + t("camerasCount", { n: dept.camera_count }) + ")";
        deptSelect.appendChild(opt);
      });

      const noDeptCams = camerasForDepartment("none");
      if (noDeptCams.length) {
        const optNone = document.createElement("option");
        optNone.value = "none";
        optNone.textContent = t("noDepartment") + " (" + t("camerasCount", { n: noDeptCams.length }) + ")";
        deptSelect.appendChild(optNone);
      }

      if (prevDept && Array.from(deptSelect.options).some(function (o) { return o.value === prevDept; })) {
        deptSelect.value = prevDept;
      }
      populateCameraSelect(prevCam);
    }

    async function loadStatDates(camId) {
      try {
        const data = await request(API + statsApiBase() + camId + "/dates");
        statDates = data.dates || [];
        if (isPeopleMode() && data.server_today) {
          serverToday = data.server_today;
        }
      } catch (_e) {
        statDates = [];
      }
    }

    function clearDetail() {
      selectedDate = null;
      if (detailSection) detailSection.classList.add("hidden");
      if (zonesTableBody) zonesTableBody.innerHTML = "";
      if (timelineEl) timelineEl.innerHTML = "";
      document.querySelectorAll(".stats-day-row").forEach(function (tr) {
        tr.classList.remove("selected");
      });
    }

    function renderRoiTable(days) {
      currentDays = days || [];
      tableBody.innerHTML = "";
      if (!currentDays.length) {
        tableBody.innerHTML =
          '<tr><td colspan="8" class="help-text">' + t("statsNoData") + "</td></tr>";
        if (summaryEl) summaryEl.textContent = "";
        clearDetail();
        return;
      }

      let sumWork = 0;
      let sumIdle = 0;
      let sumPerson = 0;
      currentDays.forEach(function (day) {
        sumWork += day.work_seconds || 0;
        sumIdle += day.idle_seconds || 0;
        sumPerson += day.person_seconds || 0;
        const tr = document.createElement("tr");
        tr.className = "stats-day-row";
        tr.dataset.date = day.date;
        tr.innerHTML =
          "<td>" +
          fmtDateRu(day.date) +
          "</td><td>" +
          fmtDuration(day.work_seconds) +
          "</td><td>" +
          fmtDuration(day.idle_seconds) +
          "</td><td>" +
          fmtPersonHours(day.person_seconds) +
          "</td><td>" +
          fmtDuration(day.seconds_0_workers) +
          "</td><td>" +
          fmtDuration(day.seconds_1_worker) +
          "</td><td>" +
          fmtDuration(day.seconds_2_workers) +
          "</td><td>" +
          (day.zones ? day.zones.length : 0) +
          "</td>";
        tr.addEventListener("click", function () {
          selectDay(day.date);
        });
        tableBody.appendChild(tr);
      });

      if (summaryEl) {
        summaryEl.textContent = t("statsRoiSummary", {
          days: currentDays.length,
          work: fmtDuration(sumWork),
          idle: fmtDuration(sumIdle),
          personHours: fmtPersonHours(sumPerson),
        });
      }
    }

    function renderPeopleTable(days) {
      currentDays = days || [];
      tableBody.innerHTML = "";
      if (!currentDays.length) {
        tableBody.innerHTML =
          '<tr><td colspan="6" class="help-text">' + t("statsNoPeopleData") + "</td></tr>";
        if (summaryEl) summaryEl.textContent = "";
        clearDetail();
        return;
      }

      let sumPerson = 0;
      currentDays.forEach(function (day) {
        sumPerson += day.person_seconds || 0;
        const tr = document.createElement("tr");
        tr.className = "stats-day-row";
        tr.dataset.date = day.date;
        tr.innerHTML =
          "<td>" +
          fmtDateRu(day.date) +
          "</td><td>" +
          fmtPersonHours(day.person_seconds) +
          "</td><td>" +
          fmtDuration(day.seconds_0_workers) +
          "</td><td>" +
          fmtDuration(day.seconds_1_worker) +
          "</td><td>" +
          fmtDuration(day.seconds_2_workers) +
          "</td><td>" +
          fmtDuration(day.seconds_3_workers) +
          "</td>";
        tr.addEventListener("click", function () {
          selectDay(day.date);
        });
        tableBody.appendChild(tr);
      });

      if (summaryEl) {
        summaryEl.textContent = t("statsPeopleSummary", {
          days: currentDays.length,
          personHours: fmtPersonHours(sumPerson),
        });
      }
    }

    function renderTable(days) {
      if (isPeopleMode()) renderPeopleTable(days);
      else renderRoiTable(days);
    }

    async function selectDay(dateStr) {
      selectedDate = dateStr;
      document.querySelectorAll(".stats-day-row").forEach(function (tr) {
        tr.classList.toggle("selected", tr.dataset.date === dateStr);
      });

      const day = currentDays.find(function (d) {
        return d.date === dateStr;
      });
      if (!day) return;

      if (detailSection) detailSection.classList.remove("hidden");
      const opts = window.DF_DAY_VIEW_OPTS || { viewStartHour: 7, viewEndHour: 19 };
      if (detailTitle) {
        detailTitle.textContent =
          (isPeopleMode()
            ? t("statsPeopleDayDetail", { date: fmtDateRu(dateStr) })
            : t("statsDayDetail", { date: fmtDateRu(dateStr) })) +
          " · " +
          pad2(opts.viewStartHour) +
          ":00–" +
          pad2(opts.viewEndHour) +
          ":00";
      }

      const camId = camSelect.value;
      if (!camId || !timelineEl) return;

      if (isPeopleMode()) {
        if (zonesTableBody) {
          zonesTableBody.innerHTML =
            "<tr><td>" +
            fmtPersonHours(day.person_seconds) +
            "</td><td>" +
            fmtDuration(day.seconds_0_workers) +
            "</td><td>" +
            fmtDuration(day.seconds_1_worker) +
            "</td><td>" +
            fmtDuration(day.seconds_2_workers) +
            "</td><td>" +
            fmtDuration(day.seconds_3_workers) +
            "</td></tr>";
        }
        timelineEl.innerHTML = '<p class="help-text">' + t("loading") + "</p>";
        try {
          const timeline = await request(
            API + statsApiBase() + camId + "/" + encodeURIComponent(dateStr) + "/timeline"
          );
          renderPeopleTimeline(timelineEl, timeline);
        } catch (e) {
          timelineEl.innerHTML = '<p class="help-text">' + e.message + "</p>";
        }
        return;
      }

      if (zonesTableBody) {
        zonesTableBody.innerHTML = "";
        const zones = (day.zones || []).slice().sort(function (a, b) {
          return (a.roi_index || 0) - (b.roi_index || 0);
        });
        if (!zones.length) {
          zonesTableBody.innerHTML =
            '<tr><td colspan="7" class="help-text">' + t("statsNoZones") + "</td></tr>";
        } else {
          zones.forEach(function (z) {
            const tr = document.createElement("tr");
            tr.innerHTML =
              "<td>" +
              zoneDisplayName(z) +
              "</td><td>" +
              fmtDuration(z.work_seconds) +
              "</td><td>" +
              fmtDuration(z.idle_seconds) +
              "</td><td>" +
              fmtPersonHours(z.person_seconds) +
              "</td><td>" +
              fmtDuration(z.seconds_0_workers) +
              "</td><td>" +
              fmtDuration(z.seconds_1_worker) +
              "</td><td>" +
              fmtDuration(z.seconds_2_workers) +
              "</td>";
            zonesTableBody.appendChild(tr);
          });
        }
      }

      timelineEl.innerHTML = '<p class="help-text">' + t("loading") + "</p>";
      try {
        const [workTimeline, workersTimeline] = await Promise.all([
          request(
            API + statsApiBase() + camId + "/" + encodeURIComponent(dateStr) + "/timeline"
          ),
          request(
            API +
              statsApiBase() +
              camId +
              "/" +
              encodeURIComponent(dateStr) +
              "/workers-timeline"
          ),
        ]);

        timelineEl.innerHTML = "";

        const workTitle = document.createElement("h3");
        workTitle.className = "stats-timeline-subtitle";
        workTitle.textContent = t("statsTimelineWorkIdle");
        timelineEl.appendChild(workTitle);

        const workWrap = document.createElement("div");
        workWrap.className = "stats-timeline-block";
        timelineEl.appendChild(workWrap);

        workTimeline.date = dateStr;
        if (window.DF_renderTimeline) {
          window.DF_renderTimeline(
            workWrap,
            workTimeline,
            window.DF_DAY_VIEW_OPTS || { mode: "day", viewStartHour: 7, viewEndHour: 19 }
          );
        }

        const workersTitle = document.createElement("h3");
        workersTitle.className = "stats-timeline-subtitle";
        workersTitle.textContent = t("statsTimelineWorkers");
        timelineEl.appendChild(workersTitle);

        const rangeStart = workersTimeline.range_start || 0;
        const rangeEnd = workersTimeline.range_end || rangeStart + 1;
        const zonesTl = (workersTimeline.zones || []).slice().sort(function (a, b) {
          return (a.roi_index || 0) - (b.roi_index || 0);
        });
        if (!zonesTl.length) {
          const empty = document.createElement("p");
          empty.className = "help-text";
          empty.textContent = t("statsNoZones");
          timelineEl.appendChild(empty);
        } else {
          zonesTl.forEach(function (z) {
            renderRoiZoneTimeline(timelineEl, z, rangeStart, rangeEnd);
          });
        }
      } catch (e) {
        timelineEl.innerHTML = '<p class="help-text">' + e.message + "</p>";
      }
      return;
    }

    async function loadStats() {
      const camId = camSelect.value;
      const from = fromInput ? fromInput.value : "";
      const to = toInput ? toInput.value : "";
      const colspan = tableColspan();
      clearDetail();
      if (!deptSelect.value || !camId || !from || !to) {
        tableBody.innerHTML =
          '<tr><td colspan="' +
          colspan +
          '" class="help-text">' +
          t("statsSelectFilters") +
          "</td></tr>";
        if (summaryEl) summaryEl.textContent = "";
        return;
      }
      tableBody.innerHTML =
        '<tr><td colspan="' + colspan + '" class="help-text">' + t("loading") + "</td></tr>";
      try {
        const data = await request(
          API +
            statsApiBase() +
            camId +
            "/daily?from=" +
            encodeURIComponent(from) +
            "&to=" +
            encodeURIComponent(to)
        );
        if (isPeopleMode() && data.server_today) {
          serverToday = data.server_today;
          if (toInput && toInput.value < data.server_today) {
            toInput.value = data.server_today;
          }
        }
        renderTable(data.days || []);
      } catch (e) {
        tableBody.innerHTML =
          '<tr><td colspan="' + colspan + '" class="help-text">' + e.message + "</td></tr>";
        if (summaryEl) summaryEl.textContent = "";
      }
    }

    deptSelect.addEventListener("change", function () {
      clearDetail();
      statDates = [];
      populateCameraSelect(null);
      tableBody.innerHTML =
        '<tr><td colspan="' +
        tableColspan() +
        '" class="help-text">' +
        t("statsSelectFilters") +
        "</td></tr>";
      if (summaryEl) summaryEl.textContent = "";
    });

    camSelect.addEventListener("change", async function () {
      clearDetail();
      const camId = camSelect.value;
      if (!camId) {
        statDates = [];
        tableBody.innerHTML =
          '<tr><td colspan="' +
          tableColspan() +
          '" class="help-text">' +
          t("statsSelectFilters") +
          "</td></tr>";
        if (summaryEl) summaryEl.textContent = "";
        return;
      }
      await loadStatDates(camId);
      applyPeriod(activePeriod);
      loadStats();
    });

    if (fromInput) {
      fromInput.addEventListener("change", function () {
        activePeriod = "";
        renderChips();
        loadStats();
      });
    }
    if (toInput) {
      toInput.addEventListener("change", function () {
        activePeriod = "";
        renderChips();
        loadStats();
      });
    }

    updateTableHead();
    updateDetailHead();
    renderModeChips();
    renderChips();
    applyPeriod(activePeriod);
    loadDepartments()
      .then(function () {
        if (deptSelect.value && camSelect.value) {
          return loadStatDates(camSelect.value).then(loadStats);
        }
        tableBody.innerHTML =
          '<tr><td colspan="' +
          tableColspan() +
          '" class="help-text">' +
          t("statsSelectFilters") +
          "</td></tr>";
      })
      .catch(function (e) {
        tableBody.innerHTML =
          '<tr><td colspan="' +
          tableColspan() +
          '" class="help-text">' +
          e.message +
          "</td></tr>";
      });
  };
})();
