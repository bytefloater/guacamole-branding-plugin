(function patchTranslate() {

    var linked = /@:([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)/g;

    function applyPatch(injector) {
        var $translate = injector.get('$translate');
        var original   = $translate.instant.bind($translate);

        $translate.instant = function(id, params, interpolationId, lang, sanitize) {
            var result = original(id, params, interpolationId, lang, sanitize);
            if (typeof result === 'string' && result.indexOf('@:') !== -1) {
                result = result.replace(linked, function(match, refKey) {
                    var resolved = original(refKey);
                    return (resolved !== refKey) ? resolved : match;
                });
            }
            return result;
        };
        console.log('[branding] $translate.instant patched');
    }

    document.addEventListener('DOMContentLoaded', function() {
        // Try html element first (ng-app lives here), fall back to body
        var injector = angular.element(document.documentElement).injector()
                    || angular.element(document.body).injector();

        if (injector) {
            applyPatch(injector);
        } else {
            // Angular may still be bootstrapping — wait one tick
            setTimeout(function() {
                var injector = angular.element(document.documentElement).injector()
                            || angular.element(document.body).injector();
                if (injector) {
                    applyPatch(injector);
                } else {
                    console.error('[branding] Could not get AngularJS injector');
                }
            }, 0);
        }
    });

})();