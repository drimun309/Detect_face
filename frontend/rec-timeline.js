/** Диаграммы работы/простоя ROI: день = 24 ч, ролик = интервал записи. */
(function () {
  const MODE_COLORS = {
    work: "#4caf50",
    idle: "#ff9800",
    standby: "#3d3d3d",
  };

  const HOUR_TICKS = [0, 3, 6, 9, 12, 15, 18, 21, 24];

  function t(key, vars) {
    return window.DF_I18N ? window.DF_I18N.t(key, vars) : key;
  }

  function fmtHm(ts) {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function fmtDuration(sec) {
    const total = Math.max(0, Math.floor(sec));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) return h + "ч " + m + "м";
    if (m > 0) return m + "м";
    return s + "с";
  }

  /** Полночь выбранной даты в локальной TZ браузера. */
  function dayBounds(dateStr) {
    const parts = (dateStr || "").split("-").map(Number);
    if (parts.length !== 3) return { dayStart: 0, dayEnd: 86400 };
    const d = new Date(parts[0], parts[1] - 1, parts[2], 0, 0, 0, 0);
    const dayStart = d.getTime() / 1000;
    return { dayStart: dayStart, dayEnd: dayStart + 86400 };
  }

  function pctInRange(ts, rangeStart, rangeEnd) {
    if (rangeEnd <= rangeStart) return 0;
    return ((ts - rangeStart) / (rangeEnd - rangeStart)) * 100;
  }

  function shiftSpan(shift, rangeStart, rangeEnd) {
    if (!shift || !shift.enabled) return null;
    const ss = shift.start_sec || 0;
    const se = shift.end_sec || 0;
    let s = rangeStart + (ss % 86400);
    let e = rangeStart + (se % 86400);
    if (se <= ss) e += 86400;
    s = Math.max(s, rangeStart);
    e = Math.min(e, rangeEnd);
    if (e <= s) return null;
    return {
      left: pctInRange(s, rangeStart, rangeEnd),
      width: pctInRange(e, rangeStart, rangeEnd) - pctInRange(s, rangeStart, rangeEnd),
    };
  }

  function isTodayLocal(dateStr) {
    const d = new Date();
    const y = d.getFullYear();
    const m = pad2(d.getMonth() + 1);
    const day = pad2(d.getDate());
    return dateStr === y + "-" + m + "-" + day;
  }

  function mergeSegments(segments, rangeStart, rangeEnd, dataEnd) {
    const capEnd =
      dataEnd != null ? Math.min(rangeEnd, dataEnd) : rangeEnd;
    const list = (segments || [])
      .filter(function (s) {
        return s.end > rangeStart && s.start < capEnd;
      })
      .map(function (s) {
        return {
          mode: s.mode,
          start: Math.max(s.start, rangeStart),
          end: Math.min(s.end, capEnd),
        };
      })
      .sort(function (a, b) {
        return a.start - b.start;
      });
    if (!list.length) {
      return [{ mode: "standby", start: rangeStart, end: capEnd }];
    }
    return list;
  }

  function appendLegend(wrap, shift) {
    const legend = document.createElement("div");
    legend.className = "rec-timeline-legend";
    ["work", "idle", "standby"].forEach(function (mode) {
      const item = document.createElement("span");
      item.className = "rec-timeline-legend-item";
      item.innerHTML =
        '<i style="background:' + MODE_COLORS[mode] + '"></i> ' + t("recTimeline_" + mode);
      legend.appendChild(item);
    });
    if (shift && shift.enabled) {
      const sh = document.createElement("span");
      sh.className = "rec-timeline-legend-item rec-timeline-legend-shift";
      sh.innerHTML = '<i class="rec-legend-shift"></i> ' + t("recTimelineShift");
      legend.appendChild(sh);
    }
    wrap.appendChild(legend);
  }

  function appendHourAxis(trackWrap, rangeStart, rangeEnd, mode) {
    const axis = document.createElement("div");
    axis.className = "rec-timeline-hour-axis";

    if (mode === "day") {
      HOUR_TICKS.forEach(function (h) {
        const tick = document.createElement("span");
        tick.className = "rec-timeline-hour-tick";
        tick.style.left = (h / 24) * 100 + "%";
        tick.textContent = pad2(h) + ":00";
        axis.appendChild(tick);
      });
    } else {
      const startLbl = document.createElement("span");
      startLbl.className = "rec-timeline-hour-tick rec-timeline-hour-tick-edge";
      startLbl.style.left = "0%";
      startLbl.textContent = fmtHm(rangeStart);
      axis.appendChild(startLbl);

      const endLbl = document.createElement("span");
      endLbl.className = "rec-timeline-hour-tick rec-timeline-hour-tick-edge rec-timeline-hour-tick-end";
      endLbl.style.left = "100%";
      endLbl.textContent = fmtHm(rangeEnd);
      axis.appendChild(endLbl);
    }

    trackWrap.appendChild(axis);
  }

  function buildTrack(
    segments,
    rangeStart,
    rangeEnd,
    shift,
    showShiftOnTrack,
    dataEnd
  ) {
    const trackWrap = document.createElement("div");
    trackWrap.className = "rec-timeline-track-wrap";

    const track = document.createElement("div");
    track.className = "rec-timeline-track";

    if (showShiftOnTrack && shift && shift.enabled) {
      const span = shiftSpan(shift, rangeStart, rangeEnd);
      if (span) {
        const band = document.createElement("div");
        band.className = "rec-timeline-shift-band";
        band.style.left = span.left + "%";
        band.style.width = Math.max(0.15, span.width) + "%";
        band.title = t("recTimelineShift") + ": " + shift.start_time + " – " + shift.end_time;
        track.appendChild(band);
      }
    }

    mergeSegments(segments, rangeStart, rangeEnd, dataEnd).forEach(function (seg) {
      const bar = document.createElement("div");
      bar.className = "rec-timeline-seg seg-" + seg.mode;
      const left = pctInRange(seg.start, rangeStart, rangeEnd);
      const right = pctInRange(seg.end, rangeStart, rangeEnd);
      bar.style.left = left + "%";
      bar.style.width = Math.max(0.25, right - left) + "%";
      bar.style.background = MODE_COLORS[seg.mode] || MODE_COLORS.standby;
      bar.title =
        t("recTimeline_" + seg.mode) + ": " + fmtHm(seg.start) + " – " + fmtHm(seg.end);
      track.appendChild(bar);
    });

    if (dataEnd != null && dataEnd < rangeEnd) {
      const future = document.createElement("div");
      future.className = "rec-timeline-future";
      const left = pctInRange(dataEnd, rangeStart, rangeEnd);
      future.style.left = left + "%";
      future.style.width = Math.max(0, 100 - left) + "%";
      future.title = t("recTimelineFuture");
      track.appendChild(future);

      const nowMark = document.createElement("div");
      nowMark.className = "rec-timeline-now-mark";
      nowMark.style.left = left + "%";
      track.appendChild(nowMark);
    }

    trackWrap.appendChild(track);
    return trackWrap;
  }

  function renderTimeline(container, tl, opts) {
    opts = opts || {};
    const mode = opts.mode === "clip" ? "clip" : "day";
    const dateStr = tl.date || "";

    let rangeStart;
    let rangeEnd;
    let dataEnd = null;
    if (mode === "day") {
      if (tl.range_start) {
        rangeStart = tl.range_start;
        rangeEnd =
          tl.day_end && tl.day_end > tl.range_start
            ? tl.day_end
            : tl.range_start + 86400;
        dataEnd =
          tl.range_end && tl.range_end > tl.range_start
            ? tl.range_end
            : rangeEnd;
      } else {
        const b = dayBounds(dateStr);
        rangeStart = b.dayStart;
        rangeEnd = b.dayEnd;
        dataEnd = rangeEnd;
        if (isTodayLocal(dateStr)) {
          dataEnd = Math.min(rangeEnd, Date.now() / 1000);
        }
      }
    } else {
      rangeStart = opts.clipStart != null ? opts.clipStart : tl.range_start;
      rangeEnd = opts.clipEnd != null ? opts.clipEnd : tl.range_end;
    }

    const shift = tl.shift || { enabled: false };
    const showShiftOnTrack = mode === "day";

    container.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.className = "rec-timeline rec-timeline-" + mode;

    const header = document.createElement("div");
    header.className = "rec-timeline-header";
    if (mode === "day") {
      header.textContent = t("recTimelineDayScale", { date: dateStr });
      if (shift.enabled) {
        header.textContent +=
          " · " + t("recTimelineShift") + " " + shift.start_time + "–" + shift.end_time;
      }
      if (dataEnd != null && dataEnd < rangeEnd) {
        header.textContent +=
          " · " + t("recTimelineDayUntil", { time: fmtHm(dataEnd) });
      }
    } else {
      header.textContent =
        t("recTimelineClipScale") +
        ": " +
        fmtHm(rangeStart) +
        " – " +
        fmtHm(rangeEnd);
    }
    wrap.appendChild(header);

    if (mode === "clip") {
      const note = document.createElement("p");
      note.className = "help-text rec-timeline-note";
      note.textContent = t("recTimelineDetectNote");
      wrap.appendChild(note);
    }

    const zones = tl.zones || [];
    if (mode === "day") {
      const hasDaily = zones.some(function (z) {
        return (z.daily_work_seconds || 0) > 0 || (z.daily_idle_seconds || 0) > 0;
      });
      const hasHourly = zones.some(function (z) {
        return z.timeline_source === "hourly";
      });
      if ((tl.events_in_range === 0 || tl.events_in_range === "0") && !hasDaily) {
        const noEv = document.createElement("p");
        noEv.className = "help-text rec-timeline-no-events";
        noEv.textContent = t("recTimelineDayNoEvents", { date: dateStr });
        wrap.appendChild(noEv);
      } else if (hasHourly) {
        const note = document.createElement("p");
        note.className = "help-text rec-timeline-no-events";
        note.textContent = t("recTimelineHourlyNote");
        wrap.appendChild(note);
      }
    }
    if (!zones.length) {
      const empty = document.createElement("p");
      empty.className = "help-text";
      empty.textContent = t("recTimelineEmpty");
      wrap.appendChild(empty);
    } else {
      zones.forEach(function (z) {
        const row = document.createElement("div");
        row.className = "rec-timeline-row";

        const lbl = document.createElement("span");
        lbl.className = "rec-timeline-zone-label";
        lbl.textContent = "ROI " + z.roi_index;
        if (
          mode === "day" &&
          ((z.daily_work_seconds || 0) > 0 || (z.daily_idle_seconds || 0) > 0)
        ) {
          const sub = document.createElement("span");
          sub.className = "rec-timeline-zone-sub";
          sub.textContent = t("recTimelineDailyTotals", {
            work: fmtDuration(z.daily_work_seconds || 0),
            idle: fmtDuration(z.daily_idle_seconds || 0),
          });
          lbl.appendChild(document.createElement("br"));
          lbl.appendChild(sub);
        }

        const col = document.createElement("div");
        col.className = "rec-timeline-zone-col";
        const trackWrap = buildTrack(
          z.segments,
          rangeStart,
          rangeEnd,
          shift,
          showShiftOnTrack,
          mode === "day" ? dataEnd : null
        );
        col.appendChild(trackWrap);
        appendHourAxis(col, rangeStart, rangeEnd, mode);

        row.appendChild(lbl);
        row.appendChild(col);
        wrap.appendChild(row);
      });
    }

    appendLegend(wrap, shift);
    container.appendChild(wrap);
  }

  function filterTimeline(tl, rangeStart, rangeEnd) {
    if (!tl || !tl.zones) return tl;
    return {
      date: tl.date,
      shift: tl.shift,
      range_start: rangeStart,
      range_end: rangeEnd,
      zones: tl.zones.map(function (z) {
        return {
          roi_index: z.roi_index,
          roi_key: z.roi_key,
          segments: mergeSegments(z.segments, rangeStart, rangeEnd),
        };
      }),
    };
  }

  function createCollapsible(parent, tl, opts) {
    opts = opts || {};
    const details = document.createElement("details");
    details.className = "rec-timeline-details";
    const summary = document.createElement("summary");
    const from = opts.clipStart != null ? fmtHm(opts.clipStart) : "";
    const to = opts.clipEnd != null ? fmtHm(opts.clipEnd) : "";
    summary.textContent = t("recTimelineToggle") + (from && to ? " (" + from + " – " + to + ")" : "");
    details.appendChild(summary);
    const body = document.createElement("div");
    body.className = "rec-timeline-body";
    renderTimeline(body, tl, {
      mode: "clip",
      clipStart: opts.clipStart,
      clipEnd: opts.clipEnd,
    });
    details.appendChild(body);
    parent.appendChild(details);
    return details;
  }

  window.DF_renderTimeline = renderTimeline;
  window.DF_renderTimelineCollapsible = createCollapsible;
  window.DF_filterTimeline = filterTimeline;
})();
