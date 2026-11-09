/** @odoo-module **/
// Hero da home: cena 3D dos demos /qualificacao/<slug> rodando em ciclo
// automático ao fundo do <section class="lq-hero">. Os quadros vêm do
// controller dos demos (o static do módulo é sombreado no servidor).
//
// A cena é injetada em runtime e removida no destroy(): o publicWidget é
// destruído antes do editor do site salvar, então nada disso vai pro arch.
import publicWidget from "web.public.widget";

const EQUIPMENTS = [
    { slug: "autoclave", name: "Autoclaves", scope: "Qualificação QI · QO · QD" },
    { slug: "estufa", name: "Estufas", scope: "Qualificação térmica" },
    { slug: "termodesinfectora", name: "Termodesinfectoras", scope: "Qualificação de processo" },
    { slug: "camara-fria", name: "Câmaras Frias", scope: "Mapeamento térmico" },
];
const TOTAL_FRAMES = 150;
const FPS = 12.5;

function frameUrl(slug, n) {
    return `/qualificacao/${slug}/seq/f_${String(n).padStart(4, "0")}.webp`;
}

publicWidget.registry.LqHeroScene = publicWidget.Widget.extend({
    selector: ".lq-hero",

    start() {
        const mobile = window.matchMedia("(max-width: 767.98px)").matches;
        this.step = mobile ? 6 : 3;
        this.reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        this.frames = EQUIPMENTS.map(() => []);
        this.ready = EQUIPMENTS.map(() => false);
        this.eq = 0;
        this.idx = 0;
        this.visible = true;
        this._buildDom();
        this._showMeta();
        if (this.reduced) {
            this.img.src = frameUrl(EQUIPMENTS[0].slug, 1);
            return this._super(...arguments);
        }
        this._preload(0).then(() => this._preloadRest(1));
        this._observe();
        this._onScroll = this._onScroll.bind(this);
        window.addEventListener("scroll", this._onScroll, { passive: true });
        this._last = 0;
        this._tick = this._tick.bind(this);
        this._raf = requestAnimationFrame(this._tick);
        return this._super(...arguments);
    },

    destroy() {
        cancelAnimationFrame(this._raf);
        cancelAnimationFrame(this._scrollRaf);
        if (this._onScroll) {
            window.removeEventListener("scroll", this._onScroll);
        }
        if (this._io) {
            this._io.disconnect();
        }
        if (this.scene) {
            this.scene.remove();
            this.meta.remove();
        }
        this._super(...arguments);
    },

    _buildDom() {
        this.scene = document.createElement("div");
        this.scene.className = "lq-hero-scene";
        this.scene.setAttribute("aria-hidden", "true");
        this.img = document.createElement("img");
        this.img.alt = "";
        this.img.src = frameUrl(EQUIPMENTS[0].slug, 1);
        this.scene.appendChild(this.img);

        this.meta = document.createElement("div");
        this.meta.className = "lq-hero-meta";
        this.dots = document.createElement("div");
        this.dots.className = "lq-hero-dots";
        EQUIPMENTS.forEach(() => this.dots.appendChild(document.createElement("i")));
        this.link = document.createElement("a");
        this.link.className = "lq-hero-tag";
        this.link.target = "_blank";
        this.link.rel = "noopener";
        this.link.innerHTML = "<small></small><strong></strong>";
        this.meta.append(this.dots, this.link);

        this.el.prepend(this.scene);
        this.el.appendChild(this.meta);
    },

    _showMeta() {
        const eq = EQUIPMENTS[this.eq];
        this.link.href = `/qualificacao/${eq.slug}`;
        this.link.querySelector("small").textContent = eq.scope;
        this.link.querySelector("strong").textContent = eq.name;
        const dur = (TOTAL_FRAMES / this.step / FPS).toFixed(2) + "s";
        [...this.dots.children].forEach((d, i) => {
            d.className = "";
            d.style.setProperty("--lq-dur", dur);
            if (i === this.eq) {
                void d.offsetWidth; // reinicia a animação da barra
                d.className = this.reduced ? "is-on is-static" : "is-on";
            }
        });
    },

    _preload(i) {
        const slug = EQUIPMENTS[i].slug;
        const loads = [];
        for (let n = 1; n <= TOTAL_FRAMES; n += this.step) {
            const im = new Image();
            im.decoding = "async";
            im.src = frameUrl(slug, n);
            this.frames[i].push(im);
            loads.push(new Promise((res) => { im.onload = im.onerror = res; }));
        }
        return Promise.all(loads).then(() => { this.ready[i] = true; });
    },

    _preloadRest(i) {
        if (i >= EQUIPMENTS.length || this.isDestroyed()) {
            return;
        }
        this._preload(i).then(() => this._preloadRest(i + 1));
    },

    _observe() {
        if (!("IntersectionObserver" in window)) {
            return;
        }
        this._io = new IntersectionObserver((entries) => {
            this.visible = entries[0].isIntersecting;
        });
        this._io.observe(this.el);
    },

    _tick(t) {
        this._raf = requestAnimationFrame(this._tick);
        if (!this.visible || document.hidden || !this.ready[this.eq] || t - this._last < 1000 / FPS) {
            return;
        }
        this._last = t;
        const list = this.frames[this.eq];
        this.img.src = list[this.idx].src;
        this.idx += 1;
        if (this.idx >= list.length) {
            this.idx = 0;
            const next = (this.eq + 1) % EQUIPMENTS.length;
            if (this.ready[next]) { // senão repete o atual até o próximo carregar
                this.eq = next;
                this._showMeta();
            }
        }
    },

    _onScroll() {
        cancelAnimationFrame(this._scrollRaf);
        this._scrollRaf = requestAnimationFrame(() => {
            const y = Math.min(window.scrollY, this.el.offsetHeight);
            this.scene.style.transform = `translate3d(0, ${y * 0.25}px, 0) scale(${1 + y * 0.0004})`;
        });
    },
});

export default publicWidget.registry.LqHeroScene;
