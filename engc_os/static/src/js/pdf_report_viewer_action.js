/** @odoo-module **/

/**
 * Componente que exibe PDF de relatórios em WebView (iframe com PDF.js).
 * Abre o PDF dentro do app em vez de fazer download ou abrir em nova aba.
 * Usado quando o usuário gera um relatório PDF (ex: Ordem de Serviço, Checklist, etc).
 */

import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, useRef, useSubEnv } from "@odoo/owl";

export class PdfReportViewerAction extends Component {
    setup() {
        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });
        useSetupAction();

        this.actionService = useService("action");
        this.title = this.props.display_name || this.props.name || "PDF";
        this.pdfViewerUrl = this.props.pdfViewerUrl;
        this.iframe = useRef("iframe");
    }

    /**
     * Abre o diálogo de impressão do navegador (o PDF.js viewer gerencia isso).
     */
    onPrint() {
        try {
            const iframeEl = this.iframe.el;
            if (iframeEl && iframeEl.contentWindow) {
                iframeEl.contentWindow.print();
            }
        } catch (e) {
            this.env.services.notification.add(
                "Não foi possível abrir a impressão. Use Ctrl+P no visualizador.",
                { type: "warning" }
            );
        }
    }
}

PdfReportViewerAction.components = { Layout };
PdfReportViewerAction.template = "engc_os.PdfReportViewerAction";

/**
 * Constrói a URL do relatório PDF no mesmo formato do Odoo core (_getReportUrl).
 * @param {Object} action - ir.actions.report
 * @param {Object} env - ambiente (para context do usuário)
 * @returns {string}
 */
function getReportPdfUrl(action, env) {
    let url = `/report/pdf/${action.report_name}`;
    const actionContext = action.context || {};
    if (action.data && JSON.stringify(action.data) !== "{}") {
        const options = encodeURIComponent(JSON.stringify(action.data));
        const context = encodeURIComponent(JSON.stringify(actionContext));
        url += `?options=${options}&context=${context}`;
    } else {
        if (actionContext.active_ids && actionContext.active_ids.length) {
            const ids = Array.isArray(actionContext.active_ids)
                ? actionContext.active_ids
                : [actionContext.active_ids];
            url += `/${ids.join(",")}`;
        }
        // Context necessário para alguns relatórios; session também fornece user/company.
        const context = encodeURIComponent(
            JSON.stringify(env.services?.user?.context || actionContext)
        );
        url += (url.includes("?") ? "&" : "?") + `context=${context}`;
    }
    return url;
}

/**
 * Handler para ir.actions.report: abre PDF em WebView (iframe) em vez de download.
 * Registrado com sequence=1 para rodar antes do default.
 */
async function pdfReportWebViewHandler(action, options, env) {
    if (action.report_type !== "qweb-pdf") {
        return null;
    }
    const state = await env.services.rpc("/report/check_wkhtmltopdf");
    // Só abre no WebView se wkhtmltopdf estiver ok ou upgrade
    if (state !== "ok" && state !== "upgrade") {
        return null; // deixa o handler padrão tratar (mostra HTML ou notificação)
    }
    const pdfUrl = getReportPdfUrl(action, env);
    const pdfViewerUrl =
        "/web/static/lib/pdfjs/web/viewer.html?file=" +
        encodeURIComponent(pdfUrl);
    return env.services.action.doAction({
            type: "ir.actions.client",
            tag: "engc_os.PdfReportViewerAction",
            name: action.display_name || action.name || "PDF",
            display_name: action.display_name || action.name || "PDF",
            target: "current",
            context: {},
        props: {
            pdfViewerUrl,
            display_name: action.display_name || action.name || "PDF",
        },
    });
}

registry.category("actions").add("engc_os.PdfReportViewerAction", PdfReportViewerAction);

// Handler com prioridade alta para rodar antes do default (abre PDF em WebView em vez de download)
registry
    .category("ir.actions.report handlers")
    .add("engc_os_pdf_webview", pdfReportWebViewHandler, { sequence: 1 });
