/*
 * LabQuali Homepage — animações GSAP
 * Libs vendored: GSAP 3.12.5 + ScrollTrigger (static/src/lib/)
 *
 * Estados iniciais definidos via JS (gsap.from/gsap.set), NUNCA via CSS opacity:0,
 * para que o conteúdo permaneça visível se o JS não rodar (editor Odoo, falha de
 * carregamento, prefers-reduced-motion).
 */
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        // ---- GUARDS ----
        // editor do Odoo Website aberto → não animar (evita esconder conteúdo em edição)
        if (document.body.classList.contains("editor_enable")) {
            return;
        }
        // respeitar preferência de movimento reduzido
        if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        // libs ausentes → bail (conteúdo já está visível)
        if (!window.gsap || !window.ScrollTrigger) {
            return;
        }
        // só roda na homepage LabQuali
        if (!document.querySelector(".lq-hero")) {
            return;
        }

        var gsap = window.gsap;
        gsap.registerPlugin(window.ScrollTrigger);

        var toArray = gsap.utils.toArray;

        // ================= HERO — entrada no load =================
        var heroEls = toArray(
            ".lq-hero .lq-hero-badge, .lq-hero h1, .lq-hero .lq-hero-sub, .lq-hero .d-flex a, .lq-hero .lq-hero-stats > div"
        );
        gsap.set(heroEls, { willChange: "transform, opacity" });
        var heroTl = gsap.timeline({
            defaults: { ease: "power3.out", duration: 0.9 },
            onComplete: function () {
                gsap.set(heroEls, { clearProps: "willChange" });
            },
        });
        heroTl
            .from(".lq-hero .lq-hero-badge", { y: 30, opacity: 0, duration: 0.6 })
            .from(".lq-hero h1", { y: 40, opacity: 0 }, "-=0.35")
            .from(".lq-hero .lq-hero-sub", { y: 30, opacity: 0 }, "-=0.55")
            .from(".lq-hero .d-flex a", { y: 24, opacity: 0, stagger: 0.12 }, "-=0.5")
            .from(".lq-hero .lq-hero-stats > div", { y: 24, opacity: 0, stagger: 0.12 }, "-=0.4");

        // ================= HERO — parallax do conteúdo no scroll =================
        var heroContent = document.querySelector(".lq-hero .container");
        if (heroContent) {
            gsap.to(heroContent, {
                yPercent: 22,
                opacity: 0.35,
                ease: "none",
                scrollTrigger: {
                    trigger: ".lq-hero",
                    start: "top top",
                    end: "bottom top",
                    scrub: true,
                },
            });
        }

        // ================= CONTADOR — stats do hero =================
        toArray(".lq-hero-stats .lq-stat-num").forEach(function (el) {
            var raw = el.textContent.trim();
            var match = raw.match(/(\D*)(\d+)(\D*)/); // prefixo, número, sufixo (+500, 15+, 100%)
            if (!match) {
                return;
            }
            var prefix = match[1] || "";
            var target = parseInt(match[2], 10);
            var suffix = match[3] || "";
            var counter = { val: 0 };
            gsap.to(counter, {
                val: target,
                duration: 1.6,
                ease: "power1.out",
                scrollTrigger: { trigger: el, start: "top 85%", once: true },
                onUpdate: function () {
                    el.textContent = prefix + Math.round(counter.val) + suffix;
                },
            });
        });

        // ================= REVEAL por seção — cards com stagger =================
        function revealBatch(selector, opts) {
            var items = toArray(selector);
            if (!items.length) {
                return;
            }
            opts = opts || {};
            window.ScrollTrigger.batch(items, {
                start: "top 82%",
                onEnter: function (batch) {
                    // will-change transiente: liga só durante a animação, limpa ao fim
                    gsap.set(batch, { willChange: "transform, opacity" });
                    gsap.from(batch, {
                        y: opts.y || 50,
                        opacity: 0,
                        scale: opts.scale || 0.95,
                        duration: opts.duration || 0.8,
                        ease: "power3.out",
                        stagger: opts.stagger || 0.1,
                        overwrite: true,
                        onComplete: function () {
                            gsap.set(batch, { clearProps: "willChange" });
                        },
                    });
                },
            });
        }

        revealBatch(".lq-service-card", { y: 60, stagger: 0.12 });
        revealBatch(".lq-diff-card", { y: 55, stagger: 0.09 });
        revealBatch(".lq-equip-item", { y: 35, scale: 0.9, stagger: 0.05, duration: 0.6 });
        revealBatch(".lq-client-logo", { y: 30, scale: 0.92, stagger: 0.05, duration: 0.5 });

        // ================= Títulos de seção =================
        toArray(".lq-services, .lq-diff, .lq-equip, .lq-clients, .lq-cta").forEach(function (section) {
            var heads = section.querySelectorAll(".lq-section-tag, .lq-section-title, .lq-section-sub");
            if (!heads.length) {
                return;
            }
            gsap.from(heads, {
                y: 28,
                opacity: 0,
                duration: 0.7,
                ease: "power3.out",
                stagger: 0.12,
                scrollTrigger: { trigger: section, start: "top 80%", once: true },
            });
        });

        // ================= CTA — reveal + float contínuo =================
        var ctaInner = document.querySelector(".lq-cta .container");
        if (ctaInner) {
            gsap.from(ctaInner, {
                y: 50,
                opacity: 0,
                duration: 0.9,
                ease: "power3.out",
                scrollTrigger: { trigger: ".lq-cta", start: "top 80%", once: true },
            });
        }
        var ctaBtn = document.querySelector(".lq-cta-btn");
        if (ctaBtn) {
            // float contínuo (repeat infinito) → will-change persistente é justificado aqui
            gsap.set(ctaBtn, { willChange: "transform" });
            gsap.to(ctaBtn, {
                y: -8,
                duration: 1.4,
                ease: "sine.inOut",
                repeat: -1,
                yoyo: true,
            });
            ctaBtn.addEventListener("mouseenter", function () {
                gsap.to(ctaBtn, { scale: 1.06, duration: 0.25, ease: "power2.out", overwrite: "auto" });
            });
            ctaBtn.addEventListener("mouseleave", function () {
                gsap.to(ctaBtn, { scale: 1, duration: 0.25, ease: "power2.out", overwrite: "auto" });
            });
        }

        // imagens podem carregar depois → recalcular posições dos triggers
        window.addEventListener("load", function () {
            window.ScrollTrigger.refresh();
        });
    });
})();
