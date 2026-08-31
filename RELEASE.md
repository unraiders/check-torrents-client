# Cambios en esta versión

### v2.4.1

#### 🐞 Correcciones

- Corregida la detección de torrents con trackers "Not working" en qBittorrent. La versión v5.2 (Web API v2.15.1) dividió el estado de tracker `4` en `4` (Not working), `5` (Tracker error) y `6` (Unreachable), por lo que los torrents con los dos estados nuevos dejaban de contabilizarse y no aparecían en las notificaciones ni en el resumen.
