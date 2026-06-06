/** @odoo-module **/
import { Component, useState, onWillStart, useExternalListener } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

function isoDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}
function parseISO(s) {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(y, m - 1, d);
}
function addDays(s, n) {
    const d = parseISO(s);
    d.setDate(d.getDate() + n);
    return isoDate(d);
}
function startOfWeek(date) {
    const x = new Date(date);
    const dow = (x.getDay() + 6) % 7; // segunda = 0
    x.setDate(x.getDate() - dow);
    return x;
}

export class VisitaBoard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        const monday = startOfWeek(new Date());
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        this.state = useState({
            date_from: isoDate(monday),
            date_to: isoDate(sunday),
            technicians: [],
            visitas: [],
            pinnedTecnicos: [],
            openDropdown: null,
            tecnicoOptions: [],
            osOptions: [],
            tecnicoOptionsLoaded: false,
            osOptionsLoaded: false,
            dropdownPos: { top: 0, left: 0 },
            osFilter: "",
        });
        useExternalListener(window, "click", () => this.closeDropdowns());
        onWillStart(() => this._fetch());
    }

    async _fetch() {
        const data = await this.orm.call(
            "afr.qualificacao.os.visita", "board_fetch",
            [this.state.date_from, this.state.date_to]
        );
        this.state.technicians = data.technicians;
        this.state.visitas = data.visitas;
        // invalida cache de opções: OS pode ter mudado de estado / técnicos remarcados
        this.state.tecnicoOptionsLoaded = false;
        this.state.osOptionsLoaded = false;
    }

    get days() {
        const out = [];
        let cur = this.state.date_from;
        let guard = 0;
        while (cur <= this.state.date_to && guard < 366) {
            out.push(cur);
            cur = addDays(cur, 1);
            guard++;
        }
        return out;
    }

    get displayTechnicians() {
        const byId = {};
        for (const t of this.state.technicians) {
            byId[t.id] = { id: t.id, name: t.name };
        }
        for (const t of this.state.pinnedTecnicos) {
            if (!byId[t.id]) {
                byId[t.id] = { id: t.id, name: t.name };
            }
        }
        return Object.values(byId).sort((a, b) =>
            (a.name || "").localeCompare(b.name || ""));
    }

    get availableTecnicoOptions() {
        // só técnicos que ainda NÃO estão no board
        const present = new Set(this.displayTechnicians.map((t) => t.id));
        return this.state.tecnicoOptions.filter((t) => !present.has(t.id));
    }

    _span() {
        return Math.round(
            (parseISO(this.state.date_to) - parseISO(this.state.date_from)) / 86400000
        ) + 1;
    }

    cellVisitas(tecnicoId, day) {
        return this.state.visitas.filter(
            (v) => v.tecnico_id === tecnicoId && v.date === day
        );
    }

    colorClass(osId) {
        return "o_vb_color_" + (((osId || 0) % 8) + 1);
    }

    dayLabel(day) {
        return parseISO(day).toLocaleDateString(undefined, {
            weekday: "short", day: "2-digit", month: "2-digit",
        });
    }

    barTitle(v) {
        let t = `${v.os_name} · ${v.partner_name} · ${v.planned_hours}h`;
        if (v.equipment_names) {
            t += ` · ${v.equipment_names}`;
        }
        if (v.conflict && v.conflict_msg) {
            t += ` · ⚠ ${v.conflict_msg}`;
        }
        return t;
    }

    async openTecnicoDropdown() {
        if (!this.state.tecnicoOptionsLoaded) {
            this.state.tecnicoOptions = await this.orm.call(
                "afr.qualificacao.os.visita", "board_technician_options", []);
            this.state.tecnicoOptionsLoaded = true;
        }
        this.state.openDropdown =
            this.state.openDropdown === "tecnico" ? null : "tecnico";
    }
    addTecnico(tec) {
        if (!this.state.pinnedTecnicos.some((t) => t.id === tec.id)) {
            this.state.pinnedTecnicos.push({ id: tec.id, name: tec.name });
        }
        this.state.openDropdown = null;
    }
    async openOsDropdown(tecnicoId, day) {
        if (!this.state.osOptionsLoaded) {
            this.state.osOptions = await this.orm.call(
                "afr.qualificacao.os.visita", "board_os_options", []);
            this.state.osOptionsLoaded = true;
        }
        this.state.osFilter = "";
        const key = `os:${tecnicoId}:${day}`;
        this.state.openDropdown = this.state.openDropdown === key ? null : key;
    }
    get filteredOsOptions() {
        const q = (this.state.osFilter || "").trim().toLowerCase();
        if (!q) { return this.state.osOptions; }
        return this.state.osOptions.filter(
            (o) => (o.name || "").toLowerCase().includes(q));
    }
    onOsFilterInput(ev) { this.state.osFilter = ev.target.value; }
    async addVisita(osId, tecnicoId, day) {
        this.state.openDropdown = null;
        await this.orm.call("afr.qualificacao.os.visita", "board_create_visita",
            [osId, tecnicoId, day]);
        await this._fetch();
    }
    async onSplitOverflow(ev, visitaId) {
        ev.stopPropagation();
        await this.orm.call("afr.qualificacao.os.visita",
            "board_split_overflow", [visitaId]);
        await this._fetch();
    }
    onDeleteVisita(ev, visitaId) {
        ev.stopPropagation();
        this.dialog.add(ConfirmationDialog, {
            title: "Apagar visita",
            body: "Tem certeza que deseja apagar esta visita?",
            confirmLabel: "Apagar",
            cancelLabel: "Cancelar",
            confirm: async () => {
                await this.orm.call("afr.qualificacao.os.visita",
                    "board_delete_visita", [visitaId]);
                await this._fetch();
            },
            cancel: () => {},
        });
    }
    hhmm(f) {
        // float horas → "HH:MM"
        const h = Math.floor(f || 0);
        let m = Math.round(((f || 0) - h) * 60);
        let hh = h;
        if (m === 60) { m = 0; hh = h + 1; }
        return String(hh).padStart(2, "0") + ":" + String(m).padStart(2, "0");
    }
    _toFloat(s) {
        // "HH:MM" → float horas
        const [h, m] = (s || "0:0").split(":").map(Number);
        return (h || 0) + (m || 0) / 60;
    }
    async onSetHour(ev, visitaId, which, currentStart, currentStop) {
        ev.stopPropagation();
        const val = this._toFloat(ev.target.value);
        const start = which === "start" ? val : currentStart;
        const stop = which === "stop" ? val : currentStop;
        await this.orm.call("afr.qualificacao.os.visita",
            "board_set_hours", [visitaId, start, stop]);
        await this._fetch();
    }
    stopBar(ev) { ev.stopPropagation(); }
    closeDropdowns() {
        if (this.state.openDropdown !== null) {
            this.state.openDropdown = null;
        }
    }
    onAddTecnicoClick(ev) {
        ev.stopPropagation();
        this._captureDropdownPos(ev);
        this.openTecnicoDropdown();
    }
    onAddVisitaClick(ev, tecnicoId, day) {
        ev.stopPropagation();
        this._captureDropdownPos(ev);
        this.openOsDropdown(tecnicoId, day);
    }
    stopDropdownClick(ev) { ev.stopPropagation(); }
    _captureDropdownPos(ev) {
        // posição fixed do botão clicado — escapa ao clipping dos overflows ancestrais
        const rect = ev.currentTarget.getBoundingClientRect();
        const width = 220; // min-width do dropdown
        let left = rect.left;
        if (left + width > window.innerWidth) {
            left = Math.max(8, window.innerWidth - width - 8);
        }
        this.state.dropdownPos = { top: rect.bottom, left: left };
    }
    get dropdownStyle() {
        const p = this.state.dropdownPos;
        return `position:fixed;top:${p.top}px;left:${p.left}px;`;
    }

    get todayDate() {
        return isoDate(new Date());
    }

    async prevRange() {
        const span = this._span();
        this.state.date_from = addDays(this.state.date_from, -span);
        this.state.date_to = addDays(this.state.date_to, -span);
        await this._fetch();
    }
    async nextRange() {
        const span = this._span();
        this.state.date_from = addDays(this.state.date_from, span);
        this.state.date_to = addDays(this.state.date_to, span);
        await this._fetch();
    }
    async today() {
        const monday = startOfWeek(new Date());
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        this.state.date_from = isoDate(monday);
        this.state.date_to = isoDate(sunday);
        await this._fetch();
    }
    async onChangeFrom(ev) { this.state.date_from = ev.target.value; await this._fetch(); }
    async onChangeTo(ev) { this.state.date_to = ev.target.value; await this._fetch(); }

    onDragStart(ev, visitaId) {
        ev.dataTransfer.setData("text/plain", String(visitaId));
        ev.dataTransfer.effectAllowed = "move";
    }
    onDragOver(ev) { ev.preventDefault(); ev.dataTransfer.dropEffect = "move"; }
    onDragEnter(ev) {
        ev.currentTarget.classList.add("o_vb_drop_active");
    }
    onDragLeave(ev) {
        if (!ev.relatedTarget || !ev.currentTarget.contains(ev.relatedTarget)) {
            ev.currentTarget.classList.remove("o_vb_drop_active");
        }
    }
    async onDrop(ev, tecnicoId, day) {
        ev.preventDefault();
        ev.currentTarget.classList.remove("o_vb_drop_active");
        const visitaId = parseInt(ev.dataTransfer.getData("text/plain"), 10);
        if (!visitaId) { return; }
        await this.orm.call(
            "afr.qualificacao.os.visita", "board_reschedule",
            [visitaId, day, tecnicoId]
        );
        await this._fetch();
    }

    openVisita(visitaId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "afr.qualificacao.os.visita",
            res_id: visitaId,
            views: [[false, "form"]],
            target: "new",
        }, {
            onClose: () => this._fetch(),
        });
    }
}
VisitaBoard.template = "afr_qualificacao_agendamento.VisitaBoard";
registry.category("actions").add("afr_qualif_visita_board", VisitaBoard);
