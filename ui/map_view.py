import os
import folium
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from core.network import is_connected

class MapView(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.temp_map_file = os.path.abspath("temp_active_map.html")

        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

    def render_routes_map(self, center: list, routes: list, active_route_id=None):
        online = is_connected(timeout=1.5)
        if online:
            self._render_online_folium(center, routes, active_route_id)
        else:
            self._render_offline_vector(routes, active_route_id)

    def _render_online_folium(self, center: list, routes: list, active_route_id):
        m = folium.Map(location=center, zoom_start=12, tiles=None, control_scale=True)

        folium.TileLayer(
            tiles='https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='© OpenStreetMap contributors',
            name='Plan Standard OSM',
            max_zoom=18,
            overlay=False
        ).add_to(m)

        folium.TileLayer(
            tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
            attr='© OpenTopoMap (CC-BY-SA)',
            name='Carte Topo',
            max_zoom=17,
            overlay=False
        ).add_to(m)

        active_route = None
        for r in routes:
            if r.get("id") == active_route_id:
                active_route = r
                break

        # 1. Tracé des autres itinéraires possédant une trace
        for r in routes:
            if r.get("id") == active_route_id or not r.get("has_track"):
                continue
            coords = r.get("coords", [])
            if len(coords) >= 2:
                folium.PolyLine(coords, color="#FF9100", weight=2.5, opacity=0.45).add_to(m)

        # 2. Rendu de l'itinéraire actif
        if active_route:
            if active_route.get("has_track") and len(active_route.get("coords", [])) >= 2:
                coords = active_route["coords"]
                folium.PolyLine(coords, color="#000000", weight=8, opacity=0.85).add_to(m)
                folium.PolyLine(coords, color="#00E5FF", weight=4, opacity=1.0, tooltip=f"<b>{active_route['title']}</b>").add_to(m)
                folium.CircleMarker(location=coords[0], radius=7, color="#000000", fill_color="#00E676", fill=True, fill_opacity=1.0, tooltip="Départ").add_to(m)
                folium.CircleMarker(location=coords[-1], radius=7, color="#000000", fill_color="#FFD600", fill=True, fill_opacity=1.0, tooltip=f"Sommet ({active_route.get('elevation_max', 0)}m)").add_to(m)

                crit_segs = active_route.get("eval", {}).get("critical_segments", [])
                for seg in crit_segs:
                    seg_coords = seg.get("coords", [])
                    if len(seg_coords) >= 2:
                        folium.PolyLine(
                            seg_coords, color="#FF1744", weight=7, opacity=0.95,
                            dash_array="6, 8", tooltip=f"<b>⚠️ PASSAGE CRITIQUE : {seg['reason']}</b>"
                        ).add_to(m)

                m.fit_bounds(coords, padding=[40, 40])

            elif active_route.get("point_marker"):
                pt = active_route["point_marker"]
                folium.Marker(
                    location=pt,
                    popup=f"<b>{active_route['title']}</b><br>Altitude : {active_route.get('elevation_max')}m<br><i>(Trace GPS non renseignée sur C2C)</i>",
                    tooltip=f"📍 {active_route['title']} (Sans trace)",
                    icon=folium.Icon(color="orange", icon="info-sign")
                ).add_to(m)
                m.location = pt
                m.zoom_start = 13

        folium.LayerControl(position="topright", collapsed=True).add_to(m)
        m.save(self.temp_map_file)
        self.load(QUrl.fromLocalFile(self.temp_map_file))

    def _render_offline_vector(self, routes: list, active_route_id):
        active_route = None
        for r in routes:
            if r.get("id") == active_route_id:
                active_route = r
                break
        if not active_route and routes:
            active_route = routes[0]

        if not active_route or not active_route.get("has_track"):
            title = active_route.get("title", "") if active_route else "Aucun itinéraire"
            html = f"""
            <html><body style='background:#16191E; color:#E2E8F0; font-family:sans-serif; display:flex; flex-direction:column; justify-content:center; align-items:center; height:100vh;'>
            <div style='background:#2D3748; padding:20px; border-radius:8px; text-align:center; max-width:450px;'>
                <h3 style='color:#ECC94B; margin-top:0;'>📍 Trace GPS non disponible</h3>
                <p><b>{title}</b></p>
                <p style='color:#A0AEC0; font-size:13px;'>Cet itinéraire est documenté sans fichier GPX sur Camptocamp. Consultez la fiche descriptive pour les détails de l'itinéraire.</p>
            </div>
            </body></html>
            """
            self.setHtml(html)
            return

        coords = active_route["coords"]
        lats = [pt[0] for pt in coords]
        lons = [pt[1] for pt in coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        w, h = 800, 600
        pad = 60
        span_lat = max(0.0001, max_lat - min_lat)
        span_lon = max(0.0001, max_lon - min_lon)

        svg_points = []
        for lat, lon in coords:
            x = pad + ((lon - min_lon) / span_lon) * (w - 2 * pad)
            y = (h - pad) - ((lat - min_lat) / span_lat) * (h - 2 * pad)
            svg_points.append(f"{x:.1f},{y:.1f}")

        poly_str = " ".join(svg_points)
        start_pt = svg_points[0].split(",")
        end_pt = svg_points[-1].split(",")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ margin:0; padding:0; background:#16191E; color:#E2E8F0; font-family:'Segoe UI',sans-serif; overflow:hidden; }}
                .banner {{ background:#2D3748; padding:8px 15px; font-size:12px; border-bottom:1px solid #4A5568; display:flex; justify-content:space-between; }}
                .badge {{ background:#38A169; color:white; padding:2px 6px; border-radius:3px; font-weight:bold; }}
                svg {{ width:100vw; height:calc(100vh - 40px); }}
                .track-bg {{ stroke:#000000; stroke-width:8; fill:none; stroke-linecap:round; }}
                .track-fg {{ stroke:#00E5FF; stroke-width:4; fill:none; stroke-linecap:round; }}
            </style>
        </head>
        <body>
            <div class="banner">
                <span><b>{active_route['title']}</b> (+{active_route.get('elevation_gain')}m)</span>
                <span class="badge">TRACÉ GPS DISPONIBLE</span>
            </div>
            <svg viewBox="0 0 {w} {h}">
                <polyline points="{poly_str}" class="track-bg" />
                <polyline points="{poly_str}" class="track-fg" />
                <circle cx="{start_pt[0]}" cy="{start_pt[1]}" r="7" fill="#00E676" stroke="#000" stroke-width="2"/>
                <circle cx="{end_pt[0]}" cy="{end_pt[1]}" r="7" fill="#FF1744" stroke="#000" stroke-width="2"/>
            </svg>
        </body>
        </html>
        """
        self.setHtml(html_content)