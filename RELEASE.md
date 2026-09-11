# Cambios en esta versión

### v2.5.0

#### ✨ Novedades

- Nueva variable `MENSAJE_EXTENDIDO`: añade entre corchetes el motivo de cada torrent en pausa (`[parado]`, `[error]`, `[desconocido]`) y, en los torrents con trackers "Not working", el mensaje con el que el tracker explica el fallo (`[Torrent not registered with this tracker.]`, `[You have reached a rate limit...]`). Permite distinguir de un vistazo un fallo pasajero de uno que requiere intervención. Solo qBittorrent.
- Nuevas variables `REANUNCIO` y `REANUNCIO_ESPERA`: cuando se detectan torrents con el tracker en error, se fuerza un reanuncio de esos torrents —respetando el intervalo mínimo que pide cada tracker—, se espera unos segundos y solo se notifican los que sigan fallando. Evita los avisos por errores pasajeros, como los trackers que rechazan el primer anuncio después de reiniciar el cliente. Solo qBittorrent.

#### 🔧 Mejoras

- El estado del tracker se decide mirando todas las entradas del torrent y no solo la primera, replicando el criterio de la interfaz de qBittorrent: basta con que un tracker funcione para no darlo por caído. Las entradas `[DHT]`, `[PEX]` y `[LSD]` quedan excluidas de esa valoración.
- Los trackers se obtienen en una única petición mediante `torrents_info(include_trackers=True)` (Web API v2.11.4+) en lugar de una petición por torrent, con reserva al método anterior en servidores más antiguos. En una biblioteca de 4.675 torrents el tiempo de proceso baja de unos 117 a menos de 2 segundos.
- Se registra un aviso en el log cuando qBittorrent devuelve un estado de tracker desconocido, para no volver a perder torrents del recuento en silencio ante futuros cambios de la API.
