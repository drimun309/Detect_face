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

  const video = () => document.getElementById("stream-video");
  const canvas = () => document.getElementById("roi-canvas");
  const statusEl = () => document.getElementById("roi-status");
  const namesPanel = () => document.getElementById("roi-names-panel");

  function defaultZoneName(index) {
    return t("roiZoneDefault", { n: index });
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
      if (poly.points.length >= 3) {
        const cx =
          poly.points.reduce(function (s, p) {
            return s + p.x;
          }, 0) / poly.points.length;
        const cy =
          poly.points.reduce(function (s, p) {
            return s + p.y;
          }, 0) / poly.points.length;
        const lbl = zoneLabel(poly, polyIdx);
        ctx.font = "bold 14px sans-serif";
        ctx.fillStyle = "#ffffff";
        ctx.strokeStyle = "#1b5e20";
        ctx.lineWidth = 3;
        const textX = cx * c.width - Math.min(20, lbl.length * 3);
        ctx.strokeText(lbl, textX, cy * c.height - 8);
        ctx.fillText(lbl, textX, cy * c.height - 8);
      }
    });
    if (currentPoints.length) {
      drawPoly(currentPoints, "#ffeb3b", null, null);
    }
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
    if (enabled && n > 0) {
      el.textContent = t("roiActive") + " (" + n + ")";
      el.className = "roi-status active";
    } else if (isSelecting) {
      el.textContent = t("roiSelecting");
      el.className = "roi-status";
    } else {
      el.textContent = t("roiOff");
      el.className = "roi-status";
    }
  }

  function setSelecting(on) {
    isSelecting = on;
    dragState = null;
    const c = canvas();
    const editBtn = document.getElementById("roi-edit-btn");
    if (c) c.classList.toggle("hidden", !on);
    if (editBtn) editBtn.classList.toggle("btn-primary", on);
    if (on) layoutCanvas();
    else draw();
    renderNamesPanel();
    updateStatus(roiEnabled && completedPolygons.length > 0);
  }

  window.DF_setStreamCameraId = function (id) {
    cameraId = id;
    completedPolygons = [];
    currentPoints = [];
    roiEnabled = false;
    setSelecting(false);
    if (id) loadRoi(id).catch(function () {});
    else renderNamesPanel();
  };

  window.DF_initRoi = function () {
    const editBtn = document.getElementById("roi-edit-btn");
    const clearBtn = document.getElementById("roi-clear-btn");
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

    c.addEventListener("mousedown", function (e) {
      if (!isSelecting) return;
      e.preventDefault();
      const rect = c.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      const pt = normFromCanvas(cx, cy);
      if (!pt) return;
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
      if (isSelecting) e.preventDefault();
    });

    window.addEventListener("resize", function () {
      if (isSelecting) layoutCanvas();
    });

    const v = video();
    if (v) {
      v.addEventListener("loadedmetadata", function () {
        if (isSelecting) layoutCanvas();
      });
    }
  };
})();
