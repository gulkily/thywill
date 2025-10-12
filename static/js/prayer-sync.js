(function () {
  'use strict';

  if (!window.ThywillOffline) {
    return;
  }

  var MARK_TARGET_PREFIX = 'prayer-marks-';

  function pathFromDetail(detail) {
    if (!detail) {
      return null;
    }
    if (detail.path) {
      return detail.path;
    }
    if (detail.requestConfig && detail.requestConfig.path) {
      return detail.requestConfig.path;
    }
    return null;
  }

  function extractPrayerIdFromPath(path) {
    if (!path) {
      return null;
    }
    var segments = path.split('/').filter(Boolean);
    return segments.length ? segments[segments.length - 1] : null;
  }

  function ensureQueuedNotice(prayerId) {
    var targetId = MARK_TARGET_PREFIX + prayerId;
    var target = document.getElementById(targetId);
    if (!target) {
      return;
    }

    if (target.querySelector('[data-offline-pending]')) {
      return;
    }

    var notice = document.createElement('div');
    notice.dataset.offlinePending = 'true';
    notice.className = 'mt-2 text-xs text-yellow-700 dark:text-yellow-300';
    notice.textContent = 'Marked offline – will sync when you reconnect.';
    target.appendChild(notice);
  }

  function recordTelemetry(eventType, metadata) {
    try {
      var storageKey = 'thywill_offline_telemetry';
      var raw = localStorage.getItem(storageKey);
      var events = [];
      if (raw) {
        events = JSON.parse(raw);
        if (!Array.isArray(events)) {
          events = [];
        }
      }
      events.push({
        type: eventType,
        metadata: metadata || {},
        at: new Date().toISOString()
      });
      if (events.length > 50) {
        events = events.slice(events.length - 50);
      }
      localStorage.setItem(storageKey, JSON.stringify(events));
    } catch (error) {
      // Ignore storage failures (private mode, quota, etc.)
    }
  }

  function incrementBadge(button) {
    if (!button) {
      return;
    }
    var badge = button.querySelector('span:last-child');
    if (!badge) {
      return;
    }
    var current = parseInt(badge.textContent, 10);
    if (Number.isNaN(current)) {
      current = 0;
    }
    badge.textContent = (current + 1).toString();
  }

  function markButtonQueued(button) {
    if (!button) {
      return;
    }
    button.dataset.offlineQueued = 'true';
    button.setAttribute('aria-live', 'polite');
    button.title = 'Marked while offline – queued for sync.';
  }

  function hasActiveServiceWorker() {
    return 'serviceWorker' in navigator && !!navigator.serviceWorker.controller;
  }

  function requestServiceWorkerFlush() {
    if (!hasActiveServiceWorker()) {
      return;
    }

    navigator.serviceWorker.controller.postMessage('flushPrayerQueue');
  }

  function clearQueuedState(prayerId) {
    var button = document.querySelector('form[action="/mark/' + prayerId + '"] button');
    if (button) {
      delete button.dataset.offlineQueued;
      button.removeAttribute('aria-live');
      button.title = 'Mark this prayer as prayed';
    }

    var target = document.getElementById(MARK_TARGET_PREFIX + prayerId);
    if (target) {
      var notice = target.querySelector('[data-offline-pending]');
      if (notice) {
        notice.remove();
      }
    }
  }

  function scheduleBackgroundSync() {
    if (!('serviceWorker' in navigator)) {
      return;
    }

    navigator.serviceWorker.ready.then(function (registration) {
      if (!registration.sync) {
        return;
      }
      registration.sync.register('thywill-prayer-sync').catch(function () {
        // Ignore unsupported sync registration attempts
      });
    });
  }

  async function hydrateExistingQueueState() {
    try {
      var queued = await window.ThywillOffline.getQueuedMarks();
      queued.forEach(function (record) {
        var button = document.querySelector('form[action="/mark/' + record.prayerId + '"] button');
        markButtonQueued(button);
        ensureQueuedNotice(record.prayerId);
      });
      updateConnectivityBanner();
    } catch (error) {
      console.error('[Offline] Unable to hydrate queued marks:', error);
    }
  }

  function handleBeforeRequest(event) {
    var detail = event.detail || {};
    var path = pathFromDetail(detail);

    if (!path || path.indexOf('/mark/') === -1) {
      return;
    }

    if (navigator.onLine) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();

    var prayerId = extractPrayerIdFromPath(path);
    if (!prayerId) {
      return;
    }

    var triggeringElement = detail.elt || null;
    if (triggeringElement && triggeringElement.tagName === 'BUTTON') {
      incrementBadge(triggeringElement);
      markButtonQueued(triggeringElement);
    }

    ensureQueuedNotice(prayerId);

    window.ThywillOffline.enqueuePrayerMark({
      prayerId: prayerId,
      url: path,
      prayedAt: new Date().toISOString(),
      metadata: {
        targetId: detail.target ? detail.target.id : null
      }
    }).then(function () {
      scheduleBackgroundSync();
      requestServiceWorkerFlush();
      recordTelemetry('mark_queued', { prayerId: prayerId });
      updateConnectivityBanner();
    }).catch(function (error) {
      console.error('[Offline] Failed to queue prayer mark:', error);
      recordTelemetry('queue_error', { reason: error && error.message ? error.message : 'unknown' });
    });
  }

  async function sendQueuedMark(record) {
    var url = record.url || '/mark/' + record.prayerId;
    var absoluteUrl = new URL(url, window.location.origin).toString();
    var body = JSON.stringify({ prayed_at: record.prayedAt });

    var response = await fetch(absoluteUrl, {
      method: record.method || 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/html',
        'HX-Request': 'true',
        'X-Thywill-Offline': 'foreground'
      },
      body: body,
      credentials: 'same-origin'
    });

    if (!response.ok) {
      throw new Error('Failed to sync prayer mark');
    }

    var html = await response.text();
    var targetId = (record.metadata && record.metadata.targetId) || (MARK_TARGET_PREFIX + record.prayerId);
    var target = document.getElementById(targetId);
    if (target) {
      target.innerHTML = html;
      if (window.htmx && typeof window.htmx.process === 'function') {
        window.htmx.process(target);
      }
    }

    clearQueuedState(record.prayerId);
    recordTelemetry('sync_success', { prayerId: record.prayerId, source: 'foreground' });
  }

  function flushQueue() {
    if (!navigator.onLine) {
      return;
    }

    if (hasActiveServiceWorker()) {
      requestServiceWorkerFlush();
      return;
    }

    window.ThywillOffline.flushQueuedMarks(sendQueuedMark)
      .then(function () {
        updateConnectivityBanner();
      })
      .catch(function (error) {
        console.error('[Offline] Failed to flush queued marks:', error);
        recordTelemetry('sync_failed', { reason: error && error.message ? error.message : 'unknown' });
      });
  }

  function updateConnectivityBanner() {
    var banner = document.getElementById('offline-status-banner');
    if (!banner) {
      return;
    }

    window.ThywillOffline.getQueuedMarks()
      .then(function (records) {
        var queueCount = records.length;
        var online = navigator.onLine;
        var messageEl = document.getElementById('offline-status-message');
        var countEl = document.getElementById('offline-status-count');

        if (!online) {
          banner.classList.remove('hidden');
          if (messageEl) {
            messageEl.textContent = 'Offline mode: changes will sync when you reconnect.';
          }
          if (countEl) {
            if (queueCount > 0) {
              countEl.textContent = queueCount + (queueCount === 1 ? ' update queued' : ' updates queued');
              countEl.classList.remove('hidden');
            } else {
              countEl.classList.add('hidden');
            }
          }
          return;
        }

        if (queueCount > 0) {
          banner.classList.remove('hidden');
          if (messageEl) {
            messageEl.textContent = 'Syncing queued prayer marks…';
          }
          if (countEl) {
            countEl.textContent = queueCount + (queueCount === 1 ? ' pending update' : ' pending updates');
            countEl.classList.remove('hidden');
          }
        } else {
          banner.classList.add('hidden');
        }
      })
      .catch(function () {
        // Ignore banner update failures
      });
  }

  document.addEventListener('DOMContentLoaded', function () {
    hydrateExistingQueueState();
    document.body.addEventListener('htmx:beforeRequest', handleBeforeRequest);
    window.addEventListener('online', flushQueue);
    window.addEventListener('online', updateConnectivityBanner);
    window.addEventListener('offline', updateConnectivityBanner);
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'visible') {
        flushQueue();
        updateConnectivityBanner();
      }
    });

    if (navigator.onLine) {
      flushQueue();
    }

    updateConnectivityBanner();

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', function (event) {
        var data = event.data || {};
        if (data.type !== 'offline-prayer-sync') {
          return;
        }

        var targetId = (data.metadata && data.metadata.targetId) || (MARK_TARGET_PREFIX + data.prayerId);
        if (data.html) {
          var target = document.getElementById(targetId);
          if (target) {
            target.innerHTML = data.html;
            if (window.htmx && typeof window.htmx.process === 'function') {
              window.htmx.process(target);
            }
          }
        }

        clearQueuedState(data.prayerId);
        recordTelemetry('sync_success', { prayerId: data.prayerId, source: 'service-worker' });
        updateConnectivityBanner();
      });
    }
  });
})();
