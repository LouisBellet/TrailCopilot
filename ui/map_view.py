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
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

    def render_routes_map(self, center: list, routes: list, active_route_id=None):
        """Bascule automatiquement entre Folium (En ligne) et le Rendu Vectoriel SVG (Hors-ligne)."""
        online = is_connected()

        if online:
            self._render_online_folium(center, routes, active_route_id)
        else:
            self._render_offline_vector(routes, active_route_id)

    def _render_online_folium(self, center: list, routes: list, active_route_id):
        """Mode En Ligne : Tuiles OpenTopoMap + Leaflet."""
        m = folium.Map(location=center, zoom_start=13, tiles=None, control_scale=True)

        folium.TileLayer(
            tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
            attr='© OpenTopoMap (CC-BY-SA)',
            name='Carte Topographique',
            max_zoom=17,
            overlay=False
        ).add_to(m)

        folium.TileLayer(
            tiles='https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='© OpenStreetMap',
            name='Plan Standard',
            overlay=False
        ).add_to(m)

        active_coords = []
        for r in routes:
            coords = r.get("coords", [])
            if len(coords) < 2:
                continue

            is_active = (r.get("id") == active_route_id)
            if is_active:
                active_coords = coords
                folium.PolyLine(coords, color="#000000", weight=8, opacity=0.85).add_to(m)
                folium.PolyLine(coords, color="#00E5FF", weight=4, opacity=1.0, tooltip=r['title']).add_to(m)
                folium.CircleMarker(location=coords[0], radius=7, color="#000000", fill_color="#00E676", fill=True, fill_opacity=1.0).add_to(m)
                folium.CircleMarker(location=coords[-1], radius=7, color="#000000", fill_color="#FF1744", fill=True, fill_opacity=1.0).add_to(m)
            else:
                folium.PolyLine(coords, color="#FF9100", weight=3, opacity=0.5).add_to(m)

        if active_coords:
            m.fit_bounds(active_coords, padding=[40, 40])
        elif routes and len(routes[0].get("coords", [])) >= 2:
            m.fit_bounds(routes[0]["coords"], padding=[40, 40])

        folium.LayerControl(position="topright", collapsed=True).add_to(m)
        m.save(self.temp_map_file)
        self.load(QUrl.fromLocalFile(self.temp_map_file))

    def _render_offline_vector(self, routes: list, active_route_id):
        """Mode Hors-Ligne : Rendu vectoriel SVG pur, autonome, sans CDN ni dépendance."""
        active_route = None
        for r in routes:
            if r.get("id") == active_route_id:
                active_route = r
                break
        if not active_route and routes:
            active_route = routes[0]

        if not active_route or not active_route.get("coords"):
            html = """
            <html><body style='background:#16191E; color:#A0AEC0; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh;'>
            <h3>⚠️ Mode Hors-Ligne : Aucun tracé sélectionné</h3>
            </body></html>
            """
            self.setHtml(html)
            return

        coords = active_route["coords"]
        lats = [pt[0] for pt in coords]
        lons = [pt[1] for pt in coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        # Normalisation dans un canevas SVG 800x600 avec marges
        w, h = 800, 600
        pad = 60
        span_lat = max(0.0001, max_lat - min_lat)
        span_lon = max(0.0001, max_lon - min_lon)

        svg_points = []
        for lat, lon in coords:
            # Inversion de l'axe Y pour les coordonnées écran
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
                .badge {{ background:#DD6B20; color:white; padding:2px 6px; border-radius:3px; font-weight:bold; }}
                svg {{ width:100vw; height:calc(100vh - 40px); }}
                .grid-line {{ stroke:#2D3748; stroke-width:1; stroke-dasharray:4; }}
                .track-bg {{ stroke:#000000; stroke-width:8; fill:none; stroke-linecap:round; stroke-linejoin:round; opacity:0.8; }}
                .track-fg {{ stroke:#00E5FF; stroke-width:4; fill:none; stroke-linecap:round; stroke-linejoin:round; }}
            </style>
        </head>
        <body>
            <div class="banner">
                <span><b>{active_route['title']}</b> (+{active_route.get('elevation_gain')}m / -{active_route.get('elevation_loss')}m)</span>
                <span class="badge">MODE HORS-LIGNE</span>
            </div>
            <svg viewBox="0 0 {w} {h}">
                <!-- Grille topographique locale -->
                <line x1="{pad}" y1="{pad}" x2="{w-pad}" y2="{pad}" class="grid-line" />
                <line x1="{pad}" y1="{h/2}" x2="{w-pad}" y2="{h/2}" class="grid-line" />
                <line x1="{pad}" y1="{h-pad}" x2="{w-pad}" y2="{h-pad}" class="grid-line" />
                <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{h-pad}" class="grid-line" />
                <line x1="{w/2}" y1="{pad}" x2="{w/2}" y2="{h-pad}" class="grid-line" />
                <line x1="{w-pad}" y1="{pad}" x2="{w-pad}" y2="{h-pad}" class="grid-line" />

                <!-- Tracé vectoriel haute visibilité -->
                <polyline points="{poly_str}" class="track-bg" />
                <polyline points="{poly_str}" class="track-fg" />

                <!-- Départ -->
                <circle cx="{start_pt[0]}" cy="{start_pt[1]}" r="8" fill="#00E676" stroke="#000000" stroke-width="2"/>
                <text x="{float(start_pt[0])+12}" y="{float(start_pt[1])+4}" fill="#00E676" font-size="12" font-weight="bold">DÉPART</text>

                <!-- Arrivée / Sommet -->
                <circle cx="{end_pt[0]}" cy="{end_pt[1]}" r="8" fill="#FF1744" stroke="#000000" stroke-width="2"/>
                <text x="{float(end_pt[0])+12}" y="{float(end_pt[1])+4}" fill="#FF1744" font-size="12" font-weight="bold">ARRIVÉE ({active_route.get('elevation_max')}m)</text>
            </svg>
        </body>
        </html>
        """
        self.setHtml(html_content)