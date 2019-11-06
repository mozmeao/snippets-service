List of Targeting Attributes
============================

This is a list of available targeting attributes for ASRSnippets (Activity
Stream Router).


 #. **Browser's Channel:** A choice among Release, Beta, ESR, Dev and Nightly.

 #. **Browser's Locale:** The Browser's locale.

 #. **Default Browser:** Is Firefox set as the Default Browser on the OS level?
    "Yes" or "No".

 #. **Profile Age (created):** How long ago was the Profile created? Can be
    anything from hours to months to years. Supports ranges, e.g. From one day
    to fourteen days, to target users during their first two weeks of using
    Firefox.

 #. **Previous Session End:** How long ago was this Profile last used? Can be
    anything from hours to months to years. Supports ranges, e.g. From 0 to 24
    hours, to targets users who open their Firefox daily.

 #. **Firefox Version:** Current Firefox Version. Supports ranges.

 #. **Uses Firefox Sync:** Is there a connected Firefox Account Syncing? "Yes" or
    "No".

 #. **Firefox Services Enabled:** Has the connected Firefox Account signed up for
    other Firefox Services? A choice of "Yes" or "No" for Lockwise, Monitor,
    Send, FPN, Notes and Pocket.

 #. **Country:** User's Country based on Geo-Location.

 #. **Is Developer:** Is the user a Developer? This is decided based on the
    number of times the user has opened the Firefox DevTools. We consider them a
    developer is opened count is equal or above 5.

 #. **Current Search Engine:** Current default Search Engine.

 #. **Total bookmarks count:** Total number of bookmarks set by the User. Supports
    ranges.

 #. **Desktop Devices Count:** Number of Desktop Devices connected to Firefox
    Sync. Supports ranges.

 #. **Mobile Devices Count:** Number of Mobile Devices connected to Firefox
    Sync. Supports ranges.

 #. **Total Devices Count:** Total number of Devices connected to Firefox Sync.
    Supports ranges.

 #. **Can Install Addons:** Can the user install Addons or blocked by the Admin?
    "Yes" or "No"

 #. **Total Addons:** Total number of installed Addons.

 #. **Browser Addon:** Is a Addon installed or not installed? Can target any
    available Addon.

 #. **Operating System:** User's operating system. A choice among "Windows", "Mac"
    and "Linux".

 #. **Updates Enabled:** Are updates enabled? "Yes" or "No"

 #. **Updates Autodownload Enabled:** Is updates auto-download enabled? "Yes" or
    "No".

All targeting options except for Channel and Locale are optional.

Also all targeting except for Channel and Locale happens on the Browser, in the
Activity Stream component which selects the best Snippet to display.
