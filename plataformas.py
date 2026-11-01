"""
Juego de plataformas 2D con Pygame (base usando figuras basicas).

Controles:
    <- / ->  o  A / D   : Moverse
    Espacio / Up / W    : Saltar (doble salto incluido)
    Shift               : Correr
    R                   : Reiniciar nivel
    ESC                 : Salir

Ejecutar:
    python3 plataformas.py
"""

import math
import random
import sys

import pygame

# ----------------------------------------------------------------------------
# Configuracion general
# ----------------------------------------------------------------------------
ANCHO, ALTO = 960, 540
FPS = 60

GRAVEDAD = 0.55
MAX_CAIDA = 16
VEL_MOV = 4.2
VEL_RUN = 6.8
VEL_SALTO = -11.8
COYOTE_FRAMES = 6      # margen para saltar justo despues de dejar el suelo
SALTOS_MAX = 2         # doble salto

# Colores
NEGRO = (15, 15, 25)
BLANCO = (240, 240, 240)
CIELO_ARRIBA = (35, 60, 110)
CIELO_ABAJO = (110, 150, 200)
SUELO = (70, 100, 70)
SUELO_BORDE = (120, 170, 110)
PLATAFORMA = (110, 90, 70)
PLATAFORMA_BORDE = (170, 140, 110)
MOVIL = (90, 120, 160)
PINCHO = (160, 160, 170)
MONEDA = (255, 210, 60)
META = (80, 220, 160)
ENEMIGO = (200, 80, 80)
JUGADOR = (255, 140, 60)
JUGADOR_CONTORNO = (200, 90, 30)


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def rect(x, y, w, h):
    return pygame.Rect(int(x), int(y), int(w), int(h))


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ----------------------------------------------------------------------------
# Entidades del nivel
# ----------------------------------------------------------------------------
class Plataforma:
    """Rectangulo solido estatico."""

    def __init__(self, x, y, w, h, color=PLATAFORMA, borde=PLATAFORMA_BORDE):
        self.rect = rect(x, y, w, h)
        self.color = color
        self.borde = borde

    def draw(self, surf, ox, oy):
        r = self.rect.move(ox, oy)
        pygame.draw.rect(surf, self.color, r)
        pygame.draw.rect(surf, self.borde, r, 2)
        # linea superior tipo "cesped"/borde iluminado
        pygame.draw.line(surf, self.borde, (r.left + 2, r.top + 2), (r.right - 3, r.top + 2), 3)


class PlataformaMovil(Plataforma):
    """Plataforma que se mueve entre dos puntos (horizontal o vertical)."""

    def __init__(self, x, y, w, h, destino, velocidad=1.5):
        super().__init__(x, y, w, h, MOVIL, (150, 190, 230))
        self.origen = pygame.math.Vector2(x, y)
        self.fin = pygame.math.Vector2(destino[0], destino[1])
        self.velocidad = velocidad
        self.t = 0.0
        self.direccion = 1
        self.desplazamiento = pygame.math.Vector2(0, 0)

    def update(self):
        anterior = pygame.math.Vector2(self.rect.x, self.rect.y)
        self.t += self.velocidad / max(1.0, self.origen.distance_to(self.fin)) * self.direccion
        if self.t >= 1:
            self.t, self.direccion = 1.0, -1
        elif self.t <= 0:
            self.t, self.direccion = 0.0, 1
        pos = self.origen.lerp(self.fin, self.t)
        self.rect.x, self.rect.y = int(pos.x), int(pos.y)
        self.desplazamiento = pygame.math.Vector2(self.rect.x - anterior.x,
                                                  self.rect.y - anterior.y)


class Pincho:
    """Zona mortal dibujada como triangulos."""

    def __init__(self, x, y, w, h=18, paso=18):
        self.rect = rect(x, y, w, h)
        self.paso = paso

    def draw(self, surf, ox, oy):
        r = self.rect.move(ox, oy)
        n = max(1, r.width // self.paso)
        ancho_pico = r.width / n
        for i in range(n):
            x1 = r.left + i * ancho_pico
            pts = [(x1, r.bottom), (x1 + ancho_pico / 2, r.top), (x1 + ancho_pico, r.bottom)]
            pygame.draw.polygon(surf, PINCHO, pts)
            pygame.draw.polygon(surf, BLANCO, pts, 1)


class Moneda:
    """Coleccionable que flota y brilla."""

    RADIO = 9

    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        self.recolectada = False
        self.fase = random.uniform(0, math.tau)

    def hitbox(self, tiempo):
        flota = math.sin(tiempo * 0.05 + self.fase) * 4
        return rect(self.pos.x - self.RADIO, self.pos.y - self.RADIO + flota,
                    self.RADIO * 2, self.RADIO * 2)

    def draw(self, surf, ox, oy, tiempo):
        if self.recolectada:
            return
        hb = self.hitbox(tiempo)
        centro = hb.center
        centro = (centro[0] + ox, centro[1] + oy)
        brillo = abs(math.sin(tiempo * 0.05 + self.fase))
        radio_x = max(3, int(self.RADIO * (0.4 + 0.6 * abs(math.cos(tiempo * 0.03 + self.fase)))))
        pygame.draw.circle(surf, lerp_color(MONEDA, BLANCO, brillo * 0.4), centro, self.RADIO + 2, 0)
        pygame.draw.ellipse(surf, MONEDA, (centro[0] - radio_x, centro[1] - self.RADIO,
                                           radio_x * 2, self.RADIO * 2))
        pygame.draw.ellipse(surf, (200, 150, 20),
                            (centro[0] - radio_x, centro[1] - self.RADIO, radio_x * 2, self.RADIO * 2), 2)


class Meta:
    """Puerta/bandera de final de nivel."""

    def __init__(self, x, y, w=46, h=70):
        self.rect = rect(x, y, w, h)

    def draw(self, surf, ox, oy, tiempo):
        r = self.rect.move(ox, oy)
        pygame.draw.rect(surf, (60, 60, 70), r.inflate(10, 10), border_radius=8)
        pygame.draw.rect(surf, META, r.inflate(4, 4), 3, border_radius=8)
        # destello interior animado
        t = (math.sin(tiempo * 0.04) + 1) / 2
        pygame.draw.rect(surf, lerp_color((20, 60, 50), META, t),
                         r.inflate(-14, -14), border_radius=6)
        # poste y bandera
        pygame.draw.line(surf, BLANCO, (r.centerx, r.top - 30), (r.centerx, r.top), 3)
        pygame.draw.polygon(surf, (240, 90, 90),
                            [(r.centerx, r.top - 30), (r.centerx + 24, r.top - 24), (r.centerx, r.top - 16)])


class Enemigo:
    """Ronda simple por una plataforma; se elimina si saltas sobre ella."""

    def __init__(self, x, y, izq, der, velocidad=1.4):
        self.rect = rect(x, y, 28, 24)
        self.izq, self.der = izq, der
        self.velocidad = velocidad
        self.dir = 1
        self.vivo = True
        self.fase_ojos = 0.0

    def update(self):
        if not self.vivo:
            return
        self.rect.x += self.velocidad * self.dir
        if self.rect.right >= self.der:
            self.rect.right, self.dir = self.der, -1
        elif self.rect.left <= self.izq:
            self.rect.left, self.dir = self.izq, 1

    def draw(self, surf, ox, oy, tiempo):
        if not self.vivo:
            return
        r = self.rect.move(ox, oy)
        cuerpo = lerp_color(ENEMIGO, NEGRO, 0.15)
        pygame.draw.rect(surf, cuerpo, r, border_radius=6)
        pygame.draw.rect(surf, (120, 40, 40), r, 2, border_radius=6)
        # "patitas"
        fase = math.sin(tiempo * 0.2) * 3
        for dx in (-8, 0, 8):
            pygame.draw.line(surf, cuerpo, (r.centerx + dx, r.bottom),
                             (r.centerx + dx + fase, r.bottom + 5), 3)
        # ojos
        ex = r.centerx + self.dir * 6
        pygame.draw.circle(surf, BLANCO, (ex - 5, r.top + 9), 4)
        pygame.draw.circle(surf, BLANCO, (ex + 5, r.top + 9), 4)
        pygame.draw.circle(surf, NEGRO, (ex - 5 + self.dir * 2, r.top + 9), 2)
        pygame.draw.circle(surf, NEGRO, (ex + 5 + self.dir * 2, r.top + 9), 2)


class Particula:
    def __init__(self, x, y, vx, vy, vida, color, tam=4, gravitada=True):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.vida = vida
        self.vida_max = vida
        self.color = color
        self.tam = tam
        self.gravitada = gravitada

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.gravitada:
            self.vy += 0.25
        self.vida -= 1

    def draw(self, surf, ox, oy):
        if self.vida <= 0:
            return
        alpha = max(0, min(255, int(255 * self.vida / self.vida_max)))
        tam = max(1, int(self.tam * self.vida / self.vida_max))
        s = pygame.Surface((tam, tam), pygame.SRCALPHA)
        s.fill((*self.color[:3], alpha))
        surf.blit(s, (int(self.x + ox), int(self.y + oy)))


# ----------------------------------------------------------------------------
# Jugador
# ----------------------------------------------------------------------------
class Jugador:
    ANCHO, ALTO = 30, 44

    def __init__(self, x, y):
        self.spawn = (x, y)
        self.rect = rect(x, y, self.ANCHO, self.ALTO)
        self.vel = pygame.math.Vector2(0, 0)
        self.on_ground = False
        self.coyote = 0
        self.saltos_restantes = SALTOS_MAX
        self.ultima_plat_movil = None
        self.mirando_derecha = True
        self.tiempo_sin_suelo = 0
        self.invulnerable = 0
        # animacion procedural
        self.anim_fase = 0.0

    def reset(self):
        self.rect.topleft = self.spawn
        self.vel.update(0, 0)
        self.on_ground = False
        self.invulnerable = 40

    def mover(self, teclas):
        izquierda = teclas[pygame.K_LEFT] or teclas[pygame.K_a]
        derecha = teclas[pygame.K_RIGHT] or teclas[pygame.K_d]
        correr = teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]
        vel_max = VEL_RUN if correr else VEL_MOV

        dir_objetivo = int(derecha) - int(izquierda)
        if dir_objetivo != 0:
            self.mirando_derecha = dir_objetivo > 0
        # aceleracion suave
        objetivo = dir_objetivo * vel_max
        self.vel.x += (objetivo - self.vel.x) * (0.3 if self.on_ground else 0.12)
        if abs(self.vel.x) < 0.05:
            self.vel.x = 0

    def intentar_salto(self, presionada_arriba):
        if not presionada_arriba:
            return []
        if self.on_ground or self.coyote > 0:
            self.vel.y = VEL_SALTO
            self.coyote = 0
            self.saltos_restantes = SALTOS_MAX - 1
            return [("suelo", self.rect.midbottom)]
        elif self.saltos_restantes > 0:
            self.vel.y = VEL_SALTO * 0.92
            self.saltos_restantes -= 1
            return [("aire", self.rect.midbottom)]
        return []

    def corte_salto(self, arriba_suelta):
        if arriba_suelta and self.vel.y < -4:
            self.vel.y = -4

    def fisica(self, plataformas, mundo_rect):
        eventos = []

        # Gravedad
        self.vel.y = min(self.vel.y + GRAVEDAD, MAX_CAIDA)

        # --- eje X ---
        self.rect.x += round(self.vel.x)
        for p in plataformas:
            if self.rect.colliderect(p.rect):
                if self.vel.x > 0:
                    self.rect.right = p.rect.left
                elif self.vel.x < 0:
                    self.rect.left = p.rect.right
                self.vel.x = 0

        # --- eje Y ---
        self.rect.y += round(self.vel.y)
        aterrizo = False
        estaba_aereo = not self.on_ground
        self.on_ground = False
        for p in plataformas:
            if self.rect.colliderect(p.rect):
                if self.vel.y > 0:  # cayendo
                    self.rect.bottom = p.rect.top
                    self.vel.y = 0
                    self.on_ground = True
                    self.ultima_plat_movil = p if isinstance(p, PlataformaMovil) else None
                    aterrizo = estaba_aereo
                elif self.vel.y < 0:  # subiendo -> golpe techo
                    self.rect.top = p.rect.bottom
                    self.vel.y = 0

        if self.on_ground:
            self.coyote = COYOTE_FRAMES
            self.saltos_restantes = SALTOS_MAX
        else:
            self.coyote -= 1

        if isinstance(self.ultima_plat_movil, PlataformaMovil) and self.on_ground:
            self.rect.x += int(self.ultima_plat_movil.desplazamiento.x)
            self.rect.y += int(self.ultima_plat_movil.desplazamiento.y)

        # Limites del mundo
        if self.rect.left < mundo_rect.left:
            self.rect.left = mundo_rect.left
            self.vel.x = 0
        if self.rect.right > mundo_rect.right:
            self.rect.right = mundo_rect.right
            self.vel.x = 0

        if aterrizo:
            eventos.append(("aterrizar", self.rect.midbottom))

        self.tiempo_sin_suelo = 0 if self.on_ground else self.tiempo_sin_suelo + 1

        # caida al vacio
        if self.rect.top > mundo_rect.bottom + 200:
            eventos.append(("vacio", self.rect.center))
            self.reset()

        if self.invulnerable > 0:
            self.invulnerable -= 1

        # fase de animacion segun velocidad
        self.anim_fase += 0.15 + abs(self.vel.x) * 0.06
        return eventos

    def hitbox_enemigo(self):
        return self.rect.inflate(-4, -2)

    def draw(self, surf, ox, oy):
        r = self.rect.move(ox, oy)
        parpadea = self.invulnerable > 0 and (self.invulnerable // 4) % 2 == 0
        color = lerp_color(JUGADOR, BLANCO, 0.5) if parpadea else JUGADOR

        # sombra
        som = pygame.Surface((r.width, 8), pygame.SRCALPHA)
        som.fill((0, 0, 0, 70))
        surf.blit(som, (r.x, r.bottom - 2))

        # cuerpo (rectangulo redondeado)
        cuerpo = r.inflate(-6, -14)
        pygame.draw.rect(surf, color, cuerpo, border_radius=6)
        pygame.draw.rect(surf, JUGADOR_CONTORNO, cuerpo, 2, border_radius=6)

        # cabeza (circulo)
        cabeza_radio = 10
        cx = r.centerx
        cy = r.top + 8
        bob = math.sin(self.anim_fase * 2) * (1.5 if abs(self.vel.x) > 0.5 else 0.4)
        cy += bob
        pygame.draw.circle(surf, color, (cx, int(cy)), cabeza_radio)
        pygame.draw.circle(surf, JUGADOR_CONTORNO, (cx, int(cy)), cabeza_radio, 2)

        # ojos segun direccion
        d = 1 if self.mirando_derecha else -1
        pygame.draw.circle(surf, BLANCO, (cx + d * 4, int(cy) - 2), 3)
        pygame.draw.circle(surf, NEGRO, (cx + d * 5, int(cy) - 2), 2)

        # piernas animadas (lineas)
        f = math.sin(self.anim_fase) * 6 if abs(self.vel.x) > 0.5 else 0
        pierna_y = r.bottom - 2
        pygame.draw.line(surf, JUGADOR_CONTORNO, (cx - 5, r.bottom - 12), (cx - 5 + f, pierna_y), 3)
        pygame.draw.line(surf, JUGADOR_CONTORNO, (cx + 5, r.bottom - 12), (cx + 5 - f, pierna_y), 3)

        # brazos
        brazo_y = cuerpo.centery
        pygame.draw.line(surf, JUGADOR_CONTORNO, (cuerpo.centerx - 8, brazo_y),
                         (cuerpo.left - 4, brazo_y + f * 0.5), 3)
        pygame.draw.line(surf, JUGADOR_CONTORNO, (cuerpo.centerx + 8, brazo_y),
                         (cuerpo.right + 4, brazo_y - f * 0.5), 3)

        # indicador de doble salto disponible
        if not self.on_ground and self.saltos_restantes > 0:
            pygame.draw.circle(surf, (255, 255, 160), (cx, r.bottom + 6), 3)


# ----------------------------------------------------------------------------
# Nivel
# ----------------------------------------------------------------------------
class Nivel:
    def __init__(self, numero=1):
        self.numero = numero
        self.plataformas = []
        self.moviles = []
        self.pinchos = []
        self.monedas = []
        self.enemigos = []
        self.meta = None
        self.spawn = (80, 380)
        self.mundo = rect(0, 0, 2400, ALTO + 200)
        self._construir(numero)

    def _P(self, x, y, w, h, color=SUELO, borde=SUELO_BORDE):
        p = Plataforma(x, y, w, h, color, borde)
        self.plataformas.append(p)
        return p

    def _M(self, x, y, w, h, destino, vel=1.5):
        p = PlataformaMovil(x, y, w, h, destino, vel)
        self.plataformas.append(p)
        self.moviles.append(p)
        return p

    def _monedas(self, x, y, n, dx=34, dy=0):
        for i in range(n):
            self.monedas.append(Moneda(x + i * dx, y + i * dy))

    def _construir(self, numero):
        if numero == 1:
            # ---- nivel introductorio ----
            self._P(0, 470, 620, 120)                       # suelo inicial
            self._P(700, 470, 500, 120)                     # suelo tras hueco
            self._P(1300, 470, 1100, 120)                   # suelo final
            self._P(250, 380, 120, 20)
            self._P(430, 300, 120, 20)
            self._M(620, 330, 110, 18, (620, 200), 1.2)     # movil vertical
            self._P(820, 260, 140, 20)
            self._P(1020, 340, 120, 20)
            self._P(1180, 250, 100, 20)
            self._P(1450, 380, 130, 20)
            self._M(1650, 360, 120, 18, (1850, 360), 1.6)   # movil horizontal
            self._P(1950, 300, 130, 20)
            self._P(2150, 220, 180, 20)
            self._P(1500, 430, 180, 14, (150, 90, 90), (220, 140, 140))  # zona elevada decorativa

            self.pinchos.append(Pincho(760, 452, 120))
            self.pinchos.append(Pincho(1380, 452, 100))
            self.pinchos.append(Pincho(1980, 452, 140))

            self.enemigos.append(Enemigo(830, 446, 705, 1195))
            self.enemigos.append(Enemigo(1500, 446, 1305, 1975, 1.8))
            self.enemigos.append(Enemigo(860, 236, 822, 958, 1.1))

            self._monedas(270, 340, 3)
            self._monedas(450, 258, 3)
            self._monedas(640, 150, 3, dx=30)
            self._monedas(850, 215, 3)
            self._monedas(1040, 295, 3)
            self._monedas(1470, 335, 3)
            self._monedas(1690, 315, 4, dx=30)
            self._monedas(1980, 250, 3)
            self._monedas(2190, 170, 4, dx=32)

            self.meta = Meta(2250, 150)
            self.spawn = (80, 400)
        else:
            # ---- nivel 2: mas plataformas moviles y pinchos ----
            self._P(0, 470, 400, 120)
            self._P(560, 430, 200, 160)
            self._P(900, 380, 160, 210)
            self._P(1250, 470, 350, 120)
            self._P(1850, 420, 550, 170)
            self._M(420, 300, 110, 18, (420, 170), 1.4)
            self._M(760, 300, 110, 18, (900, 300), 1.6)
            self._M(1100, 250, 110, 18, (1250, 250), 1.8)
            self._M(1650, 350, 110, 18, (1650, 200), 1.3)
            self._P(1450, 200, 120, 20)
            self._P(1950, 300, 140, 20)
            self._P(2150, 220, 200, 20)

            self.pinchos.append(Pincho(580, 412, 160))
            self.pinchos.append(Pincho(1270, 452, 310))
            self.pinchos.append(Pincho(1900, 402, 120))

            self.enemigos.append(Enemigo(1300, 446, 1255, 1595, 1.6))
            self.enemigos.append(Enemigo(1980, 396, 1855, 2395, 2.0))

            self._monedas(440, 130, 3)
            self._monedas(600, 380, 3)
            self._monedas(800, 250, 4)
            self._monedas(1130, 200, 4)
            self._monedas(1300, 420, 3)
            self._monedas(1470, 155, 3)
            self._monedas(1680, 160, 3)
            self._monedas(1980, 250, 3)
            self._monedas(2180, 170, 4)

            self.meta = Meta(2280, 150)
            self.spawn = (60, 400)

    @property
    def total_monedas(self):
        return len(self.monedas)

    def actualizar(self):
        for m in self.moviles:
            m.update()
        for e in self.enemigos:
            e.update()

    def todas_solids(self):
        return self.plataformas


# ----------------------------------------------------------------------------
# Camara
# ----------------------------------------------------------------------------
class Camara:
    def __init__(self):
        self.offset = pygame.math.Vector2(0, 0)

    def seguir(self, objetivo_jugador, suavizado=0.12):
        destino_x = objetivo_jugador.centerx - ANCHO / 2
        destino_y = objetivo_jugador.centery - ALTO / 2 - 40
        self.offset.x += (destino_x - self.offset.x) * suavizado
        self.offset.y += (destino_y - self.offset.y) * suavizado * 0.6

    def limitar(self, mundo):
        self.offset.x = max(mundo.left, min(self.offset.x, mundo.right - ANCHO))
        self.offset.y = max(mundo.top - 150, min(self.offset.y, mundo.bottom - ALTO))

    @property
    def ox(self):
        return int(-self.offset.x)

    @property
    def oy(self):
        return int(-self.offset.y)


# ----------------------------------------------------------------------------
# Fondo con parallax
# ----------------------------------------------------------------------------
class Fondo:
    def __init__(self):
        self.estrellas = [(random.uniform(0, ANCHO * 3), random.uniform(0, ALTO * 0.6),
                           random.uniform(1, 2.4)) for _ in range(90)]
        self.colinas = [(random.uniform(0, 3000), random.uniform(380, 470),
                         random.uniform(90, 220)) for _ in range(14)]
        self.nubes = [(random.uniform(0, 2600), random.uniform(40, 200),
                       random.uniform(40, 90)) for _ in range(8)]

    def draw(self, surf, cam):
        # degradado de cielo
        for i in range(ALTO):
            t = i / ALTO
            pygame.draw.line(surf, lerp_color(CIELO_ARRIBA, CIELO_ABAJO, t),
                             (0, i), (ANCHO, i))
        ox1 = int(-cam.offset.x * 0.2) % (ANCHO * 3)
        # nubes (parallax lento)
        for nx, ny, nr in self.nubes:
            x = (nx - cam.offset.x * 0.25) % (ANCHO + 300) - 150
            c = (230, 235, 245)
            pygame.draw.ellipse(surf, c, (x, ny, nr * 2.2, nr * 0.8))
            pygame.draw.ellipse(surf, c, (x + nr * 0.5, ny - nr * 0.3, nr * 1.4, nr * 0.9))
        # colinas lejanas
        for cx, cy, cr in self.colinas:
            x = (cx - cam.offset.x * 0.45) % 3200 - 200
            pygame.draw.circle(surf, (55, 85, 75), (int(x), int(cy + cr)), int(cr))
        # montana media
        for mx in range(0, 3400, 420):
            x = (mx - cam.offset.x * 0.65) % 3400 - 200
            base = ALTO - 40
            pygame.draw.polygon(surf, (70, 95, 120),
                                [(x, base), (x + 170, base - 210), (x + 340, base)])
            pygame.draw.polygon(surf, BLANCO,
                                [(x + 130, base - 160), (x + 170, base - 210), (x + 210, base - 160)])


# ----------------------------------------------------------------------------
# HUD
# ----------------------------------------------------------------------------
class HUD:
    def __init__(self):
        try:
            self.font = pygame.font.SysFont("dejavusansmono", 20, bold=True)
            self.font_grande = pygame.font.SysFont("dejavusansmono", 40, bold=True)
        except Exception:
            self.font = pygame.font.Font(None, 24)
            self.font_grande = pygame.font.Font(None, 44)

    def panel(self, surf, texto, x, y, relleno=8):
        img = self.font.render(texto, True, BLANCO)
        fondo = pygame.Surface((img.get_width() + relleno * 2, img.get_height() + relleno * 2),
                               pygame.SRCALPHA)
        fondo.fill((0, 0, 0, 130))
        surf.blit(fondo, (x, y))
        surf.blit(img, (x + relleno, y + relleno))
        return fondo.get_rect(topleft=(x, y))

    def mensaje_central(self, surf, titulo, sub=None):
        t = self.font_grande.render(titulo, True, BLANCO)
        r = t.get_rect(center=(ANCHO // 2, ALTO // 2 - 20))
        caja = r.inflate(60, 40 if sub else 20)
        fondo = pygame.Surface(caja.size, pygame.SRCALPHA)
        fondo.fill((0, 0, 0, 170))
        surf.blit(fondo, caja.topleft)
        surf.blit(t, r)
        if sub:
            s = self.font.render(sub, True, (200, 200, 210))
            surf.blit(s, s.get_rect(midtop=(ANCHO // 2, r.bottom + 10)))


# ----------------------------------------------------------------------------
# Juego principal
# ----------------------------------------------------------------------------
class Juego:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("PyPlatforms - Plataformas 2D (figuras basicas)")
        self.screen = pygame.display.set_mode((ANCHO, ALTO))
        self.clock = pygame.time.Clock()
        self.hud = HUD()
        self.camara = Camara()
        self.fondo = Fondo()
        self.particulas = []
        self.tiempo = 0
        self.vidas = 3
        self.estado = "jugando"   # jugando | gano | perdio
        self.nivel_num = 1
        self.cargar_nivel(1)

    def cargar_nivel(self, n):
        self.nivel_num = n
        self.nivel = Nivel(n)
        self.jugador = Jugador(*self.nivel.spawn)
        self.monedas_ok = 0
        self.camara.offset.update(0, 0)

    # ------- efectos -------
    def burst(self, x, y, color, n=12, vel=3, gravitada=True):
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            v = random.uniform(vel * 0.4, vel)
            self.particulas.append(Particula(x, y, math.cos(ang) * v, math.sin(ang) * v - 1,
                                             random.randint(18, 34), color,
                                             tam=random.uniform(3, 6), gravitada=gravitada))

    # ------- entrada -------
    def manejar_eventos(self):
        self.arriba_presionada = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return False
                if ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self.arriba_presionada = True
                if ev.key == pygame.K_r:
                    if self.estado in ("gano", "perdio"):
                        self.vidas = 3
                        self.estado = "jugando"
                        self.cargar_nivel(1)
                    else:
                        self.jugador.reset()
            if ev.type == pygame.KEYUP:
                if ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    self.arriba_suelta_frame = True
        return True

    # ------- logica -------
    def actualizar(self):
        self.tiempo += 1
        teclas = pygame.key.get_pressed()

        if self.estado == "jugando":
            self.nivel.actualizar()
            j = self.jugador
            j.mover(teclas)
            for tipo, pos in j.intentar_salto(getattr(self, "arriba_presionada", False)):
                self.burst(pos[0], pos[1], (255, 220, 150) if tipo == "suelo" else (180, 220, 255),
                           n=8, vel=2.2, gravitada=False)
            if getattr(self, "arriba_suelta_frame", False):
                j.corte_salto(True)
            self.arriba_suelta_frame = False

            eventos = j.fisica(self.nivel.todas_solids(), self.nivel.mundo)
            for tipo, pos in eventos:
                if tipo == "aterrizar":
                    self.burst(pos[0], pos[1], (200, 200, 210), n=6, vel=2, gravitada=False)

            # monedas
            for m in self.nivel.monedas:
                if not m.recolectada and j.rect.colliderect(m.hitbox(self.tiempo)):
                    m.recolectada = True
                    self.monedas_ok += 1
                    self.burst(m.pos.x, m.pos.y, MONEDA, n=10, vel=3, gravitada=False)

            # pinchos / enemigos / vacio
            if j.invulnerable == 0:
                daño = False
                for p in self.nivel.pinchos:
                    if j.hitbox_enemigo().colliderect(p.rect):
                        daño = True
                for e in self.nivel.enemigos:
                    if e.vivo and j.hitbox_enemigo().colliderect(e.rect):
                        if j.vel.y > 1.5 and j.rect.bottom < e.rect.centery + 10:
                            # pisoton
                            e.vivo = False
                            j.vel.y = VEL_SALTO * 0.7
                            self.burst(e.rect.centerx, e.rect.centery, ENEMIGO, n=14, vel=4)
                        else:
                            daño = True
                if tipo_vacio := ("vacio", None) in [(t, None) for t, _ in eventos]:
                    pass
                if any(t == "vacio" for t, _ in eventos):
                    self.vidas -= 1
                    self.burst(j.rect.centerx, ALTO - 10, (255, 120, 120), n=16, vel=4)
                    daño = False
                    if self.vidas <= 0:
                        self.estado = "perdio"
                if daño:
                    j.invulnerable = 60
                    j.vel.update(0, -7)
                    j.rect.y -= 8
                    self.vidas -= 1
                    self.burst(j.rect.centerx, j.rect.centery, (255, 100, 100), n=14, vel=4)
                    if self.vidas <= 0:
                        self.estado = "perdio"
                    else:
                        # reaparece en el spawn del nivel
                        j.reset()
                        j.rect.topleft = self.nivel.spawn

            # meta
            if self.nivel.meta and j.rect.colliderect(self.nivel.meta.rect):
                self.burst(self.nivel.meta.rect.centerx, self.nivel.meta.rect.centery,
                           META, n=24, vel=5, gravitada=False)
                if self.nivel_num < 2:
                    self.cargar_nivel(self.nivel_num + 1)
                else:
                    self.estado = "gano"

            self.camara.seguir(j.rect)
            self.camara.limitar(rect(self.nivel.mundo.left, self.nivel.mundo.top - 150,
                                     self.nivel.mundo.width, self.nivel.mundo.height + 150))
        else:
            # en pantallas de fin, la camara se queda tranquila
            self.camara.limitar(rect(self.nivel.mundo.left, self.nivel.mundo.top - 150,
                                     self.nivel.mundo.width, self.nivel.mundo.height + 150))

        # particulas
        for p in self.particulas:
            p.update()
        self.particulas = [p for p in self.particulas if p.vida > 0]

    # ------- dibujo -------
    def dibujar(self):
        self.fondo.draw(self.screen, self.camara)
        ox, oy = self.camara.ox, self.camara.oy

        for p in self.nivel.plataformas:
            p.draw(self.screen, ox, oy)
        for pn in self.nivel.pinchos:
            pn.draw(self.screen, ox, oy)
        for m in self.nivel.monedas:
            m.draw(self.screen, ox, oy, self.tiempo)
        for e in self.nivel.enemigos:
            e.draw(self.screen, ox, oy, self.tiempo)
        if self.nivel.meta:
            self.nivel.meta.draw(self.screen, ox, oy, self.tiempo)
        self.jugador.draw(self.screen, ox, oy)
        for p in self.particulas:
            p.draw(self.screen, ox, oy)

        # HUD
        self.hud.panel(self.screen,
                       f"NIVEL {self.nivel_num}   Monedas: {self.monedas_ok}/{self.nivel.total_monedas}",
                       12, 12)
        # vidas como corazoncitos (circulos)
        hx = 24
        for i in range(self.vidas):
            pygame.draw.circle(self.screen, (230, 70, 90), (hx + i * 26, 70), 9)
            pygame.draw.circle(self.screen, BLANCO, (hx + i * 26, 70), 9, 2)
        self.hud.panel(self.screen, "ESC salir | R reiniciar | Shift correr", 12, ALTO - 42)

        if self.estado == "gano":
            self.hud.mensaje_central(self.screen, "!NIVEL COMPLETADO!",
                                     "Presiona R para volver a jugar")
        elif self.estado == "perdio":
            self.hud.mensaje_central(self.screen, "GAME OVER",
                                     "Presiona R para reintentar")

        pygame.display.flip()

    # ------- bucle -------
    def run(self):
        self.arriba_suelta_frame = False
        ejecutando = True
        while ejecutando:
            ejecutando = self.manejar_eventos()
            self.actualizar()
            self.dibujar()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Juego().run()
