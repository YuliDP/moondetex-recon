import http.client
import socket
import ssl
import time

from guardado_seguro_politicas_v35 import validar_dominio_alcance
from validador_dns_v33 import validar_ips_resueltas


# =====================================
# MOONDETEX - CLASE 38
# SENSOR HTTP SEGURO PARA BUG BOUNTY
# =====================================

class ControladorVelocidad:
    """Garantiza una pausa minima entre peticiones para respetar limites de tasa."""

    def __init__(self, intervalo_segundos=1.5):
        if intervalo_segundos < 0.2:
            raise ValueError("El intervalo minimo seguro es 0.2 segundos.")
        self.intervalo = float(intervalo_segundos)
        self._ultimo_envio = 0.0

    def esperar(self):
        ahora = time.monotonic()
        transcurrido = ahora - self._ultimo_envio
        if self._ultimo_envio > 0 and transcurrido < self.intervalo:
            time.sleep(self.intervalo - transcurrido)
        self._ultimo_envio = time.monotonic()


def _crear_contexto_ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


class _ConexionHTTPFijada(http.client.HTTPConnection):
    def __init__(self, host, puerto, ip_fijada, timeout=10):
        super().__init__(host, port=puerto, timeout=timeout)
        self._ip_fijada = ip_fijada

    def connect(self):
        self.sock = socket.create_connection(
            (self._ip_fijada, self.port),
            self.timeout,
        )


class _ConexionHTTPSFijada(http.client.HTTPSConnection):
    def __init__(self, host, puerto, ip_fijada, timeout=10):
        contexto = _crear_contexto_ssl()
        super().__init__(host, port=puerto, timeout=timeout, context=contexto)
        self._ip_fijada = ip_fijada

    def connect(self):
        sock = socket.create_connection(
            (self._ip_fijada, self.port),
            self.timeout,
        )
        # Mantiene SNI y validacion de certificado contra el dominio real
        self.sock = self._context.wrap_socket(
            sock,
            server_hostname=self.host,
        )


def _validar_ticket_autorizacion(ticket):
    if not isinstance(ticket, dict) or ticket.get("autorizado") is not True:
        raise ValueError("Ticket de autorizacion invalido o no aprobado.")

    protocolo = ticket.get("protocolo")
    host = ticket.get("host")
    puerto = ticket.get("puerto")
    ip_fijada = ticket.get("ip_fijada")

    if protocolo not in ("http", "https"):
        raise ValueError("Protocolo no permitido en el ticket.")

    if type(host) is not str or host.startswith("*."):
        raise ValueError("Host invalido en el ticket.")
    validar_dominio_alcance(host)

    if type(puerto) is not int or not 1 <= puerto <= 65535:
        raise ValueError("Puerto invalido en el ticket.")

    # Revalidar la IP fijada para impedir tickets falsificados hacia redes locales
    validar_ips_resueltas([ip_fijada])


def _validar_ruta_http(ruta):
    if type(ruta) is not str or not ruta.startswith("/"):
        raise ValueError("La ruta HTTP debe comenzar con '/'.")

    # Bloquear inyeccion de cabeceras (CRLF Injection)
    if "\r" in ruta or "\n" in ruta or "\x00" in ruta:
        raise ValueError("Caracteres de control no permitidos en la ruta HTTP.")


def analizar_cabeceras_http(host, protocolo, estado, cabeceras):
    """Convierte cabeceras HTTP en observaciones listas para historial_observaciones."""
    cab_norm = {k.lower(): v.strip() for k, v in cabeceras.items()}
    observaciones = []

    # 1. Detectar redirecciones sin seguirlas automaticamente
    if estado in (301, 302, 303, 307, 308):
        destino = cab_norm.get("location", "(sin cabecera Location)")
        observaciones.append({
            "clave": f"{host}:http_redirect_{estado}",
            "titulo": f"Redireccion HTTP {estado} detectada",
            "detalle": f"El servidor redirige hacia: {destino}",
        })

    # 2. Detectar exposicion de tecnologias en cabeceras
    for cabecera_tech in ("server", "x-powered-by", "x-aspnet-version"):
        if cabecera_tech in cab_norm:
            observaciones.append({
                "clave": f"{host}:banner_{cabecera_tech}",
                "titulo": f"Cabecera tecnologica expuesta ({cabecera_tech})",
                "detalle": f"Valor reportado: {cab_norm[cabecera_tech]}",
            })

    # 3. Revisar ausencia de cabeceras defensivas basicas
    defensivas = [
        ("content-security-policy", "Falta Content-Security-Policy (CSP)"),
        ("x-frame-options", "Falta X-Frame-Options (riesgo de Clickjacking)"),
        ("x-content-type-options", "Falta X-Content-Type-Options"),
    ]
    if protocolo == "https":
        defensivas.append(
            ("strict-transport-security", "Falta Strict-Transport-Security (HSTS)")
        )

    for nombre_cab, titulo in defensivas:
        if nombre_cab not in cab_norm:
            observaciones.append({
                "clave": f"{host}:missing_{nombre_cab}",
                "titulo": titulo,
                "detalle": f"El recurso no incluye la cabecera {nombre_cab}.",
            })

    return observaciones


def consultar_http_seguro(
    ticket,
    ruta="/",
    metodo="HEAD",
    identificador_bounty="MoonDetex-Research",
    controlador_tasa=None,
    timeout=10,
    max_bytes=65536,
):
    _validar_ticket_autorizacion(ticket)
    _validar_ruta_http(ruta)

    if metodo not in ("HEAD", "GET"):
        raise ValueError("Solo se permiten metodos pasivos HEAD o GET.")

    if controlador_tasa is not None:
        controlador_tasa.esperar()

    protocolo = ticket["protocolo"]
    host = ticket["host"]
    puerto = ticket["puerto"]
    ip_fijada = ticket["ip_fijada"]

    if protocolo == "https":
        conexion = _ConexionHTTPSFijada(host, puerto, ip_fijada, timeout=timeout)
    else:
        conexion = _ConexionHTTPFijada(host, puerto, ip_fijada, timeout=timeout)

    cabeceras_envio = {
        "Host": host,
        "User-Agent": "MoonDetex-Sensor/0.38 (Authorized Bug Bounty Recon)",
        "X-Bug-Bounty": identificador_bounty,
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        "Connection": "close",
    }

    try:
        conexion.request(metodo, ruta, headers=cabeceras_envio)
        respuesta = conexion.getresponse()
        estado = respuesta.status
        cabeceras_recibidas = dict(respuesta.getheaders())
        cuerpo_parcial = respuesta.read(max_bytes) if metodo == "GET" else b""
    finally:
        conexion.close()

    observaciones = analizar_cabeceras_http(
        host, protocolo, estado, cabeceras_recibidas
    )

    return {
        "host": host,
        "ip_conectada": ip_fijada,
        "puerto": puerto,
        "ruta": ruta,
        "estado_http": estado,
        "bytes_leidos": len(cuerpo_parcial),
        "observaciones": observaciones,
    }


# =====================================
# LABORATORIO OFFLINE (SIN INTERNET)
# =====================================

if __name__ == "__main__":

    print("\nMOONDETEX - CLASE 38")
    print("SENSOR HTTP SEGURO (LABORATORIO OFFLINE)")
    print("========================================")

    # 1. Intentar usar un ticket falsificado hacia localhost
    ticket_falso = {
        "autorizado": True,
        "protocolo": "https",
        "host": "api.objetivo.com",
        "puerto": 443,
        "ip_fijada": "127.0.0.1",
    }

    try:
        consultar_http_seguro(ticket_falso)
    except ValueError as error:
        print(f"BLOQUEADO (Ticket manipulado): {error}")

    # 2. Intentar inyeccion de cabeceras en la ruta
    ticket_valido = {
        "autorizado": True,
        "protocolo": "https",
        "host": "api.objetivo.com",
        "puerto": 443,
        "ip_fijada": "93.184.216.34",
    }

    try:
        consultar_http_seguro(ticket_valido, ruta="/login\r\nX-Inyectado: malicioso")
    except ValueError as error:
        print(f"BLOQUEADO (Inyeccion CRLF en ruta): {error}")

    # 3. Simular analisis de cabeceras de una respuesta real
    print("\n--- Analisis de respuesta simulada (200 OK) ---")
    hallazgos = analizar_cabeceras_http(
        host="api.objetivo.com",
        protocolo="https",
        estado=200,
        cabeceras={
            "Server": "nginx/1.24.0",
            "X-Powered-By": "PHP/8.1.2",
            "X-Content-Type-Options": "nosniff",
        },
    )
    for item in hallazgos:
        print(f"  [{item['clave']}] {item['titulo']} -> {item['detalle']}")

    # 4. Simular redireccion peligrosa hacia metadatos cloud (sin seguirla)
    print("\n--- Analisis de redireccion sospechosa (302) ---")
    hallazgos_redirect = analizar_cabeceras_http(
        host="api.objetivo.com",
        protocolo="https",
        estado=302,
        cabeceras={
            "Location": "http://169.254.169.254/latest/meta-data/",
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        },
    )
    for item in hallazgos_redirect:
        print(f"  [{item['clave']}] {item['titulo']} -> {item['detalle']}")