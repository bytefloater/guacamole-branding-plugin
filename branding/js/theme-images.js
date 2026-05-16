(function () {
    var BASE = 'app/ext/branding/images/settings/';

    function isDark() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    function updateImages() {
        var suffix = isDark() ? 'dark' : 'light';
        document.querySelectorAll('img').forEach(function (img) {
            if (img.src.includes('touchscreen') && !img.src.includes('-' + suffix)) {
                img.src = BASE + 'touchscreen-' + suffix + '.svg';
            } else if (img.src.includes('touchpad') && !img.src.includes('-' + suffix)) {
                img.src = BASE + 'touchpad-' + suffix + '.svg';
            }
        });
    }

    function init() {
        var observer = new MutationObserver(function (mutations) {
            for (var i = 0; i < mutations.length; i++) {
                if (mutations[i].addedNodes.length) {
                    updateImages();
                    break;
                }
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
        updateImages();
    }

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateImages);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
