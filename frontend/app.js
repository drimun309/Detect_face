/** i18n: ru (default) / en */
(function (global) {
  const STRINGS = {
    ru: {
      appTitle: "Распознавание лиц",
      tabCameras: "Камеры",
      tabSettings: "Настройки",
      tabEnroll: "Регистрация лиц",
      tabRecordings: "Записи",
      tabStats: "Статистика",
      statsTitle: "Аналитика",
      statsHint: "Рабочие зоны: работа/простой и чел·часы; общая зона: чел·часы, смена 07:00–19:00",
      statsRoiSummary: "{days} дн. · 07:00–19:00 · работа {work} · простой {idle} · чел·часы {personHours}",
      statsTimelineWorkIdle: "Работа и простой",
      statsTimelineWorkers: "Занятость (чел·часы)",
      statsMode: "Тип аналитики",
      statsModeRoi: "Рабочие зоны",
      statsSealerProducts: "Готовые изделия",
      statsSealerCycles: "Циклы",
      statsSealerSummary: "готовые изделия: {n}",
      statsModePeople: "Общая зона",
      statsPersonHours: "Чел·часы",
      statsWorkAllZones: "Работа (всех зон)",
      statsIdleAllZones: "Простой (всех зон)",
      statsPersonHoursAllZones: "Чел·часы (всех зон)",
      statsWorkAllZonesHint: "Сумма работы по всем рабочим зонам за смену 07:00–19:00",
      statsIdleAllZonesHint: "Сумма простоя по всем рабочим зонам за смену 07:00–19:00",
      statsPersonHoursAllZonesHint: "Сумма чел·часов по всем рабочим зонам за смену 07:00–19:00",
      statsWorkers0: "0 чел. в зоне",
      statsWorkers1: "1 чел. в зоне",
      statsWorkers2: "2 чел. в зоне",
      statsWorkers3: "3 чел. в зоне",
      statsPeopleZoneName: "Общая зона",
      statsPeopleSummary: "{days} дн. · 07:00–19:00 · чел·часы {personHours}",
      statsPeopleDayDetail: "Общая зона: {date}",
      statsNoPeopleData: "Нет данных по общей зоне за период",
      statsFilters: "Фильтры",
      statsFrom: "С",
      statsTo: "По",
      statsPeriod: "Период",
      statsPeriodDays: "{n} дн.",
      statsPeriodAll: "Все данные",
      statsTableTitle: "По дням",
      statsWork: "Работа",
      statsIdle: "Простой",
      statsZones: "Зон",
      statsZone: "Рабочая зона",
      statsZoneLabel: "Зона {n}",
      statsSelectFilters: "Выберите отдел, камеру и период",
      selectDepartment: "-- Выберите отдел --",
      statsSelectDepartmentFirst: "-- Сначала выберите отдел --",
      statsNoCamerasInDept: "В этом отделе нет камер",
      statsNoData: "Нет данных за выбранный период",
      statsNoZones: "Нет зон за этот день",
      statsSummary: "{days} дн. · 07:00–19:00 · работа {work} · простой {idle}",
      statsDayDetail: "Детализация: {date}",
      date: "Дата",
      camera: "Камера",
      addCamera: "Добавить камеру",
      addDepartment: "Добавить отдел",
      department: "Отдел",
      noDepartment: "Без отдела",
      departmentName: "Название отдела",
      saveDepartment: "Сохранить отдел",
      confirmDeleteDepartment: "Удалить отдел «{name}»? Камеры останутся без отдела.",
      departmentSaved: "Отдел создан",
      departmentUpdated: "Отдел переименован",
      departmentDeleted: "Отдел удалён",
      editDepartment: "Изменить",
      cameraDepartmentUpdated: "Камера перенесена в другой отдел",
      camerasCount: "{n} кам.",
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
      watchMaxQuality: "Макс. качество",
      watchMaxQualityOn: "Макс. качество: вкл",
      watchMaxQualityOff: "Макс. качество: выкл",
      watchMaxQualityHint: "Переключение разрешения…",
      streamQuality: "Качество",
      streamQualityGlobal: "По умолчанию (настройки)",
      cameraStreamQuality: "Качество детекции",
      cameraStreamQualityHint:
        "Разрешение annotated-потока для этой камеры. «По умолчанию» — из глобальных настроек.",
      streamQualityHint: "Смена разрешения…",
      packageDetectionOff: "Пакеты: выкл.",
      packageDetectionOn: "Пакеты: вкл.",
      packageDetectionHint: "Переключение…",
      rodPoseOff: "Ручка YOLO: выкл.",
      rodPoseOn: "Ручка YOLO: вкл.",
      rodPoseHint: "Переключение…",
      sealerRoiEdit: "ROI ручки",
      sealerRoiClear: "Очистить ручку",
      sealerRoiActive: "Готовые изделия: {n}",
      sealerRoiNotConfigured: "ROI ручки: не настроен",
      sealerRoiDrawing: "Нарисуйте прямоугольник на ручке в покое (перетащите мышью)",
      sealerRoiIncomplete: "Для зоны запайщика нужен прямоугольник",
      sealerRoiClearConfirm: "Удалить зону ручки запайщика?",
      sealerRoiNeedDetection: "Откройте просмотр с детекцией (кнопка «Детекция» на камере)",
      sealerRoiStats: "За смену (7–19): {n} · угол {act}°",
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
      workersInFrame: "работников в кадре",
      workersNone: "Работников в кадре: нет",
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
      personDetModel: "Модель детекции человека",
      personDetModelHelp:
        "YOLOv8s — класс person (COCO). CrowdHuman — тело и голова. YOLO26n — лёгкая ONNX. Пакеты — детекция package/label.",
      crowdhumanDetType: "CrowdHuman: классы",
      crowdhumanBoth: "Тело и голова",
      crowdhumanBody: "Только тело",
      crowdhumanHead: "Только голова",
      crowdhumanDetTypeHelp:
        "Для модели CrowdHuman: детектировать тело, голову или оба класса одновременно.",
      personTracker: "Трекер людей",
      trackerOff: "Выкл.",
      trackerByteTrack: "ByteTrack",
      trackerBoTSORT: "BoT-SORT",
      trackerSORT: "SORT (Kalman)",
      personTrackerHelp:
        "Сопровождает человека между кадрами и предсказывает движение, если детекция на мгновение пропала (~ = предсказание). StrongSORT ≈ BoT-SORT.",
      personTrackBuffer: "Держать трек (кадров)",
      personTrackBufferHelp:
        "Сколько кадров без детекции оставлять бокс по предсказанию (больше — стабильнее, но дольше «призрак»).",
      modeFace: "Лицо",
      modePerson: "Человек",
      modeFacePerson: "Лицо + человек",
      detectionModeHelp: "Лицо — распознавание по БД, человек — детекция тела, лицо + человек — оба класса.",
      sectionRecognition: "Распознавание (PostgreSQL)",
      sectionStream: "Поток и производительность",
      sectionDisplay: "Отображение",
      sectionRecording: "Запись видео",
      recEnabled: "Запись",
      recRetention: "Хранить дней",
      recChunk: "Длительность ролика (мин)",
      recShiftEnabled: "Только в смену",
      recShiftStart: "Начало смены",
      recShiftEnd: "Конец смены",
      recAutoEnabled: "Авто-запись по смене",
      recQuality: "Качество (разрешение записи)",
      recQualityHint: "2K: поток с детекцией автоматически переключается в макс. качество. Меньше разрешение — меньше файлы.",
      recCrf: "CRF (качество/размер)",
      recCrfHint: "Типично 24–32.",
      recordingsTitle: "Записи видео",
      recordingsSelectCamera: "Выбор камеры",
      selectCamera: "-- Выберите камеру --",
      selectDate: "-- Сначала выберите камеру --",
      recordingsList: "Ролики",
      recSelectHint: "Выберите отдел, камеру и дату для просмотра записей",
      recPlay: "Смотреть",
      recPause: "Пауза",
      play: "Смотреть",
      recordingsDayTimeline: "День: работа и простой",
      recTimelineDayHint: "Выберите камеру и дату для диаграммы за день",
      recTimelineDayScale: "Шкала 24 ч · {date}",
      recTimelineDayUntil: "данные до {time}",
      recTimelineDayNoEvents:
        "За {date} нет накопленной истории (ни журнал смен, ни почасовые данные). Нужен работающий поток с ROI.",
      recTimelineHourlyNote:
        "По журналу смен за день записей нет; полоса построена из почасовых накоплений (roi_timer_hourly).",
      recTimelineDailyTotals: "итого: раб. {work}, прост. {idle}",
      recTimelineFuture: "Будущее время (данных ещё нет)",
      recTimelineClipScale: "Интервал записи",
      recTimelineToggle: "Работа / простой по зонам",
      recTimelineShift: "Смена",
      recTimelineEmpty: "Нет данных по зонам за этот период",
      recTimelineDetectNote:
        "По журналу смен режима из БД (работа / простой / ожидание).",
      recTimeline_work: "работа",
      recTimeline_idle: "простой",
      recTimeline_standby: "ожидание",
      recToggle: "Запись: выкл.",
      recOn: "Запись: ВКЛ",
      recOff: "Запись: выкл.",
      recErrDisabled: "Включите запись в настройках (Запись → Вкл)",
      recErrShift: "Сейчас вне смены — запись недоступна",
      recErrStart: "Не удалось запустить запись",
      recNeedDetection: "Запись доступна только в режиме «Смотреть с детекцией»",
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
      frameInterval: "Частота кадров для обработки",
      frameIntervalHelp:
        "1 = YOLO на каждом кадре (боксы синхронны). 2, 4… = реже детекция, меньше CPU; при пропуске повторяется последний отрисованный кадр.",
      streamFps: "FPS потока",
      streamFpsHelp: "Частота исходящего видео в браузер (ffmpeg). Не зависит от частоты детекции.",
      streamResolution: "Разрешение",
      res720: "1280×720 (HD)",
      res1080: "1920×1080 (Full HD)",
      res1440: "2560×1440 (2K)",
      res540: "960×540",
      res360: "640×360 (легче)",
      resHint: "Смена разрешения перезапускает активные потоки.",
      embeddingRefresh: "Обновление БД (сек)",
      embeddingRefreshHelp: "Перечитывание эмбеддингов из PostgreSQL.",
      sectionRoiTimer: "ROI: работа / простой",
      roiTimerSwitch: "Порог смены режима (сек)",
      roiTimerSwitchHelp:
        "Сколько секунд подряд человек в зоне (или вне зоны), чтобы сменить работа↔простой и записать в журнал.",
      roiTimerGrace: "Пауза детекции (сек)",
      roiTimerGraceHelp: "Краткое пропадание bbox не сбрасывает «человек в зоне».",
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
      roiHint: "ЛКМ — точка/перетаскивание вершины, ПКМ — завершить зону. Детекция только внутри ROI.",
      roiNeedStream: "Сначала включите просмотр камеры",
      roiClearConfirm: "Удалить все зоны ROI для этой камеры?",
      roiZoneDefault: "Зона {n}",
      roiNamePlaceholder: "Название зоны",
      roiDeleteZoneConfirm: "Удалить зону «{name}»?",
      peopleZoneEdit: "Общая зона",
      peopleZoneClear: "Очистить общую",
      peopleZoneActive: "Общая зона активна ({n}/3)",
      peopleZoneStats: "В общей зоне сейчас: {n}/3 · За смену (7–19): {time} чел·ч",
      peopleZoneShiftHours: "смена {time} чел·ч",
      peopleZoneNotConfigured: "Общая зона: не настроена",
      peopleZoneDrawing:
        "Общая зона: ЛКМ — точки полигона, ПКМ — завершить (мин. 3 точки)",
      peopleZoneIncomplete: "Для общей зоны нужен полигон из ≥3 точек.",
      peopleZoneClearConfirm: "Удалить общую зону?",
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
      tabRecordings: "Recordings",
      tabStats: "Statistics",
      statsTitle: "Analytics",
      statsHint: "Work zones: work/idle and person·hours; whole zone: person·hours, shift 07:00–19:00",
      statsRoiSummary: "{days} days · 07:00–19:00 · work {work} · idle {idle} · person·hours {personHours}",
      statsTimelineWorkIdle: "Work and idle",
      statsTimelineWorkers: "Occupancy (person·hours)",
      statsMode: "Analytics type",
      statsModeRoi: "Work zones",
      statsModePeople: "Whole zone",
      statsPersonHours: "Person·h",
      statsWorkAllZones: "Work (all zones)",
      statsIdleAllZones: "Idle (all zones)",
      statsPersonHoursAllZones: "Person·h (all zones)",
      statsWorkAllZonesHint: "Sum of work time across all work zones for shift 07:00–19:00",
      statsIdleAllZonesHint: "Sum of idle time across all work zones for shift 07:00–19:00",
      statsPersonHoursAllZonesHint: "Sum of person·hours across all work zones for shift 07:00–19:00",
      statsWorkers0: "0 in zone",
      statsWorkers1: "1 in zone",
      statsWorkers2: "2 in zone",
      statsWorkers3: "3 in zone",
      statsPeopleZoneName: "Whole zone",
      statsPeopleSummary: "{days} days · 07:00–19:00 · person·h {personHours}",
      statsPeopleDayDetail: "Whole zone: {date}",
      statsNoPeopleData: "No whole-zone data for this period",
      statsFilters: "Filters",
      statsFrom: "From",
      statsTo: "To",
      statsPeriod: "Period",
      statsPeriodDays: "{n} days",
      statsPeriodAll: "All data",
      statsTableTitle: "By day",
      statsWork: "Work",
      statsIdle: "Idle",
      statsZones: "Zones",
      statsZone: "Work zone",
      statsZoneLabel: "Zone {n}",
      statsSelectFilters: "Select department, camera and period",
      selectDepartment: "-- Select department --",
      statsSelectDepartmentFirst: "-- Select department first --",
      statsNoCamerasInDept: "No cameras in this department",
      statsNoData: "No data for the selected period",
      statsNoZones: "No zones for this day",
      statsSummary: "{days} days · 07:00–19:00 · work {work} · idle {idle}",
      statsDayDetail: "Details: {date}",
      date: "Date",
      camera: "Camera",
      addCamera: "Add camera",
      addDepartment: "Add department",
      department: "Department",
      noDepartment: "No department",
      departmentName: "Department name",
      saveDepartment: "Save department",
      confirmDeleteDepartment: "Delete department «{name}»? Cameras will be unassigned.",
      departmentSaved: "Department created",
      departmentUpdated: "Department renamed",
      departmentDeleted: "Department deleted",
      editDepartment: "Rename",
      cameraDepartmentUpdated: "Camera moved to another department",
      camerasCount: "{n} cam.",
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
      watchMaxQuality: "Max quality",
      watchMaxQualityOn: "Max quality: on",
      watchMaxQualityOff: "Max quality: off",
      watchMaxQualityHint: "Switching resolution…",
      streamQuality: "Quality",
      streamQualityGlobal: "Default (settings)",
      cameraStreamQuality: "Detection quality",
      cameraStreamQualityHint:
        "Annotated stream resolution for this camera. Default uses global settings.",
      streamQualityHint: "Changing resolution…",
      packageDetectionOff: "Packages: off",
      packageDetectionOn: "Packages: on",
      packageDetectionHint: "Switching…",
      rodPoseOff: "Handle YOLO: off",
      rodPoseOn: "Handle YOLO: on",
      rodPoseHint: "Switching…",
      sealerRoiEdit: "Sealer handle ROI",
      sealerRoiClear: "Clear handle ROI",
      sealerRoiActive: "Finished products: {n}",
      sealerRoiNotConfigured: "Sealer handle ROI: not configured",
      sealerRoiDrawing: "Draw a rectangle on the handle at rest (drag with mouse)",
      sealerRoiIncomplete: "Sealer ROI needs a rectangle",
      sealerRoiClearConfirm: "Remove sealer handle ROI?",
      sealerRoiNeedDetection: "Open detection view (Detection button on the camera)",
      sealerRoiStats: "Shift (7–19): {n} · angle {act}°",
      statsSealerProducts: "Готовые изделия",
      statsSealerCycles: "Циклы",
      statsSealerSummary: "finished products: {n}",
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
      workersInFrame: "workers in frame",
      workersNone: "No workers in frame",
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
      personDetModel: "Person detection model",
      personDetModelHelp:
        "YOLOv8s — COCO person class. CrowdHuman — body and head. YOLO26n — lightweight ONNX. Packages — package/label detection.",
      crowdhumanDetType: "CrowdHuman classes",
      crowdhumanBoth: "Body and head",
      crowdhumanBody: "Body only",
      crowdhumanHead: "Head only",
      crowdhumanDetTypeHelp:
        "For CrowdHuman model: detect body, head, or both classes.",
      personTracker: "People tracker",
      trackerOff: "Off",
      trackerByteTrack: "ByteTrack",
      trackerBoTSORT: "BoT-SORT",
      trackerSORT: "SORT (Kalman)",
      personTrackerHelp:
        "Tracks people across frames and predicts motion when detection briefly drops (~ = predicted). StrongSORT ≈ BoT-SORT.",
      personTrackBuffer: "Keep track (frames)",
      personTrackBufferHelp:
        "How many frames to keep a box by prediction without detection (higher = more stable, longer ghost).",
      modeFace: "Face",
      modePerson: "Person",
      modeFacePerson: "Face + person",
      detectionModeHelp: "Face uses DB recognition, person detects full body, face + person enables both.",
      sectionRecognition: "Recognition (PostgreSQL)",
      sectionStream: "Stream & performance",
      sectionDisplay: "Display",
      sectionRecording: "Recording",
      recEnabled: "Recording",
      recRetention: "Keep days",
      recChunk: "Chunk (min)",
      recShiftEnabled: "Only during shift",
      recShiftStart: "Shift start",
      recShiftEnd: "Shift end",
      recAutoEnabled: "Auto record by shift",
      recQuality: "Recording resolution",
      recQualityHint: "2K: detection stream switches to max quality automatically. Lower resolution -> smaller files.",
      recCrf: "CRF (quality/size)",
      recCrfHint: "Typical 24–32.",
      recordingsTitle: "Recordings",
      recordingsSelectCamera: "Select camera",
      selectCamera: "-- Select camera --",
      selectDate: "-- Select date --",
      recordingsList: "Files",
      recSelectHint: "Select department, camera and date to view recordings",
      recPlay: "Play",
      recPause: "Pause",
      play: "Play",
      recordingsDayTimeline: "Day: work & idle",
      recTimelineDayHint: "Select camera and date for the day chart",
      recTimelineDayScale: "24h scale · {date}",
      recTimelineDayUntil: "data until {time}",
      recTimelineDayNoEvents:
        "No history for {date} (no mode log or hourly data). ROI stream must be running.",
      recTimelineHourlyNote:
        "No mode-change log for this day; chart uses hourly totals (roi_timer_hourly).",
      recTimelineDailyTotals: "total: work {work}, idle {idle}",
      recTimelineFuture: "Future time (no data yet)",
      recTimelineClipScale: "Recording interval",
      recTimelineToggle: "Work / idle by zone",
      recTimelineShift: "Shift",
      recTimelineEmpty: "No zone data for this period",
      recTimelineDetectNote:
        "From DB mode-change log (work / idle / standby).",
      recTimeline_work: "work",
      recTimeline_idle: "idle",
      recTimeline_standby: "standby",
      recToggle: "Rec: off",
      recOn: "Rec: ON",
      recOff: "Rec: off",
      recErrDisabled: "Enable recording in Settings (Recording → On)",
      recErrShift: "Outside shift hours — recording unavailable",
      recErrStart: "Failed to start recording",
      recNeedDetection: "Recording works only in “Watch with detection” mode",
      detConf: "Detector confidence",
      detConfHelp: "Higher = fewer false detections. Try 25–55%.",
      detNms: "NMS overlap",
      detNmsHelp: "Usually 0.45.",
      minDetScore: "Min score for DB match",
      minDetScoreHelp: "Low-score faces skip embedding match.",
      frDistance: "Distance threshold (cosine)",
      frDistanceHelp: "Lower = stricter. Typical 0.4–0.75.",
      frameInterval: "Processing frame interval",
      frameIntervalHelp:
        "1 = YOLO every frame (boxes in sync). 2, 4… = less CPU; skipped frames re-send the last annotated frame.",
      streamFps: "Stream FPS",
      streamFpsHelp: "Outgoing video rate to the browser (ffmpeg). Independent of detection rate.",
      streamResolution: "Resolution",
      res720: "1280×720 (HD)",
      res1080: "1920×1080 (Full HD)",
      res1440: "2560×1440 (2K)",
      res540: "960×540",
      res360: "640×360 (light)",
      resHint: "Resolution change restarts active streams.",
      embeddingRefresh: "DB refresh (sec)",
      embeddingRefreshHelp: "Reload embeddings from PostgreSQL.",
      sectionRoiTimer: "ROI: work / idle",
      roiTimerSwitch: "Mode switch threshold (sec)",
      roiTimerSwitchHelp:
        "Seconds person must be in/out of zone before work/idle is logged.",
      roiTimerGrace: "Detection grace (sec)",
      roiTimerGraceHelp: "Brief missed frames do not clear presence.",
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
      roiHint: "LMB — add point/drag vertex, RMB — close polygon. Detection inside ROI only.",
      roiNeedStream: "Start camera stream first",
      roiClearConfirm: "Remove all ROI zones for this camera?",
      roiZoneDefault: "Zone {n}",
      roiNamePlaceholder: "Zone name",
      roiDeleteZoneConfirm: "Delete zone «{name}»?",
      peopleZoneEdit: "Whole zone",
      peopleZoneClear: "Clear whole zone",
      peopleZoneActive: "Whole zone active ({n}/3)",
      peopleZoneStats: "In whole zone now: {n}/3 · Shift (7–19): {time} person·h",
      peopleZoneShiftHours: "shift {time} person·h",
      peopleZoneNotConfigured: "Whole zone: not configured",
      peopleZoneDrawing:
        "Whole zone: LMB — polygon points, RMB — finish (min. 3 points)",
      peopleZoneIncomplete: "Whole zone needs a polygon with at least 3 points.",
      peopleZoneClearConfirm: "Remove whole zone?",
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

    if (!form || form.dataset.settingsReady === "1") return;
    form.dataset.settingsReady = "1";

    const crowdhumanGroup = document.getElementById("crowdhuman_det_type_group");

    function updateCrowdHumanOptions() {
      const isCrowd = form.person_det_model?.value === "crowdhuman_yolov5m";
      if (crowdhumanGroup) crowdhumanGroup.hidden = !isCrowd;
    }

    form.person_det_model?.addEventListener("change", updateCrowdHumanOptions);

    async function loadPersonModels() {
      const select = form.person_det_model;
      if (!select) return;
      try {
        const data = await request(API + "/settings/person-models");
        const items = data.items || [];
        if (!items.length) return;
        const current = select.value;
        select.innerHTML = "";
        items.forEach(function (m) {
          const opt = document.createElement("option");
          opt.value = m.id;
          const missing = m.exists === false ? " (нет файла)" : "";
          opt.textContent = (m.label_ru || m.id) + missing;
          select.appendChild(opt);
        });
        if (current && select.querySelector('option[value="' + current + '"]')) {
          select.value = current;
        }
      } catch (_e) {
        /* оставляем статические option из HTML */
      }
    }

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
        await loadPersonModels();
        const s = await request(API + "/settings/detection");
        form.detection_mode.value = s.detection_mode || "face";
        if (form.person_det_model) {
          form.person_det_model.value = s.person_det_model || "yolov8s";
        }
        if (form.crowdhuman_det_type) {
          form.crowdhuman_det_type.value = s.crowdhuman_det_type || "both";
        }
        if (form.person_tracker) {
          form.person_tracker.value = s.person_tracker || "bytetrack";
        }
        if (form.person_track_buffer) {
          form.person_track_buffer.value = s.person_track_buffer ?? 90;
        }
        updateCrowdHumanOptions();
        confRange.value = Math.round(s.fr_det_conf * 100);
        confPct.textContent = confRange.value + "%";
        form.fr_det_nms.value = s.fr_det_nms;
        distRange.value = s.fr_distance;
        distVal.textContent = s.fr_distance;
        form.min_det_score.value = s.min_det_score;
        form.stream_frame_interval.value = String(s.stream_frame_interval || 1);
        form.stream_fps.value = s.stream_fps;
        const res = s.stream_width + "x" + s.stream_height;
        if (form.stream_resolution.querySelector('option[value="' + res + '"]')) {
          form.stream_resolution.value = res;
        }
        form.embedding_refresh_sec.value = s.embedding_refresh_sec;
        form.stream_show_unknown_distance.checked = s.stream_show_unknown_distance;
        if (form.roi_timer_switch_sec) {
          form.roi_timer_switch_sec.value = s.roi_timer_switch_sec ?? 60;
        }
        if (form.roi_timer_reset_grace_sec) {
          form.roi_timer_reset_grace_sec.value = s.roi_timer_reset_grace_sec ?? 7;
        }

        try {
          const streams = await request(API + "/streams/status");
          const n = (streams.items && streams.items[0] && streams.items[0].enrolled_faces) || 0;
          enrolledEl.textContent = t("enrolledCount", { n: n });
        } catch (_) {
          enrolledEl.textContent = "";
        }
        saveMsg.textContent = "";

        // recording settings
        try {
          const r = await request(API + "/settings/recording");
          document.getElementById("rec_enabled").value = r.enabled ? "true" : "false";
          document.getElementById("rec_auto_enabled").checked = !!r.auto_enabled;
          document.getElementById("rec_retention").value = r.retention_days ?? 3;
          document.getElementById("rec_chunk").value = r.chunk_duration_min ?? 10;
          const q = (r.record_width || 1280) + "x" + (r.record_height || 720);
          if (document.getElementById("rec_quality").querySelector('option[value="' + q + '"]')) {
            document.getElementById("rec_quality").value = q;
          }
          document.getElementById("rec_crf").value = r.record_crf ?? 28;
          document.getElementById("rec_shift_enabled").checked = !!(r.shift && r.shift.enabled);
          document.getElementById("rec_shift_start").value = (r.shift && r.shift.start_time) || "09:00";
          document.getElementById("rec_shift_end").value = (r.shift && r.shift.end_time) || "18:00";
        } catch (_) {}
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
        person_det_model: String(form.person_det_model?.value || "yolov8s"),
        crowdhuman_det_type: String(form.crowdhuman_det_type?.value || "both"),
        person_tracker: String(form.person_tracker?.value || "bytetrack"),
        person_track_buffer: Number(form.person_track_buffer?.value || 90),
        fr_det_conf: Math.min(1, Math.max(0.01, Number(confRange.value) / 100)),
        fr_det_nms: Number(form.fr_det_nms.value),
        fr_distance: Number(distRange.value),
        min_det_score: Number(form.min_det_score.value),
        stream_frame_interval: Number(form.stream_frame_interval.value || 1),
        stream_fps: Number(form.stream_fps.value),
        stream_width: Number(parts[0]),
        stream_height: Number(parts[1]),
        stream_show_unknown_distance: form.stream_show_unknown_distance.checked,
        embedding_refresh_sec: Number(form.embedding_refresh_sec.value),
        roi_timer_switch_sec: Number(form.roi_timer_switch_sec?.value || 60),
        roi_timer_reset_grace_sec: Number(form.roi_timer_reset_grace_sec?.value || 7),
      };
      try {
        await request(API + "/settings/detection", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const recPayload = {
          enabled: document.getElementById("rec_enabled").value === "true",
          auto_enabled: document.getElementById("rec_auto_enabled").checked,
          retention_days: Number(document.getElementById("rec_retention").value || 3),
          chunk_duration_min: Number(document.getElementById("rec_chunk").value || 10),
          record_width: Number(String(document.getElementById("rec_quality").value).split("x")[0] || 1280),
          record_height: Number(String(document.getElementById("rec_quality").value).split("x")[1] || 720),
          record_crf: Number(document.getElementById("rec_crf").value || 28),
          shift: {
            enabled: document.getElementById("rec_shift_enabled").checked,
            start_time: document.getElementById("rec_shift_start").value || "09:00",
            end_time: document.getElementById("rec_shift_end").value || "18:00",
          },
        };
        await request(API + "/settings/recording", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(recPayload),
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
  const cameraFormController = form && window.DF_CameraFormController
    ? new window.DF_CameraFormController(API, form)
    : null;
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
  const addDepartmentBtn = document.getElementById("add-department-btn");
  const departmentModal = document.getElementById("department-modal");
  const departmentModalBackdrop = document.getElementById("department-modal-backdrop");
  const departmentModalClose = document.getElementById("department-modal-close");
  const departmentForm = document.getElementById("department-form");
  const departmentFormMsg = document.getElementById("department-form-msg");
  const departmentCancelBtn = document.getElementById("department-cancel-btn");
  const departmentFormTitle = document.getElementById("department-form-title");
  const cameraDepartmentSelect = document.getElementById("camera-department");
  let editingCameraId = null;
  let departmentsCache = [];
  let editingDepartmentId = null;
  const collapsedDepts = new Set();
  let camerasDeptFilter = "";
  let camerasListCache = [];
  let streamByIdCache = {};

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
  let stallTimer = null;
  let stallLastTime = 0;
  let stallTicks = 0;
  let mseMediaSource = null;
  let mseObjectUrl = null;
  let useDirectGo2rtc = false;
  let currentStreamName = "";
  let currentCameraId = null;
  let currentCameraName = "";
  let currentUseAnnotated = false;
  let currentStreamQualityPreset = "global";
  let packageDetectionEnabled = false;
  let rodPoseEnabled = false;
  let recordingActive = false;

  function cameraQualityPreset(cam) {
    if (!cam || cam.stream_width == null || cam.stream_height == null) return "global";
    return String(cam.stream_width) + "x" + String(cam.stream_height);
  }

  function applyStreamQualityPreset(preset, effectiveW, effectiveH) {
    const select = document.getElementById("stream-quality-select");
    const label = document.querySelector(".stream-quality-label");
    const player = document.querySelector(".stream-player-wrap");
    const dialog = document.querySelector(".stream-modal-dialog");
    const show = currentUseAnnotated && !!currentCameraId;
    if (select) {
      select.classList.toggle("hidden", !show);
      if (show) select.value = preset || "global";
      select.disabled = false;
    }
    if (label) label.classList.toggle("hidden", !show);
    const isLarge =
      preset === "2560x1440" || (Number(effectiveW) >= 2560 && Number(effectiveH) >= 1440);
    if (player) player.classList.toggle("stream-max-quality", isLarge);
    if (dialog) dialog.classList.toggle("stream-max-quality", isLarge);
    if (isLarge) window.dispatchEvent(new Event("resize"));
  }

  function updateMaxQualityBtn() {
    applyStreamQualityPreset(currentStreamQualityPreset);
  }

  async function loadStreamQualityState() {
    if (!currentCameraId || !currentUseAnnotated) {
      currentStreamQualityPreset = "global";
      applyStreamQualityPreset("global");
      return;
    }
    try {
      const data = await request(
        API + "/cameras/" + currentCameraId + "/stream/quality"
      );
      currentStreamQualityPreset = (data && data.preset) || "global";
      if (streamMeta && data.effective_width && data.effective_height) {
        streamMeta.textContent =
          currentStreamName +
          " · " +
          data.effective_width +
          "×" +
          data.effective_height;
      }
      applyStreamQualityPreset(
        currentStreamQualityPreset,
        data.effective_width,
        data.effective_height
      );
    } catch (_) {
      applyStreamQualityPreset("global");
    }
  }

  async function setCameraStreamQuality(preset) {
    if (!currentCameraId || !currentUseAnnotated) return;
    const select = document.getElementById("stream-quality-select");
    if (select) select.disabled = true;
    try {
      const data = await request(
        API + "/cameras/" + currentCameraId + "/stream/quality",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ preset: preset || "global" }),
        }
      );
      currentStreamQualityPreset = (data && data.preset) || preset || "global";
      if (streamMeta && data.effective_width && data.effective_height) {
        streamMeta.textContent =
          currentStreamName +
          " · " +
          data.effective_width +
          "×" +
          data.effective_height;
      }
      isConnected = false;
      shouldReconnect = true;
      reconnectAttempt = 0;
      setTimeout(function () {
        connectStream();
      }, 800);
      applyStreamQualityPreset(
        currentStreamQualityPreset,
        data.effective_width,
        data.effective_height
      );
    } catch (err) {
      setStatus(err.message, true);
      if (select) select.value = currentStreamQualityPreset;
    } finally {
      if (select) select.disabled = false;
    }
  }

  function updatePackageDetectionBtn() {
    const btn = document.getElementById("package-detection-btn");
    if (!btn) return;
    const show = currentUseAnnotated && !!currentCameraId;
    btn.classList.toggle("hidden", !show);
    btn.classList.toggle("btn-primary", packageDetectionEnabled);
    btn.classList.toggle("btn-secondary", !packageDetectionEnabled);
    btn.textContent = packageDetectionEnabled
      ? t("packageDetectionOn")
      : t("packageDetectionOff");
  }

  function updateRodPoseBtn() {
    const btn = document.getElementById("rod-pose-btn");
    if (!btn) return;
    const show = currentUseAnnotated && !!currentCameraId;
    btn.classList.toggle("hidden", !show);
    btn.classList.toggle("btn-primary", rodPoseEnabled);
    btn.classList.toggle("btn-secondary", !rodPoseEnabled);
    btn.textContent = rodPoseEnabled ? t("rodPoseOn") : t("rodPoseOff");
  }

  async function loadPackageDetectionState() {
    if (!currentCameraId || !currentUseAnnotated) {
      packageDetectionEnabled = false;
      updatePackageDetectionBtn();
      return;
    }
    try {
      const data = await request(
        API + "/cameras/" + currentCameraId + "/package-detection"
      );
      packageDetectionEnabled = !!(data && data.package_detection_enabled);
    } catch (_) {
      packageDetectionEnabled = false;
    }
    updatePackageDetectionBtn();
    if (window.DF_onPackageDetectionChanged) window.DF_onPackageDetectionChanged();
  }

  async function loadRodPoseState() {
    if (!currentCameraId || !currentUseAnnotated) {
      rodPoseEnabled = false;
      updateRodPoseBtn();
      return;
    }
    try {
      const data = await request(
        API + "/cameras/" + currentCameraId + "/rod-pose"
      );
      rodPoseEnabled = !!(data && data.rod_pose_enabled);
    } catch (_) {
      rodPoseEnabled = false;
    }
    updateRodPoseBtn();
    if (window.DF_onRodPoseChanged) window.DF_onRodPoseChanged();
  }

  window.DF_getPackageDetectionEnabled = function () {
    return !!packageDetectionEnabled;
  };

  window.DF_getRodPoseEnabled = function () {
    return !!rodPoseEnabled;
  };

  window.DF_getSealerRoiAvailable = function () {
    return !!(currentUseAnnotated && currentCameraId);
  };

  window.DF_onPackageDetectionChanged = function () {
    if (window.DF_updateSealerRoiControls) window.DF_updateSealerRoiControls();
  };

  window.DF_onRodPoseChanged = function () {
    if (window.DF_updateSealerRoiControls) window.DF_updateSealerRoiControls();
  };

  async function setPackageDetection(enabled) {
    if (!currentCameraId || !currentUseAnnotated) return;
    const btn = document.getElementById("package-detection-btn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = t("packageDetectionHint");
    }
    try {
      const data = await request(
        API + "/cameras/" + currentCameraId + "/package-detection",
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enabled: !!enabled }),
        }
      );
      packageDetectionEnabled = !!(data && data.package_detection_enabled);
      isConnected = false;
      shouldReconnect = true;
      reconnectAttempt = 0;
      setTimeout(function () {
        connectStream();
      }, 800);
    } catch (err) {
      setStatus(err.message, true);
    } finally {
      if (btn) btn.disabled = false;
      updatePackageDetectionBtn();
      if (window.DF_onPackageDetectionChanged) window.DF_onPackageDetectionChanged();
    }
  }

  async function setRodPose(enabled) {
    if (!currentCameraId || !currentUseAnnotated) return;
    const btn = document.getElementById("rod-pose-btn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = t("rodPoseHint");
    }
    try {
      const data = await request(
        API + "/cameras/" + currentCameraId + "/rod-pose",
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enabled: !!enabled }),
        }
      );
      rodPoseEnabled = !!(data && data.rod_pose_enabled);
      isConnected = false;
      shouldReconnect = true;
      reconnectAttempt = 0;
      setTimeout(function () {
        connectStream();
      }, 800);
    } catch (err) {
      setStatus(err.message, true);
    } finally {
      if (btn) btn.disabled = false;
      updateRodPoseBtn();
      if (window.DF_onRodPoseChanged) window.DF_onRodPoseChanged();
    }
  }

  async function setStreamMaxQuality(enabled) {
    if (!currentCameraId || !currentUseAnnotated) return;
    try {
      const data = await request(
        API + "/cameras/" + currentCameraId + "/stream/quality",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ max_quality: !!enabled }),
        }
      );
      if (streamMeta && data.effective_width && data.effective_height) {
        streamMeta.textContent =
          currentStreamName +
          " · " +
          data.effective_width +
          "×" +
          data.effective_height;
      }
      applyStreamQualityPreset(
        currentStreamQualityPreset,
        data.effective_width,
        data.effective_height
      );
      isConnected = false;
      shouldReconnect = true;
      reconnectAttempt = 0;
      setTimeout(function () {
        connectStream();
      }, 600);
    } catch (err) {
      setStatus(err.message, true);
    }
  }

  function workerCountLabel(n) {
    const count = Math.max(0, Number(n) || 0);
    if (count === 0) return t("workersNone");
    const nAbs = count % 100;
    const n1 = nAbs % 10;
    let word = "работников";
    if (nAbs < 11 || nAbs > 19) {
      if (n1 === 1) word = "работник";
      else if (n1 >= 2 && n1 <= 4) word = "работника";
    }
    return "В кадре: " + count + " " + word;
  }

  function annotatedRtspUrl(cameraId) {
    return "rtsp://mediamtx:8554/annot_cam_" + cameraId;
  }

  async function refreshRecordingUi() {
    const btn = document.getElementById("rec-toggle-btn");
    if (!btn || !currentCameraId) return;
    try {
      const st = await request(API + "/recordings/" + currentCameraId + "/status");
      recordingActive = !!(st && st.recording);
    } catch (_) {}
    btn.textContent = recordingActive ? t("recOn") : t("recOff");
    btn.classList.toggle("btn-primary", recordingActive);
    btn.classList.toggle("btn-secondary", !recordingActive);
  }

  function setStatus(message, isError) {
    statusEl.textContent = message;
    statusEl.className = "global-status" + (isError ? " error" : "");
  }

  function setStreamState(text) {
    streamState.textContent = text;
  }

  function cameraIpDisplay(cam) {
    const raw = String(cam.ip || "").trim();
    if (!raw) return "—";
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(raw)) {
      try {
        return new URL(raw).hostname || raw;
      } catch (_) {}
    }
    const hostPart = raw.split("/")[0];
    const atIdx = hostPart.lastIndexOf("@");
    if (atIdx >= 0) return hostPart.slice(atIdx + 1).split(":")[0] || raw;
    return hostPart.split(":")[0] || raw;
  }

  function wsBaseViaNginx() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return proto + "://" + window.location.host + "/go2rtc/api/ws";
  }

  function wsBaseDirect() {
    return "ws://" + (window.location.hostname || "localhost") + ":1985/api/ws";
  }

  function stopStallWatch() {
    if (stallTimer) {
      clearInterval(stallTimer);
      stallTimer = null;
    }
    stallLastTime = 0;
    stallTicks = 0;
  }

  function startStallWatch() {
    stopStallWatch();
    stallLastTime = streamVideo ? streamVideo.currentTime || 0 : 0;
    stallTicks = 0;
    stallTimer = setInterval(function () {
      if (!streamVideo || !shouldReconnect || !currentStreamName) return;
      if (streamVideo.paused) return;
      const t = streamVideo.currentTime || 0;
      if (t > stallLastTime + 0.04) {
        stallLastTime = t;
        stallTicks = 0;
        return;
      }
      stallTicks += 1;
      if (stallTicks < 8) return;
      console.warn("[stream] stalled, reconnecting", currentStreamName);
      stallTicks = 0;
      isConnected = false;
      setStreamState("connecting");
      connectStream();
    }, 1000);
  }

  function cleanupMse() {
    if (mseMediaSource) {
      try {
        if (mseMediaSource.readyState === "open") {
          const buffers = mseMediaSource.sourceBuffers;
          for (let i = buffers.length - 1; i >= 0; i--) {
            try {
              mseMediaSource.removeSourceBuffer(buffers[i]);
            } catch (_) {}
          }
        }
      } catch (_) {}
      mseMediaSource = null;
    }
    if (mseObjectUrl) {
      try {
        URL.revokeObjectURL(mseObjectUrl);
      } catch (_) {}
      mseObjectUrl = null;
    }
  }

  function cleanupPeer(keepVideo) {
    stopStallWatch();
    cleanupMse();
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

  function mseCodecs() {
    const list = [
      "avc1.640029",
      "avc1.64002A",
      "avc1.640033",
      "avc1.42E01E",
      "avc1.4D401F",
    ];
    if (typeof MediaSource === "undefined" || !MediaSource.isTypeSupported) {
      return list.join();
    }
    return list
      .filter(function (codec) {
        return MediaSource.isTypeSupported('video/mp4; codecs="' + codec + '"');
      })
      .join();
  }

  function connectStream() {
    if (typeof MediaSource !== "undefined") {
      connectMse();
      return;
    }
    connectMp4();
  }

  function connectMse() {
    if (!currentStreamName || !streamVideo) return;
    cleanupPeer(true);
    shouldReconnect = true;
    setStreamState("connecting");

    const wsUrl =
      (useDirectGo2rtc ? wsBaseDirect() : wsBaseViaNginx()) +
      "?src=" +
      encodeURIComponent(currentStreamName);

    const mse = new MediaSource();
    mseMediaSource = mse;
    mseObjectUrl = URL.createObjectURL(mse);
    streamVideo.srcObject = null;
    streamVideo.src = mseObjectUrl;
    streamVideo.muted = true;
    streamVideo.playsInline = true;
    streamVideo.playbackRate = 1;

    let sourceBuffer = null;
    let queue = [];
    let mseRequested = false;

    function requestMse() {
      if (mseRequested || !ws || ws.readyState !== WebSocket.OPEN) return;
      if (mse.readyState !== "open") return;
      mseRequested = true;
      try {
        URL.revokeObjectURL(mseObjectUrl);
      } catch (_) {}
      ws.send(JSON.stringify({ type: "mse", value: mseCodecs() }));
    }

    function appendPending() {
      if (!sourceBuffer || sourceBuffer.updating || queue.length === 0) return;
      try {
        sourceBuffer.appendBuffer(queue.shift());
      } catch (err) {
        console.warn("[MSE] append", err);
      }
    }

    function trimPlayed() {
      if (!sourceBuffer || sourceBuffer.updating || queue.length || !sourceBuffer.buffered.length) {
        return;
      }
      try {
        const start0 = sourceBuffer.buffered.start(0);
        const end = sourceBuffer.buffered.end(sourceBuffer.buffered.length - 1);
        const removeUntil = Math.min(streamVideo.currentTime - 0.5, end - 2);
        if (removeUntil > start0 + 0.8) {
          sourceBuffer.remove(start0, removeUntil);
        }
      } catch (_) {}
    }

    mse.addEventListener("sourceopen", requestMse, { once: true });

    try {
      ws = new WebSocket(wsUrl);
    } catch (err) {
      connectMp4();
      return;
    }
    ws.binaryType = "arraybuffer";
    ws.onopen = requestMse;
    ws.onmessage = function (event) {
      if (typeof event.data === "string") {
        let msg;
        try {
          msg = JSON.parse(event.data);
        } catch (_) {
          return;
        }
        if (msg.type === "error") {
          console.warn("[MSE] go2rtc", msg.value);
          if (ws) ws.onclose = null;
          if (!useDirectGo2rtc) {
            useDirectGo2rtc = true;
            connectMse();
          } else {
            connectMp4();
          }
          return;
        }
        if (msg.type !== "mse" || sourceBuffer || mse.readyState !== "open") return;
        try {
          sourceBuffer = mse.addSourceBuffer(msg.value);
          sourceBuffer.mode = "segments";
          sourceBuffer.addEventListener("updateend", function () {
            if (queue.length) appendPending();
            else trimPlayed();
          });
        } catch (err) {
          console.warn("[MSE] sourceBuffer", err);
          if (ws) ws.onclose = null;
          connectMp4();
          return;
        }
        isConnected = true;
        reconnectAttempt = 0;
        setStreamState("connected");
        setStatus(t("connecting", { name: currentStreamName }));
        streamVideo.play().catch(function (playErr) {
          console.warn("[MSE] play blocked", playErr);
          setStatus(t("autoplayBlocked"), true);
        });
        if (window.DF_onStreamVideoReady) window.DF_onStreamVideoReady();
        return;
      }
      if (!sourceBuffer) return;
      if (sourceBuffer.updating || queue.length) {
        queue.push(event.data);
        return;
      }
      try {
        sourceBuffer.appendBuffer(event.data);
      } catch (err) {
        queue.push(event.data);
        console.warn("[MSE] appendBuffer", err);
      }
    };
    ws.onerror = function () {
      if (!useDirectGo2rtc) useDirectGo2rtc = true;
    };
    ws.onclose = function () {
      if (!shouldReconnect) return;
      isConnected = false;
      setStreamState("connecting");
      scheduleReconnect();
    };
  }

  /** Fallback: HTTP fMP4. Не seek — на live stream.mp4 это даёт чёрный экран и скачки. */
  function connectMp4() {
    if (!currentStreamName || !streamVideo) return;
    cleanupPeer(true);
    shouldReconnect = true;
    setStreamState("connecting");
    const url =
      window.location.origin +
      "/go2rtc/api/stream.mp4?src=" +
      encodeURIComponent(currentStreamName);
    streamVideo.srcObject = null;
    streamVideo.src = url;
    streamVideo.muted = true;
    streamVideo.playsInline = true;
    streamVideo.playbackRate = 1;
    streamVideo.onloadeddata = function () {
      isConnected = true;
      reconnectAttempt = 0;
      setStreamState("connected");
      setStatus(t("connecting", { name: currentStreamName }));
      startStallWatch();
      if (window.DF_onStreamVideoReady) window.DF_onStreamVideoReady();
    };
    streamVideo.onerror = function () {
      isConnected = false;
      stopStallWatch();
      setStreamState("error");
      scheduleReconnect();
    };
    streamVideo
      .play()
      .then(function () {
        isConnected = true;
        setStreamState("connected");
        startStallWatch();
        if (window.DF_onStreamVideoReady) window.DF_onStreamVideoReady();
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
      connectStream();
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

  function openDepartmentModal(dept) {
    if (!departmentModal) return;
    editingDepartmentId = dept && dept.id ? dept.id : null;
    if (departmentForm) departmentForm.reset();
    const idInput = document.getElementById("department-edit-id");
    if (idInput) idInput.value = editingDepartmentId ? String(editingDepartmentId) : "";
    if (departmentFormTitle) {
      departmentFormTitle.textContent = editingDepartmentId
        ? t("editDepartment") + (dept && dept.name ? ": " + dept.name : "")
        : t("addDepartment");
    }
    const nameInput = document.getElementById("department-name");
    if (nameInput) nameInput.value = dept && dept.name ? dept.name : "";
    if (departmentFormMsg) departmentFormMsg.textContent = "";
    departmentModal.classList.remove("hidden");
    departmentModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    if (nameInput) setTimeout(function () { nameInput.focus(); }, 50);
  }

  function closeDepartmentModal() {
    if (!departmentModal) return;
    editingDepartmentId = null;
    departmentModal.classList.add("hidden");
    departmentModal.setAttribute("aria-hidden", "true");
    if (!cameraModal || cameraModal.classList.contains("hidden")) {
      if (!streamModal || streamModal.classList.contains("hidden")) {
        document.body.style.overflow = "";
      }
    }
  }

  async function loadDepartmentsForSelect(selectedId) {
    if (!cameraDepartmentSelect) return;
    try {
      const data = await request(API + "/departments");
      departmentsCache = data.items || [];
    } catch (_) {
      departmentsCache = [];
    }
    cameraDepartmentSelect.innerHTML = "";
    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = t("noDepartment");
    cameraDepartmentSelect.appendChild(opt0);
    departmentsCache.forEach(function (dept) {
      const opt = document.createElement("option");
      opt.value = String(dept.id);
      opt.textContent = dept.name;
      cameraDepartmentSelect.appendChild(opt);
    });
    if (selectedId) cameraDepartmentSelect.value = String(selectedId);
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

  async function fillCameraForm(cam) {
    setCameraFormMode(cam.id);
    form.name.value = cam.name;
    form.ip.value = cam.ip;
    form.port.value = cam.port;
    form.protocol.value = cam.protocol || "rtsp";
    form.username.value = cam.username || "";
    form.password.value = "";
    form.path.value = cam.path;
    form.enabled.checked = !!cam.enabled;
    form.inference_interval.value = cam.inference_interval || "";
    const qualitySelect = document.getElementById("camera-stream-quality");
    if (qualitySelect) qualitySelect.value = cameraQualityPreset(cam);
    if (cameraDepartmentSelect) {
      cameraDepartmentSelect.value = cam.department_id ? String(cam.department_id) : "";
    }
    if (cameraFormMsg) cameraFormMsg.textContent = "";
    openCameraModal();
    try {
      await Promise.all([
        loadDepartmentsForSelect(cam.department_id || null),
        window.DF_models
          ? window.DF_models.populateCameraModelSelect(cam.id)
          : Promise.resolve(),
      ]);
      if (cameraDepartmentSelect) {
        cameraDepartmentSelect.value = cam.department_id ? String(cam.department_id) : "";
      }
    } catch (err) {
      if (cameraFormMsg) cameraFormMsg.textContent = err.message || String(err);
    }
  }

  function resetCameraForm() {
    if (!form) return;
    form.reset();
    form.port.value = "554";
    form.path.value = "/Streaming/Channels/101";
    form.enabled.checked = true;
    form.inference_interval.value = "";
    const qualitySelect = document.getElementById("camera-stream-quality");
    if (qualitySelect) qualitySelect.value = "global";
    const modelSelect = document.getElementById("camera-models");
    if (modelSelect) modelSelect.innerHTML = "";
    setCameraFormMode(null);
    if (cameraFormMsg) cameraFormMsg.textContent = "";
  }

  function mkBtn(cls, label, attrs) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = cls;
    b.textContent = label;
    Object.keys(attrs || {}).forEach(function (k) {
      b.setAttribute(k, attrs[k]);
    });
    return b;
  }

  function buildCameraDeptSelect(cam) {
    const sel = document.createElement("select");
    sel.className = "cam-dept-select form-select";
    sel.title = t("department");
    const optNone = document.createElement("option");
    optNone.value = "";
    optNone.textContent = t("noDepartment");
    sel.appendChild(optNone);
    departmentsCache.forEach(function (dept) {
      const opt = document.createElement("option");
      opt.value = String(dept.id);
      opt.textContent = dept.name;
      sel.appendChild(opt);
    });
    sel.value = cam.department_id ? String(cam.department_id) : "";
    sel.addEventListener("change", async function () {
      const prevId = cam.department_id != null ? cam.department_id : null;
      const newDept = sel.value ? Number(sel.value) : null;
      if (newDept === prevId) return;
      sel.disabled = true;
      try {
        await request(API + "/cameras/" + cam.id, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ department_id: newDept }),
        });
        cam.department_id = newDept;
        setStatus(t("cameraDepartmentUpdated"));
        await loadCameras();
      } catch (err) {
        sel.value = prevId != null ? String(prevId) : "";
        setStatus(err.message, true);
      } finally {
        sel.disabled = false;
      }
    });
    return sel;
  }

  function zonesForCamera(cam) {
    const list =
      (window.DF_zoneIndex && window.DF_zoneIndex[String(cam.department_id)]) || [];
    return list.filter(function (zone) {
      return Number(zone.camera_id) === Number(cam.id);
    });
  }

  function buildCameraRow(cam, streamById) {
    const st = streamById[String(cam.id)];
    let detCell = "—";
    if (st && st.stream_running) {
      const wc =
        st.workers_count != null ? st.workers_count : st.faces_count;
      detCell = workerCountLabel(wc);
    } else if (cam.enabled) {
      detCell = t("detOff");
    }
    const tr = document.createElement("tr");
    tr.className = "camera-row";
    const tdId = document.createElement("td");
    tdId.textContent = cam.id;
    const tdName = document.createElement("td");
    const nameWrap = document.createElement("span");
    nameWrap.className = "cam-name";
    const dot = document.createElement("i");
    const live = st && st.stream_running;
    dot.className = "cam-status" + (live ? " on" : cam.enabled ? " idle" : "");
    dot.title = live ? t("detOn") : cam.enabled ? t("detOff") : t("no");
    nameWrap.append(dot, document.createTextNode(cam.name));
    tdName.className = "cam-cell-name";
    tdName.appendChild(nameWrap);
    const zoneLine = document.createElement("div");
    zoneLine.className = "cam-zones";
    const camZones = zonesForCamera(cam);
    zoneLine.textContent = camZones.length
      ? camZones.map(function (zone) { return zone.name; }).join(" · ")
      : "Нет рабочих зон";
    tdName.appendChild(zoneLine);
    const tdIp = document.createElement("td");
    tdIp.textContent = cameraIpDisplay(cam);
    const tdEn = document.createElement("td");
    tdEn.textContent = cam.enabled ? t("yes") : t("no");
    const tdDet = document.createElement("td");
    tdDet.textContent = detCell;
    const tdDept = document.createElement("td");
    tdDept.className = "col-department";
    tdDept.appendChild(buildCameraDeptSelect(cam));
    const tdAct = document.createElement("td");
    tdAct.className = "actions";
    tdAct.append(
      mkBtn("watch-annot-btn btn btn-primary", t("watchDetection"), {
        "data-id": String(cam.id),
        "data-name": cam.name,
      }),
      mkBtn("watch-btn btn btn-secondary", t("watchRaw"), {
        "data-id": String(cam.id),
        "data-name": cam.name,
      }),
      mkBtn("edit-btn btn btn-secondary", t("editCamera"), {
        "data-id": String(cam.id),
      }),
      mkBtn("delete-btn btn btn-danger", t("delete"), {
        "data-id": String(cam.id),
      })
    );
    tr.append(tdId, tdName, tdIp, tdEn, tdDet, tdDept, tdAct);
    return tr;
  }

  function isDeptExpanded(deptKey) {
    return !collapsedDepts.has(deptKey);
  }

  function toggleDeptGroup(deptKey) {
    if (collapsedDepts.has(deptKey)) collapsedDepts.delete(deptKey);
    else collapsedDepts.add(deptKey);
    const expanded = isDeptExpanded(deptKey);
    document.querySelectorAll('.camera-row[data-dept-key="' + deptKey + '"]').forEach(function (row) {
      row.classList.toggle("hidden", !expanded);
    });
    const toggle = document.querySelector('.dept-toggle[data-dept-key="' + deptKey + '"]');
    if (toggle) {
      toggle.textContent = expanded ? "▼" : "▶";
      toggle.classList.toggle("expanded", expanded);
    }
  }

  function appendDeptGroup(tableEl, deptKey, title, cameras, streamById, deptId) {
    const filtered = true;
    const expanded = filtered || isDeptExpanded(deptKey);
    const header = document.createElement("tr");
    header.className = "dept-header-row";
    const td = document.createElement("td");
    td.colSpan = 7;
    const wrap = document.createElement("div");
    wrap.className = "dept-header-cell";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "dept-toggle" + (expanded ? " expanded" : "");
    toggle.dataset.deptKey = deptKey;
    toggle.textContent = expanded ? "▼" : "▶";
    toggle.addEventListener("click", function () {
      toggleDeptGroup(deptKey);
    });
    const titleEl = document.createElement("strong");
    titleEl.className = "dept-title";
    titleEl.textContent = title;
    const countEl = document.createElement("span");
    countEl.className = "dept-count help-text";
    countEl.textContent = " (" + t("camerasCount", { n: cameras.length }) + ")";
    if (!filtered) wrap.append(toggle);
    wrap.append(titleEl, countEl);
    if (deptId) {
      const editBtn = mkBtn("dept-edit-btn btn btn-secondary", t("editDepartment"), {
        "data-dept-id": String(deptId),
        "data-dept-name": title,
      });
      editBtn.addEventListener("click", function () {
        openDepartmentModal({ id: deptId, name: title });
      });
      const delBtn = mkBtn("dept-delete-btn btn btn-danger", t("delete"), {
        "data-dept-id": String(deptId),
        "data-dept-name": title,
      });
      wrap.append(editBtn, delBtn);
    }
    td.appendChild(wrap);
    header.appendChild(td);
    tableEl.appendChild(header);
    cameras.forEach(function (cam) {
      const row = buildCameraRow(cam, streamById);
      row.dataset.deptKey = deptKey;
      if (!expanded) row.classList.add("hidden");
      tableEl.appendChild(row);
    });
  }

  function camerasByDepartment() {
    const byDept = {};
    const noDept = [];
    camerasListCache.forEach(function (cam) {
      if (cam.department_id) {
        const key = String(cam.department_id);
        if (!byDept[key]) byDept[key] = [];
        byDept[key].push(cam);
      } else {
        noDept.push(cam);
      }
    });
    return { byDept: byDept, noDept: noDept };
  }

  function ensureCamerasDept() {
    const grouped = camerasByDepartment();
    if (camerasDeptFilter === "none" && grouped.noDept.length > 0) return;
    if (departmentsCache.some(function (dept) {
      return String(dept.id) === camerasDeptFilter;
    })) return;
    if (grouped.noDept.length > 0) {
      camerasDeptFilter = "none";
      return;
    }
    camerasDeptFilter = departmentsCache.length ? String(departmentsCache[0].id) : "";
  }

  function renderCamerasDeptNav() {
    const nav = document.getElementById("cameras-dept-nav");
    if (!nav || !window.DF_fillDeptNav) return;
    ensureCamerasDept();
    const grouped = camerasByDepartment();
    const items = departmentsCache.map(function (dept) {
      const cameras = grouped.byDept[String(dept.id)] || [];
      return {
        id: String(dept.id),
        name: dept.name,
        count: t("camerasCount", { n: cameras.length }),
        emptyText: t("statsNoCamerasInDept"),
        zones: cameras.map(function (cam) {
          return { name: cam.name };
        }),
      };
    });
    if (grouped.noDept.length > 0) {
      items.unshift({
        id: "none",
        name: t("noDepartment"),
        count: t("camerasCount", { n: grouped.noDept.length }),
        emptyText: t("statsNoCamerasInDept"),
        zones: grouped.noDept.map(function (cam) {
          return { name: cam.name };
        }),
      });
    }
    window.DF_fillDeptNav(nav, items, camerasDeptFilter, function (id) {
      camerasDeptFilter = id;
      renderCamerasDeptNav();
    });
    renderCamerasTable();
  }

  function renderCamerasTable() {
    ensureCamerasDept();
    const title = document.getElementById("cameras-title");
    const grouped = camerasByDepartment();
    const dept = departmentsCache.find(function (item) {
      return String(item.id) === camerasDeptFilter;
    });
    if (title) {
      title.textContent =
        camerasDeptFilter === "none"
          ? t("noDepartment")
          : dept
            ? dept.name
            : t("cameras");
    }
    table.innerHTML = "";
    if (camerasDeptFilter === "none") {
      appendDeptGroup(
        table,
        "none",
        t("noDepartment"),
        grouped.noDept,
        streamByIdCache,
        null
      );
      if (!table.querySelector(".camera-row")) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 7;
        td.className = "help-text";
        td.textContent = t("statsNoCamerasInDept");
        tr.appendChild(td);
        table.appendChild(tr);
      }
      return;
    }
    if (!dept) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 7;
      td.className = "help-text";
      td.textContent = grouped.noDept.length ? t("noDepartment") : t("addDepartment");
      tr.appendChild(td);
      table.appendChild(tr);
      return;
    }
    appendDeptGroup(
      table,
      "d" + dept.id,
      dept.name,
      grouped.byDept[String(dept.id)] || [],
      streamByIdCache,
      dept.id
    );
    if (!table.querySelector(".camera-row")) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 7;
      td.className = "help-text";
      td.textContent = t("statsNoCamerasInDept");
      tr.appendChild(td);
      table.appendChild(tr);
    }
  }

  async function loadCameras() {
    const data = await request(API + "/cameras");
    const deptData = await request(API + "/departments").catch(function () {
      return { items: [] };
    });
    departmentsCache = deptData.items || [];
    const streams = await request(API + "/streams/status").catch(function () {
      return { items: [] };
    });
    streamByIdCache = {};
    (streams.items || []).forEach(function (s) {
      streamByIdCache[String(s.camera_id)] = s;
    });
    camerasListCache = data.items || [];
    ensureCamerasDept();
    renderCamerasDeptNav();
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
    currentStreamQualityPreset = "global";
    updateMaxQualityBtn();
    loadPackageDetectionState();
    loadRodPoseState();
    loadStreamQualityState();
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

  async function ensureAnnotatedStream(cameraId) {
    if (!currentUseAnnotated) return;
    try {
      await request(API + "/cameras/" + cameraId + "/stream/start", { method: "POST" });
    } catch (err) {
      setStatus(err.message, true);
      throw err;
    }
  }

  function openStream(cameraId, cameraName, useAnnotated) {
    currentStreamName = useAnnotated ? "cam" + cameraId + "_annot" : "cam" + cameraId;
    currentCameraId = String(cameraId);
    currentCameraName = cameraName || "";
    currentUseAnnotated = !!useAnnotated;
    useDirectGo2rtc = false;
    reconnectAttempt = 0;
    shouldReconnect = true;
    isConnected = false;
    openStreamModal(cameraName, useAnnotated);
    if (streamMeta) streamMeta.textContent = currentStreamName;
    if (window.DF_setStreamCameraId) window.DF_setStreamCameraId(String(cameraId));
    setStreamState("connecting");
    setStatus(t("connecting", { name: currentStreamName }));
    const startView = function () {
      connectStream();
      refreshRecordingUi().catch(function () {});
    };
    if (useAnnotated) {
      ensureAnnotatedStream(cameraId)
        .then(function () {
          setTimeout(function () {
            startView();
            if (window.DF_syncStreamQuality) window.DF_syncStreamQuality(cameraId);
          }, 400);
        })
        .catch(function () {
          scheduleReconnect();
        });
    } else {
      startView();
    }
  }

  async function syncStreamQualityFromStatus(cameraId) {
    try {
      const data = await request(API + "/cameras/" + cameraId + "/stream/quality");
      if (!data) return;
      currentStreamQualityPreset = data.preset || "global";
      if (streamMeta && data.effective_width && data.effective_height) {
        streamMeta.textContent =
          currentStreamName +
          " · " +
          data.effective_width +
          "×" +
          data.effective_height;
      }
      applyStreamQualityPreset(
        currentStreamQualityPreset,
        data.effective_width,
        data.effective_height
      );
    } catch (_) {}
  }

  window.DF_syncStreamQuality = syncStreamQualityFromStatus;

  function closeStream() {
    cleanupPeer(false);
    if (window.DF_setStreamCameraId) window.DF_setStreamCameraId(null);
    currentStreamName = "";
    currentCameraId = null;
    currentCameraName = "";
    currentUseAnnotated = false;
    currentStreamQualityPreset = "global";
    updateMaxQualityBtn();
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
      if (tab === "recordings" && window.DF_initRecordings) window.DF_initRecordings();
      if (tab === "stats" && window.DF_initStats) window.DF_initStats();
      if (tab === "settings" && window.DF_initSettings) window.DF_initSettings(setStatus);
      if (tab === "cameras") loadCameras().catch(function () {});
      if (tab === "dashboard" && window.DF_loadDashboard) window.DF_loadDashboard();
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
    addCameraBtn.addEventListener("click", async function () {
      resetCameraForm();
      const selectedDept = camerasDeptFilter || null;
      await Promise.all([
        loadDepartmentsForSelect(selectedDept),
        window.DF_models
          ? window.DF_models.populateCameraModelSelect(null)
          : Promise.resolve(),
      ]);
      openCameraModal();
    });
  }
  if (addDepartmentBtn) {
    addDepartmentBtn.addEventListener("click", function () {
      openDepartmentModal();
    });
  }
  if (departmentCancelBtn) departmentCancelBtn.addEventListener("click", closeDepartmentModal);
  if (departmentModalClose) departmentModalClose.addEventListener("click", closeDepartmentModal);
  if (departmentModalBackdrop) {
    departmentModalBackdrop.addEventListener("click", closeDepartmentModal);
  }
  if (departmentForm) {
    departmentForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      const name = String(new FormData(departmentForm).get("name") || "").trim();
      if (!name) return;
      if (departmentFormMsg) departmentFormMsg.textContent = t("saving");
      try {
        if (editingDepartmentId) {
          await request(API + "/departments/" + editingDepartmentId, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name }),
          });
          setStatus(t("departmentUpdated"));
        } else {
          await request(API + "/departments", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name }),
          });
          setStatus(t("departmentSaved"));
        }
        closeDepartmentModal();
        await loadCameras();
      } catch (err) {
        if (departmentFormMsg) departmentFormMsg.textContent = err.message;
        setStatus(err.message, true);
      }
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
      return;
    }
    if (departmentModal && !departmentModal.classList.contains("hidden")) {
      closeDepartmentModal();
    }
  });

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    if (cameraSubmitBtn) cameraSubmitBtn.disabled = true;
    if (cameraFormMsg) cameraFormMsg.textContent = t("saving");
    try {
      if (!cameraFormController) throw new Error("Camera form module is not loaded");
      await cameraFormController.save(editingCameraId);
      setStatus(editingCameraId ? t("cameraUpdated") : t("cameraSaved"));
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
    const deptDelBtn = e.target.closest(".dept-delete-btn");
    if (deptDelBtn) {
      const deptId = deptDelBtn.getAttribute("data-dept-id");
      const deptName = deptDelBtn.getAttribute("data-dept-name") || "";
      if (!confirm(t("confirmDeleteDepartment", { name: deptName }))) return;
      try {
        await request(API + "/departments/" + deptId, { method: "DELETE" });
        setStatus(t("departmentDeleted"));
        collapsedDepts.delete("d" + deptId);
        await loadCameras();
      } catch (err) {
        setStatus(err.message, true);
      }
      return;
    }
    const editBtn = e.target.closest(".edit-btn");
    if (editBtn) {
      const id = editBtn.getAttribute("data-id");
      const cached = camerasListCache.find(function (cam) {
        return String(cam.id) === String(id);
      });
      if (cached) {
        fillCameraForm(cached).catch(function (err) {
          setStatus(err.message, true);
        });
        return;
      }
      request(API + "/cameras/" + id)
        .then(function (cam) {
          return fillCameraForm(cam);
        })
        .catch(function (err) {
          setStatus(err.message, true);
        });
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

  const streamQualitySelect = document.getElementById("stream-quality-select");
  if (streamQualitySelect) {
    streamQualitySelect.addEventListener("change", function () {
      setCameraStreamQuality(streamQualitySelect.value);
    });
  }

  const packageDetectionBtn = document.getElementById("package-detection-btn");
  if (packageDetectionBtn) {
    packageDetectionBtn.addEventListener("click", function () {
      setPackageDetection(!packageDetectionEnabled);
    });
  }

  const rodPoseBtn = document.getElementById("rod-pose-btn");
  if (rodPoseBtn) {
    rodPoseBtn.addEventListener("click", function () {
      setRodPose(!rodPoseEnabled);
    });
  }

  const recToggleBtn = document.getElementById("rec-toggle-btn");
  if (recToggleBtn) {
    recToggleBtn.addEventListener("click", async function () {
      if (!currentCameraId) {
        setStatus(t("roiNeedStream"), true);
        return;
      }
      if (!currentUseAnnotated && !recordingActive) {
        setStatus(t("recNeedDetection"), true);
        return;
      }
      recToggleBtn.disabled = true;
      try {
        if (!recordingActive) {
          let recW = 1280;
          let recH = 720;
          try {
            const recSettings = await request(API + "/settings/recording");
            recW = Number(recSettings.record_width) || 1280;
            recH = Number(recSettings.record_height) || 720;
          } catch (_) {}
          if (recW >= 2560 || recH >= 1440) {
            await setStreamMaxQuality(true);
          }
          const rtsp = annotatedRtspUrl(currentCameraId);
          const res = await request(
            API +
              "/recordings/" +
              currentCameraId +
              "/start?camera_name=" +
              encodeURIComponent(currentCameraName) +
              "&rtsp_url=" +
              encodeURIComponent(rtsp) +
              "&manual=true",
            { method: "POST" }
          );
          if (!res || !res.recording) {
            const errKey =
              res && res.error === "recording_disabled"
                ? "recErrDisabled"
                : res && res.error === "outside_shift"
                  ? "recErrShift"
                  : "recErrStart";
            setStatus(t(errKey), true);
            recordingActive = false;
          } else {
            recordingActive = true;
            setStatus(t("recOn"), false);
          }
        } else {
          await request(API + "/recordings/" + currentCameraId + "/stop", { method: "POST" });
          recordingActive = false;
          setStatus(t("recOff"), false);
        }
      } catch (err) {
        setStatus(err.message, true);
      } finally {
        recToggleBtn.disabled = false;
        refreshRecordingUi().catch(function () {});
      }
    });
  }

  window.DF_onEnrollSuccess = function () {
    fetch(API + "/faces/reload-embeddings", { method: "POST" }).catch(function () {});
    loadCameras().catch(function () {});
  };

  if (window.DF_I18N) window.DF_I18N.applyI18n();
  if (window.DF_initRoi) window.DF_initRoi();
  setInterval(function () {
    if (document.getElementById("tab-cameras").classList.contains("active")) {
      loadCameras().catch(function () {});
    }
  }, 5000);
})();

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

  window.DF_initRecordings = function () {
    const tab = document.getElementById("tab-recordings");
    if (!tab || tab.dataset.recReady === "1") return;
    tab.dataset.recReady = "1";

    const deptSelect = document.getElementById("rec-department-select");
    const camSelect = document.getElementById("rec-camera-select");
    const dateSelect = document.getElementById("rec-date-select");
    const list = document.getElementById("rec-file-list");
    const dayTimelineEl = document.getElementById("rec-day-timeline");
    const video = document.getElementById("rec-video");
    const title = document.getElementById("rec-player-title");
    const prevBtn = document.getElementById("rec-prev-btn");
    const nextBtn = document.getElementById("rec-next-btn");
    const progress = document.getElementById("rec-progress");
    const timeDisplay = document.getElementById("rec-time-display");
    const playBtn = document.getElementById("rec-play-btn");

    let currentFiles = [];
    let currentIndex = -1;
    let dayTimeline = null;
    let allCameras = [];
    let seeking = false;

    if (!deptSelect || !camSelect || !dateSelect || !list) return;

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
      if (!window.DF_fillDeptNav) return;
      const items = Array.from(deptSelect.options)
        .filter(function (opt) { return opt.value; })
        .map(function (opt) {
          return {
            id: opt.value,
            name: opt.dataset.name || opt.textContent,
            count: opt.dataset.count || "",
          };
        });
      window.DF_attachZones(items, function (withZones) {
        window.DF_fillDeptNav(
          document.getElementById("rec-dept-nav"),
          withZones,
          deptSelect.value,
          function (id) {
            if (deptSelect.value === id) return;
            deptSelect.value = id;
            bindDeptNav();
            deptSelect.dispatchEvent(new Event("change"));
          }
        );
      });
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

    function resetPlayerUi() {
      if (progress) {
        progress.value = "0";
        progress.max = "0";
        progress.disabled = true;
      }
      updateRecTime(0);
      updatePlayBtn();
    }

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
        if (!seeking && progress) {
          progress.value = String(video.currentTime || 0);
        }
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
        const tsec = parseFloat(progress.value) || 0;
        video.currentTime = tsec;
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

    async function loadDates() {
      const camId = camSelect.value;
      const camName = selectedCamName();
      if (!camId || !camName) {
        dateSelect.disabled = true;
        dateSelect.innerHTML = "<option value=\"\">" + t("selectDate") + "</option>";
        list.innerHTML = "<p class=\"help-text\">" + t("recSelectHint") + "</p>";
        return;
      }
      const dates = await request(API + "/recordings/" + camId + "/" + encodeURIComponent(camName) + "/dates");
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
        const playBtn = document.createElement("button");
        playBtn.type = "button";
        playBtn.className = "btn btn-primary";
        playBtn.textContent = t("play");
        playBtn.addEventListener("click", function () {
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
        right.appendChild(playBtn);
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
                clipTl = window.DF_filterTimeline(
                  dayTimeline,
                  file.start_ts,
                  file.end_ts
                );
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

    function updateNavButtons() {
      if (prevBtn) prevBtn.disabled = currentIndex <= 0;
      if (nextBtn) nextBtn.disabled = currentIndex < 0 || currentIndex >= currentFiles.length - 1;
    }

    function openAtIndex(idx) {
      if (!video) return;
      const camId = camSelect.value;
      const camName = selectedCamName();
      const date = dateSelect.value;
      if (!camId || !camName || !date) return;
      if (!Array.isArray(currentFiles) || !currentFiles.length) return;
      if (idx < 0 || idx >= currentFiles.length) return;

      currentIndex = idx;
      const f = currentFiles[currentIndex];
      const url =
        API +
        "/recordings/" +
        camId +
        "/" +
        encodeURIComponent(camName) +
        "/" +
        encodeURIComponent(date) +
        "/" +
        encodeURIComponent(f.filename) +
        "/file";
      if (title) title.textContent = camName + " · " + date + " · " + f.filename;
      resetPlayerUi();
      video.playbackRate = 1;
      video.src = url;
      video.load();
      openModal();
      video.play().catch(function () {});
      updateNavButtons();
    }

    deptSelect.onchange = function () {
      populateCameraSelect(null);
      dateSelect.disabled = true;
      dateSelect.innerHTML = "<option value=\"\">" + t("selectDate") + "</option>";
      list.innerHTML = "<p class=\"help-text\">" + t("recSelectHint") + "</p>";
      if (dayTimelineEl) {
        dayTimelineEl.innerHTML = "<p class=\"help-text\">" + t("recTimelineDayHint") + "</p>";
      }
      dayTimeline = null;
    };

    camSelect.onchange = function () {
      loadDates().then(loadFiles).catch(function (e) {
        list.innerHTML = "<p class=\"help-text\">" + e.message + "</p>";
      });
    };
    dateSelect.onchange = function () {
      loadFiles().catch(function (e) {
        list.innerHTML = "<p class=\"help-text\">" + e.message + "</p>";
      });
    };

    const closeBtn = document.getElementById("rec-player-modal-close");
    const back = document.getElementById("rec-player-modal-backdrop");
    function closeRecModal() {
      if (video) {
        video.pause();
        video.removeAttribute("src");
        video.load();
      }
      resetPlayerUi();
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
        if (currentIndex > 0) openAtIndex(currentIndex - 1);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        if (currentIndex >= 0 && currentIndex < currentFiles.length - 1) {
          openAtIndex(currentIndex + 1);
        }
      });
    }

    loadDepartments().catch(function (e) {
      list.innerHTML = "<p class=\"help-text\">" + e.message + "</p>";
    });
  };
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
