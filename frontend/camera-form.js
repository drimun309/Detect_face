/** Isolated camera creation/update controller. */
(function (global) {
  "use strict";

  class CameraFormController {
    constructor(apiBase, form) {
      this.apiBase = apiBase;
      this.form = form;
    }

    payloadFromForm() {
      const data = new FormData(this.form);
      const department = data.get("department_id");
      const quality = String(data.get("stream_quality") || "global");
      const payload = {
        name: String(data.get("name") || "").trim(),
        ip: String(data.get("ip") || "").trim(),
        port: Number(data.get("port") || 554),
        protocol: data.get("protocol") || "rtsp",
        username: data.get("username") ? String(data.get("username")) : null,
        password: data.get("password") ? String(data.get("password")) : null,
        path: String(data.get("path") || "/Streaming/Channels/101").trim(),
        enabled: data.get("enabled") === "on",
        department_id: department ? Number(department) : null,
        stream_width: null,
        stream_height: null,
      };
      if (quality.indexOf("x") > 0) {
        const parts = quality.split("x");
        payload.stream_width = Number(parts[0]);
        payload.stream_height = Number(parts[1]);
      }
      return payload;
    }

    async save(cameraId) {
      const payload = this.payloadFromForm();
      if (cameraId && !new FormData(this.form).get("password")) delete payload.password;
      if (!payload.name || !payload.ip) throw new Error("Укажите название и IP камеры");
      const response = await fetch(
        this.apiBase + "/cameras" + (cameraId ? "/" + cameraId : ""),
        {
          method: cameraId ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      const text = await response.text();
      if (!response.ok) {
        let message = text || "HTTP " + response.status;
        try { message = JSON.parse(text).detail || message; } catch (_) {}
        throw new Error(message);
      }
      const camera = JSON.parse(text);
      if (global.DF_models) await global.DF_models.saveCameraModels(camera.id);
      return camera;
    }
  }

  global.DF_CameraFormController = CameraFormController;
})(window);
