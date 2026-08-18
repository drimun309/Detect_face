/** Панель записей: отдел → камера → дата → ролики. Общая для вкладок «Камеры» и «Записи». */
(function () {
  const API = "/api/v1";
  const t = (key, vars) => window.DF_I18N.t(key, vars);

  async function request(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error((await res.text()) || "HTTP " + res.status);
    if (res.status === 204) return null;
    return res.json();
  }

  function openModal() {
    const m = document.getElementById("rec-player-modal");
    if (!m) return;
    m.classList.remove("hidden");
    m.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    const m = document.getElementById("rec-player-modal");
    if (!m) return;
    m.classList.add("hidden");
    m.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  function recFmtTime(sec) {
    if (!isFinite(sec) || sec < 0) return "00:00";
    const total = Math.floor(sec);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const mm = String(m).padStart(2, "0");
    const ss = String(s).padStart(2, "0");
    return h > 0 ? h + ":" + mm + ":" + ss : mm + ":" + ss;
  }

  let recPlayerBound = false;
  let recActivePanel = null;
  let seeking = false;

  function bindRecPlayer() {
    if (recPlayerBound) return;
    recPlayerBound = true;
    const video = document.getElementById("rec-video");
    const title = document.getElementById("rec-player-title");
    const prevBtn = document.getElementById("rec-prev-btn");
    const nextBtn = document.getElementById("rec-next-btn");
    const progress = document.getElementById("rec-progress");
    const timeDisplay = document.getElementById("rec-time-display");
    const playBtn = document.getElementById("rec-play-btn");

    function updateRecTime(preview) {
      if (!video || !timeDisplay) return;
      const cur = preview != null ? preview : video.currentTime || 0;
      const dur = video.duration || 0;
      timeDisplay.textContent = recFmtTime(cur) + " / " + recFmtTime(dur);
    }

    function updatePlayBtn() {
      if (!playBtn || !video) return;
      const playing = !video.paused && !video.ended;
      playBtn.textContent = playing ? "❚❚" : "▶";
      playBtn.title = playing ? t("recPause") : t("recPlay");
    }

    window.DF_recPlayerReset = function () {
      if (progress) {
        progress.value = "0";
        progress.max = "0";
        progress.disabled = true;
      }
      updateRecTime(0);
      updatePlayBtn();
    };

    if (video) {
      video.addEventListener("loadedmetadata", function () {
        if (progress) {
          const dur = video.duration || 0;
          progress.max = String(dur);
          progress.disabled = !(dur > 0);
          progress.value = "0";
        }
        updateRecTime(0);
      });
      video.addEventListener("timeupdate", function () {
        if (!seeking && progress) progress.value = String(video.currentTime || 0);
        updateRecTime();
      });
      video.addEventListener("play", updatePlayBtn);
      video.addEventListener("pause", updatePlayBtn);
      video.addEventListener("ended", updatePlayBtn);
      video.addEventListener("click", function () {
        if (video.paused) video.play().catch(function () {});
        else video.pause();
      });
    }

    if (progress) {
      progress.addEventListener("input", function () {
        seeking = true;
        updateRecTime(parseFloat(progress.value) || 0);
      });
      progress.addEventListener("change", function () {
        if (!video) return;
        video.currentTime = parseFloat(progress.value) || 0;
        seeking = false;
        updateRecTime();
      });
    }

    if (playBtn && video) {
      playBtn.addEventListener("click", function () {
        if (video.paused) video.play().catch(function () {});
        else video.pause();
      });
    }

    const closeBtn = document.getElementById("rec-player-modal-close");
    const back = document.getElementById("rec-player-modal-backdrop");
    function closeRecModal() {
      if (video) {
        video.pause();
        video.removeAttribute("src");
        video.load();
      }
      window.DF_recPlayerReset();
      closeModal();
    }
    if (closeBtn) closeBtn.onclick = closeRecModal;
    if (back) back.onclick = closeRecModal;

    document.querySelectorAll("[id^='rec-speed-btn']").forEach(function (b) {
      b.addEventListener("click", function () {
        const sp = Number(b.getAttribute("data-speed") || "1");
        if (video) video.playbackRate = sp;
      });
    });

    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        if (recActivePanel && recActivePanel.currentIndex > 0) {
          recActivePanel.openAtIndex(recActivePanel.currentIndex - 1);
        }
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        if (
          recActivePanel &&
          recActivePanel.currentIndex >= 0 &&
          recActivePanel.currentIndex < recActivePanel.currentFiles.length - 1
        ) {
          recActivePanel.openAtIndex(recActivePanel.currentIndex + 1);
        }
      });
    }

    window.DF_recPlayerPlay = function (panel, idx) {
      const videoEl = document.getElementById("rec-video");
      const titleEl = document.getElementById("rec-player-title");
      if (!videoEl || !panel) return;
      const ctx = panel.playContext(idx);
      if (!ctx) return;
      recActivePanel = panel;
      panel.currentIndex = idx;
      if (titleEl) titleEl.textContent = ctx.title;
      window.DF_recPlayerReset();
      videoEl.playbackRate = 1;
      videoEl.src = ctx.url;
      videoEl.load();
      openModal();
      videoEl.play().catch(function () {});
      panel.updateNavButtons();
    };
  }

  function createRecordingsPanel(opts) {
    bindRecPlayer();
    const deptSelect = opts.deptSelect;
    const camSelect = opts.camSelect;
    const dateSelect = opts.dateSelect;
    const list = opts.list;
    const dayTimelineEl = opts.dayTimelineEl;
    const deptNavEl = opts.deptNavEl;

    let currentFiles = [];
    let currentIndex = -1;
    let dayTimeline = null;
    let allCameras = [];

    if (!deptSelect || !camSelect || !dateSelect || !list) return null;

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

    function selectedCamName() {
      return camSelect.options[camSelect.selectedIndex]?.dataset?.name || "";
    }

    function cameraZoneKey(camId) {
      return String(camId) + ":0";
    }

    function selectedCameraKey() {
      return camSelect.value ? cameraZoneKey(camSelect.value) : "";
    }

    function resetRecordingsView() {
      dateSelect.disabled = true;
      dateSelect.innerHTML = "<option value=\"\">" + t("selectDate") + "</option>";
      list.innerHTML = "<p class=\"help-text\">" + t("recSelectHint") + "</p>";
      if (dayTimelineEl) {
        dayTimelineEl.innerHTML = "<p class=\"help-text\">" + t("recTimelineDayHint") + "</p>";
      }
      dayTimeline = null;
      currentFiles = [];
      currentIndex = -1;
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
        opt.dataset.name = cam.name;
        camSelect.appendChild(opt);
      });

      if (preserveId && cameras.some(function (c) { return String(c.id) === String(preserveId); })) {
        camSelect.value = String(preserveId);
      }
    }

    function bindDeptNav() {
      if (!deptNavEl || !window.DF_fillDeptNav) return;
      const items = Array.from(deptSelect.options)
        .filter(function (opt) { return opt.value; })
        .map(function (opt) {
          const cameras = camerasForDepartment(opt.value);
          return {
            id: opt.value,
            name: opt.dataset.name || opt.textContent,
            count: t("camerasCount", { n: cameras.length }),
            emptyText: t("statsNoCamerasInDept"),
            zones: cameras.map(function (cam) {
              return { name: cam.name, camera_id: cam.id, roi_index: 0 };
            }),
          };
        });
      window.DF_fillDeptNav(
        deptNavEl,
        items,
        deptSelect.value,
        function (id) {
          selectDepartment(id);
        },
        {
          key: selectedCameraKey(),
          onSelect: function (deptId, zoneKey, zone) {
            selectDepartment(deptId);
            selectCamera(String(zone.camera_id));
          },
        }
      );
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
      (deptData.items || []).forEach(function (dept) {
        const opt = document.createElement("option");
        opt.value = String(dept.id);
        opt.dataset.name = dept.name;
        opt.dataset.count = t("camerasCount", { n: dept.camera_count });
        opt.textContent = dept.name;
        deptSelect.appendChild(opt);
      });

      if (prevDept && Array.from(deptSelect.options).some(function (o) { return o.value === prevDept; })) {
        deptSelect.value = prevDept;
      } else if (deptSelect.options.length) {
        deptSelect.selectedIndex = 0;
      }
      populateCameraSelect(prevCam);
      bindDeptNav();
    }

    async function loadDates() {
      const camId = camSelect.value;
      const camName = selectedCamName();
      if (!camId || !camName) {
        dateSelect.disabled = true;
        dateSelect.innerHTML = "<option value=\"\">" + t("selectDate") + "</option>";
        list.innerHTML = "<p class=\"help-text\">" + t("recSelectHint") + "</p>";
        return;
      }
      const dates = await request(
        API + "/recordings/" + camId + "/" + encodeURIComponent(camName) + "/dates"
      );
      dateSelect.disabled = false;
      dateSelect.innerHTML = "";
      const opt0 = document.createElement("option");
      opt0.value = "";
      opt0.textContent = "—";
      dateSelect.appendChild(opt0);
      dates.forEach(function (d) {
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = d;
        dateSelect.appendChild(opt);
      });
    }

    async function loadDayTimeline(camId, camName, date) {
      if (!dayTimelineEl) return;
      dayTimelineEl.innerHTML = "<p class=\"help-text\">" + t("loading") + "</p>";
      try {
        dayTimeline = await request(
          API +
            "/recordings/" +
            camId +
            "/" +
            encodeURIComponent(camName) +
            "/" +
            encodeURIComponent(date) +
            "/timeline"
        );
        dayTimeline.date = date;
        dayTimelineEl.innerHTML = "";
        if (window.DF_renderTimeline) {
          window.DF_renderTimeline(
            dayTimelineEl,
            dayTimeline,
            window.DF_DAY_VIEW_OPTS || { mode: "day", viewStartHour: 7, viewEndHour: 19 }
          );
        }
      } catch (e) {
        dayTimeline = null;
        dayTimelineEl.innerHTML = "<p class=\"help-text\">" + e.message + "</p>";
      }
    }

    function updateNavButtons() {
      const prevBtn = document.getElementById("rec-prev-btn");
      const nextBtn = document.getElementById("rec-next-btn");
      if (prevBtn) prevBtn.disabled = currentIndex <= 0;
      if (nextBtn) nextBtn.disabled = currentIndex < 0 || currentIndex >= currentFiles.length - 1;
    }

    async function loadFiles() {
      const camId = camSelect.value;
      const camName = selectedCamName();
      const date = dateSelect.value;
      if (!camId || !camName || !date) {
        list.innerHTML = "<p class=\"help-text\">" + t("recSelectHint") + "</p>";
        if (dayTimelineEl) {
          dayTimelineEl.innerHTML = "<p class=\"help-text\">" + t("recTimelineDayHint") + "</p>";
        }
        dayTimeline = null;
        return;
      }
      await loadDayTimeline(camId, camName, date);
      const files = await request(
        API + "/recordings/" + camId + "/" + encodeURIComponent(camName) + "/" + encodeURIComponent(date)
      );
      currentFiles = files || [];
      currentIndex = -1;
      if (!files.length) {
        list.innerHTML = "<p class=\"help-text\">(пусто)</p>";
        updateNavButtons();
        return;
      }
      list.innerHTML = "";
      files.forEach(function (f) {
        const row = document.createElement("div");
        row.className = "rec-item";
        const head = document.createElement("div");
        head.className = "rec-item-head";
        const left = document.createElement("div");
        const nm = document.createElement("div");
        nm.className = "rec-item-title";
        nm.textContent = f.filename;
        const meta = document.createElement("div");
        meta.className = "rec-item-meta";
        let metaTxt = f.size ? Math.round(f.size / 1024 / 1024) + " MB" : "";
        if (f.start_ts && f.end_ts) {
          metaTxt +=
            (metaTxt ? " · " : "") +
            new Date(f.start_ts * 1000).toLocaleTimeString() +
            " – " +
            new Date(f.end_ts * 1000).toLocaleTimeString();
        } else if (f.mtime) {
          metaTxt += (metaTxt ? " · " : "") + new Date(f.mtime * 1000).toLocaleString();
        }
        meta.textContent = metaTxt;
        left.appendChild(nm);
        left.appendChild(meta);
        const right = document.createElement("div");
        right.className = "button-group";
        const playRowBtn = document.createElement("button");
        playRowBtn.type = "button";
        playRowBtn.className = "btn btn-primary";
        playRowBtn.textContent = t("play");
        playRowBtn.addEventListener("click", function () {
          openAtIndex(files.findIndex(function (x) { return x.filename === f.filename; }));
        });
        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.className = "btn btn-danger";
        delBtn.textContent = t("delete");
        delBtn.addEventListener("click", async function () {
          if (!confirm(t("delete") + " " + f.filename + "?")) return;
          await request(
            API +
              "/recordings/" +
              camId +
              "/" +
              encodeURIComponent(camName) +
              "/" +
              encodeURIComponent(date) +
              "/" +
              encodeURIComponent(f.filename),
            { method: "DELETE" }
          );
          loadFiles().catch(function () {});
        });
        right.appendChild(playRowBtn);
        right.appendChild(delBtn);
        head.appendChild(left);
        head.appendChild(right);
        row.appendChild(head);

        if (window.DF_renderTimelineCollapsible && f.start_ts && f.end_ts) {
          (async function (rowEl, file) {
            let clipTl = {
              date: date,
              range_start: file.start_ts,
              range_end: file.end_ts,
              shift: (dayTimeline && dayTimeline.shift) || { enabled: false },
              zones: [],
            };
            try {
              clipTl = await request(
                API +
                  "/recordings/" +
                  camId +
                  "/" +
                  encodeURIComponent(camName) +
                  "/" +
                  encodeURIComponent(date) +
                  "/timeline?from_ts=" +
                  file.start_ts +
                  "&to_ts=" +
                  file.end_ts
              );
              clipTl.date = date;
            } catch (_) {
              if (dayTimeline && window.DF_filterTimeline) {
                clipTl = window.DF_filterTimeline(dayTimeline, file.start_ts, file.end_ts);
                clipTl.date = date;
                if (dayTimeline.shift) clipTl.shift = dayTimeline.shift;
              }
            }
            window.DF_renderTimelineCollapsible(rowEl, clipTl, {
              clipStart: file.start_ts,
              clipEnd: file.end_ts,
            });
          })(row, f);
        }

        list.appendChild(row);
      });
      updateNavButtons();
    }

    function playContext(idx) {
      const camId = camSelect.value;
      const camName = selectedCamName();
      const date = dateSelect.value;
      if (!camId || !camName || !date) return null;
      if (!Array.isArray(currentFiles) || !currentFiles.length) return null;
      if (idx < 0 || idx >= currentFiles.length) return null;
      const f = currentFiles[idx];
      return {
        title: camName + " · " + date + " · " + f.filename,
        url:
          API +
          "/recordings/" +
          camId +
          "/" +
          encodeURIComponent(camName) +
          "/" +
          encodeURIComponent(date) +
          "/" +
          encodeURIComponent(f.filename) +
          "/file",
      };
    }

    function openAtIndex(idx) {
      window.DF_recPlayerPlay(panel, idx);
    }

    function selectDepartment(id) {
      if (String(deptSelect.value) !== String(id)) deptSelect.value = String(id);
      populateCameraSelect(null);
      resetRecordingsView();
      bindDeptNav();
      if (opts.onDepartmentSelect) opts.onDepartmentSelect(id);
    }

    function ensureNoneDepartment() {
      if (deptSelect.querySelector('option[value="none"]')) return;
      const opt = document.createElement("option");
      opt.value = "none";
      opt.dataset.name = t("noDepartment");
      opt.textContent = t("noDepartment");
      deptSelect.insertBefore(opt, deptSelect.firstChild);
    }

    function selectCamera(camId) {
      populateCameraSelect(camId);
      camSelect.value = String(camId);
      const cam = allCameras.find(function (c) { return String(c.id) === String(camId); });
      if (opts.onCameraSelect) opts.onCameraSelect(cam || null);
      loadDates().then(loadFiles).catch(function (e) {
        list.innerHTML = "<p class=\"help-text\">" + e.message + "</p>";
      });
      bindDeptNav();
    }

    deptSelect.onchange = function () {
      populateCameraSelect(null);
      resetRecordingsView();
      bindDeptNav();
    };

    camSelect.onchange = function () {
      const cam = allCameras.find(function (c) { return String(c.id) === camSelect.value; });
      if (opts.onCameraSelect) opts.onCameraSelect(cam || null);
      loadDates().then(loadFiles).catch(function (e) {
        list.innerHTML = "<p class=\"help-text\">" + e.message + "</p>";
      });
      bindDeptNav();
    };

    dateSelect.onchange = function () {
      loadFiles().catch(function (e) {
        list.innerHTML = "<p class=\"help-text\">" + e.message + "</p>";
      });
    };

    const panel = {
      get currentFiles() { return currentFiles; },
      get currentIndex() { return currentIndex; },
      set currentIndex(v) { currentIndex = v; },
      loadDepartments: loadDepartments,
      selectDepartment: selectDepartment,
      ensureNoneDepartment: ensureNoneDepartment,
      selectCamera: selectCamera,
      openAtIndex: openAtIndex,
      playContext: playContext,
      updateNavButtons: updateNavButtons,
    };

    return panel;
  }

  window.DF_createRecordingsPanel = createRecordingsPanel;

  window.DF_initRecordings = function () {
    const tab = document.getElementById("tab-recordings");
    if (!tab || tab.dataset.recReady === "1") return;
    tab.dataset.recReady = "1";
    window.DF_recPanel = createRecordingsPanel({
      deptSelect: document.getElementById("rec-department-select"),
      camSelect: document.getElementById("rec-camera-select"),
      dateSelect: document.getElementById("rec-date-select"),
      list: document.getElementById("rec-file-list"),
      dayTimelineEl: document.getElementById("rec-day-timeline"),
      deptNavEl: document.getElementById("rec-dept-nav"),
    });
    if (window.DF_recPanel) {
      window.DF_recPanel.loadDepartments().catch(function (e) {
        const list = document.getElementById("rec-file-list");
        if (list) list.innerHTML = "<p class=\"help-text\">" + e.message + "</p>";
      });
    }
  };

  window.DF_initCamRecordings = function () {
    const tab = document.getElementById("tab-cameras");
    if (!tab || tab.dataset.camRecReady === "1") return;
    tab.dataset.camRecReady = "1";
    window.DF_camRecPanel = createRecordingsPanel({
      deptSelect: document.getElementById("cam-rec-department-select"),
      camSelect: document.getElementById("cam-rec-camera-select"),
      dateSelect: document.getElementById("cam-rec-date-select"),
      list: document.getElementById("cam-rec-file-list"),
      dayTimelineEl: document.getElementById("cam-rec-day-timeline"),
      onCameraSelect: function (cam) {
        const title = document.getElementById("cam-recordings-title");
        const hint = document.getElementById("cam-recordings-hint");
        if (title) title.textContent = cam ? cam.name : t("recordingsTitle");
        if (hint) {
          hint.textContent = cam ? t("recSelectDateHint") : t("recSelectCameraHint");
        }
      },
    });
  };
})();
