/** ROI overlay на видеоплеере (как analiz). */
(function () {
  const API = "/api/v1";
  const t = (key) => (window.DF_I18N ? window.DF_I18N.t(key) : key);

  let cameraId = null;
  let isSelecting = false;
  let completedPolygons = [];
  let currentPoints = [];

  const video = () => document.getElementById("stream-video");
  const canvas = () => document.getElementById("roi-canvas");
  const statusEl = () => document.getElementById("roi-status");

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

    function drawPoly(points, stroke, fill) {
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
    }

    completedPolygons.forEach(function (poly) {
      drawPoly(poly.points, "#4caf50", "rgba(76, 175, 80, 0.15)");
    });
    if (currentPoints.length) {
      drawPoly(currentPoints, "#ffeb3b", null);
    }
  }

  async function loadRoi(id) {
    const res = await fetch(API + "/cameras/" + id + "/roi");
    if (!res.ok) return;
    const data = await res.json();
    completedPolygons = data.polygons || [];
    currentPoints = [];
    updateStatus(data.enabled);
    draw();
  }

  async function saveRoi(enabled) {
    if (!cameraId) return;
    const polygons = completedPolygons.map(function (p) {
      return { points: p.points };
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
    completedPolygons = data.polygons || [];
    updateStatus(data.enabled);
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
    const c = canvas();
    const editBtn = document.getElementById("roi-edit-btn");
    if (c) c.classList.toggle("hidden", !on);
    if (editBtn) editBtn.classList.toggle("btn-primary", on);
    if (on) layoutCanvas();
    else draw();
    updateStatus(completedPolygons.length > 0);
  }

  window.DF_setStreamCameraId = function (id) {
    cameraId = id;
    completedPolygons = [];
    currentPoints = [];
    setSelecting(false);
    if (id) loadRoi(id).catch(function () {});
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
          setSelecting(false);
          updateStatus(false);
          draw();
        });
    });

    c.addEventListener("mousedown", function (e) {
      if (!isSelecting) return;
      e.preventDefault();
      const rect = c.getBoundingClientRect();
      const pt = normFromCanvas(e.clientX - rect.left, e.clientY - rect.top);
      if (!pt) return;
      if (e.button === 2) {
        if (currentPoints.length >= 3) {
          completedPolygons.push({ points: currentPoints.slice() });
          currentPoints = [];
          saveRoi(true);
        }
        return;
      }
      currentPoints.push(pt);
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
