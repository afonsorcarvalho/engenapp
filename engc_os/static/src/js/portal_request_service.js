/** @odoo-module */

import publicWidget from "web.public.widget";
import "portal.portal"; // força dependência do portal para incluir no PortalHomeCounters

/**
 * Mantém o link "Solicitações de Serviço" sempre visível na home do portal (/my),
 * mesmo quando o contador for zero.
 */
publicWidget.registry.PortalHomeCounters.include({
    _getCountersAlwaysDisplayed() {
        return this._super(...arguments).concat(["request_service_count"]);
    },
});
