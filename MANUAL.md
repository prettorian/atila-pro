# 📖 MANUAL DE USUARIO — ATILA PRO 7.7

> **Uso ético únicamente.** Solo sistemas propios o con autorización escrita del titular.
> Prohibido evadir cobros de servicios ajenos o cualquier fin ilícito.

---

## 1. ¿Qué es ATILA PRO?

ATILA PRO es una herramienta de **reconocimiento y auditoría de infraestructura IPv4**,
pensada para entornos móviles (Termux/Android) y Linux.

Permite:
- Escanear rangos de IPs en 2 etapas (TCP-ping + verificación CONNECT extremo-a-extremo)
- Obtener rangos frescos de operadoras argentinas y clouds/CDN mundiales vía BGP
- Administrar hosts vivos, proxies reales, historial y estadísticas
- Trabajar offline (modo chip) o con internet
- Exportar resultados en JSON / CSV / HTML

**Autor:** TheFlaggg (@TheFlaggg) · **Co-diseño:** McGyver-Pro (IA)

---

## 2. Instalación

### Requisitos
- Termux (Android) o cualquier Linux con Python 3.8+
- Conexión a internet solo para descargar y consultar BGP
- `tmux` recomendado para escaneos largos

### En Termux

```bash
pkg update && pkg install python curl tmux git -y
pip install requests
termux-setup-storage
```

### Descargar desde el repo oficial

```bash
curl -sL https://raw.githubusercontent.com/prettorian/atila-pro/main/atila.py -o atila.py
curl -sL https://raw.githubusercontent.com/prettorian/atila-pro/main/checksums.txt -o checksums.txt
```

### Verificar integridad (SIEMPRE antes de ejecutar)

```bash
sha256sum -c checksums.txt
```
Debe responder: `atila.py: OK`. Si dice `FAILED`, **no lo ejecutes** y avisa al autor.

### Ejecutar

```bash
python3 atila.py
```

---

## 3. Activación de licencia

ATILA PRO funciona **sin key** en modo LIBRE (uso personal/educativo). Si compraste una key:

```bash
python3 atila.py --activate "TU-KEY-AQUI"
```

El banner inicial muestra tu estado:
- **LIBRE** → uso gratuito, sin key
- **PRO** → key anual activa
- **SOCIO FUNDADOR** → key única, créditos permanentes
- **EXPIRADA** → tu key venció, renová

Para consultar el estado en cualquier momento:

```bash
python3 atila.py --license
```

O desde el menú principal, opción **[22] Licencia**.

---

## 4. Menú principal (01-22)

### Menús de uso rápido

| # | Nombre | Para qué sirve |
|---|---|---|
| 01 | Single Host | Probar un dominio o IP: HTTP, server, título |
| 02 | Browse & Scan | Cargar un `.txt` de hosts y probar uno a uno |
| 03 | Quick Test | Probar 10 sitios populares (Google, GitHub, etc.) |
| 04 | CIDR Scan | Escanear un rango corto (máx 256 IPs) buscando puertos abiertos |
| 05 | Subdomain Enum | Encontrar subdominios vía wordlist + crt.sh + Wayback |
| 06 | Reverse IP | Ver qué dominios están en una IP |
| 07 | Domain Extractor | Extraer dominios de un texto o archivo |
| 08 | Proxy Relay | Detectar proxies públicos desde listas web |
| 09 | Trick Lab | 4 pruebas de vulnerabilidad básica (redirect, XSS, SQLi, info) || 10 | H2 Detector | Verificar si un host soporta HTTP/2 |

### Menús CORE (los que más vas a usar)

| # | Nombre | Para qué sirve |
|---|---|---|
| 11 | **Mobile Proxy Scan** | ★ Escaneo 2 etapas en rangos CIDR: TCP-ping + CONNECT+E2E. Soporta modo continuo y rango-por-rango. Guarda proxies reales y hosts vivos. |
| 14 | Carrier ASN Hunt | Detecta el ASN del chip + descarga rangos frescos del BGP global |
| 15 | MacGyver Pack AR | Genera paquete offline de rangos de operadoras AR (Personal, Claro, Movistar) |
| 16 | Fresh Pools AR | Rangos frescos de operadoras AR vía BGP (requiere internet) |
| 17 | Fresh Cloud Pack | Rangos de Cloudflare, AWS, Google, Azure, Hetzner, etc. |
| 18 | **Vivos Lab** | ★ Laboratorio sobre tus hosts vivos: re-verificar, inspeccionar, time-lapse, estadísticas, exportar |

### Menús de gestión

| # | Nombre | Para qué sirve |
|---|---|---|
| 12 | Update ATILA | Actualizar desde el gist oficial (legacy) |
| 13 | Install Command | Instalar `atila` como comando global en `$PREFIX/bin` |
| 19 | Ver Bitácora | Leer las últimas 30 líneas del log (`~/.atila/atila.log`) |
| 20 | Configuración | Preferencias persistentes (workers, timeouts, modos, rutas) |
| 21 | Historial | Estadísticas acumuladas + últimos 10 archivos generados |
| 22 | Licencia | Activar key, ver créditos del proyecto |

---

## 5. Caso de uso típico: tu primer escaneo

### Paso 1 — Generar un paquete de rangos

Para operadoras argentinas, menú **[15] MacGyver Pack AR** → elegí una operadora → guarda un `.txt` en `~/atila-pro/`.

### Paso 2 — Escanear

Menú **[11] Mobile Proxy Scan** → ruta del `.txt` → modo `1` (continuo) o `2` (rango-por-rango).

### Paso 3 — Leer los resultados

Al terminar:
- `proxies_FECHA.txt` → proxies reales verificados
- `hosts_vivos_FECHA.txt` → IPs con puertos abiertos (mapa de infraestructura)

### Paso 4 — Analizar

Menú **[18] Vivos Lab** → cargá `hosts_vivos_FECHA.txt` → opción 4 (estadísticas) o 5 (exportar a HTML para compartir).

---

## 6. Airbag tmux (escaneos largos)
Si dejás correr un escaneo de más de 100.000 IPs fuera de tmux, ATILA te frena y avisa:

```bash
tmux new -s caza
atila
# [11] → escanear
# Ctrl+B, D → salís dejando corriendo
# Después: tmux attach -t caza → volvés
```

Y para maratones nocturnas:

```bash
termux-wake-lock
# escaneo
termux-wake-unlock
```

---

## 7. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `Key inválida (firma no coincide)` | Key incorrecta o pegada mal | Copiar/pegar la key completa |
| `Key expirada` | Ya pasó la fecha | Renovar con el autor |
| `SyntaxError` | Archivo modificado o corrupto | Reinstalar desde el repo oficial |
| `Fallo de conexión HTTP/JSON` | Sin internet | Verificar conexión; el script cae a `curl` del sistema |
| `Permiso denegado` | Storage no concedido | `termux-setup-storage` y aceptar |
| El escaneo se corta al cerrar la app | No estás en tmux | Usá tmux (ver sección 6) |

---

## 8. Preguntas frecuentes

**¿Puedo usar esto gratis?**
Sí. Para estudio, auditoría propia o sistemas con autorización, es completamente libre (Licencia APL-1.0).

**¿Para qué sirve la key entonces?**
Para uso regular/productivo, para apoyar el desarrollo, y (en el caso Fundador) para aparecer en los créditos permanentes.

**¿Qué pasa si mi key expira?**
Seguís pudiendo usar la herramienta, pero vuelve al modo LIBRE. Podés renovarla en cualquier momento.

**¿Puedo modificar el código?**
Sí, para uso propio. Si distribuís una versión modificada, debés indicar que es modificada, mantener la licencia y no usar el nombre "ATILA PRO".

**¿Es legal usar esto?**
Sí, para auditar sistemas propios o con autorización escrita del titular. Usarlo contra sistemas ajenos es ilegal y viola la licencia.
**¿Puedo crackearlo para no pagar?**
El código es abierto, técnicamente podrías. Pero perdés el soporte, las actualizaciones y la tranquilidad de apoyar una herramienta que te sirve. Además, las keys son un gesto de reconocimiento al autor: un café al año.

---

## 9. Contacto y soporte

- **Autor:** TheFlaggg (@TheFlaggg)
- **Repo oficial:** https://github.com/prettorian/atila-pro
- **Cobros:** PayPal @ATILANET
- **Reportes de bugs, consultas, sugerencias:** por los canales que el autor indique en el README

---

*Licencia APL-1.0 · © 2026 TheFlaggg · Co-diseño: McGyver-Pro (IA)*
