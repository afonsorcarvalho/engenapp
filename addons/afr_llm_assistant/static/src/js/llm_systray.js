/** @odoo-module **/

/**
 * Ícone no systray que abre o painel do assistente LLM (LM Studio).
 * Usa RPC padrão do ORM para sessão/mensagens no backend.
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { Component, markup, useRef, useState } from "@odoo/owl";

/**
 * Aceita apenas URLs relativas geradas pelo backend (form, anexo, relatório).
 * Evita `javascript:` e caracteres que quebrariam o atributo HTML.
 */
function isSafeOdooHref(path) {
    if (!path || typeof path !== "string" || path.length > 4000) {
        return false;
    }
    if (/[\s<>'"]|^javascript:/i.test(path)) {
        return false;
    }
    if (path.startsWith("/web#")) {
        return /^\/web#[\w.&=%+\-/?:]*$/i.test(path);
    }
    if (path.startsWith("/web/content/")) {
        return /^\/web\/content\/\d+(\?[\w.&=%+\-/]*)?$/.test(path);
    }
    return /^\/report\/(pdf|html|text)\/[a-z0-9_.]+\/[\d,]+$/i.test(path);
}

/**
 * Escapa o texto e envolve paths Odoo (ou Markdown [rótulo](path)) em links `<a>`.
 */
function llmMessageBodyToMarkup(raw) {
    if (!raw) {
        return markup("");
    }
    const parts = [];
    let idx = 0;
    const re =
        /(\[[^\]]{0,400}\]\(\/(?:web#|web\/content\/|report\/(?:pdf|html|text)\/)[^)\s]{1,3000}\))|(\/(?:web#|web\/content\/|report\/(?:pdf|html|text)\/)[^\s<'"]{1,3000})/g;
    let m;
    while ((m = re.exec(raw)) !== null) {
        if (m.index > idx) {
            parts.push(escape(raw.slice(idx, m.index)));
        }
        const token = m[0];
        const md = m[1];
        const bare = m[2];
        if (md) {
            const inner = /^\[([^\]]*)\]\(([^)]+)\)$/.exec(md);
            const href = inner && inner[2];
            const label = inner && inner[1];
            if (inner && href && isSafeOdooHref(href)) {
                const safeHref = href.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
                parts.push(
                    `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${escape(
                        label || href
                    )}</a>`
                );
            } else {
                parts.push(escape(token));
            }
        } else if (bare && isSafeOdooHref(bare)) {
            const safeHref = bare.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
            const disp = bare.length > 120 ? `${bare.slice(0, 117)}…` : bare;
            parts.push(
                `<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${escape(disp)}</a>`
            );
        } else {
            parts.push(escape(token));
        }
        idx = m.index + token.length;
    }
    if (idx < raw.length) {
        parts.push(escape(raw.slice(idx)));
    }
    return markup(parts.join(""));
}

export class LlmSystray extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.messagesRef = useRef("messagesScroll");
        this.state = useState({
            open: false,
            loading: false,
            messages: [],
            sessionId: null,
            input: "",
        });
    }

    /**
     * Executa após o OWL pintar o painel (dois rAF para o scroll medir alturas corretas).
     */
    _scheduleScroll(fn) {
        requestAnimationFrame(() => {
            requestAnimationFrame(() => fn());
        });
    }

    /** Rola a lista até ao fundo (últimas mensagens). */
    _scrollMessagesToEnd() {
        this._scheduleScroll(() => {
            const el = this.messagesRef.el;
            if (el) {
                el.scrollTop = el.scrollHeight;
            }
        });
    }

    /** Coloca o início do corpo da última resposta do assistente no topo da área visível. */
    _scrollToLatestAssistantBodyStart() {
        this._scheduleScroll(() => {
            const container = this.messagesRef.el;
            if (!container) {
                return;
            }
            let lastAssistant = null;
            for (const child of container.children) {
                if (child.classList && child.classList.contains("o_llm_systray_msg_assistant")) {
                    lastAssistant = child;
                }
            }
            const body = lastAssistant && lastAssistant.querySelector(".o_llm_systray_msg_body");
            const target = body || lastAssistant;
            if (target) {
                target.scrollIntoView({ block: "start", behavior: "smooth", inline: "nearest" });
            } else {
                this._scrollMessagesToEnd();
            }
        });
    }

    toggleOpen() {
        this.state.open = !this.state.open;
        if (this.state.open) {
            this.ensureSessionAndLoad();
        }
    }

    onInput(ev) {
        this.state.input = ev.target.value;
    }

    async ensureSessionAndLoad() {
        if (!this.state.sessionId) {
            try {
                this.state.sessionId = await this.orm.call(
                    "afr.llm.chat.session",
                    "get_or_create_my_session",
                    []
                );
            } catch (e) {
                this.notification.add(
                    (e && e.message) || "Não foi possível iniciar a sessão de chat.",
                    { type: "danger" }
                );
                this.state.open = false;
                return;
            }
        }
        await this.loadMessages({ scrollToEnd: true });
    }

    /**
     * @param {Object} [options]
     * @param {boolean} [options.scrollToEnd] — após carregar, ir às últimas mensagens (fundo).
     * @param {boolean} [options.scrollToLatestAssistantStart] — ir ao início do texto da última resposta do assistente.
     */
    async loadMessages(options = {}) {
        if (!this.state.sessionId) {
            return;
        }
        try {
            this.state.messages = await this.orm.searchRead(
                "afr.llm.chat.message",
                [["session_id", "=", this.state.sessionId]],
                ["role", "body", "create_date"],
                { order: "create_date asc, id asc", limit: 200 }
            );
            if (options.scrollToLatestAssistantStart) {
                this._scrollToLatestAssistantBodyStart();
            } else if (options.scrollToEnd) {
                this._scrollMessagesToEnd();
            }
        } catch (e) {
            this.notification.add(
                (e && e.message) || "Erro ao carregar mensagens.",
                { type: "danger" }
            );
        }
    }

    async onSend() {
        const text = (this.state.input || "").trim();
        if (!text || this.state.loading) {
            return;
        }
        if (!this.state.sessionId) {
            await this.ensureSessionAndLoad();
        }
        this.state.loading = true;
        this.state.input = "";
        try {
            const queue = await this.orm.call(
                "afr.llm.chat.session",
                "action_queue_message",
                [this.state.sessionId],
                { text }
            );
            const jobId = queue && queue.job_id;
            if (!jobId) {
                throw new Error("Resposta inválida do servidor (job_id ausente).");
            }
            // RPC longo sem bloquear o indicador global de carregamento do backend.
            const result = await this.orm.silent.call(
                "afr.llm.chat.job",
                "action_process",
                [jobId]
            );
            if (result && result.state === "error" && result.message) {
                this.notification.add(result.message, { type: "danger" });
            }
            await this.loadMessages({ scrollToLatestAssistantStart: true });
        } catch (e) {
            this.notification.add(
                (e && e.message && e.message.data && e.message.data.message) ||
                    (e && e.message) ||
                    "Erro ao enviar mensagem.",
                { type: "danger" }
            );
            await this.loadMessages({ scrollToEnd: true });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Corpo da mensagem com links clicáveis (paths relativos / Markdown do assistente).
     */
    messageToMarkup(body) {
        return llmMessageBodyToMarkup(body || "");
    }

    async onClear() {
        if (!this.state.sessionId || this.state.loading) {
            return;
        }
        this.state.loading = true;
        try {
            await this.orm.call("afr.llm.chat.session", "action_clear_messages", [this.state.sessionId]);
            await this.loadMessages({ scrollToEnd: true });
        } catch (e) {
            this.notification.add(
                (e && e.message) || "Erro ao limpar histórico.",
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }
}

LlmSystray.template = "afr_llm_assistant.LlmSystray";

registry.category("systray").add(
    "afr_llm_assistant.systray",
    { Component: LlmSystray },
    { sequence: 60 }
);
