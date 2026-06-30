/** ROI overlay на видеоплеере (как analiz). */
(function () {
  const API = "/api/v1";
  const t = (key, vars) => (window.DF_I18N ? window.DF_I18N.t(key, vars) : key);

  let cameraId = null;
  let isSelecting = false;
  let completedPolygons = [];
  let currentPoints = [];
  let dragState = null;
  let saveTimer = null;
  let roiEnabled = false;
  let peopleZone = {
    enabled: false,
    polygon: [],
    max_workers: 3,
    current_workers: 0,
    person_seconds: 0,
  };
  let isDrawingPeopleZone = false;
  let peopleDraftPolygon = [];
  let peopleZonePollTimer = null;

  const video = () => document.getElementById("stream-video");
  const canvas = () => document.getElementById("roi-canvas");
  const statusEl = () => document.getElementById("roi-status");
  const namesPanel = () => document.getElementById("roi-names-panel");

  function stopPeopleZonePoll() {
    if (peopleZonePollTimer) {
      clearInterval(peopleZonePollTimer);
      peopleZonePollTimer = null;
    }
  }

  function startPeopleZonePoll() {
    stopPeopleZonePoll();
    if (!cameraId) return;
    peopleZonePollTimer = setInterval(function () {
      loadPeopleZone(cameraId, true).catch(function () {});
    }, 5000);
  }

  function defaultZoneName(index) {
    return t("roiZoneDefault", { n: index });
  }

  function peopleZoneConfigured() {
    return !!(peopleZone.enabled && peopleZone.polygon.length >= 3);
  }

  function formatShiftPersonTime(sec) {
    const total = Math.max(0, Math.floor(Number(sec) || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return h + ":" + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
  }

  function updatePeopleZoneStats() {
    const el = document.getElementById("people-zone-stats");
    if (!el) return;
    if (!peopleZoneConfigured()) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.classList.remove("hidden");
    el.textContent = t("peopleZoneStats", {
      n: peopleZone.current_workers || 0,
      time: formatShiftPersonTime(peopleZone.person_seconds),
    });
  }

  function updatePeopleZoneBtn() {
    const peopleBtn = document.getElementById("people-zone-btn");
    if (!peopleBtn) return;
    const active = isDrawingPeopleZone || peopleZoneConfigured();
    peopleBtn.classList.toggle("btn-primary", active);
    peopleBtn.classList.toggle("btn-secondary", !active);
    peopleBtn.title = peopleZoneConfigured()
      ? t("peopleZoneActive", { n: peopleZone.current_workers || 0 })
      : t("peopleZoneNotConfigured");
  }

  function refreshPeopleZoneOverlay() {
    updatePeopleZoneBtn();
    updatePeopleZoneStats();
    if (updateCanvasVisibility()) layoutCanvas();
    else draw();
  }

  function zoneLabel(poly, polyIdx) {
    const name = poly && poly.name ? String(poly.name).trim() : "";
    return name || defaultZoneName(polyIdx + 1);
  }

  function normalizePolygon(poly, index) {
    if (Array.isArray(poly)) {
      return { name: defaultZoneName(index), points: poly };
    }
    return {
      name: (poly.name && String(poly.name).trim()) || defaultZoneName(index),
      points: (poly.points || []).map(function (p) {
        return { x: p.x, y: p.y };
      }),
    };
  }

  function normalizePointList(points) {
    return (points || []).map(function (p) {
      return { x: p.x, y: p.y };
    });
  }

  function getVideoRect() {
    const v = video();
    const c = canvas();
    if (!v || !c) return null;
    const wrap = v.parentElement;
    if (!wrap) return null;
    const rect = v.getBoundingClientRect();
    const wrapRect = wrap.getBoundingClientRect();
    const vw = v.videoWidth || v.clientWidth || 1;
    const vh = v.videoHeight || v.clientHeight || 1;
    const displayAspect = rect.width / rect.height;
    const videoAspect = vw / vh;
    let displayX = 0;
    let displayY = 0;
    let displayW = rect.width;
    let displayH = rect.height;
    if (videoAspect > displayAspect) {
      displayH = rect.width / videoAspect;
      displayY = (rect.height - displayH) / 2;
    } else {
      displayW = rect.height * videoAspect;
      displayX = (rect.width - displayW) / 2;
    }
    return {
      x: rect.left - wrapRect.left + displayX,
      y: rect.top - wrapRect.top + displayY,
      width: displayW,
      height: displayH,
    };
  }

  function layoutCanvas() {
    const c = canvas();
    const r = getVideoRect();
    if (!c || !r) return;
    c.width = Math.max(1, Math.floor(r.width));
    c.height = Math.max(1, Math.floor(r.height));
    c.style.left = r.x + "px";
    c.style.top = r.y + "px";
    c.style.width = r.width + "px";
    c.style.height = r.height + "px";
    draw();
  }

  function normFromCanvas(cx, cy) {
    const c = canvas();
    if (!c) return null;
    return {
      x: Math.max(0, Math.min(1, cx / c.width)),
      y: Math.max(0, Math.min(1, cy / c.height)),
    };
  }

  function draw() {
    const c = canvas();
    if (!c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, c.width, c.height);

    function drawPoly(points, stroke, fill, activeVertexIdx) {
      if (points.length < 2) return;
      ctx.beginPath();
      ctx.moveTo(points[0].x * c.width, points[0].y * c.height);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x * c.width, points[i].y * c.height);
      }
      if (points.length >= 3) {
        ctx.closePath();
        if (fill) {
          ctx.fillStyle = fill;
          ctx.fill();
        }
      }
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 2;
      ctx.stroke();
      points.forEach(function (p) {
        ctx.beginPath();
        ctx.arc(p.x * c.width, p.y * c.height, 4, 0, Math.PI * 2);
        ctx.fillStyle = stroke;
        ctx.fill();
      });
      if (
        typeof activeVertexIdx === "number" &&
        activeVertexIdx >= 0 &&
        activeVertexIdx < points.length
      ) {
        const p = points[activeVertexIdx];
        ctx.beginPath();
        ctx.arc(p.x * c.width, p.y * c.height, 7, 0, Math.PI * 2);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    completedPolygons.forEach(function (poly, polyIdx) {
      const activeIdx =
        dragState && dragState.polyIndex === polyIdx ? dragState.pointIndex : null;
      drawPoly(poly.points, "#5ba8e0", "rgba(91, 168, 224, 0.18)", activeIdx);
    });
    if (currentPoints.length) {
      drawPoly(currentPoints, "#ffeb3b", null, null);
    }

    function drawPeoplePolygon(points) {
      if (!points || points.length < 2) return;
      drawPoly(points, "#ff4dff", "rgba(255, 77, 255, 0.12)", null);
    }

    const peoplePoly =
      isDrawingPeopleZone && peopleDraftPolygon.length
        ? peopleDraftPolygon
        : peopleZone.polygon;
    drawPeoplePolygon(peoplePoly);
  }

  function renderNamesPanel() {
    const panel = namesPanel();
    if (!panel) return;
    if (!completedPolygons.length) {
      panel.classList.add("hidden");
      panel.innerHTML = "";
      return;
    }
    panel.classList.remove("hidden");
    panel.innerHTML = "";
    completedPolygons.forEach(function (poly, idx) {
      const row = document.createElement("div");
      row.className = "roi-name-row";
      const label = document.createElement("label");
      label.textContent = defaultZoneName(idx + 1);
      const input = document.createElement("input");
      input.type = "text";
      input.className = "input";
      input.maxLength = 64;
      input.value = zoneLabel(poly, idx);
      input.placeholder = t("roiNamePlaceholder");
      input.dataset.polyIndex = String(idx);
      input.addEventListener("input", function () {
        const i = Number(input.dataset.polyIndex);
        if (completedPolygons[i]) {
          completedPolygons[i].name = input.value;
          draw();
          scheduleSave(roiEnabled);
        }
      });
      input.addEventListener("change", function () {
        const i = Number(input.dataset.polyIndex);
        if (completedPolygons[i]) {
          completedPolygons[i].name = input.value.trim() || defaultZoneName(i + 1);
          input.value = completedPolygons[i].name;
          saveRoi(roiEnabled);
        }
      });
      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn btn-danger btn-sm roi-zone-delete";
      delBtn.title = t("delete");
      delBtn.textContent = "×";
      delBtn.addEventListener("click", function () {
        deleteZone(idx);
      });
      row.appendChild(label);
      row.appendChild(input);
      row.appendChild(delBtn);
      panel.appendChild(row);
    });
  }

  function deleteZone(idx) {
    const poly = completedPolygons[idx];
    if (!poly) return;
    const name = zoneLabel(poly, idx);
    if (!confirm(t("roiDeleteZoneConfirm", { name: name }))) return;
    if (dragState && dragState.polyIndex === idx) dragState = null;
    else if (dragState && dragState.polyIndex > idx) dragState.polyIndex -= 1;
    completedPolygons.splice(idx, 1);
    currentPoints = [];
    const stillEnabled = roiEnabled && completedPolygons.length > 0;
    renderNamesPanel();
    draw();
    saveRoi(stillEnabled);
  }

  function scheduleSave(enabled) {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      saveRoi(enabled);
    }, 400);
  }

  function findNearestVertex(cx, cy, maxDistancePx) {
    const c = canvas();
    if (!c || !completedPolygons.length) return null;
    let best = null;
    let bestDist = Number.POSITIVE_INFINITY;
    for (let pIdx = 0; pIdx < completedPolygons.length; pIdx++) {
      const points = completedPolygons[pIdx].points || [];
      for (let i = 0; i < points.length; i++) {
        const px = points[i].x * c.width;
        const py = points[i].y * c.height;
        const dx = px - cx;
        const dy = py - cy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= maxDistancePx && dist < bestDist) {
          bestDist = dist;
          best = { polyIndex: pIdx, pointIndex: i };
        }
      }
    }
    return best;
  }

  async function loadRoi(id) {
    const res = await fetch(API + "/cameras/" + id + "/roi");
    if (!res.ok) return;
    const data = await res.json();
    completedPolygons = (data.polygons || []).map(function (poly, idx) {
      return normalizePolygon(poly, idx + 1);
    });
    currentPoints = [];
    roiEnabled = !!data.enabled;
    updateStatus(roiEnabled);
    renderNamesPanel();
    draw();
  }

  async function loadPeopleZone(id, silent) {
    const res = await fetch(API + "/cameras/" + id + "/people-zone");
    if (!res.ok) return;
    const data = await res.json();
    if (isDrawingPeopleZone) {
      peopleZone.current_workers = data.current_workers || 0;
      peopleZone.person_seconds = data.person_seconds || 0;
      if (!silent) updateStatus(roiEnabled);
      updatePeopleZoneBtn();
      return;
    }
    peopleZone = {
      enabled: !!data.enabled,
      polygon: normalizePointList(data.polygon),
      max_workers: 3,
      current_workers: data.current_workers || 0,
      person_seconds: data.person_seconds || 0,
    };
    updateStatus(roiEnabled);
    refreshPeopleZoneOverlay();
  }

  async function savePeopleZone(enabled) {
    if (!cameraId) return false;
    if (enabled && peopleZone.polygon.length < 3) {
      alert(t("peopleZoneIncomplete"));
      return false;
    }
    const body = {
      enabled: !!enabled,
      polygon: peopleZone.polygon,
      max_workers: 3,
    };
    const res = await fetch(API + "/cameras/" + cameraId + "/people-zone", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let err = await res.text();
      try {
        const parsed = JSON.parse(err);
        err = parsed.detail || err;
      } catch (_) {}
      alert(err);
      return false;
    }
    const data = await res.json();
    peopleZone = {
      enabled: !!data.enabled,
      polygon: normalizePointList(data.polygon),
      max_workers: 3,
      current_workers: data.current_workers || 0,
      person_seconds: data.person_seconds || 0,
    };
    updateStatus(roiEnabled);
    refreshPeopleZoneOverlay();
    return true;
  }

  async function saveRoi(enabled) {
    if (!cameraId) return;
    const polygons = completedPolygons.map(function (p, idx) {
      return {
        name: zoneLabel(p, idx),
        points: p.points,
      };
    });
    const res = await fetch(API + "/cameras/" + cameraId + "/roi", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: enabled, polygons: polygons }),
    });
    if (!res.ok) {
      const err = await res.text();
      alert(err);
      return;
    }
    const data = await res.json();
    completedPolygons = (data.polygons || []).map(function (poly, idx) {
      return normalizePolygon(poly, idx + 1);
    });
    roiEnabled = !!data.enabled;
    updateStatus(roiEnabled);
    renderNamesPanel();
    draw();
  }

  function updateStatus(enabled) {
    const el = statusEl();
    if (!el) return;
    const n = completedPolygons.length;
    if (isDrawingPeopleZone) {
      el.textContent = t("peopleZoneDrawing");
      el.className = "roi-status active";
      return;
    }
    if (isSelecting) {
      el.textContent = t("roiSelecting");
      el.className = "roi-status";
      return;
    }

    const parts = [];
    if (enabled && n > 0) {
      parts.push(t("roiActive") + " (" + n + ")");
    } else if (cameraId) {
      parts.push(t("roiOff"));
    }
    if (cameraId) {
      if (peopleZoneConfigured()) {
        parts.push(
          t("peopleZoneActive", { n: peopleZone.current_workers || 0 }) +
            " · " +
            t("peopleZoneShiftHours", {
              time: formatShiftPersonTime(peopleZone.person_seconds),
            })
        );
      } else {
        parts.push(t("peopleZoneNotConfigured"));
      }
    }
    if (parts.length) {
      el.textContent = parts.join(" · ");
      el.className =
        "roi-status" + (enabled && n > 0 || peopleZoneConfigured() ? " active" : "");
    } else {
      el.textContent = t("roiOff");
      el.className = "roi-status";
    }
  }

  function updateCanvasVisibility() {
    const c = canvas();
    if (!c) return false;
    const visible = isSelecting || isDrawingPeopleZone || peopleZoneConfigured();
    c.classList.toggle("hidden", !visible);
    c.style.pointerEvents = isSelecting || isDrawingPeopleZone ? "auto" : "none";
    return visible;
  }

  function setSelecting(on) {
    isSelecting = on;
    dragState = null;
    if (on) isDrawingPeopleZone = false;
    const editBtn = document.getElementById("roi-edit-btn");
    const visible = updateCanvasVisibility();
    if (editBtn) editBtn.classList.toggle("btn-primary", on);
    if (visible) layoutCanvas();
    else draw();
    renderNamesPanel();
    updateStatus(roiEnabled && completedPolygons.length > 0);
  }

  function setPeopleZoneDrawing(on) {
    isDrawingPeopleZone = on;
    if (on) {
      isSelecting = false;
      dragState = null;
      peopleDraftPolygon = [];
    }
    const editBtn = document.getElementById("roi-edit-btn");
    const visible = updateCanvasVisibility();
    if (editBtn) editBtn.classList.toggle("btn-primary", isSelecting);
    updatePeopleZoneBtn();
    if (visible) layoutCanvas();
    else draw();
    updateStatus(roiEnabled);
  }

  window.DF_setStreamCameraId = function (id) {
    const prevId = cameraId;
    const sameCamera = id && prevId === id;
    cameraId = id;
    if (!id) {
      stopPeopleZonePoll();
      completedPolygons = [];
      currentPoints = [];
      peopleZone = {
        enabled: false,
        polygon: [],
        max_workers: 3,
        current_workers: 0,
        person_seconds: 0,
      };
      isDrawingPeopleZone = false;
      peopleDraftPolygon = [];
      roiEnabled = false;
      updateCanvasVisibility();
      updatePeopleZoneBtn();
      setSelecting(false);
      renderNamesPanel();
      return;
    }
    if (!sameCamera) {
      completedPolygons = [];
      currentPoints = [];
      peopleZone = {
        enabled: false,
        polygon: [],
        max_workers: 3,
        current_workers: 0,
        person_seconds: 0,
      };
      isDrawingPeopleZone = false;
      peopleDraftPolygon = [];
      roiEnabled = false;
      updateCanvasVisibility();
      setSelecting(false);
    }
    loadRoi(id).catch(function () {});
    loadPeopleZone(id).catch(function () {});
    startPeopleZonePoll();
  };

  window.DF_onStreamVideoReady = function () {
    if (!cameraId) return;
    setTimeout(function () {
      refreshPeopleZoneOverlay();
    }, 80);
    loadPeopleZone(cameraId, true)
      .then(function () {
        updateStatus(roiEnabled);
        refreshPeopleZoneOverlay();
      })
      .catch(function () {
        refreshPeopleZoneOverlay();
      });
  };

  window.DF_initRoi = function () {
    const editBtn = document.getElementById("roi-edit-btn");
    const clearBtn = document.getElementById("roi-clear-btn");
    const peopleBtn = document.getElementById("people-zone-btn");
    const peopleClearBtn = document.getElementById("people-zone-clear-btn");
    const c = canvas();
    if (!editBtn || !c) return;

    editBtn.addEventListener("click", function () {
      if (!cameraId) {
        alert(t("roiNeedStream"));
        return;
      }
      setSelecting(!isSelecting);
    });

    clearBtn.addEventListener("click", function () {
      if (!cameraId) return;
      if (!confirm(t("roiClearConfirm"))) return;
      fetch(API + "/cameras/" + cameraId + "/roi", { method: "DELETE" })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          completedPolygons = data.polygons || [];
          currentPoints = [];
          roiEnabled = false;
          setSelecting(false);
          updateStatus(false);
          renderNamesPanel();
          draw();
        });
    });

    if (peopleBtn) {
      peopleBtn.addEventListener("click", function () {
        if (!cameraId) {
          alert(t("roiNeedStream"));
          return;
        }
        if (isDrawingPeopleZone) {
          setPeopleZoneDrawing(false);
          return;
        }
        setPeopleZoneDrawing(true);
      });
    }

    if (peopleClearBtn) {
      peopleClearBtn.addEventListener("click", function () {
        if (!cameraId) return;
        if (!confirm(t("peopleZoneClearConfirm"))) return;
        peopleZone = {
          enabled: false,
          polygon: [],
          max_workers: 3,
          current_workers: 0,
        };
        peopleDraftPolygon = [];
        setPeopleZoneDrawing(false);
        savePeopleZone(false);
      });
    }

    c.addEventListener("mousedown", function (e) {
      if (!isSelecting && !isDrawingPeopleZone) return;
      e.preventDefault();
      const rect = c.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      const pt = normFromCanvas(cx, cy);
      if (!pt) return;
      if (isDrawingPeopleZone) {
        if (e.button === 2) {
          if (peopleDraftPolygon.length >= 3) {
            peopleZone.polygon = peopleDraftPolygon.slice();
            peopleDraftPolygon = [];
            peopleZone.enabled = true;
            savePeopleZone(true).then(function (ok) {
              if (ok) setPeopleZoneDrawing(false);
            });
          }
          return;
        }
        if (e.button === 0) {
          peopleDraftPolygon.push(pt);
          draw();
        }
        return;
      }
      if (e.button === 2) {
        if (currentPoints.length >= 3) {
          completedPolygons.push({
            name: defaultZoneName(completedPolygons.length + 1),
            points: currentPoints.slice(),
          });
          currentPoints = [];
          renderNamesPanel();
          saveRoi(true);
        }
        return;
      }

      if (e.button === 0) {
        const hit = findNearestVertex(cx, cy, 10);
        if (hit) {
          dragState = hit;
          draw();
          return;
        }
      }
      currentPoints.push(pt);
      draw();
    });

    c.addEventListener("mousemove", function (e) {
      if (!isSelecting || !dragState) return;
      const rect = c.getBoundingClientRect();
      const pt = normFromCanvas(e.clientX - rect.left, e.clientY - rect.top);
      if (!pt) return;
      const poly = completedPolygons[dragState.polyIndex];
      if (!poly || !poly.points || !poly.points[dragState.pointIndex]) return;
      poly.points[dragState.pointIndex] = pt;
      draw();
    });

    c.addEventListener("mouseup", function () {
      if (!isSelecting || !dragState) return;
      dragState = null;
      saveRoi(roiEnabled);
      draw();
    });

    c.addEventListener("mouseleave", function () {
      if (!isSelecting || !dragState) return;
      dragState = null;
      saveRoi(roiEnabled);
      draw();
    });

    c.addEventListener("contextmenu", function (e) {
      if (isSelecting || isDrawingPeopleZone) e.preventDefault();
    });

    window.addEventListener("resize", function () {
      if (isSelecting || isDrawingPeopleZone || peopleZoneConfigured()) layoutCanvas();
    });

    const v = video();
    if (v) {
      v.addEventListener("loadedmetadata", function () {
        refreshPeopleZoneOverlay();
      });
      v.addEventListener("loadeddata", function () {
        refreshPeopleZoneOverlay();
      });
    }
  };
})();
