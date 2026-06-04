/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

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
        const monday = startOfWeek(new Date());
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);
        this.state = useState({
            date_from: isoDate(monday),
            date_to: isoDate(sunday),
            technicians: [],
            visitas: [],
        });
        onWillStart(() => this._fetch());
    }

    async _fetch() {
        const data = await this.orm.call(
            "afr.qualificacao.os.visita", "board_fetch",
            [this.state.date_from, this.state.date_to]
        );
        this.state.technicians = data.technicians;
        this.state.visitas = data.visitas;
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
    async onDrop(ev, tecnicoId, day) {
        ev.preventDefault();
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
        });
    }
}
VisitaBoard.template = "afr_qualificacao_agendamento.VisitaBoard";
registry.category("actions").add("afr_qualif_visita_board", VisitaBoard);
