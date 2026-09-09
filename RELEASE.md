# Cambios en esta versión

### v2.5.0

#### 🔧 Mejoras

- El aviso de torrents en pausa muestra ahora el motivo de cada uno (`[parado]`, `[error]`, `[desconocido]`), en lugar de agruparlos todos bajo el texto genérico "en pausa, parados o con error".
- El estado del tracker se decide mirando todas las entradas del torrent y no solo la primera, replicando el criterio de la interfaz de qBittorrent: basta con que un tracker funcione para no darlo por caído. Las entradas `[DHT]`, `[PEX]` y `[LSD]` quedan excluidas de esa valoración.
- Los trackers se obtienen en una única petición mediante `torrents_info(include_trackers=True)` (Web API v2.11.4+) en lugar de una petición por torrent, con reserva al método anterior en servidores más antiguos. En una biblioteca de 4.675 torrents el tiempo de proceso baja de unos 117 a menos de 2 segundos.
- Se registra un aviso en el log cuando qBittorrent devuelve un estado de tracker desconocido, y el mensaje del tracker (`msg`) cuando un anuncio falla, para no volver a perder torrents del recuento en silencio ante futuros cambios de la API.
