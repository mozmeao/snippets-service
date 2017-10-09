'use strict';

var SNIPPET_METRICS_SAMPLE_RATE = {{ settings.METRICS_SAMPLE_RATE }};
var SNIPPET_METRICS_URL = '{{ metrics_url }}';
var ABOUTHOME_SHOWN_SNIPPET = null;
var USER_COUNTRY = null;
var GEO_CACHE_DURATION = 1000 * 60 * 60 * 24 * 30; // 30 days

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
        showCallbackID: showCallbackID
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
        value: configValue
    });
};
// End MozUITour


(function(showDefaultSnippets) {
    'use strict';

    // showDefaultSnippets polyfill, available in about:home v4
    if (typeof showDefaultSnippets !== 'function') {
        showDefaultSnippets = function() {
            localStorage.snippets = '';
            showSnippets();
        };
    }

    // gSnippetsMap polyfill, available in Firefox 22 and above.
    var gSnippetsMap = null;
    if (supportsLocalStorage()) {
        // localStorage is available, so we wrap it with gSnippetsMap.
        gSnippetsMap = {
            set: function(key, value) {
                localStorage[key] = value;
            },
            get: function(key) {
                return localStorage[key];
            }
        };
        window.gSnippetsMap = gSnippetsMap;
    } else {
        // localStorage isn't available, use gSnippetsMap (backed by IndexedDB).
        gSnippetsMap = window.gSnippetsMap;
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

    // Get appinfo from UITour
    updateAppInfoStatus();

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
            );
        }

        // Filter Snippets based on the has_fxaccount attribute.
        var has_fxaccount = gSnippetsMap.get('fxaccount');
        if (has_fxaccount === true) {
            snippets = snippets.filter(
                function(snippet) {
                    return (snippet.client_options.has_fxaccount == 'yes' ||
                            snippet.client_options.has_fxaccount == 'any');
                }
            );
        } else if (has_fxaccount === false) {
            snippets = snippets.filter(
                function(snippet) {
                    return (snippet.client_options.has_fxaccount == 'no' ||
                            snippet.client_options.has_fxaccount == 'any');
                }
            );
        } else {
            snippets = snippets.filter(
                function(snippet) {
                    return (snippet.client_options.has_fxaccount == 'any');
                }
            );
        }

        // Filter Snippets based on TestPilot addon existence.
        var has_testpilot = Boolean(window.navigator.testpilotAddon);
        if (has_testpilot === true) {
            snippets = snippets.filter(
                function(snippet) {
                    return (snippet.client_options.has_testpilot == 'yes' ||
                            snippet.client_options.has_testpilot == 'any');
                }
            );
        } else {
            snippets = snippets.filter(
                function(snippet) {
                    return (snippet.client_options.has_testpilot == 'no' ||
                            snippet.client_options.has_testpilot == 'any');
                }
            );
        }

        // Filter Snippets based on whether Firefox is the default browser or now.
        var appInfo = gSnippetsMap.get('appInfo');
        if (appInfo && (appInfo.defaultBrowser === true || appInfo.defaultBrowser === undefined)) {
            snippets = snippets.filter(
                function(snippet) {
                    return (snippet.client_options.is_default_browser == 'yes' ||
                            snippet.client_options.is_default_browser == 'any');
                }
            );
        } else {
            snippets = snippets.filter(
                function(snippet) {
                    return (snippet.client_options.is_default_browser == 'no' ||
                            snippet.client_options.is_default_browser == 'any');
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

        // Filter based on Firefox version
        var userAgent = window.navigator.userAgent.match(/Firefox\/([0-9]+)\./);
        var firefox_version  = userAgent ? parseInt(userAgent[1]) : 0;
        if (firefox_version !== 0) {
            snippets = snippets.filter(
                function(snippet) {
                    var lower_bound = snippet.client_options.version_lower_bound;
                    var upper_bound = snippet.client_options.version_upper_bound;
                    if (lower_bound && lower_bound !== 'any') {
                        if (lower_bound === 'current_release') {
                            if (firefox_version !== CURRENT_RELEASE)
                                return false;
                        }
                        else {
                            if (firefox_version < lower_bound) {
                                return false;
                            }
                        }
                    }
                    if (upper_bound && upper_bound !== 'any') {
                        if (upper_bound === 'older_than_current_release') {
                            if (firefox_version >= CURRENT_RELEASE)
                                return false;
                        }
                        else {
                            if (firefox_version > upper_bound)
                                return false;
                        }
                    }
                    return true;
                });
        }

        // Filter based on screen resolution
        var verticalScreenResolution = screen.width;
        snippets = snippets.filter(
            function(snippet) {
                let snippetResolutions = snippet.client_options.screen_resolutions.split(';');
                let display = false;
                snippetResolutions.forEach(function(resolution) {
                    let minmax = resolution.split('-');
                    if (parseInt(minmax[0]) <= verticalScreenResolution
                        && verticalScreenResolution < parseInt(minmax[1])) {
                        display = true;
                        return;
                    }
                });
                return display;
            }
        );

        // Filter based on Profile age
        //
        // appInfo.profileCreatedWeeksAgo can be either undefined for Firefox
        // versions that don't expose this information, or a number >= 0.
        if (appInfo && appInfo.profileCreatedWeeksAgo !== undefined) {
            let profileAge = appInfo.profileCreatedWeeksAgo;
            snippets = snippets.filter(
                function(snippet) {
                    let lower_bound = snippet.client_options.profileage_lower_bound;
                    let upper_bound = snippet.client_options.profileage_upper_bound;
                    if (lower_bound > -1 && profileAge < lower_bound) {
                        return false;
                    }
                    if (upper_bound > -1 && profileAge >= upper_bound) {
                        return false;
                    }
                    return true;
                }
            );
        }
        else {
            // Remove all snippets that use profile age since this information
            // is not available.
            snippets = snippets.filter(
                function(snippet) {
                    if (snippet.client_options.profileage_lower_bound > -1
                        || snippet.client_options.profileage_upper_bound > -1) {
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
                var blockID = snippet.campaign || snippet.id;
                if (blockList.indexOf(blockID) === -1) {
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

    function updateFxAccountStatus() {
        var callback = function(result) {
            gSnippetsMap.set('fxaccount', result.setup);
        };
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

    function updateAppInfoStatus() {
        var callback = function(result) {
            gSnippetsMap.set('appInfo', result);
        };
        var event = new CustomEvent(
            'mozUITour', {
                bubbles: true,
                detail: {
                    action:'getConfiguration',
                    data: {
                        configuration: 'appinfo',
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
        };
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
        var blockSnippet = function (event) {
            event.preventDefault();
            event.stopPropagation();

            addToBlockList();

            // Waiting for 500ms before reloading the page after user blocks a snippet,
            // will allow the IndexedDB more time to complete its transaction. While
            // this is an imperfect non-deterministic solution it will fix the issue
            // for most of the users. Ideally we would create our own
            // connection to the iDB and ensure that the write completes
            // before we reload the page. Bug 1236090.
            function reloadWindow() {
                window.location.reload();
            }
            sendMetric('snippet-blocked', function() { setTimeout(reloadWindow, 500); });
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
        var callback;
        var metric;
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
            metric = target.dataset.metric || 'click';
            if (target.href) {
                // First handle the special about:accounts links which have
                // custom metric and need to call showFirefoxAccounts method.
                // Due to the special nature of about:accounts we can only open
                // in the same tab. For other links if user is not opening a new
                // tab, preventDefault action.
                if (target.href.indexOf('about:accounts') === 0) {
                    // Custom metric for about:accounts links
                    metric = target.dataset.metric || ABOUTHOME_SHOWN_SNIPPET.id + '-about-accounts-click';
                    callback = function() {
                        var event = new CustomEvent(
                            'mozUITour',
                            { bubbles: true, detail: { action:'showFirefoxAccounts', data: {}}}
                        );
                        document.dispatchEvent(event);
                    };
                }
                else if (event.button === 0 && !(event.metaKey || event.ctrlKey)) {
                    event.preventDefault();
                    callback = function() {
                        target.click();
                    };
                }
            }
            sendMetric(metric, callback, target.href);
        }
    }, false);
})(window.showDefaultSnippets);

// Send impressions and other interactions to the service
// If no parameter is entered, quit function
function sendMetric(metric, callback, href) {
    {# In preview mode, disable sampling, log metric, but do not send to service #}
    {% if preview %}
      console.log("[preview mode] Sending metric: " + metric);
      if (callback) {
          setTimeout(callback);
      }
      return;
    {% else %}
      if (!SNIPPET_METRICS_URL || (Math.random() > SNIPPET_METRICS_SAMPLE_RATE) || (!metric)) {
          if (callback) {
              // setTimeout is here because when metrics succeeds the callback is async.
              // When we don't use metrics, we should be consistent and
              // fire the callback async too.
              setTimeout(callback);
          }
          return;
      }

      var locale = '{{ locale }}';
      var userCountry = USER_COUNTRY || '';
      var campaign = ABOUTHOME_SHOWN_SNIPPET.campaign;
      var snippet_id = ABOUTHOME_SHOWN_SNIPPET.id;
      var snippet_full_name = ABOUTHOME_SHOWN_SNIPPET.name;

      var url = (SNIPPET_METRICS_URL + '?snippet_name=' + snippet_id +
                 '&snippet_full_name=' + snippet_full_name +
                 '&locale=' + locale + '&country=' + userCountry +
                 '&metric=' + metric + '&campaign=' + campaign);

      if (href) {
          url = url + "&href=" + escape(href);
      }

      var request = new XMLHttpRequest();
      request.open('GET', url);
      if (callback) {
          request.addEventListener('loadend', callback, false);
      }
      request.send();
      return request;
    {% endif %}
}

function popFromBlockList(snippetID) {
    var blockList = getBlockList();
    var item = blockList.pop(snippetID);
    gSnippetsMap.set('blockList', blockList);
    return item;
}

function addToBlockList(snippetID) {
    var blockList = getBlockList();
    if (snippetID === undefined) {
        snippetID = ABOUTHOME_SHOWN_SNIPPET.campaign || ABOUTHOME_SHOWN_SNIPPET.id;
    }
    if (blockList.indexOf(snippetID) === -1) {
        blockList = [snippetID].concat(blockList);
        gSnippetsMap.set('blockList', blockList);
    }
}

function getBlockList() {
    if (gSnippetsMap.get('blockList') === undefined) {
        gSnippetsMap.set('blockList', []);
    }
    return gSnippetsMap.get('blockList');
}
