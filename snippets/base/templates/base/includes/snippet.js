<script type="text/javascript">
//<![CDATA[
'use strict';

var SNIPPET_METRICS_SAMPLE_RATE = {{ settings.METRICS_SAMPLE_RATE }};
var SNIPPET_METRICS_URL = '{{ settings.METRICS_URL }}';
var ABOUTHOME_SHOWN_SNIPPET = null;
var USER_COUNTRY = null;
var GEO_CACHE_DURATION = 1000 * 60 * 60 * 24 * 30; // 30 days

var BLOCKED_DATABASE_NAME = "abouthome";
var BLOCKED_DATABASE_VERSION = 1;
var BLOCKED_DATABASE_STORAGE = "persistent";
var BLOCKED_OBJECTSTORE_NAME = "snippets";

// Start MozUITour
// Copy from https://hg.mozilla.org/mozilla-central/file/tip/browser/components/uitour/UITour-lib.js
if (typeof Mozilla == 'undefined') {
    var Mozilla = {};
}

if (typeof Mozilla.UITour == 'undefined') {
    Mozilla.UITour = {};
}

function _sendEvent(action, data) {
    var event = new CustomEvent('mozUITour', {
        bubbles: true,
        detail: {
            action: action,
            data: data || {}
        }
    });

    document.dispatchEvent(event);
}

function _generateCallbackID() {
    return Math.random().toString(36).replace(/[^a-z]+/g, '');
}

function _waitForCallback(callback) {
    var id = _generateCallbackID();

    function listener(event) {
        if (typeof event.detail != 'object')
            return;
        if (event.detail.callbackID != id)
            return;

        document.removeEventListener('mozUITourResponse', listener);
        callback(event.detail.data);
    }
    document.addEventListener('mozUITourResponse', listener);

    return id;
}

Mozilla.UITour.showHighlight = function(target, effect) {
    _sendEvent('showHighlight', {
        target: target,
        effect: effect
    });
};

Mozilla.UITour.hideHighlight = function() {
    _sendEvent('hideHighlight');
};

Mozilla.UITour.showMenu = function(name, callback) {
    var showCallbackID;
    if (callback)
        showCallbackID = _waitForCallback(callback);

    _sendEvent('showMenu', {
        name: name,
        showCallbackID: showCallbackID,
    });
};

Mozilla.UITour.hideMenu = function(name) {
    _sendEvent('hideMenu', {
        name: name
    });
};

Mozilla.UITour.getConfiguration = function(configName, callback) {
    _sendEvent('getConfiguration', {
        callbackID: _waitForCallback(callback),
        configuration: configName,
    });
};

Mozilla.UITour.setConfiguration = function(configName, configValue) {
    _sendEvent('setConfiguration', {
        configuration: configName,
        value: configValue,
    });
};
// End MozUITour


(function(showDefaultSnippets) {
    'use strict';

  function initBlockList(callback) {
    function error() {
      // If we fail to setup the db, just return a dummy so the snippet displays.
      callback(Object.freeze({
        get: function () {},
        set: function (aKey, aValue, callback) {
          callback = callback || function(){};
          callback();
        },
        has: function () {
          return false;
        },
        delete: function (aKey, callback) {
          callback = callback || function(){};
          callback();
        },
        clear: function (callback) {
          callback = callback || function(){};
          callback();
        },
        get size() { return 0; }
      }));
    }
    var openRequest = indexedDB.open(BLOCKED_DATABASE_NAME, {version: BLOCKED_DATABASE_VERSION,
                                                     storage: BLOCKED_DATABASE_STORAGE});

    openRequest.onerror = function (event) {
      // Try to delete the old database so that we can start this process over
      // next time.
      indexedDB.deleteDatabase(BLOCKED_DATABASE_NAME);
      error();
    };

    openRequest.onupgradeneeded = function (event) {
      var db = event.target.result;
      if (!db.objectStoreNames.contains(BLOCKED_OBJECTSTORE_NAME)) {
        db.createObjectStore(BLOCKED_OBJECTSTORE_NAME);
      }
    }

    openRequest.onsuccess = function (event) {
      var db = event.target.result;

      db.onversionchange = function (event) {
        event.target.close();
      }
      var cache = new Map();
      var cursorRequest = db.transaction(BLOCKED_OBJECTSTORE_NAME)
                            .objectStore(BLOCKED_OBJECTSTORE_NAME).openCursor();

      cursorRequest.onerror = error;

      cursorRequest.onsuccess = function(event) {
        var cursor = event.target.result;

        // Populate the cache from the persistent storage.
        if (cursor) {
          cache.set(cursor.key, cursor.value);
          cursor.continue();
          return;
        }

        // The cache has been filled up, create the blocked snippets map.
        window.blockedSnippets = Object.freeze({
          get: function (aKey) {
            return cache.get(aKey);
          },
          set: function (aKey, aValue, callback) {
            callback = callback || function(){};
            var transaction = db.transaction(BLOCKED_OBJECTSTORE_NAME, "readwrite");
            transaction.oncomplete = callback;
            transaction.objectStore(BLOCKED_OBJECTSTORE_NAME).put(aValue, aKey);
            cache.set(aKey, aValue);
          },
          has: function (aKey) {
            return cache.has(aKey);
          },
          delete: function (aKey, callback) {
            callback = callback || function(){};
            var transaction = db.transaction(BLOCKED_OBJECTSTORE_NAME, "readwrite");
            transaction.oncomplete = callback;
            transaction.objectStore(BLOCKED_OBJECTSTORE_NAME).delete(aKey);
            cache.delete(aKey);
          },
          clear: function (callback) {
            callback = callback || function(){};
            var transaction = db.transaction(BLOCKED_OBJECTSTORE_NAME, "readwrite");
            transaction.oncomplete = callback;
            transaction.objectStore(BLOCKED_OBJECTSTORE_NAME).clear();
            cache.clear();
          },
          get size() { return cache.size; }
        });
        callback(window.blockedSnippets);
      }
    }

  }

  function blockListReady(gSnippetsMap) {
    // showDefaultSnippets polyfill, available in about:home v4
    if (typeof showDefaultSnippets !== 'function') {
        showDefaultSnippets = function() {
            localStorage.snippets = '';
            showSnippets();
        };
    }

    var show_snippet = null;
    if (ABOUTHOME_SNIPPETS.length > 0) {
        show_snippet = chooseSnippet(ABOUTHOME_SNIPPETS);
    }

    if (show_snippet) {
        ABOUTHOME_SHOWN_SNIPPET = show_snippet;

        // Inject the snippet onto the page.
        var snippetContainer = document.createElement('div');
        snippetContainer.innerHTML = show_snippet.code;
        document.getElementById('snippets').appendChild(snippetContainer);
        activateScriptTags(snippetContainer);

        try {
            activateSnippetsButtonClick(show_snippet);
        } catch (err) {
            // Do nothing, most likely a newer version of Firefox w/o
            // activateSnippetsButtonClick
        }

        // By the time show_snippet event reaches #snippets the snippet
        // will have finished initializing and altering the DOM. It's the
        // time to modifyLinks() and addSnippetBlockLinks().
        var snippets = document.getElementById('snippets');
        snippets.addEventListener('show_snippet', function(event) {
            var topSection = document.getElementById('topSection');
            // Add sample rate and snippet ID to currently displayed links.
            var parameters = ('sample_rate=' + SNIPPET_METRICS_SAMPLE_RATE + '&snippet_name=' +
                              ABOUTHOME_SHOWN_SNIPPET.id);
            modifyLinks(topSection.querySelectorAll('a'), parameters);
            addSnippetBlockLinks(topSection.querySelectorAll('.block-snippet-button'));
            keypressIsMine(snippetContainer.querySelector('.snippet'));
            sendImpression();
        });
        // Trigger show_snippet event
        var evt = document.createEvent('Event');
        evt.initEvent('show_snippet', true, true);
        snippetContainer.querySelector('.snippet').dispatchEvent(evt);
    } else {
        showDefaultSnippets();
    }

    // Update FxAccount Status
    updateFxAccountStatus();

    // Update Selected Search Engine
    updateSelectedSearchEngine();

    // Fetch user country if we don't have it.
    if (!haveUserCountry()) {
        downloadUserCountry();
    }

    {% if preview %}
    function chooseSnippet(snippets) {
        return snippets[0];
    }
    {% else %}
    // Choose which snippet to display to the user based on various factors,
    // such as which country they are in.
    function chooseSnippet(snippets) {
        USER_COUNTRY = getUserCountry();
        if (USER_COUNTRY) {
            snippets = snippets.filter(
                function(snippet) {
                    var countries = snippet.countries;
                    if (countries.length && countries.indexOf(USER_COUNTRY) === -1) {
                        return false;
                    }
                    return true;
                }
            );
        }
        else {
            // If we don't have the user's country, remove all geolocated snippets.
            // Bug 1140476
            snippets = snippets.filter(
                function(snippet) {
                    return snippet.countries.length === 0;
                }
            )
        }

        // FxAccount is already setup skip snippets that link to
        // about:accounts
        if (isFxAccountSetup()) {
            snippets = snippets.filter(
                function(snippet) {
                    return !hasAboutAccountsLink(snippet);
                }
            );
        }

        // Exclude snippets from search providers.
        var searchProvider = gSnippetsMap.get('selectedSearchEngine');
        if (searchProvider) {
            snippets = snippets.filter(
                function(snippet) {
                    var excludeFromSearchEngines = snippet.exclude_from_search_engines;
                    if (excludeFromSearchEngines.length && excludeFromSearchEngines.indexOf(searchProvider) !== -1) {
                        return false;
                    }
                    return true;
                }
            );
        }

        // Exclude snippets in block list.
        var blockList = getBlockList();
        snippets = snippets.filter(
            function (snippet) {
                if (blockList.indexOf(snippet.id) === -1) {
                    return true;
                }
                return false;
            }
        );

        // Choose a random snippet from the snippets list.
        if (snippets && snippets.length) {
            var sum = 0;
            var number_of_snippets = snippets.length;
            for (var k = 0; k < number_of_snippets; k++) {
                sum += snippets[k].weight;
                snippets[k].weight = sum;
            }
            var random_number = Math.random() * sum;
            for (var k = 0; k < number_of_snippets; k++) {
                if (random_number < snippets[k].weight) {
                    return snippets[k];
                }
            }
        } else {
            return null;
        }
    }
    {% endif %}

    // Check whether snippet links to about:accounts.
    function hasAboutAccountsLink(snippet) {
        return snippet.code.indexOf('href="about:accounts"') !== -1;
    }

    function isFxAccountSetup() {
        var fxaccount = gSnippetsMap.get('fxaccount');
        if (fxaccount !== undefined) {
            return fxaccount;
        }
        // If fxaccount === undefined pretend that sync is already
        // setup, to avoid showing about:accounts snippets to browsers
        // that do not support mozUITour signal or have accounts
        // already setup.
        return true;
    }

    function updateFxAccountStatus() {
        var callback = function(result) {
            gSnippetsMap.set('fxaccount', result.setup);
        }
        var event = new CustomEvent(
            'mozUITour', {
                bubbles: true,
                detail: {
                    action:'getConfiguration',
                    data: {
                        configuration: 'sync',
                        callbackID: _waitForCallback(callback)
                    }
                }
            }
        );
        document.dispatchEvent(event);
    }

    function updateSelectedSearchEngine() {
        var callback = function(result) {
            gSnippetsMap.set('selectedSearchEngine', result.searchEngineIdentifier);
        }
        var event = new CustomEvent(
            'mozUITour', {
                bubbles: true,
                detail: {
                    action:'getConfiguration',
                    data: {
                        configuration: 'selectedSearchEngine',
                        callbackID: _waitForCallback(callback)
                    }
                }
            }
        );
        document.dispatchEvent(event);
    }

    // Check whether we have the user's country stored and if it is still valid.
    function haveUserCountry() {
        // Check if there's an existing country code to use.
        if (gSnippetsMap.get('geoCountry')) {
            // Make sure we have a valid lastUpdated date.
            var lastUpdated = Date.parse(gSnippetsMap.get('geoLastUpdated'));
            if (lastUpdated) {
                // Make sure that it is past the lastUpdated date.
                var now = new Date();
                if (now < lastUpdated + GEO_CACHE_DURATION) {
                    return true;
                }
            }
        }

        return false;
    }

    function getUserCountry() {
        if (haveUserCountry()) {
            return gSnippetsMap.get('geoCountry').toLowerCase();
        } else {
            return null;
        }
    }

    // Download the user's country using the geolocation service.
    // Please do not directly use this code or Snippets key.
    // Contact MLS team for your own credentials.
    // https://location.services.mozilla.com/contact
    function downloadUserCountry() {
        var GEO_URL = "{{ settings.GEO_URL }}";
        var request = new XMLHttpRequest();
        request.timeout = 60000;
        request.onreadystatechange = function() {
            if (request.readyState == 4 && request.status == 200) {
                var country_data = JSON.parse(request.responseText);

                try {
                    gSnippetsMap.set('geoCountry', country_data.country_code);
                    gSnippetsMap.set('geoLastUpdated', new Date());
                } catch (e) {
                    // Most likely failed to load Data file. Continue on without us,
                    // we'll try again next time.
                }
            }
        };
        request.open('GET', GEO_URL, true);
        request.send();
    }

    // Notifies stats server that the given snippet ID
    // was shown. No personally-identifiable information
    // is sent.
    function sendImpression() {
        sendMetric('impression');
    }

    // Modifies the given links to include the specified GET parameters.
    function modifyLinks(links, parameters) {
        for (var k = 0, len = links.length; k < len; k++) {
            var link = links[k];
            var delimeter = (link.href.indexOf('?') !== -1 ? '&' : '?');

            // Pull the fragment off of the link
            var fragment_position = link.href.indexOf('#');
            if (fragment_position === -1) {
                fragment_position = link.href.length;
            }

            var href = link.href.substring(0, fragment_position);
            var fragment = link.href.substring(fragment_position);

            link.href = href + delimeter + parameters + fragment;
        }
    }

    // Add links to buttons that block snippets.
    function addSnippetBlockLinks(elements) {
        var snippet_id = ABOUTHOME_SHOWN_SNIPPET.id;
        var blockSnippet = function (event) {
            event.preventDefault();
            addToBlockList(snippet_id, function() {
              sendMetric('snippet-blocked', function() {
                window.location.reload();
              })
            });
        };

        for (var k = 0; k < elements.length; k++) {
            var button = elements[k];
            button.addEventListener('click', blockSnippet);
        }
    }

    // Bug 1238092. Got fixed in Fx45. We can drop this when Fx44
    // usage drops significantly.
    function keypressIsMine(snippet) {
        snippet.addEventListener('keypress', function(event) {
            var tagName = event.target.tagName.toLowerCase();
            if (tagName === 'input' || tagName === 'select') {
                event.stopPropagation();
            }
        });
    }

    // Check for localStorage support. Copied from Modernizr.
    function supportsLocalStorage() {
        var s = 'snippets-test';
        try {
            localStorage.setItem(s, s);
            localStorage.removeItem(s);
            return true;
        } catch(e) {
            return false;
        }
    }

    // Scripts injected by innerHTML are inactive, so we have to relocate them
    // through DOM manipulation to activate their contents.
    // (Adapted from http://mxr.mozilla.org/mozilla-central/source/browser/base/content/abouthome/aboutHome.js)
    function activateScriptTags(element) {
       Array.forEach(element.getElementsByTagName('script'), function(elt) {
           var relocatedScript = document.createElement('script');
           relocatedScript.type = 'text/javascript;version=1.8';
           relocatedScript.text = elt.text;
           elt.parentNode.replaceChild(relocatedScript, elt);
       });
    }

    // Listen for clicks on links, send metrics and handle
    // about:account custom links.
    var topSection = document.getElementById('topSection');
    topSection.addEventListener('click', function(event) {
        var target = event.target;
        while (target.tagName && target.tagName.toLowerCase() !== 'a') {
            // Do not track clicks outside topSection.
            if (target.id === 'topSection') {
                return;
            }
            target = target.parentNode;
        }

        // Count snippet clicks.
        if (target.dataset.eventCounted !== 'true') {
            target.dataset.eventCounted = 'true';
            // Fetch custom metric or default to 'click'
            var metric = target.dataset.metric || 'click';
            // If user is not opening a new tab, preventDefault action.
            if (target.href && (event.button === 0 && !(event.metaKey || event.ctrlKey))) {
                event.preventDefault();
                var callback = function() {
                    target.click();
                }
            }
            sendMetric(metric, callback);
        }

        // Handle about:accounts clicks.
        if (target.href && target.href.indexOf('about:accounts') === 0) {
            var snippet_id = ABOUTHOME_SHOWN_SNIPPET.id;
            var metric = snippet_id + '-about-accounts-click';
            var fire_event = function() {
                var event = new CustomEvent(
                    'mozUITour',
                    { bubbles: true, detail: { action:'showFirefoxAccounts', data: {}}}
                );
                document.dispatchEvent(event);
            };
            sendMetric(metric, fire_event);
        }
    }, false);

    function popFromBlockList(snippetID) {
      var blockList = getBlockList();
      var item = blockList.pop(snippetID);
      gSnippetsMap.set('blockList', blockList);
      return item;
    }

    function addToBlockList(snippetID, callback) {
      var blockList = getBlockList();
      snippetID = parseInt(snippetID, 10);
      if (blockList.indexOf(snippetID) === -1) {
          blockList = [snippetID].concat(blockList);
          gSnippetsMap.set('blockList', blockList, callback);
      }
    }

    function getBlockList() {
      if (gSnippetsMap.get('blockList') === undefined) {
          gSnippetsMap.set('blockList', []);
      }
      return gSnippetsMap.get('blockList');
    }
  }

  initBlockList(blockListReady);
})(window.showDefaultSnippets);

// Send impressions and other interactions to the service
// If no parameter is entered, quit function
function sendMetric(metric, callback) {
    {# In preview mode, disable sampling, log metric, but do not send to service #}
    {% if preview %}
      console.log("[preview mode] Sending metric: " + metric);
      if (callback) {
          callback();
      }
      return;
    {% else %}
      if ((Math.random() > SNIPPET_METRICS_SAMPLE_RATE) || (!metric)) {
          if (callback) {
              callback();
          }
          return;
      }

      var locale = '{{ locale }}';
      var userCountry = USER_COUNTRY || '';
      var campaign = ABOUTHOME_SHOWN_SNIPPET.campaign;
      var snippet_id = ABOUTHOME_SHOWN_SNIPPET.id;

      var url = (SNIPPET_METRICS_URL + '?snippet_name=' + snippet_id +
                 '&locale=' + locale + '&country=' + userCountry +
                 '&metric=' + metric + '&campaign=' + campaign);
      var request = new XMLHttpRequest();
      request.open('GET', url);
      if (callback) {
          request.addEventListener('loadend', callback, false);
      }
      request.send();
      return request;
    {% endif %}
}
//]]>
</script>
