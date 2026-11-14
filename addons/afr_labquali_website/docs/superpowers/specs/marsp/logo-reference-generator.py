import math, sys

GRAF, ORG = "#2B3036", "#F26B2A"
_u = [0]
MU = 'maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120"'
C = 60

def uid():
    _u[0] += 1
    return _u[0]

def circ(r, cx=C, cy=C):
    return f"M{cx-r:.2f} {cy:.2f} A{r} {r} 0 1 0 {cx+r:.2f} {cy:.2f} A{r} {r} 0 1 0 {cx-r:.2f} {cy:.2f}Z "

def ell(rx, ry, cx=0.0):
    return f"M{cx-rx:.2f} 0 A{rx:.2f} {ry:.2f} 0 1 0 {cx+rx:.2f} 0 A{rx:.2f} {ry:.2f} 0 1 0 {cx-rx:.2f} 0Z "

def lens(rx, ry, cx=0.0):
    return f"M{cx-rx:.2f} 0 Q{cx:.2f} {-2*ry:.2f} {cx+rx:.2f} 0 Q{cx:.2f} {2*ry:.2f} {cx-rx:.2f} 0Z"

def rot(t):
    return f'transform="translate({C} {C}) rotate({t})"'

def layered(fg, acc, under, disk, tilt, gap=2.6, disk_attrs=""):
    """under: svg string (hole + halo) in fg; disk: path d in rotated frame, drawn in front with a clear gap."""
    u = uid()
    m = (f'<mask id="m{u}" {MU}><rect width="120" height="120" fill="#fff"/>'
         f'<g {rot(tilt)}><path d="{disk}" fill="#000" stroke="#000" stroke-width="{2*gap}" stroke-linejoin="round"/></g></mask>')
    return m + f'<g mask="url(#m{u})">{under}</g><g {rot(tilt)}><path d="{disk}" fill="{acc}" {disk_attrs}/></g>'

def eclipse(fg, acc, ro=(58, 12.5), k=0.64, tilt=-24, Ro=32, Ri=20, gap=2.2, cassini=None, shift=0.0, back=False, off=0.0):
    u = uid(); rx, ry = ro
    ring = ell(rx, ry)
    if cassini:
        for f in cassini: ring += ell(rx*f, ry*f)
    ring += ell(rx*k, ry*k, shift)
    halo = f"{circ(Ro, C, C-off)}{circ(Ri)}"
    defs = (f'<defs><clipPath id="f{u}"><rect x="-70" y="0" width="140" height="50"/></clipPath>'
            f'<clipPath id="k{u}"><rect x="-70" y="-50" width="140" height="50.5"/></clipPath></defs>')
    hm = (f'<mask id="h{u}" {MU}><rect width="120" height="120" fill="#fff"/><g {rot(tilt)}>'
          f'<path d="{ring}" fill-rule="evenodd" fill="#000" stroke="#000" stroke-width="{2*gap}" stroke-linejoin="round" clip-path="url(#f{u})"/></g></mask>')
    hole = f'<circle cx="{C}" cy="{C}" r="{Ri-gap}" fill="#fff"/>' if back else ""
    om = (f'<mask id="o{u}" {MU}><rect width="120" height="120" fill="#fff"/>'
          f'<circle cx="{C}" cy="{C-off}" r="{Ro+gap}" fill="#000"/>{hole}</mask>')
    return (defs + hm + om + f'<path d="{halo}" fill-rule="evenodd" fill="{fg}" mask="url(#h{u})"/>'
            f'<g mask="url(#o{u})"><g {rot(tilt)}><path d="{ring}" fill-rule="evenodd" fill="{acc}" clip-path="url(#k{u})"/></g></g>'
            f'<g {rot(tilt)}><path d="{ring}" fill-rule="evenodd" fill="{acc}" clip-path="url(#f{u})"/></g>')

T = dict(tilt=-36, ro=(56, 12))
def g1(fg, acc): return eclipse(fg, acc, **dict(T, Ro=35, Ri=20, ro=(58, 12.5)))
def g2(fg, acc): return eclipse(fg, acc, **dict(T, back=True, Ri=21, Ro=33, ro=(57, 13)))
def g3(fg, acc): return eclipse(fg, acc, tilt=-48, ro=(57, 10.5), k=0.66, Ro=31, Ri=19.5)
def g4(fg, acc): return eclipse(fg, acc, **dict(T, off=3.5, Ro=34.5, Ri=20))
def g5(fg, acc): return eclipse(fg, acc, **dict(T, shift=6, k=0.6, ro=(58, 13.5)))
def g6(fg, acc): return eclipse(fg, acc, **dict(T, ro=(57, 17), k=0.6, Ri=21, Ro=32))

def svg(fn, size, fg, acc=None):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 120 120">{fn(fg, acc or fg)}</svg>'

V = [("g1", "Halo grosso", g1, "F3 com o aro de luz mais pesado: mais presença e melhor leitura pequeno."),
     ("g2", "Anel visível pelo furo", g2, "A parte de trás do anel atravessa o furo. Ganha profundidade: o anel realmente dá a volta."),
     ("g3", "Quase diagonal", g3, "Inclinação mais forte e anel mais fino e longo. O mais dinâmico."),
     ("g4", "Halo crescente", g4, "O aro engrossa em cima e afina embaixo, como a luz curvada do buraco negro."),
     ("g5", "Anel em rastro", g5, "Furo do anel deslocado: a faixa é grossa embaixo à esquerda e fina em cima à direita, como um rastro de órbita."),
     ("g6", "Anel largo", g6, "Anel mais aberto e mais largo nas pontas: reforça a leitura de anel achatado.")]

out = ['''<link href="https://fonts.googleapis.com/css2?family=Michroma&display=swap" rel="stylesheet">
<style>
.v{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.lt{border-radius:12px;overflow:hidden;border:1px solid #2a3440;cursor:pointer}
.lt.selected{outline:3px solid #F26B2A}
.big{background:#fff;display:flex;justify-content:center}
.lock{background:#fff;padding:0 20px 16px;display:flex;align-items:center;justify-content:center;gap:10px;margin-top:-14px}
.dark{background:#0b0d10;padding:12px 20px;display:flex;align-items:center;gap:10px}
.wm{font-family:'Michroma',sans-serif;letter-spacing:.22em;line-height:1}
.r{margin-left:auto;display:flex;align-items:center;gap:10px}
.cap{background:#22262b;color:#cfd6dd;font-size:13px;padding:10px 14px;line-height:1.45}
.cap b{color:#fff}
</style>
<h2>MARSP — F3, mais 6 variações</h2>
<p class="subtitle">Todas mantêm a base da F3: aro vazado e anel achatado inclinado cruzando pela frente.</p>
<div class="v">''']
for key, name, fn, desc in V:
    out.append(f'''<div class="lt" data-choice="{key}" onclick="toggleSelect(this)">
<div class="big">{svg(fn, 190, GRAF)}</div>
<div class="lock">{svg(fn, 46, GRAF)}<span class="wm" style="font-size:20px;color:{GRAF}">MARSP</span></div>
<div class="dark">{svg(fn, 44, "#fff", ORG)}<span class="wm" style="font-size:14px;color:#eef1f4">MARSP</span>
<div class="r">{svg(fn, 24, "#fff")}{svg(fn, 16, "#fff")}<span style="background:#fff;border-radius:5px;padding:1px 4px;display:flex">{svg(fn, 30, GRAF, ORG)}</span></div></div>
<div class="cap"><b>{key.upper()} · {name}</b> — {desc}</div></div>''')
out.append("</div>")
open(sys.argv[1], "w").write("\n".join(out))
