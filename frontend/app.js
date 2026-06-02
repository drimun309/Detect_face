/** i18n: ru (default) / en */
(function (global) {
  const STRINGS = {
    ru: {
      appTitle: "Распознавание лиц",
      tabCameras: "Камеры",
      tabSettings: "Настройки",
      tabEnroll: "Регистрация лиц",
      addCamera: "Добавить камеру",
      cameras: "Камеры",
      syncGo2rtc: "Синхр. go2rtc",
      reloadFacesDb: "Обновить БД лиц",
      liveStream: "Прямой эфир",
      stop: "Стоп",
      streamHint:
        "«Смотреть с детекцией» открывает большое окно с рамками и именами из PostgreSQL.",
      streamModalDetection: "Детекция: {name}",
      streamModalRaw: "Поток: {name}",
      watchDetection: "Смотреть с детекцией",
      watchRaw: "Сырой поток",
      delete: "Удалить",
      saveCamera: "Сохранить камеру",
      enabled: "Включена",
      name: "Имя",
      ip: "IP",
      port: "Порт",
      protocol: "Протокол",
      username: "Логин",
      password: "Пароль",
      path: "Путь RTSP",
      id: "ID",
      rtsp: "RTSP",
      detection: "Детекция",
      actions: "Действия",
      yes: "да",
      no: "нет",
      detOn: "вкл",
      detOff: "выкл",
      detInFrame: "в кадре",
      confirmDelete: "Удалить камеру {id}?",
      connecting: "Подключение: {name}",
      streamStopped: "Поток остановлен",
      cameraSaved: "Камера сохранена",
      cameraUpdated: "Камера обновлена",
      cancelEdit: "Отмена",
      editCamera: "Изменить",
      cameraDeleted: "Камера удалена",
      go2rtcSynced: "go2rtc синхронизирован",
      facesReloaded: "БД обновлена: {n} лиц",
      settingsTitle: "Настройки",
      sectionDetection: "Детекция (YOLO)",
      detectionMode: "Режим детекции",
      modeFace: "Лицо",
      modePerson: "Человек",
      modeFacePerson: "Лицо + человек",
      detectionModeHelp: "Лицо — распознавание по БД, человек — детекция тела, лицо + человек — оба класса.",
      sectionRecognition: "Распознавание (PostgreSQL)",
      sectionStream: "Поток и производительность",
      sectionDisplay: "Отображение",
      detConf: "Уверенность детектора",
      detConfHelp:
        "Выше — меньше ложных лиц, но можно пропустить дальние. Рекомендуется 25–55%.",
      detNms: "NMS (перекрытие боксов)",
      detNmsHelp: "Обычно 0.45. Ниже — агрессивнее убирает дубликаты.",
      minDetScore: "Мин. score для сравнения с БД",
      minDetScoreHelp: "Лица с низким score не сравниваются с эмбеддингами.",
      frDistance: "Порог расстояния (cosine)",
      frDistanceHelp:
        "Меньше — строже совпадение (меньше ложных имён). Типично 0.4–0.75.",
      frameInterval: "Каждый N-й кадр",
      frameIntervalHelp: "Больше — быстрее CPU, реже обновляются боксы.",
      streamFps: "FPS потока",
      streamResolution: "Разрешение",
      res720: "1280×720 (HD)",
      res540: "960×540",
      res360: "640×360 (легче)",
      resHint: "Смена разрешения перезапускает активные потоки.",
      embeddingRefresh: "Обновление БД (сек)",
      embeddingRefreshHelp: "Перечитывание эмбеддингов из PostgreSQL.",
      showUnknownDist: "Расстояние для незнакомых",
      saveSettings: "Сохранить настройки",
      saving: "Сохранение…",
      loading: "Загрузка…",
      savedOk: "Настройки сохранены",
      savedErr: "Ошибка сохранения",
      enrolledCount: "Записей в БД: {n}",
      autoplayBlocked:
        "Autoplay заблокирован. Нажмите «Смотреть с детекцией» ещё раз.",
      roiEdit: "Зона ROI",
      roiClear: "Очистить ROI",
      roiOff: "ROI выкл.",
      roiActive: "ROI активен",
      roiSelecting: "Рисование ROI…",
      roiHint: "ЛКМ — точка, ПКМ — завершить зону. Детекция только внутри ROI.",
      roiNeedStream: "Сначала включите просмотр камеры",
      roiClearConfirm: "Удалить все зоны ROI для этой камеры?",
      enrollTitle: "Регистрация в базу",
      enrollHint:
        "Загрузите фото и/или видео — эмбеддинги сохранятся в PostgreSQL.",
      personName: "Имя человека",
      addPhotos: "Добавить фото",
      addVideos: "Добавить видео",
      clearFiles: "Очистить список",
      replaceOld: "Заменить старые эмбеддинги этого имени",
      videoEvery: "Кадр видео каждые",
      maxEmbeddings: "Макс. эмбеддингов",
      enrollSubmit: "Зарегистрировать",
      enrollLog: "Журнал",
      enrolledPeople: "В базе",
      embeddingsTotal: "всего эмбеддингов",
      deletePerson: "Удалить",
      confirmDeletePerson: "Удалить все эмбеддинги для «{name}»?",
      noFiles: "Добавьте фото или видео",
      enrolling: "Регистрация…",
      enrollDone: "Сохранено {n} эмбеддингов",
      fileCount: "файлов",
    },
    en: {
      appTitle: "Face Recognition",
      tabCameras: "Cameras",
      tabSettings: "Settings",
      tabEnroll: "Enroll faces",
      addCamera: "Add camera",
      cameras: "Cameras",
      syncGo2rtc: "Sync go2rtc",
      reloadFacesDb: "Reload faces DB",
      liveStream: "Live stream",
      stop: "Stop",
      streamHint:
        "«Watch with detection» opens a large viewer with boxes and names from PostgreSQL.",
      streamModalDetection: "Detection: {name}",
      streamModalRaw: "Stream: {name}",
      watchDetection: "Watch with detection",
      watchRaw: "Raw stream",
      delete: "Delete",
      saveCamera: "Save camera",
      enabled: "Enabled",
      name: "Name",
      ip: "IP",
      port: "Port",
      protocol: "Protocol",
      username: "Username",
      password: "Password",
      path: "RTSP path",
      id: "ID",
      rtsp: "RTSP",
      detection: "Detection",
      actions: "Actions",
      yes: "yes",
      no: "no",
      detOn: "on",
      detOff: "off",
      detInFrame: "in frame",
      confirmDelete: "Delete camera {id}?",
      connecting: "Connecting: {name}",
      streamStopped: "Stream stopped",
      cameraSaved: "Camera saved",
      cameraUpdated: "Camera updated",
      cancelEdit: "Cancel",
      editCamera: "Edit",
      cameraDeleted: "Camera deleted",
      go2rtcSynced: "go2rtc synced",
      facesReloaded: "DB reloaded: {n} faces",
      settingsTitle: "Settings",
      sectionDetection: "Detection (YOLO)",
      detectionMode: "Detection mode",
      modeFace: "Face",
      modePerson: "Person",
      modeFacePerson: "Face + person",
      detectionModeHelp: "Face uses DB recognition, person detects full body, face + person enables both.",
      sectionRecognition: "Recognition (PostgreSQL)",
      sectionStream: "Stream & performance",
      sectionDisplay: "Display",
      detConf: "Detector confidence",
      detConfHelp: "Higher = fewer false detections. Try 25–55%.",
      detNms: "NMS overlap",
      detNmsHelp: "Usually 0.45.",
      minDetScore: "Min score for DB match",
      minDetScoreHelp: "Low-score faces skip embedding match.",
      frDistance: "Distance threshold (cosine)",
      frDistanceHelp: "Lower = stricter. Typical 0.4–0.75.",
      frameInterval: "Every N-th frame",
      frameIntervalHelp: "Higher = less CPU.",
      streamFps: "Stream FPS",
      streamResolution: "Resolution",
      res720: "1280×720 (HD)",
      res540: "960×540",
      res360: "640×360 (light)",
      resHint: "Resolution change restarts active streams.",
      embeddingRefresh: "DB refresh (sec)",
      embeddingRefreshHelp: "Reload embeddings from PostgreSQL.",
      showUnknownDist: "Distance for unknown faces",
      saveSettings: "Save settings",
      saving: "Saving…",
      loading: "Loading…",
      savedOk: "Settings saved",
      savedErr: "Save failed",
      enrolledCount: "Faces in DB: {n}",
      autoplayBlocked: "Autoplay blocked. Click watch again.",
      roiEdit: "ROI zone",
      roiClear: "Clear ROI",
      roiOff: "ROI off",
      roiActive: "ROI active",
      roiSelecting: "Drawing ROI…",
      roiHint: "LMB — point, RMB — close polygon. Detection inside ROI only.",
      roiNeedStream: "Start camera stream first",
      roiClearConfirm: "Remove all ROI zones for this camera?",
      enrollTitle: "Enroll to database",
      enrollHint: "Upload photos and/or videos — embeddings are saved to PostgreSQL.",
      personName: "Person name",
      addPhotos: "Add photos",
      addVideos: "Add videos",
      clearFiles: "Clear list",
      replaceOld: "Replace existing embeddings for this name",
      videoEvery: "Video frame every",
      maxEmbeddings: "Max embeddings",
      enrollSubmit: "Enroll",
      enrollLog: "Log",
      enrolledPeople: "In database",
      embeddingsTotal: "total embeddings",
      deletePerson: "Delete",
      confirmDeletePerson: "Delete all embeddings for «{name}»?",
      noFiles: "Add photos or videos",
      enrolling: "Enrolling…",
      enrollDone: "Saved {n} embeddings",
      fileCount: "files",
    },
  };

  let lang = localStorage.getItem("df_lang") || "ru";

  function t(key, vars) {
    const bag = STRINGS[lang] || STRINGS.ru;
    let s = bag[key] ?? STRINGS.ru[key] ?? key;
    if (vars) {
      Object.keys(vars).forEach((k) => {
        s = s.replace("{" + k + "}", String(vars[k]));
      });
    }
    return s;
  }

  function applyI18n(root) {
    const el = root || document;
    el.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      if (key) node.textContent = t(key);
    });
    const title = document.querySelector("title");
    if (title) title.textContent = t("appTitle");
    document.documentElement.lang = lang;
  }

  function setLang(next) {
    if (!STRINGS[next]) return;
    lang = next;
    localStorage.setItem("df_lang", next);
    applyI18n();
    document.dispatchEvent(new CustomEvent("df-lang-change"));
  }

  function getLang() {
    return lang;
  }

  global.DF_I18N = { t, applyI18n, setLang, getLang };
})(window);

(function () {
  const API = "/api/v1";
  const t = () => window.DF_I18N.t.apply(null, arguments);

  async function request(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error((await res.text()) || "HTTP " + res.status);
    return res.json();
  }

  window.DF_initSettings = function (onStatus) {
    const form = document.getElementById("settings-form");
    const saveBtn = document.getElementById("settings-save-btn");
    const saveMsg = document.getElementById("settings-save-msg");
    const confPct = document.getElementById("det-conf-pct");
    const confRange = document.getElementById("fr_det_conf");
    const distVal = document.getElementById("dist-val");
    const distRange = document.getElementById("fr_distance");
    const enrolledEl = document.getElementById("settings-enrolled");

    if (!form) return;

    confRange.addEventListener("input", () => {
      confPct.textContent = confRange.value + "%";
    });
    distRange.addEventListener("input", () => {
      distVal.textContent = distRange.value;
    });

    async function loadSettings() {
      saveBtn.disabled = true;
      saveMsg.textContent = t("loading");
      saveMsg.className = "save-message";
      try {
        const s = await request(API + "/settings/detection");
        form.detection_mode.value = s.detection_mode || "face";
        confRange.value = Math.round(s.fr_det_conf * 100);
        confPct.textContent = confRange.value + "%";
        form.fr_det_nms.value = s.fr_det_nms;
        distRange.value = s.fr_distance;
        distVal.textContent = s.fr_distance;
        form.min_det_score.value = s.min_det_score;
        form.stream_frame_interval.value = s.stream_frame_interval;
        form.stream_fps.value = s.stream_fps;
        const res = s.stream_width + "x" + s.stream_height;
        if (form.stream_resolution.querySelector('option[value="' + res + '"]')) {
          form.stream_resolution.value = res;
        }
        form.embedding_refresh_sec.value = s.embedding_refresh_sec;
        form.stream_show_unknown_distance.checked = s.stream_show_unknown_distance;

        try {
          const streams = await request(API + "/streams/status");
          const n = (streams.items && streams.items[0] && streams.items[0].enrolled_faces) || 0;
          enrolledEl.textContent = t("enrolledCount", { n: n });
        } catch (_) {
          enrolledEl.textContent = "";
        }
        saveMsg.textContent = "";
      } catch (err) {
        saveMsg.textContent = err.message;
        saveMsg.className = "save-message error";
        onStatus && onStatus(err.message, true);
      } finally {
        saveBtn.disabled = false;
      }
    }

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      saveBtn.disabled = true;
      saveMsg.textContent = t("saving");
      saveMsg.className = "save-message";
      const parts = form.stream_resolution.value.split("x");
      const payload = {
        detection_mode: String(form.detection_mode.value || "face"),
        fr_det_conf: Math.min(1, Math.max(0.01, Number(confRange.value) / 100)),
        fr_det_nms: Number(form.fr_det_nms.value),
        fr_distance: Number(distRange.value),
        min_det_score: Number(form.min_det_score.value),
        stream_frame_interval: Number(form.stream_frame_interval.value),
        stream_fps: Number(form.stream_fps.value),
        stream_width: Number(parts[0]),
        stream_height: Number(parts[1]),
        stream_show_unknown_distance: form.stream_show_unknown_distance.checked,
        embedding_refresh_sec: Number(form.embedding_refresh_sec.value),
      };
      try {
        await request(API + "/settings/detection", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        saveMsg.textContent = t("savedOk");
        saveMsg.className = "save-message success";
        onStatus && onStatus(t("savedOk"), false);
        await loadSettings();
      } catch (err) {
        saveMsg.textContent = t("savedErr");
        saveMsg.className = "save-message error";
        onStatus && onStatus(err.message, true);
      } finally {
        saveBtn.disabled = false;
      }
    });

    document.addEventListener("df-lang-change", loadSettings);
    loadSettings();
  };
})();

(function () {
  const API = "/api/v1";
  const t = () => window.DF_I18N.t.apply(null, arguments);

  async function request(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error((await res.text()) || "HTTP " + res.status);
    return res.json();
  }

  window.DF_initSettings = function (onStatus) {
    const form = document.getElementById("settings-form");
    const saveBtn = document.getElementById("settings-save-btn");
    const saveMsg = document.getElementById("settings-save-msg");
    const confPct = document.getElementById("det-conf-pct");
    const confRange = document.getElementById("fr_det_conf");
    const distVal = document.getElementById("dist-val");
    const distRange = document.getElementById("fr_distance");
    const enrolledEl = document.getElementById("settings-enrolled");

    if (!form) return;

    confRange.addEventListener("input", () => {
      confPct.textContent = confRange.value + "%";
    });
    distRange.addEventListener("input", () => {
      distVal.textContent = distRange.value;
    });

    async function loadSettings() {
      saveBtn.disabled = true;
      saveMsg.textContent = t("loading");
      saveMsg.className = "save-message";
      try {
        const s = await request(API + "/settings/detection");
        form.detection_mode.value = s.detection_mode || "face";
        confRange.value = Math.round(s.fr_det_conf * 100);
        confPct.textContent = confRange.value + "%";
        form.fr_det_nms.value = s.fr_det_nms;
        distRange.value = s.fr_distance;
        distVal.textContent = s.fr_distance;
        form.min_det_score.value = s.min_det_score;
        form.stream_frame_interval.value = s.stream_frame_interval;
        form.stream_fps.value = s.stream_fps;
        const res = s.stream_width + "x" + s.stream_height;
        if (form.stream_resolution.querySelector('option[value="' + res + '"]')) {
          form.stream_resolution.value = res;
        }
        form.embedding_refresh_sec.value = s.embedding_refresh_sec;
        form.stream_show_unknown_distance.checked = s.stream_show_unknown_distance;

        try {
          const streams = await request(API + "/streams/status");
          const n = (streams.items && streams.items[0] && streams.items[0].enrolled_faces) || 0;
          enrolledEl.textContent = t("enrolledCount", { n: n });
        } catch (_) {
          enrolledEl.textContent = "";
        }
        saveMsg.textContent = "";
      } catch (err) {
        saveMsg.textContent = err.message;
        saveMsg.className = "save-message error";
        onStatus && onStatus(err.message, true);
      } finally {
        saveBtn.disabled = false;
      }
    }

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      saveBtn.disabled = true;
      saveMsg.textContent = t("saving");
      saveMsg.className = "save-message";
      const parts = form.stream_resolution.value.split("x");
      const payload = {
        detection_mode: String(form.detection_mode.value || "face"),
        fr_det_conf: Math.min(1, Math.max(0.01, Number(confRange.value) / 100)),
        fr_det_nms: Number(form.fr_det_nms.value),
        fr_distance: Number(distRange.value),
        min_det_score: Number(form.min_det_score.value),
        stream_frame_interval: Number(form.stream_frame_interval.value),
        stream_fps: Number(form.stream_fps.value),
        stream_width: Number(parts[0]),
        stream_height: Number(parts[1]),
        stream_show_unknown_distance: form.stream_show_unknown_distance.checked,
        embedding_refresh_sec: Number(form.embedding_refresh_sec.value),
      };
      try {
        await request(API + "/settings/detection", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        saveMsg.textContent = t("savedOk");
        saveMsg.className = "save-message success";
        onStatus && onStatus(t("savedOk"), false);
        await loadSettings();
      } catch (err) {
        saveMsg.textContent = t("savedErr");
        saveMsg.className = "save-message error";
        onStatus && onStatus(err.message, true);
      } finally {
        saveBtn.disabled = false;
      }
    });

    document.addEventListener("df-lang-change", loadSettings);
    loadSettings();
  };
})();
(function () {
  const API = "/api/v1";
  const t = (key, vars) => window.DF_I18N.t(key, vars);
  const RECONNECT_DELAYS = [1000, 2000, 5000];

  const form = document.getElementById("camera-form");
  const table = document.getElementById("camera-table");
  const statusEl = document.getElementById("status");
  const cameraEditId = document.getElementById("camera-edit-id");
  const cameraSubmitBtn = document.getElementById("camera-submit-btn");
  const cameraCancelBtn = document.getElementById("camera-cancel-btn");
  const cameraFormTitle = document.getElementById("camera-form-title");
  const cameraFormMsg = document.getElementById("camera-form-msg");
  const cameraModal = document.getElementById("camera-modal");
  const cameraModalBackdrop = document.getElementById("camera-modal-backdrop");
  const cameraModalClose = document.getElementById("camera-modal-close");
  const addCameraBtn = document.getElementById("add-camera-btn");
  let editingCameraId = null;

  function openCameraModal() {
    if (!cameraModal) return;
    cameraModal.classList.remove("hidden");
    cameraModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    const first = form.querySelector('input[name="name"]');
    if (first) setTimeout(function () { first.focus(); }, 50);
  }

  function closeCameraModal() {
    if (!cameraModal) return;
    cameraModal.classList.add("hidden");
    cameraModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    resetCameraForm();
  }
  const syncBtn = document.getElementById("sync-btn");
  const reloadFacesBtn = document.getElementById("reload-faces-btn");
  const streamModal = document.getElementById("stream-modal");
  const streamModalBackdrop = document.getElementById("stream-modal-backdrop");
  const streamModalClose = document.getElementById("stream-modal-close");
  const streamModalTitle = document.getElementById("stream-modal-title");
  const streamVideo = document.getElementById("stream-video");
  const streamMeta = document.getElementById("stream-meta");
  const streamState = document.getElementById("stream-state");
  const closeStreamBtn = document.getElementById("close-stream-btn");

  if (!form || !table || !statusEl) {
    console.error("[detect_face] UI elements missing — hard refresh (Ctrl+Shift+R)");
    return;
  }

  let ws = null;
  let pc = null;
  let reconnectTimer = null;
  let reconnectAttempt = 0;
  let shouldReconnect = false;
  let isConnected = false;
  let useDirectGo2rtc = false;
  let currentStreamName = "";

  function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.className = "global-status" + (isError ? " error" : "");
  }

  function setStreamState(text) {
    streamState.textContent = text;
  }

  function rtspUrl(cam) {
    const auth = cam.username && cam.password ? cam.username + ":***@" : "";
    return cam.protocol + "://" + auth + cam.ip + ":" + cam.port + cam.path;
  }

  function wsBaseViaNginx() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return proto + "://" + window.location.host + "/go2rtc/api/ws";
  }

  function wsBaseDirect() {
    return "ws://" + (window.location.hostname || "localhost") + ":1985/api/ws";
  }

  function cleanupPeer(keepVideo) {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    shouldReconnect = false;
    if (ws) {
      ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null;
      try {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close();
      } catch (_) {}
      ws = null;
    }
    if (pc) {
      pc.ontrack = pc.onicecandidate = pc.onconnectionstatechange = null;
      try {
        pc.close();
      } catch (_) {}
      pc = null;
    }
    if (!keepVideo && streamVideo) {
      streamVideo.srcObject = null;
      streamVideo.removeAttribute("src");
      try {
        streamVideo.load();
      } catch (_) {}
    }
  }

  /** MP4 через go2rtc/nginx — стабильнее WebRTC в Docker на Windows. */
  function connectMp4() {
    if (!currentStreamName || !streamVideo) return;
    cleanupPeer(true);
    setStreamState("connecting");
    const url =
      window.location.origin +
      "/go2rtc/api/stream.mp4?src=" +
      encodeURIComponent(currentStreamName);
    streamVideo.srcObject = null;
    streamVideo.src = url;
    streamVideo.muted = true;
    streamVideo.playsInline = true;
    streamVideo.onloadeddata = function () {
      isConnected = true;
      reconnectAttempt = 0;
      setStreamState("connected");
      setStatus(t("connecting", { name: currentStreamName }));
    };
    streamVideo.onerror = function () {
      isConnected = false;
      setStreamState("error");
      scheduleReconnect();
    };
    streamVideo
      .play()
      .then(function () {
        isConnected = true;
        setStreamState("connected");
      })
      .catch(function (err) {
        console.warn("[MP4] play blocked", err);
        setStatus(t("autoplayBlocked"), true);
      });
  }

  async function attachStreamToVideo(stream) {
    streamVideo.srcObject = stream;
    streamVideo.muted = true;
    streamVideo.playsInline = true;
    try {
      await streamVideo.play();
    } catch (err) {
      console.warn("[WebRTC] play blocked", err);
      setStatus(t("autoplayBlocked"), true);
    }
  }

  function scheduleReconnect() {
    if (!shouldReconnect || isConnected) return;
    const delay = RECONNECT_DELAYS[Math.min(reconnectAttempt, RECONNECT_DELAYS.length - 1)];
    reconnectTimer = setTimeout(function () {
      reconnectAttempt++;
      connectMp4();
    }, delay);
  }

  function connectWebRTC() {
    if (!currentStreamName || isConnected) return;
    cleanupPeer(true);
    setStreamState("connecting");
    const wsUrl =
      (useDirectGo2rtc ? wsBaseDirect() : wsBaseViaNginx()) +
      "?src=" +
      encodeURIComponent(currentStreamName);

    try {
      ws = new WebSocket(wsUrl);
    } catch (err) {
      setStreamState("error");
      setStatus(err.message, true);
      return;
    }

    ws.onopen = async function () {
      try {
        pc = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] });
        pc.addTransceiver("video", { direction: "recvonly" });
        pc.addTransceiver("audio", { direction: "recvonly" });
        pc.ontrack = function (event) {
          if (event.streams && event.streams[0]) attachStreamToVideo(event.streams[0]);
        };
        pc.onicecandidate = function (event) {
          if (event.candidate && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "webrtc/candidate", value: event.candidate.candidate }));
          }
        };
        pc.onconnectionstatechange = function () {
          setStreamState(pc.connectionState);
          if (pc.connectionState === "connected") {
            isConnected = true;
            reconnectAttempt = 0;
            setStatus(t("connecting", { name: currentStreamName }));
            if (ws) {
              ws.onclose = null;
              try {
                ws.close();
              } catch (_) {}
              ws = null;
            }
          } else if (pc.connectionState === "failed") {
            isConnected = false;
            cleanupPeer();
            if (!useDirectGo2rtc) {
              useDirectGo2rtc = true;
              connectWebRTC();
            } else scheduleReconnect();
          }
        };
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        ws.send(JSON.stringify({ type: "webrtc/offer", value: offer.sdp }));
      } catch (err) {
        setStreamState("error");
        setStatus(err.message, true);
        scheduleReconnect();
      }
    };

    ws.onmessage = async function (event) {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "webrtc/answer" && pc && msg.value) {
          await pc.setRemoteDescription(new RTCSessionDescription({ type: "answer", sdp: msg.value }));
        } else if (msg.type === "webrtc/candidate" && pc && msg.value) {
          try {
            await pc.addIceCandidate(new RTCIceCandidate({ candidate: msg.value, sdpMid: "0" }));
          } catch (_) {}
        }
      } catch (_) {}
    };

    ws.onerror = function () {
      if (!useDirectGo2rtc) {
        useDirectGo2rtc = true;
        connectWebRTC();
      }
    };

    ws.onclose = function () {
      if (!isConnected) scheduleReconnect();
    };
  }

  function parseApiError(text) {
    try {
      const data = JSON.parse(text);
      const detail = data.detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        return detail.map(function (e) {
          return e.msg || JSON.stringify(e);
        }).join("; ");
      }
      return text;
    } catch (_) {
      return text || "HTTP error";
    }
  }

  async function request(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(parseApiError(await res.text()) || "HTTP " + res.status);
    if (res.status === 204) return null;
    return res.json();
  }

  function cameraPayloadFromForm(fd) {
    return {
      name: String(fd.get("name") || "").trim(),
      ip: String(fd.get("ip") || "").trim(),
      port: Number(fd.get("port") || 554),
      protocol: fd.get("protocol") || "rtsp",
      username: (fd.get("username") && String(fd.get("username"))) || null,
      password: (fd.get("password") && String(fd.get("password"))) || null,
      path: String(fd.get("path") || "/Streaming/Channels/101").trim(),
      enabled: fd.get("enabled") === "on",
    };
  }

  function setCameraFormMode(editId) {
    editingCameraId = editId || null;
    if (cameraEditId) cameraEditId.value = editingCameraId ? String(editingCameraId) : "";
    if (cameraFormTitle) {
      cameraFormTitle.textContent = editingCameraId ? t("editCamera") + " #" + editingCameraId : t("addCamera");
    }
    if (cameraSubmitBtn) {
      cameraSubmitBtn.textContent = editingCameraId ? t("saveCamera") : t("saveCamera");
    }
  }

  function fillCameraForm(cam) {
    form.name.value = cam.name;
    form.ip.value = cam.ip;
    form.port.value = cam.port;
    form.protocol.value = cam.protocol || "rtsp";
    form.username.value = cam.username || "";
    form.password.value = "";
    form.path.value = cam.path;
    form.enabled.checked = !!cam.enabled;
    setCameraFormMode(cam.id);
    if (cameraFormMsg) cameraFormMsg.textContent = "";
    openCameraModal();
  }

  function resetCameraForm() {
    if (!form) return;
    form.reset();
    form.port.value = "554";
    form.path.value = "/Streaming/Channels/101";
    form.enabled.checked = true;
    setCameraFormMode(null);
    if (cameraFormMsg) cameraFormMsg.textContent = "";
  }

  async function loadCameras() {
    const data = await request(API + "/cameras");
    const streams = await request(API + "/streams/status").catch(function () {
      return { items: [] };
    });
    const streamById = {};
    (streams.items || []).forEach(function (s) {
      streamById[String(s.camera_id)] = s;
    });
    table.innerHTML = "";
    data.items.forEach(function (cam) {
      const st = streamById[String(cam.id)];
      const enrolled = (st && st.enrolled_faces) || 0;
      let detCell = "—";
      if (st && st.stream_running) {
        detCell =
          t("detOn") + " (" + st.faces_count + " " + t("detInFrame") + ", DB: " + enrolled + ")";
      } else if (cam.enabled) {
        detCell = t("detOff") + " (DB: " + enrolled + ")";
      }
      const tr = document.createElement("tr");
      const tdId = document.createElement("td");
      tdId.textContent = cam.id;
      const tdName = document.createElement("td");
      tdName.textContent = cam.name;
      const tdRtsp = document.createElement("td");
      tdRtsp.textContent = rtspUrl(cam);
      const tdEn = document.createElement("td");
      tdEn.textContent = cam.enabled ? t("yes") : t("no");
      const tdDet = document.createElement("td");
      tdDet.textContent = detCell;
      const tdAct = document.createElement("td");
      tdAct.className = "actions";

      function mkBtn(cls, label, attrs) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = cls;
        b.textContent = label;
        Object.keys(attrs).forEach(function (k) {
          b.setAttribute(k, attrs[k]);
        });
        return b;
      }

      const watchAnnot = mkBtn("watch-annot-btn btn btn-primary", t("watchDetection"), {
        "data-id": String(cam.id),
        "data-name": cam.name,
      });
      const watchRaw = mkBtn("watch-btn btn btn-secondary", t("watchRaw"), {
        "data-id": String(cam.id),
        "data-name": cam.name,
      });
      const editBtn = mkBtn("edit-btn btn btn-secondary", t("editCamera"), {
        "data-id": String(cam.id),
      });
      const delBtn = mkBtn("delete-btn btn btn-danger", t("delete"), {
        "data-id": String(cam.id),
      });
      tdAct.append(watchAnnot, watchRaw, editBtn, delBtn);
      tr.append(tdId, tdName, tdRtsp, tdEn, tdDet, tdAct);
      table.appendChild(tr);
    });
  }

  function openStreamModal(cameraName, useAnnotated) {
    if (!streamModal) return;
    if (streamModalTitle) {
      streamModalTitle.textContent = useAnnotated
        ? t("streamModalDetection", { name: cameraName })
        : t("streamModalRaw", { name: cameraName });
    }
    streamModal.classList.remove("hidden");
    streamModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    window.dispatchEvent(new Event("resize"));
  }

  function closeStreamModal() {
    if (!streamModal) return;
    streamModal.classList.add("hidden");
    streamModal.setAttribute("aria-hidden", "true");
    if (!cameraModal || cameraModal.classList.contains("hidden")) {
      document.body.style.overflow = "";
    }
  }

  function openStream(cameraId, cameraName, useAnnotated) {
    currentStreamName = useAnnotated ? "cam" + cameraId + "_annot" : "cam" + cameraId;
    useDirectGo2rtc = false;
    reconnectAttempt = 0;
    shouldReconnect = true;
    isConnected = false;
    openStreamModal(cameraName, useAnnotated);
    if (streamMeta) streamMeta.textContent = currentStreamName;
    if (window.DF_setStreamCameraId) window.DF_setStreamCameraId(String(cameraId));
    setStreamState("connecting");
    setStatus(t("connecting", { name: currentStreamName }));
    connectMp4();
  }

  function closeStream() {
    cleanupPeer(false);
    if (window.DF_setStreamCameraId) window.DF_setStreamCameraId(null);
    currentStreamName = "";
    closeStreamModal();
    if (streamMeta) streamMeta.textContent = "";
    setStreamState("—");
    setStatus(t("streamStopped"));
  }

  /* Tabs */
  document.querySelectorAll(".nav-tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const tab = btn.getAttribute("data-tab");
      document.querySelectorAll(".nav-tab").forEach(function (b) {
        b.classList.toggle("active", b === btn);
      });
      document.querySelectorAll(".tab-panel").forEach(function (p) {
        p.classList.toggle("active", p.id === "tab-" + tab);
      });
      if (tab === "enroll" && window.DF_initEnroll) window.DF_initEnroll();
    });
  });

  document.querySelectorAll(".lang-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const lang = btn.getAttribute("data-lang");
      window.DF_I18N.setLang(lang);
      document.querySelectorAll(".lang-btn").forEach(function (b) {
        b.classList.toggle("active", b.getAttribute("data-lang") === lang);
      });
      loadCameras().catch(function () {});
    });
  });

  if (addCameraBtn) {
    addCameraBtn.addEventListener("click", function () {
      resetCameraForm();
      openCameraModal();
    });
  }
  if (cameraCancelBtn) cameraCancelBtn.addEventListener("click", closeCameraModal);
  if (cameraModalClose) cameraModalClose.addEventListener("click", closeCameraModal);
  if (cameraModalBackdrop) cameraModalBackdrop.addEventListener("click", closeCameraModal);
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (streamModal && !streamModal.classList.contains("hidden")) {
      closeStream();
      return;
    }
    if (cameraModal && !cameraModal.classList.contains("hidden")) {
      closeCameraModal();
    }
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = cameraPayloadFromForm(fd);
    if (editingCameraId && !fd.get("password")) delete payload.password;
    if (!payload.name || !payload.ip) {
      setStatus(t("saveCamera"), true);
      return;
    }
    if (cameraSubmitBtn) cameraSubmitBtn.disabled = true;
    if (cameraFormMsg) cameraFormMsg.textContent = t("saving");
    try {
      if (editingCameraId) {
        await request(API + "/cameras/" + editingCameraId, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        setStatus(t("cameraUpdated"));
        if (cameraFormMsg) cameraFormMsg.textContent = t("cameraUpdated");
      } else {
        await request(API + "/cameras", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        setStatus(t("cameraSaved"));
        if (cameraFormMsg) cameraFormMsg.textContent = t("cameraSaved");
      }
      closeCameraModal();
      await loadCameras();
    } catch (err) {
      setStatus(err.message, true);
      if (cameraFormMsg) cameraFormMsg.textContent = err.message;
    } finally {
      if (cameraSubmitBtn) cameraSubmitBtn.disabled = false;
    }
  });

  table.addEventListener("click", async function (e) {
    const editBtn = e.target.closest(".edit-btn");
    if (editBtn) {
      const id = editBtn.getAttribute("data-id");
      try {
        const cam = await request(API + "/cameras/" + id);
        fillCameraForm(cam);
      } catch (err) {
        setStatus(err.message, true);
      }
      return;
    }
    const watchBtn = e.target.closest(".watch-btn");
    if (watchBtn) {
      openStream(watchBtn.getAttribute("data-id"), watchBtn.getAttribute("data-name") || "cam", false);
      return;
    }
    const watchAnnotBtn = e.target.closest(".watch-annot-btn");
    if (watchAnnotBtn) {
      openStream(watchAnnotBtn.getAttribute("data-id"), watchAnnotBtn.getAttribute("data-name") || "cam", true);
      return;
    }
    const delBtn = e.target.closest(".delete-btn");
    if (!delBtn) return;
    const id = delBtn.getAttribute("data-id");
    if (!confirm(t("confirmDelete", { id: id }))) return;
    try {
      await request(API + "/cameras/" + id, { method: "DELETE" });
      setStatus(t("cameraDeleted"));
      await loadCameras();
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  reloadFacesBtn.addEventListener("click", async function () {
    try {
      const res = await request(API + "/faces/reload-embeddings", { method: "POST" });
      setStatus(t("facesReloaded", { n: res.enrolled_faces }));
      await loadCameras();
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  syncBtn.addEventListener("click", async function () {
    try {
      await request(API + "/cameras/sync-go2rtc", { method: "POST" });
      setStatus(t("go2rtcSynced"));
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  if (closeStreamBtn) closeStreamBtn.addEventListener("click", closeStream);
  if (streamModalClose) streamModalClose.addEventListener("click", closeStream);
  if (streamModalBackdrop) streamModalBackdrop.addEventListener("click", closeStream);

  window.DF_onEnrollSuccess = function () {
    fetch(API + "/faces/reload-embeddings", { method: "POST" }).catch(function () {});
    loadCameras().catch(function () {});
  };

  if (window.DF_I18N) window.DF_I18N.applyI18n();
  if (window.DF_initRoi) window.DF_initRoi();
  if (window.DF_initSettings) window.DF_initSettings(setStatus);
  loadCameras().catch(function (err) {
    setStatus(err.message, true);
  });
  setInterval(function () {
    if (document.getElementById("tab-cameras").classList.contains("active")) {
      loadCameras().catch(function () {});
    }
  }, 5000);
})();

(function () {
  const API = "/api/v1";
  const t = (key, vars) => window.DF_I18N.t(key, vars);

  let photoFiles = [];
  let videoFiles = [];
  let initialized = false;

  function updateFileList() {
    const list = document.getElementById("enroll-file-list");
    const countEl = document.getElementById("enroll-file-count");
    if (!list) return;
    list.innerHTML = "";
    photoFiles.forEach(function (f, i) {
      const li = document.createElement("li");
      li.textContent = "[photo] " + f.name;
      li.dataset.kind = "photo";
      li.dataset.index = String(i);
      list.appendChild(li);
    });
    videoFiles.forEach(function (f, i) {
      const li = document.createElement("li");
      li.textContent = "[video] " + f.name;
      li.dataset.kind = "video";
      li.dataset.index = String(i);
      list.appendChild(li);
    });
    const total = photoFiles.length + videoFiles.length;
    if (countEl) countEl.textContent = total + " " + t("fileCount");
  }

  function appendLog(lines) {
    const box = document.getElementById("enroll-log");
    if (!box) return;
    box.textContent = (box.textContent ? box.textContent + "\n" : "") + lines.join("\n");
    box.scrollTop = box.scrollHeight;
  }

  async function loadEnrolled() {
    const table = document.getElementById("enroll-people-table");
    const totalEl = document.getElementById("enroll-db-total");
    if (!table) return;
    try {
      const data = await fetch(API + "/faces/enrolled").then(function (r) {
        if (!r.ok) throw new Error(r.statusText);
        return r.json();
      });
      table.innerHTML = "";
      data.items.forEach(function (row) {
        const tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" +
          row.name +
          "</td><td>" +
          row.count +
          '</td><td><button type="button" class="btn btn-danger btn-sm" data-name="' +
          row.name +
          '">' +
          t("deletePerson") +
          "</button></td>";
        table.appendChild(tr);
      });
      if (totalEl) {
        totalEl.textContent = data.total_embeddings + " " + t("embeddingsTotal");
      }
    } catch (err) {
      if (totalEl) totalEl.textContent = err.message;
    }
  }

  window.DF_initEnroll = function () {
    if (initialized) {
      loadEnrolled();
      return;
    }
    initialized = true;

    const form = document.getElementById("enroll-form");
    const photoInput = document.getElementById("enroll-photo-input");
    const videoInput = document.getElementById("enroll-video-input");
    const submitBtn = document.getElementById("enroll-submit");

    document.getElementById("enroll-add-photos").addEventListener("click", function () {
      photoInput.click();
    });
    document.getElementById("enroll-add-videos").addEventListener("click", function () {
      videoInput.click();
    });
    document.getElementById("enroll-clear-files").addEventListener("click", function () {
      photoFiles = [];
      videoFiles = [];
      updateFileList();
    });

    photoInput.addEventListener("change", function () {
      photoFiles = photoFiles.concat(Array.from(photoInput.files));
      photoInput.value = "";
      updateFileList();
    });
    videoInput.addEventListener("change", function () {
      videoFiles = videoFiles.concat(Array.from(videoInput.files));
      videoInput.value = "";
      updateFileList();
    });

    document.getElementById("enroll-people-table").addEventListener("click", async function (e) {
      const btn = e.target.closest("button[data-name]");
      if (!btn) return;
      const name = btn.getAttribute("data-name");
      if (!confirm(t("confirmDeletePerson", { name: name }))) return;
      try {
        await fetch(API + "/faces/person/" + encodeURIComponent(name), { method: "DELETE" });
        await loadEnrolled();
        if (window.DF_onEnrollSuccess) window.DF_onEnrollSuccess();
      } catch (err) {
        alert(err.message);
      }
    });

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      const name = document.getElementById("enroll-name").value.trim();
      if (!name) {
        alert(t("personName"));
        return;
      }
      if (!photoFiles.length && !videoFiles.length) {
        alert(t("noFiles"));
        return;
      }

      const fd = new FormData();
      fd.append("name", name);
      fd.append("replace", document.getElementById("enroll-replace").checked ? "true" : "false");
      fd.append("every", document.getElementById("enroll-every").value);
      fd.append("max_embeddings", document.getElementById("enroll-max").value);
      photoFiles.forEach(function (f) {
        fd.append("photos", f);
      });
      videoFiles.forEach(function (f) {
        fd.append("videos", f);
      });

      submitBtn.disabled = true;
      document.getElementById("enroll-log").textContent = t("enrolling") + "\n";

      try {
        const res = await fetch(API + "/faces/enroll", { method: "POST", body: fd });
        const text = await res.text();
        if (!res.ok) {
          let detail = text;
          try {
            detail = JSON.parse(text).detail || text;
          } catch (_) {}
          throw new Error(detail);
        }
        const data = JSON.parse(text);
        appendLog(data.logs || []);
        appendLog([t("enrollDone", { n: data.saved })]);
        photoFiles = [];
        videoFiles = [];
        updateFileList();
        await loadEnrolled();
        if (window.DF_onEnrollSuccess) window.DF_onEnrollSuccess();
      } catch (err) {
        appendLog([String(err.message)]);
      } finally {
        submitBtn.disabled = false;
      }
    });

    loadEnrolled();
  };
})();
