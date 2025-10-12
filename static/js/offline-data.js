(function () {
  'use strict';

  var indexedDbAvailable = typeof indexedDB !== 'undefined';

  if (!indexedDbAvailable) {
    window.ThywillOffline = {
      seedFeedData: function () { return Promise.resolve(); },
      ensureFeedReady: function () { return Promise.resolve(); },
      enqueuePrayerMark: function () { return Promise.resolve(); },
      getQueuedMarks: function () { return Promise.resolve([]); },
      removeQueuedMark: function () { return Promise.resolve(); },
      flushQueuedMarks: function () { return Promise.resolve(); }
    };
    return;
  }

  var DB_NAME = 'thywill-offline';
  var DB_VERSION = 2;
  var FEED_STORE = 'feeds';
  var SETTINGS_STORE = 'settings';
  var MARK_QUEUE_STORE = 'markQueue';

  var dbPromise;

  function openDb() {
    if (!dbPromise) {
      dbPromise = new Promise(function (resolve, reject) {
        var request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onupgradeneeded = function (event) {
          var db = event.target.result;

          if (!db.objectStoreNames.contains(FEED_STORE)) {
            db.createObjectStore(FEED_STORE, { keyPath: 'feedType' });
          }

          if (!db.objectStoreNames.contains(SETTINGS_STORE)) {
            db.createObjectStore(SETTINGS_STORE, { keyPath: 'key' });
          }

          if (!db.objectStoreNames.contains(MARK_QUEUE_STORE)) {
            db.createObjectStore(MARK_QUEUE_STORE, { keyPath: 'id' });
          }
        };

        request.onsuccess = function () {
          resolve(request.result);
        };

        request.onerror = function () {
          reject(request.error);
        };
      });
    }

    return dbPromise;
  }

  function runStore(storeName, mode, handler) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var resolved = false;
        var tx;
        try {
          tx = db.transaction(storeName, mode);
        } catch (transactionError) {
          reject(transactionError);
          return;
        }

        tx.onerror = function () {
          if (!resolved) {
            resolved = true;
            reject(tx.error);
          }
        };

        tx.oncomplete = function () {
          if (!resolved) {
            resolved = true;
            resolve(result);
          }
        };

        var store = tx.objectStore(storeName);
        var result;
        try {
          result = handler(store);
        } catch (handlerError) {
          if (!resolved) {
            resolved = true;
            reject(handlerError);
          }
          return;
        }

        if (result instanceof IDBRequest) {
          result.onsuccess = function (event) {
            if (!resolved) {
              resolved = true;
              resolve(event.target.result);
            }
          };
          result.onerror = function () {
            if (!resolved) {
              resolved = true;
              reject(result.error);
            }
          };
        } else if (result instanceof Promise) {
          result.then(function (value) {
            if (!resolved) {
              resolved = true;
              resolve(value);
            }
          }).catch(function (error) {
            if (!resolved) {
              resolved = true;
              reject(error);
            }
          });
        }
      });
    });
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function extractCategoryOptions(filterElement) {
    if (!filterElement) {
      return [];
    }

    return Array.from(filterElement.options).map(function (option) {
      return {
        value: option.value,
        label: option.textContent,
        selected: option.selected
      };
    });
  }

  function generateQueueId() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
    return 'queued-' + Date.now().toString(16) + '-' + Math.random().toString(16).slice(2, 10);
  }

  function sortByCreatedAt(records) {
    return records.sort(function (a, b) {
      var aTime = Date.parse(a.createdAt || 0);
      var bTime = Date.parse(b.createdAt || 0);
      return aTime - bTime;
    });
  }

  function saveFeedSnapshot(feedType, html) {
    if (!feedType || !html) {
      return Promise.resolve();
    }

    return runStore(FEED_STORE, 'readwrite', function (store) {
      return store.put({ feedType: feedType, html: html, updatedAt: nowIso() });
    });
  }

  function loadFeedSnapshot(feedType) {
    if (!feedType) {
      return Promise.resolve(null);
    }

    return runStore(FEED_STORE, 'readonly', function (store) {
      return store.get(feedType);
    });
  }

  function saveCategoryOptions(options) {
    if (!options || options.length === 0) {
      return Promise.resolve();
    }

    return runStore(SETTINGS_STORE, 'readwrite', function (store) {
      return store.put({ key: 'categories', options: options, updatedAt: nowIso() });
    });
  }

  function loadCategoryOptions() {
    return runStore(SETTINGS_STORE, 'readonly', function (store) {
      return store.get('categories');
    }).then(function (record) {
      return record ? record.options : [];
    });
  }

  function hydrateFeedList(feedType, listElement) {
    if (!listElement) {
      return Promise.resolve();
    }

    if (listElement.children.length > 0 && listElement.innerHTML.trim().length > 0) {
      return Promise.resolve();
    }

    return loadFeedSnapshot(feedType).then(function (snapshot) {
      if (snapshot && snapshot.html) {
        listElement.innerHTML = snapshot.html;
        if (window.htmx && typeof window.htmx.process === 'function') {
          window.htmx.process(listElement);
        }
      }
    });
  }

  function hydrateCategoryFilter(filterElement) {
    if (!filterElement) {
      return Promise.resolve();
    }

    if (filterElement.options.length > 0) {
      return Promise.resolve();
    }

    return loadCategoryOptions().then(function (options) {
      if (!options || options.length === 0) {
        return;
      }

      var fragment = document.createDocumentFragment();
      options.forEach(function (option) {
        var opt = document.createElement('option');
        opt.value = option.value;
        opt.textContent = option.label;
        if (option.selected) {
          opt.selected = true;
        }
        fragment.appendChild(opt);
      });

      filterElement.appendChild(fragment);
    });
  }

  function seedFeedData(options) {
    var feedType = options.feedType;
    var listElement = options.listElement;
    var filterElement = options.filterElement;

    if (!navigator.onLine) {
      return Promise.resolve();
    }

    var tasks = [];

    if (listElement && listElement.innerHTML.trim().length > 0) {
      tasks.push(saveFeedSnapshot(feedType, listElement.innerHTML));
    }

    if (filterElement) {
      var categoryOptions = extractCategoryOptions(filterElement);
      if (categoryOptions.length > 0) {
        tasks.push(saveCategoryOptions(categoryOptions));
      }
    }

    return Promise.all(tasks);
  }

  function ensureFeedReady(feedType, listElement, filterElement) {
    if (navigator.onLine) {
      return Promise.resolve();
    }

    return Promise.all([
      hydrateCategoryFilter(filterElement),
      hydrateFeedList(feedType, listElement)
    ]);
  }

  function enqueuePrayerMark(entry) {
    var record = {
      id: entry.id || generateQueueId(),
      prayerId: entry.prayerId,
      url: entry.url,
      method: entry.method || 'POST',
      prayedAt: entry.prayedAt,
      createdAt: entry.createdAt || nowIso(),
      metadata: entry.metadata || {}
    };

    return runStore(MARK_QUEUE_STORE, 'readwrite', function (store) {
      return store.put(record);
    }).then(function () {
      return record;
    });
  }

  function getQueuedMarks() {
    return runStore(MARK_QUEUE_STORE, 'readonly', function (store) {
      return store.getAll();
    }).then(function (records) {
      if (!records) {
        return [];
      }
      return sortByCreatedAt(records);
    });
  }

  function removeQueuedMark(id) {
    if (!id) {
      return Promise.resolve();
    }

    return runStore(MARK_QUEUE_STORE, 'readwrite', function (store) {
      return store.delete(id);
    });
  }

  function flushQueuedMarks(processor) {
    if (typeof processor !== 'function') {
      return Promise.resolve();
    }

    return getQueuedMarks().then(async function (records) {
      for (var i = 0; i < records.length; i += 1) {
        var record = records[i];
        await processor(record);
        await removeQueuedMark(record.id);
      }
    });
  }

  window.ThywillOffline = {
    seedFeedData: seedFeedData,
    ensureFeedReady: ensureFeedReady,
    enqueuePrayerMark: enqueuePrayerMark,
    getQueuedMarks: getQueuedMarks,
    removeQueuedMark: removeQueuedMark,
    flushQueuedMarks: flushQueuedMarks,
    openDb: openDb,
    hasFeedSnapshot: function (feedType) {
      return loadFeedSnapshot(feedType).then(function (record) {
        return Boolean(record && record.html);
      });
    },
    getFeedSnapshot: loadFeedSnapshot
  };
})();
