# 📡 ATILA PRO

**Scanner ético de proxies móviles y auditoría de redes — Termux/Android y Linux**
*Creado por TheFlaggg · Co-diseño: McGyver-Pro (IA)*

Herramienta de reconocimiento y auditoría de infraestructura IPv4:
escaneo en 2 etapas (TCP-ping → verificación CONNECT extremo-a-extremo),
caza de rangos por ASN/BGP, laboratorio de hosts vivos, exportación
JSON/CSV/HTML, bitácora, configuración persistente e historial.

> ⚠️ **USO ÉTICO ÚNICAMENTE.** Solo sistemas propios o con autorización
> escrita del titular. Prohibido evadir cobros de servicios ajenos o
> cualquier fin ilícito. El usuario asume toda responsabilidad.

## ✨ Características

- Motor de escaneo en 2 etapas con barra de progreso y ETA
- Modo continuo y modo rango-por-rango con guardado parcial
- Airbag tmux: aviso anti-pérdida en listas gigantes
- Fresh Pools: rangos frescos de operadoras AR y clouds/CDN
  (ip.guide, BGPView, RIPEstat)
- Vivos Lab: re-verificación, inspección, time-lapse y estadísticas
- Exportación JSON / CSV / HTML con reporte visual
- Bitácora (~/.atila/atila.log) y configuración persistente
- Historial acumulado de tu carrera de auditoría
- Sistema de keys con créditos permanentes para Socios Fundadores
- Interfaz responsive para cualquier terminal

## 📲 Instalación (Termux)

```bash
pkg update && pkg install python curl tmux -y
pip install requests
termux-setup-storage
# Descargá atila.py desde este repo (botón Code → Download,
# o el curl publicado en el release)
sha256sum -c <<< "1bf42d7bc527b481be6dbf53e30305cf6089bef8044aec2d8b4374b1c453c4bb  atila.py"
python3 atila.py
```

> La huella SHA-256 oficial se publica en cada release para que
> verifiques que tu copia es íntegra y no fue modificada por terceros.

## 🔑 Licencia y keys

Gratis para estudio y auditoría propia (Licencia APL-1.0, ver `LICENSE`).
Para uso regular, key simbólica emitida por el Autor:

| Key | Precio | Incluye |
|---|---|---|
| Anual | **5 USD** | Uso completo 12 meses + soporte |
| Socio Fundador | **12 USD** (pago único) | Lo anterior + **créditos permanentes** |

**Cómo comprar:**
1. Escribime por PayPal **@ATILANET** (o consultá otros métodos por chat).
2. Enviá el comprobante con tu alias.
3. Recibís tu key en minutos y la activás con:
   `python3 atila.py --activate TU-KEY-AQUI`

## 🛡️ Verificación de integridad

Cada release publica su huella SHA-256. Verificala siempre antes de
ejecutar: si no coincide, **no la uses** y avisale al Autor.

## 🏅 Créditos

- **Autor y mantenimiento:** TheFlaggg (@TheFlaggg)
- **Co-diseño y arquitectura:** McGyver-Pro (IA), compañero de taller desde la v2.5
- **Socios Fundadores:**
  - *(tu nombre o alias acá, si adquiriste la key Fundador)*

## 📜 Changelog

- 7.7 — Sistema de keys, créditos y vitrina pública
- 7.6.1 — Historial y estadísticas [21]
- 7.5 — Configuración persistente [20]
- 7.4 — Bitácora [19]
- 7.3 — Exportación JSON/CSV/HTML
- 7.x — Motor 2 etapas, Vivos Lab, Airbag tmux, UI responsive
