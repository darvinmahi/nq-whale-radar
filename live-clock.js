/**
 * live-clock.js — Motor de reloj compartido para todas las páginas del NQ Journal
 * ─────────────────────────────────────────────────────────────────────────────
 * Incluir con:  <script src="live-clock.js"></script>  antes del </body>
 *
 * IDs reconocidos automáticamente en cualquier página:
 *   #lc-utc-clock      → "HH:MM:SS" UTC
 *   #lc-et-clock       → "HH:MM TZ"  ET (EDT/EST automático)
 *   #lc-date-full      → "Mar 17 Marzo 2026"
 *   #lc-day-name       → "Martes"
 *   #lc-week-label     → "Semana Lun 16–Vie 20 Mar 2026 · W12"
 *   #lc-week-short     → "16–20 Mar 2026"
 *   #lc-week-start     → "Lun 16 Mar"
 *   #lc-week-end       → "Vie 20 Mar"
 *   #lc-week-tag       → badge "Semana en Curso · Lun 16–Vie 20 Mar 2026"
 *   #lc-market-status  → "▶ NYSE OPEN" o "⏸ NYSE CLOSED"
 *   #lc-countdown      → "NYSE abre en 02:15" etc
 *   #lc-sess-asia      → pill Asia (añade/quita clase 'active')
 *   #lc-sess-london    → pill London
 *   #lc-sess-ny        → pill NY
 *   #lc-futures        → NQ Futures status
 *   #lc-today          → nombre corto del día de hoy, p.ej. "Mar 17"
 *   [data-lc-week]     → cualquier elemento → reemplaza texto con semana
 *   [data-lc-date]     → cualquier elemento → reemplaza texto con fecha completa
 *   [data-lc-weekly-label] → "Sesgo Semanal — Semana Lun 16 Mar 2026"
 *   [data-lc-daily-label]  → "Sesgo Diario — Hoy Mar 17 Mar 2026"
 *   article[data-date]  → añade clase 'today-entry' si == hoy
 */
(function () {
  'use strict';

  var MONTHS_SHORT = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  var MONTHS_LONG  = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
  var DAY_LONG     = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
  var DAY_SHORT    = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];

  /* ── Pad ─────────────────────────────────────────────────── */
  function pad(n) { return String(n).padStart(2, '0'); }

  /* ── DST: devuelve -4 (EDT) o -5 (EST) ──────────────────── */
  function getNYOffset(now) {
    var y = now.getUTCFullYear();
    // 2nd Sunday of March  → DST start (clocks spring forward 2:00 AM EST = 07:00 UTC)
    var mar = new Date(Date.UTC(y, 2, 1));
    var dstStart = new Date(Date.UTC(y, 2, 8 + (7 - mar.getUTCDay()) % 7, 7));
    // 1st Sunday of November → DST end (clocks fall back 2:00 AM EDT = 06:00 UTC)
    var nov = new Date(Date.UTC(y, 10, 1));
    var dstEnd = new Date(Date.UTC(y, 10, 1 + (7 - nov.getUTCDay()) % 7, 6));
    return (now >= dstStart && now < dstEnd) ? -4 : -5;
  }

  /* ── ISO week number ──────────────────────────────────────── */
  function getISOWeek(d) {
    var tmp = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    var day = tmp.getUTCDay() || 7;
    tmp.setUTCDate(tmp.getUTCDate() + 4 - day);
    var yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1));
    return Math.ceil((((tmp - yearStart) / 86400000) + 1) / 7);
  }

  /* ── Bounds de la semana actual (Lun → Vie) ──────────────── */
  function getWeekBounds(now) {
    var dow = now.getUTCDay() || 7; // Mon=1 … Sun=7
    var monTs = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - (dow - 1));
    var mon   = new Date(monTs);
    var fri   = new Date(monTs + 4 * 86400000);
    var wk    = getISOWeek(now);

    var monStr = DAY_SHORT[1] + ' ' + mon.getUTCDate() + ' ' + MONTHS_SHORT[mon.getUTCMonth()];
    var friStr = DAY_SHORT[5] + ' ' + fri.getUTCDate() + ' ' + MONTHS_SHORT[fri.getUTCMonth()];
    var rangeShort = mon.getUTCDate() + '–' + fri.getUTCDate() + ' ' + MONTHS_SHORT[fri.getUTCMonth()] + ' ' + fri.getUTCFullYear();
    var monLabel   = DAY_SHORT[1] + ' ' + mon.getUTCDate() + ' ' + MONTHS_SHORT[mon.getUTCMonth()];

    return {
      mon: mon, fri: fri,
      monStr: monStr,          // "Lun 16 Mar"
      friStr: friStr,          // "Vie 20 Mar"
      rangeShort: rangeShort,  // "16–20 Mar 2026"
      wk: wk,
      full: monStr + '–' + friStr + ' ' + fri.getUTCFullYear() + ' · W' + wk,
      // "Lun 16–Vie 20 Mar 2026 · W12"
      tag: 'Semana en Curso · ' + mon.getUTCDate() + '–' + fri.getUTCDate() + ' ' + MONTHS_SHORT[fri.getUTCMonth()] + ' ' + fri.getUTCFullYear()
    };
  }

  /* ── Estado de sesiones ────────────────────────────────────── */
  function getSessionState(utcH, utcM, nyOff, dow) {
    var utcDec  = utcH + utcM / 60;
    var nyOpen  = -nyOff + 9 + 0.5;  // 09:30 ET in UTC
    var nyClose = -nyOff + 16;        // 16:00 ET in UTC

    var isWeekday = dow >= 1 && dow <= 5;
    var asiaActive   = utcDec >= 21 || utcDec < 6;
    var londonActive = utcDec >= 8 && utcDec < 16.5;
    var nyActive     = isWeekday && utcDec >= nyOpen && utcDec < nyClose;
    var nyseOpen     = nyActive;

    // NQ Futures: prácticamente 24h, mantenimiento 21:00-22:00 UTC (17:00-18:00 ET)
    var futuresOpen = false;
    if (isWeekday)      { futuresOpen = !(utcDec >= 21 && utcDec < 22); }
    else if (dow === 0) { futuresOpen = utcDec >= 22; } // Domingo después de 22:00

    // Countdown
    var nextLabel = '';
    var now = new Date();
    var todayBase = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));

    if (isWeekday) {
      if (!nyseOpen && utcDec < nyOpen) {
        var tOpen = new Date(todayBase);
        tOpen.setUTCHours(Math.floor(nyOpen), Math.round((nyOpen % 1) * 60), 0, 0);
        var diff = tOpen - now;
        if (diff > 0) nextLabel = '← NYSE abre en ' + pad(Math.floor(diff / 3600000)) + ':' + pad(Math.floor((diff % 3600000) / 60000));
      } else if (nyseOpen) {
        var tClose = new Date(todayBase);
        tClose.setUTCHours(Math.floor(nyClose), 0, 0, 0);
        var diff2 = tClose - now;
        if (diff2 > 0) nextLabel = '← NYSE cierra en ' + pad(Math.floor(diff2 / 3600000)) + ':' + pad(Math.floor((diff2 % 3600000) / 60000));
      } else {
        nextLabel = 'NYSE cerrado hoy';
      }
    } else {
      nextLabel = dow === 6 ? 'NYSE cerrado · Sábado' : 'NYSE cerrado · Domingo';
    }

    return { asiaActive, londonActive, nyActive, nyseOpen, futuresOpen, nextLabel };
  }

  /* ── Helpers DOM ──────────────────────────────────────────── */
  function setText(id, txt) {
    var el = document.getElementById(id);
    if (el) el.textContent = txt;
  }
  function setHtml(id, html) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }
  function setAttr(selector, txt) {
    document.querySelectorAll('[' + selector + ']').forEach(function(el) {
      el.textContent = txt;
    });
  }
  function toggle(id, active) {
    var el = document.getElementById(id);
    if (el) el.classList.toggle('active', active);
  }

  /* ── Highlight hoje ───────────────────────────────────────── */
  function highlightToday(todayStr) {
    document.querySelectorAll('article[data-date]').forEach(function(el) {
      el.classList.toggle('today-entry', el.getAttribute('data-date') === todayStr);
    });
  }

  /* ── Tick principal ───────────────────────────────────────── */
  var lastDateStr = '';

  function tick() {
    var now   = new Date();
    var utcH  = now.getUTCHours();
    var utcM  = now.getUTCMinutes();
    var utcS  = now.getUTCSeconds();
    var dow   = now.getUTCDay();
    var nyOff = getNYOffset(now);
    var nyH   = ((utcH + nyOff) + 24) % 24;
    var tzStr = nyOff === -4 ? 'EDT' : 'EST';

    /* Strings base */
    var utcClock = pad(utcH) + ':' + pad(utcM) + ':' + pad(utcS);
    var etClock  = pad(nyH)  + ':' + pad(utcM) + ' ' + tzStr;
    var dayName  = DAY_LONG[dow];
    var dayShort = DAY_SHORT[dow];
    var dateNum  = now.getUTCDate();
    var monthIdx = now.getUTCMonth();
    var yearNum  = now.getUTCFullYear();
    var dateFull = dayShort + ' ' + dateNum + ' ' + MONTHS_LONG[monthIdx] + ' ' + yearNum;
    var dateShortLabel = DAY_SHORT[dow] + ' ' + pad(dateNum) + ' ' + MONTHS_SHORT[monthIdx];
    var todayStr = yearNum + '-' + pad(monthIdx + 1) + '-' + pad(dateNum);

    /* Semana */
    var wb = getWeekBounds(now);

    /* Sesiones */
    var sess = getSessionState(utcH, utcM, nyOff, dow);

    /* ── Elementos de reloj ───────────────────────────────── */
    setText('lc-utc-clock', utcClock);
    setText('lc-et-clock',  etClock);
    setText('lc-date-full', dateFull);
    setText('lc-day-name',  dayName);
    setText('lc-today',     dayShort + ' ' + dateNum);
    setText('lc-week-label',  'Semana ' + wb.full);
    setText('lc-week-short',  wb.rangeShort);
    setText('lc-week-start',  wb.monStr);
    setText('lc-week-end',    wb.friStr);
    setText('lc-countdown',   sess.nextLabel);

    /* Reloj con separadores parpadeantes (también soporta innerHTML) */
    setHtml('lc-utc-clock-anim',
      pad(utcH) + '<span class="clock-sep">:</span>' +
      pad(utcM) + '<span class="clock-sep">:</span>' + pad(utcS));

    /* Badge "Semana en Curso" */
    var tagEl = document.getElementById('lc-week-tag');
    if (tagEl) tagEl.textContent = wb.tag;

    /* Market status pill */
    var pill = document.getElementById('lc-market-status');
    if (pill) {
      if (sess.nyseOpen) {
        pill.textContent = '▶ NYSE OPEN';
        pill.style.cssText = 'color:#34d399;border-color:rgba(52,211,153,0.4);background:rgba(52,211,153,0.08);box-shadow:0 0 8px rgba(52,211,153,0.25)';
      } else {
        pill.textContent = '⏸ NYSE CLOSED';
        pill.style.cssText = 'color:#ef4444;border-color:rgba(239,68,68,0.3);background:rgba(239,68,68,0.06);box-shadow:none';
      }
    }

    /* NQ Futures */
    var fut = document.getElementById('lc-futures');
    if (fut) {
      fut.textContent = sess.futuresOpen ? '⬡ NQ Futures: ACTIVO' : '⬡ NQ Futures: MAINT';
      fut.style.color = sess.futuresOpen ? '#a78bfa' : '#6b7280';
    }

    /* Sesion pills */
    toggle('lc-sess-asia',   sess.asiaActive);
    toggle('lc-sess-london', sess.londonActive);
    toggle('lc-sess-ny',     sess.nyActive);

    /* Header status (opcional) */
    var hdrStatus = document.getElementById('lc-hdr-status');
    var hdrSess   = document.getElementById('lc-hdr-session');
    if (hdrStatus) {
      hdrStatus.textContent = sess.nyseOpen ? '▶ Mercado Abierto · NY' : '⏸ Mercado Cerrado';
      hdrStatus.style.color = sess.nyseOpen ? '#34d399' : '#64748b';
    }
    if (hdrSess) {
      var active = [];
      if (sess.asiaActive)   active.push('Asia');
      if (sess.londonActive) active.push('London');
      if (sess.nyActive)     active.push('NY');
      hdrSess.textContent = active.length ? 'Sesión: ' + active.join(' + ') : 'Sin sesión activa';
    }

    /* ── Actualización una vez por día ──────────────────────── */
    if (todayStr !== lastDateStr) {
      lastDateStr = todayStr;

      /* Nav week label (si existe como texto) */
      setAttr('data-lc-week', wb.tag);
      setAttr('data-lc-date', dateFull);

      /* Sesgo semanal y diario — index.html y similares */
      setAttr('data-lc-weekly-label',
        '📅 Sesgo Semanal — Semana ' + wb.monStr + ' ' + yearNum);
      setAttr('data-lc-daily-label',
        '📆 Sesgo Diario — Hoy ' + dateShortLabel + ' ' + yearNum);

      /* "Estado del mercado · DD Mon YYYY" */
      setAttr('data-lc-mkt-state',
        'Estado del mercado · ' + dateNum + ' ' + MONTHS_SHORT[monthIdx] + ' ' + yearNum);

      /* Highlight today's article */
      highlightToday(todayStr);

      /* Nav week element (legacy ID del journal) */
      var navWeekEl = document.getElementById('nav-week');
      if (navWeekEl) navWeekEl.textContent = 'Semana ' + wb.full;
    }

    /* ── Labels que se actualizan a cada minuto ─────────────── */
    // Etiqueta "parcial" para el entry de hoy en el journal
    var partialEl = document.getElementById('journal-today-partial');
    if (partialEl) {
      partialEl.textContent = MONTHS_LONG[monthIdx] + ' ' + yearNum +
        ' · Sesión en curso · ' + pad(utcH) + ':' + pad(utcM) + ' UTC';
    }
    var untilEl = document.getElementById('journal-today-until');
    if (untilEl) {
      untilEl.textContent = 'Hasta ' + pad(utcH) + ':' + pad(utcM) + ' UTC';
    }
  }

  /* ── Arrancar ─────────────────────────────────────────────── */
  tick();
  setInterval(tick, 1000);

  /* Exponer para uso manual desde consola */
  window.LiveClock = { tick: tick, getNYOffset: getNYOffset, getWeekBounds: getWeekBounds };

})();
