/** Статистика работы / простоя по ROI из БД. */
(function () {
  const API = "/api/v1";
  const t = (key, vars) => (window.DF_I18N ? window.DF_I18N.t(key, vars) : key);

  async function request(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error((await res.text()) || "HTTP " + res.status);
    return res.json();
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
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

  window.DF_initStats = function () {
    const tab = document.getElementById("tab-stats");
    if (!tab || tab.dataset.statsReady === "1") return;
    tab.dataset.statsReady = "1";

    const deptSelect = document.getElementById("stats-department-select");
    const camSelect = document.getElementById("stats-camera-select");
    const fromInput = document.getElementById("stats-from-date");
    const toInput = document.getElementById("stats-to-date");
    const chipsEl = document.getElementById("stats-period-chips");
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

    const PERIODS = [
      { id: "7", days: 7 },
      { id: "14", days: 14 },
      { id: "30", days: 30 },
      { id: "all", days: 0 },
    ];

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
      const today = todayStr();
      const p = PERIODS.find(function (x) {
        return x.id === periodId;
      });
      if (!p) return;
      if (periodId === "all" && statDates.length) {
        if (fromInput) fromInput.value = statDates[0];
        if (toInput) toInput.value = statDates[statDates.length - 1];
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
        const data = await request(API + "/roi-stats/" + camId + "/dates");
        statDates = data.dates || [];
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

    function renderTable(days) {
      currentDays = days || [];
      tableBody.innerHTML = "";
      if (!currentDays.length) {
        tableBody.innerHTML =
          '<tr><td colspan="4" class="help-text">' + t("statsNoData") + "</td></tr>";
        if (summaryEl) summaryEl.textContent = "";
        clearDetail();
        return;
      }

      let sumWork = 0;
      let sumIdle = 0;
      currentDays.forEach(function (day) {
        sumWork += day.work_seconds || 0;
        sumIdle += day.idle_seconds || 0;
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
          (day.zones ? day.zones.length : 0) +
          "</td>";
        tr.addEventListener("click", function () {
          selectDay(day.date);
        });
        tableBody.appendChild(tr);
      });

      if (summaryEl) {
        summaryEl.textContent = t("statsSummary", {
          days: currentDays.length,
          work: fmtDuration(sumWork),
          idle: fmtDuration(sumIdle),
        });
      }
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
      if (detailTitle) {
        const opts = window.DF_DAY_VIEW_OPTS || { viewStartHour: 7, viewEndHour: 19 };
        detailTitle.textContent =
          t("statsDayDetail", { date: fmtDateRu(dateStr) }) +
          " · " +
          pad2(opts.viewStartHour) +
          ":00–" +
          pad2(opts.viewEndHour) +
          ":00";
      }

      if (zonesTableBody) {
        zonesTableBody.innerHTML = "";
        const zones = (day.zones || []).slice().sort(function (a, b) {
          return (a.roi_index || 0) - (b.roi_index || 0);
        });
        if (!zones.length) {
          zonesTableBody.innerHTML =
            '<tr><td colspan="3" class="help-text">' + t("statsNoZones") + "</td></tr>";
        } else {
          zones.forEach(function (z) {
            const tr = document.createElement("tr");
            tr.innerHTML =
              "<td>" +
              t("statsZoneLabel", { n: z.roi_index }) +
              "</td><td>" +
              fmtDuration(z.work_seconds) +
              "</td><td>" +
              fmtDuration(z.idle_seconds) +
              "</td>";
            zonesTableBody.appendChild(tr);
          });
        }
      }

      const camId = camSelect.value;
      if (!camId || !timelineEl) return;
      timelineEl.innerHTML = '<p class="help-text">' + t("loading") + "</p>";
      try {
        const timeline = await request(
          API + "/roi-stats/" + camId + "/" + encodeURIComponent(dateStr) + "/timeline"
        );
        timeline.date = dateStr;
        timelineEl.innerHTML = "";
        if (window.DF_renderTimeline) {
          window.DF_renderTimeline(
            timelineEl,
            timeline,
            window.DF_DAY_VIEW_OPTS || { mode: "day", viewStartHour: 7, viewEndHour: 19 }
          );
        }
      } catch (e) {
        timelineEl.innerHTML = '<p class="help-text">' + e.message + "</p>";
      }
    }

    async function loadStats() {
      const camId = camSelect.value;
      const from = fromInput ? fromInput.value : "";
      const to = toInput ? toInput.value : "";
      clearDetail();
      if (!deptSelect.value || !camId || !from || !to) {
        tableBody.innerHTML =
          '<tr><td colspan="4" class="help-text">' + t("statsSelectFilters") + "</td></tr>";
        if (summaryEl) summaryEl.textContent = "";
        return;
      }
      tableBody.innerHTML =
        '<tr><td colspan="4" class="help-text">' + t("loading") + "</td></tr>";
      try {
        const data = await request(
          API +
            "/roi-stats/" +
            camId +
            "/daily?from=" +
            encodeURIComponent(from) +
            "&to=" +
            encodeURIComponent(to)
        );
        renderTable(data.days || []);
      } catch (e) {
        tableBody.innerHTML =
          '<tr><td colspan="4" class="help-text">' + e.message + "</td></tr>";
        if (summaryEl) summaryEl.textContent = "";
      }
    }

    deptSelect.addEventListener("change", function () {
      clearDetail();
      statDates = [];
      populateCameraSelect(null);
      tableBody.innerHTML =
        '<tr><td colspan="4" class="help-text">' + t("statsSelectFilters") + "</td></tr>";
      if (summaryEl) summaryEl.textContent = "";
    });

    camSelect.addEventListener("change", async function () {
      clearDetail();
      const camId = camSelect.value;
      if (!camId) {
        statDates = [];
        tableBody.innerHTML =
          '<tr><td colspan="4" class="help-text">' + t("statsSelectFilters") + "</td></tr>";
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

    renderChips();
    applyPeriod(activePeriod);
    loadDepartments()
      .then(function () {
        if (deptSelect.value && camSelect.value) {
          return loadStatDates(camSelect.value).then(loadStats);
        }
        tableBody.innerHTML =
          '<tr><td colspan="4" class="help-text">' + t("statsSelectFilters") + "</td></tr>";
      })
      .catch(function (e) {
        tableBody.innerHTML =
          '<tr><td colspan="4" class="help-text">' + e.message + "</td></tr>";
      });
  };
})();
