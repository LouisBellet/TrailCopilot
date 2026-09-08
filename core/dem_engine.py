import math

class DEMEngine:
    @staticmethod
    def haversine_distance(coord1: list, coord2: list) -> float:
        """Calcule la distance en mètres entre deux points [lat, lon]."""
        r = 6371000.0  # Rayon de la Terre en mètres
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    @classmethod
    def analyze_slopes(cls, coords: list, elevations: list) -> dict:
        """
        Calcule les pentes le long du tracé.
        Retourne la pente moyenne, la pente maximale et la présence de passages > 30° (58%).
        """
        if len(coords) < 2 or len(elevations) < 2:
            return {"max_slope_deg": 0.0, "avg_slope_deg": 0.0, "has_critical_slopes": False}

        slopes_deg = []
        critical_segments_count = 0

        for i in range(len(coords) - 1):
            dist = cls.haversine_distance(coords[i], coords[i+1])
            if dist < 5.0:  # Évite les divisions par zéro sur des points trop proches
                continue
            
            d_ele = abs(elevations[i+1] - elevations[i])
            slope_rad = math.atan(d_ele / dist)
            slope_deg = math.degrees(slope_rad)
            slopes_deg.append(slope_deg)

            if slope_deg >= 30.0:
                critical_segments_count += 1

        if not slopes_deg:
            return {"max_slope_deg": 0.0, "avg_slope_deg": 0.0, "has_critical_slopes": False}

        max_slope = max(slopes_deg)
        avg_slope = sum(slopes_deg) / len(slopes_deg)

        return {
            "max_slope_deg": round(max_slope, 1),
            "avg_slope_deg": round(avg_slope, 1),
            "critical_segments_count": critical_segments_count,
            "has_critical_slopes": critical_segments_count > 0
        }