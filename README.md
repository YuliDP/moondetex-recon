# MOONDETEX Bug Bounty Recon (v1.0)

Herramienta modular en Python para reconocimiento de seguridad controlado, validación estricta de alcance y generación de evidencia forense con trazabilidad SHA-256.

## Características Principales

- **Control Estricto de Alcance (*Gatekeeper*):** Bloquea cualquier análisis si el proyecto no cuenta con una política activa que autorice explícitamente el dominio, puerto y protocolo.
- **Protección de Red:** Implementa *IP Pinning* (fijación de IP resuelta) para evitar desviaciones o SSRF, identificación mediante cabecera `X-Bug-Bounty` y pausas controladas entre consultas.
- **Motores de Reconocimiento Modular:**
  1. **Auditoría Pasiva DNS (DoH):** Evalúa registros `SPF`, `DMARC` y `CAA` sin tocar el servidor objetivo.
  2. **Inspección TLS y SANs:** Analiza versión de protocolo, emisor, vigencia del certificado X.509 y filtra SANs fuera de alcance.
  3. **Superficie Estándar Web:** Revisa `robots.txt` (rutas restringidas y sitemaps), `/.well-known/security.txt` y atributos de cookies.
  4. **Análisis HTTP Seguro:** Verifica cabeceras de endurecimiento (`CSP`, `HSTS`, `X-Frame-Options`, `X-Content-Type-Options`) y exposición tecnológica (`Server`).
- **Triaje y Reportes Forenses:** Clasificación de hallazgos por estado (`Pendiente`, `Revisado`, `Reportable`, `Falso Positivo`) y exportación en Markdown (`.md`) con tabla de cadena de custodia `SHA-256`.

## Requisitos e Inicio Rápido

- **Python 3.10+** con `customtkinter` instalado:
  ```bash
  pip install customtkinter
  ```
- **Interfaz Gráfica:**
  ```bash
  py main.py
  ```
- **Consola Interactiva:**
  ```bash
  py moondetex.py
  ```

## Flujo de Trabajo

1. **Crear Proyecto:** Registra el objetivo y su alcance autorizado en la pestaña **Proyectos**.
2. **Configurar Política:** Define los dominios exactos, puertos y protocolos permitidos para activar el *Gatekeeper*.
3. **Ejecutar Motores:** Selecciona el proyecto activo en **Bug Bounty** y lanza los sensores necesarios.
4. **Triaje y Exportación:** Clasifica los hallazgos detectados en la pestaña **Hallazgos** y exporta el informe técnico `.md`.