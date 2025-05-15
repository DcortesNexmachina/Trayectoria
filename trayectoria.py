import numpy as np
import matplotlib.pyplot as plt
import folium
import json
import re
import shapely
from shapely.geometry import Polygon, Point, mapping, MultiPoint, LineString, shape
from shapely.ops import unary_union
from scipy.interpolate import splprep, splev
import osmnx as ox
import pandas as pd
from geopy.distance import geodesic

class Trayectoria:
    def __init__(self, coordenadas, ancho_buffer=0.02, puntos_suavizado=50):
        """
        Inicializa la Trayectoria con una lista de coordenadas y parámetros de suavizado.
        :param coordenadas: Lista de tuplas (x, y) que definen la ruta.
        :param ancho_buffer: Ancho del área alrededor de la ruta.
        :param puntos_suavizado: Número de puntos para suavizar los bordes del polígono.
        """
        self.ancho_buffer = ancho_buffer
        self.puntos_suavizado = puntos_suavizado
        self.coordenadas = self._procesar_coordenadas(coordenadas)[::-1]
        self.area = self._crear_area_buffer_suavizado(self.coordenadas)
    def _procesar_coordenadas(self, coordenadas):
        """
        Procesa diferentes formatos de coordenadas.
        :param coordenadas: Coordenadas en diferentes formatos posibles
        :return: Lista de tuplas de coordenadas
        """
        if isinstance(coordenadas, list):
            if all(isinstance(c, (tuple, list)) and len(c) == 2 for c in coordenadas):
                return [tuple(map(float, c)) for c in coordenadas]
            if all(isinstance(c, (int, float)) for c in coordenadas):
                return list(zip(coordenadas[::2], coordenadas[1::2]))
        if isinstance(coordenadas, str):
            coords_match = re.findall(r'\[(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\]', coordenadas)
            if coords_match:
                return [(float(lon), float(lat)) for lon, lat in coords_match]
            try:
                geo_data = json.loads(coordenadas)
                if 'coordinates' in geo_data:
                    coords = geo_data['coordinates']
                    if isinstance(coords[0], list):
                        return [(coord[0], coord[1]) for coord in coords]
                    return coords
                if 'features' in geo_data:
                    coords = []
                    for feature in geo_data['features']:
                        if 'geometry' in feature and 'coordinates' in feature['geometry']:
                            coord = feature['geometry']['coordinates']
                            coords.append((coord[0], coord[1]))
                    return coords
            except (json.JSONDecodeError, ValueError):
                pass
        if isinstance(coordenadas, str):
            try:
                coords = re.findall(r'(-?\d+\.?\d*)\s*,?\s*(-?\d+\.?\d*)', coordenadas)
                if coords:
                    return [(float(lon), float(lat)) for lon, lat in coords]
            except:
                pass
        if isinstance(coordenadas, shapely.geometry.linestring.LineString):
            return list(coordenadas.coords)
        raise ValueError(f"No se pudo procesar las coordenadas: {coordenadas}")
    def _ordenar_coordenadas(self, coordenadas):
        """
        Ordena las coordenadas por el eje X.
        """
        return sorted(coordenadas, key=lambda p: p[0])
    def _suavizar_contorno(self, contorno):
        """
        Suaviza un contorno de puntos usando spline.
        :param contorno: Lista de puntos del contorno
        :return: Lista de puntos suavizados
        """
        x = [p[0] for p in contorno]
        y = [p[1] for p in contorno]
        x.append(x[0])
        y.append(y[0])
        try:
            tck, u = splprep([x, y], s=0, per=1)
            unew = np.linspace(0, 1, self.puntos_suavizado)
            x_new, y_new = splev(unew, tck)
            return list(zip(x_new, y_new))
        except:
            return contorno
    def _calcular_vector_normal(self, p1, p2):
        """
        Calcula el vector normal unitario para un segmento de línea.
        """
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = np.sqrt(dx**2 + dy**2)
        if length == 0:
            return None
        return (-dy/length, dx/length)
    def _crear_area_buffer_suavizado(self, coordenadas):
        """
        Crea un polígono buffer que incluye buffers para puntos y segmentos de línea,
        con bordes suavizados mediante splines.
        """
        if len(coordenadas) < 2:
            p = coordenadas[0]
            return Point(p).buffer(self.ancho_buffer)
        poligonos = []
        for punto in coordenadas:
            poligonos.append(Point(punto).buffer(self.ancho_buffer))
        for i in range(len(coordenadas) - 1):
            p1, p2 = coordenadas[i], coordenadas[i+1]
            vector_normal = self._calcular_vector_normal(p1, p2)
            if vector_normal is None:
                continue
            nx, ny = vector_normal
            superior1 = (p1[0] + nx * self.ancho_buffer, p1[1] + ny * self.ancho_buffer)
            superior2 = (p2[0] + nx * self.ancho_buffer, p2[1] + ny * self.ancho_buffer)
            inferior1 = (p1[0] - nx * self.ancho_buffer, p1[1] - ny * self.ancho_buffer)
            inferior2 = (p2[0] - nx * self.ancho_buffer, p2[1] - ny * self.ancho_buffer)
            segmento = Polygon([superior1, superior2, inferior2, inferior1])
            poligonos.append(segmento)
        area_buffer = unary_union(poligonos)
        if isinstance(area_buffer, Polygon):
            contorno_exterior = list(area_buffer.exterior.coords)
            contorno_suavizado = self._suavizar_contorno(contorno_exterior)
            area_buffer = Polygon(contorno_suavizado)
        return area_buffer
    def length(self, punto):
        """
        Calcula la distancia mínima desde un punto hasta el borde del área.
        """
        return self.area.boundary.distance(Point(punto))
    def superficie(self):
        """
        Calcula el área del polígono.
        """
        return self.area.area
    def contains(self, punto):
        """
        Verifica si un punto está dentro del área.
        """
        return self.area.contains(Point(punto))
    def dibujar(self):
        """
        Dibuja el área buffer y los puntos originales.
        """
        fig, ax = plt.subplots(figsize=(12, 7))
        x, y = self.area.exterior.xy
        ax.fill(x, y, color='lightblue', alpha=0.3, label="Área de buffer suavizada")
        px, py = zip(*self.coordenadas)
        ax.scatter(px, py, color='red', label="Puntos Originales", zorder=2)
        ax.plot(px, py, 'r--', alpha=0.5, label="Ruta Original")
        for punto in self.coordenadas:
            circulo = Point(punto).buffer(self.ancho_buffer)
            x, y = circulo.exterior.xy
            ax.plot(x, y, 'g--', alpha=0.5)
        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")
        ax.legend()
        ax.set_title(f"Visualización de la Ruta con Buffer Suavizado (Ancho: {self.ancho_buffer}, Puntos: {self.puntos_suavizado})")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    def to_geojson(self):
                """
                Convierte el área de buffer en un objeto GeoJSON.
                :return: Diccionario en formato GeoJSON
                """
                if isinstance(self.area, Polygon):
                    return {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [list(self.area.exterior.coords)][::-1]
                        },
                        "properties": {}
                    }
                else:
                    raise ValueError("El área no es un polígono válido.")
    def to_folium(self, mapa=None, color='blue', weight=2, fill=True, fill_opacity=0.2, marker_color='red'):
        """
        Añade el buffer a un mapa Folium existente o crea uno nuevo, incluyendo el área.

        :param mapa: Mapa Folium existente (opcional)
        :param color: Color del borde del polígono
        :param weight: Grosor del borde del polígono
        :param fill: Rellenar el polígono
        :param fill_opacity: Opacidad del relleno del polígono
        :param marker_color: Color de los marcadores en los puntos de la ruta
        :return: Mapa Folium con polígono y marcadores
        """
        if mapa is None:
            centro = self.coordenadas[0][::-1]  # Usar la primera coordenada como centro del mapa
            mapa = folium.Map(location=centro, zoom_start=12)
        geojson = self.to_geojson()
        coordenadas_revertidas = [coord[::-1] for coord in self.coordenadas]
        folium.GeoJson(
            geojson,
            style_function=lambda x: {
                'fillColor': color,
                'color': color,
                'weight': weight,
                'fillOpacity': fill_opacity
            }
        ).add_to(mapa)
        for punto in coordenadas_revertidas:
            folium.Marker(
                location=punto,
                icon=folium.Icon(color=marker_color)
            ).add_to(mapa)
        return mapa
    @classmethod
    def from_folium_html(cls, html_content, **kwargs):
        """
        Crea una instancia de Trayectoria a partir de un HTML de Folium.
        :param html_content: Contenido HTML de Folium
        :param kwargs: Argumentos adicionales para el constructor
        :return: Instancia de Trayectoria
        """
        return cls(html_content, **kwargs)
    def __repr__(self):
        return f"Trayectoria (coordinates={self.coordenadas}, ancho_buffer={self.ancho_buffer}, puntos_suavizado={self.puntos_suavizado})"
    def __getitem__(self, index):
        """
        Hace que el objeto sea suscriptable, permitiendo acceder a los elementos
        de la lista de coordenadas como si fuera una lista.
        :param index: El índice del punto a acceder.
        """
        return self.coordenadas[index]
    def __add__(self, other):
            """
            Permite sumar dos objetos Trayectoria. Combina sus coordenadas de forma que:
            1. No haya puntos repetidos.
            2. Las coordenadas estén ordenadas por el eje X.
            """
            if not isinstance(other, Trayectoria):
                raise TypeError(f"No se puede sumar Trayectoria con un objeto de tipo {type(other)}")
            coordenadas_combinadas = sorted(set(self.coordenadas + other.coordenadas), key=lambda p: p[0])
            return Trayectoria(coordenadas_combinadas, ancho_buffer=self.ancho_buffer)
    def __sub__(self, other):
            """
            Permite restar dos objetos Trayectoria. Elimina las coordenadas comunes y
            retorna un nuevo objeto con las coordenadas restantes.
            """
            if not isinstance(other, Trayectoria):
                raise TypeError(f"No se puede restar Trayectoria con un objeto de tipo {type(other)}")
            coordenadas_restantes = [p for p in self.coordenadas if p not in other.coordenadas]
            return Trayectoria(coordenadas_restantes, ancho_buffer=self.ancho_buffer)
    def __eq__(self, other):
        """
        Compara si dos Trayectorias son iguales.
        Dos Trayectorias son consideradas iguales si tienen:
        1. Las mismas coordenadas (en el mismo orden)
        2. El mismo ancho de buffer
        3. El mismo número de puntos de suavizado
        :param other: Otra instancia de Trayectoria para comparar
        :return: True si son iguales, False en caso contrario
        """
        if not isinstance(other, Trayectoria):
            return False
        return (self.coordenadas == other.coordenadas and
                self.ancho_buffer == other.ancho_buffer and
                self.puntos_suavizado == other.puntos_suavizado)
    def get_differences(self, other):
        """
        Compara dos Trayectorias y devuelve un diccionario con las diferencias encontradas.
        :param other: Otra instancia de Trayectoria para comparar
        :return: Diccionario con las diferencias encontradas o None si son iguales
        """
        if not isinstance(other, Trayectoria):
            return {"error": f"El objeto comparado no es una Trayectoria, es {type(other)}"}
        differences = {}
        if self.coordenadas != other.coordenadas:
            coords_self = set(self.coordenadas)
            coords_other = set(other.coordenadas)
            unique_self = coords_self - coords_other
            unique_other = coords_other - coords_self
            if unique_self or unique_other:
                differences["coordenadas"] = {
                    "coordenadas_diferentes_en_self": list(unique_self) if unique_self else None,
                    "coordenadas_diferentes_en_other": list(unique_other) if unique_other else None,
                    "numero_coordenadas_self": len(self.coordenadas),
                    "numero_coordenadas_other": len(other.coordenadas)
                }
        if self.ancho_buffer != other.ancho_buffer:
            differences["ancho_buffer"] = {
                "self": self.ancho_buffer,
                "other": other.ancho_buffer,
                "diferencia": abs(self.ancho_buffer - other.ancho_buffer)
            }
        if self.puntos_suavizado != other.puntos_suavizado:
            differences["puntos_suavizado"] = {
                "self": self.puntos_suavizado,
                "other": other.puntos_suavizado,
                "diferencia": abs(self.puntos_suavizado - other.puntos_suavizado)
            }
        area_diff = abs(self.area.area - other.area.area)
        if area_diff > 1e-10:  # Usar una pequeña tolerancia para comparaciones de punto flotante
            differences["area"] = {
                "self": self.area.area,
                "other": other.area.area,
                "diferencia": area_diff
            }
        return differences if differences else None
    def check_points(self, puntos, modo='contains'):
        """
        Verifica múltiples puntos contra esta Trayectoria.
        :param puntos: Lista de puntos como tuplas (x,y) o lista de Points
        :param modo: String que indica el modo de verificación:
                    'contains' - Lista de booleanos indicando si cada punto está contenido (default)
                    'any' - True si al menos un punto está contenido
                    'all' - True si todos los puntos están contenidos
                    'count' - Número de puntos contenidos
                    'which' - Índices de los puntos contenidos
                    'details' - Diccionario con información detallada
        :return: Depende del modo seleccionado
        """
        if isinstance(puntos, (tuple, Point)) or (isinstance(puntos, list) and len(puntos) == 2 and all(isinstance(x, (int, float)) for x in puntos)):
            puntos = [puntos]
        points = []
        for p in puntos:
            if isinstance(p, (tuple, list)):
                points.append(Point(p))
            elif isinstance(p, Point):
                points.append(p)
            else:
                raise ValueError(f"Formato de punto no válido: {p}")
        contenido = [self.contains(p) for p in points]
        distancias = [self.length(p) for p in points]
        if modo == 'contains':
            return contenido
        elif modo == 'any':
            return any(contenido)
        elif modo == 'all':
            return all(contenido)
        elif modo == 'count':
            return sum(contenido)
        elif modo == 'which':
            return [i for i, contains in enumerate(contenido) if contains]
        elif modo == 'details':
            return {
                'total_puntos': len(points),
                'puntos_contenidos': [i for i, contains in enumerate(contenido) if contains],
                'numero_contenidos': sum(contenido),
                'todos_contenidos': all(contenido),
                'algun_contenido': any(contenido),
                'distancias': distancias,
                'puntos_por_distancia': sorted(
                    enumerate(zip(contenido, distancias)),
                    key=lambda x: x[1][1]  # Ordenar por distancia
                )
            }
        else:
            raise ValueError(f"Modo '{modo}' no reconocido")
    @staticmethod
    def check_points_in_buffers(puntos, rutas_buffer, modo='matrix'):
        """
        Verifica múltiples puntos contra múltiples Trayectoria.
        :param puntos: Lista de puntos como tuplas (x,y) o Points
        :param rutas_buffer: Lista de objetos Trayectoria
        :param modo: String que indica el modo de verificación:
                    'matrix' - Matriz de booleanos (puntos x rutas) (default)
                    'summary' - Resumen general de contención
                    'by_point' - Análisis por punto
                    'by_buffer' - Análisis por buffer
                    'detailed' - Análisis detallado completo
        :return: Depende del modo seleccionado
        """
        if isinstance(puntos, (tuple, Point)) or (isinstance(puntos, list) and len(puntos) == 2 and all(isinstance(x, (int, float)) for x in puntos)):
            puntos = [puntos]
        if isinstance(rutas_buffer, Trayectoria):
            rutas_buffer = [rutas_buffer]
        points = []
        for p in puntos:
            if isinstance(p, (tuple, list)):
                points.append(Point(p))
            elif isinstance(p, Point):
                points.append(p)
            else:
                raise ValueError(f"Formato de punto no válido: {p}")
        matriz_contencion = np.zeros((len(points), len(rutas_buffer)), dtype=bool)
        matriz_distancias = np.zeros((len(points), len(rutas_buffer)))
        for i, point in enumerate(points):
            for j, rb in enumerate(rutas_buffer):
                matriz_contencion[i, j] = rb.contains(point)
                matriz_distancias[i, j] = rb.length(point)
        if modo == 'matrix':
            return matriz_contencion
        elif modo == 'summary':
            return {
                'total_puntos': len(points),
                'total_rutas': len(rutas_buffer),
                'puntos_en_alguna_ruta': np.any(matriz_contencion, axis=1).sum(),
                'puntos_en_todas_rutas': np.all(matriz_contencion, axis=1).sum(),
                'rutas_con_algun_punto': np.any(matriz_contencion, axis=0).sum(),
                'rutas_con_todos_puntos': np.all(matriz_contencion, axis=0).sum(),
                'matriz_contencion': matriz_contencion.tolist()
            }
        elif modo == 'by_point':
            return [{
                'punto_idx': i,
                'punto': (point.x, point.y),
                'rutas_contenedoras': np.where(matriz_contencion[i])[0].tolist(),
                'total_rutas_contenedoras': np.sum(matriz_contencion[i]),
                'distancia_minima': np.min(matriz_distancias[i]),
                'distancia_maxima': np.max(matriz_distancias[i]),
                'distancia_promedio': np.mean(matriz_distancias[i]),
                'en_todas_las_rutas': np.all(matriz_contencion[i])
            } for i, point in enumerate(points)]
        elif modo == 'by_buffer':
            return [{
                'ruta_idx': j,
                'puntos_contenidos': np.where(matriz_contencion[:, j])[0].tolist(),
                'total_puntos_contenidos': np.sum(matriz_contencion[:, j]),
                'distancia_minima': np.min(matriz_distancias[:, j]),
                'distancia_maxima': np.max(matriz_distancias[:, j]),
                'distancia_promedio': np.mean(matriz_distancias[:, j]),
                'contiene_todos_puntos': np.all(matriz_contencion[:, j])
            } for j in range(len(rutas_buffer))]
        elif modo == 'detailed':
            return {
                'summary': {
                    'total_puntos': len(points),
                    'total_rutas': len(rutas_buffer),
                    'puntos_en_alguna_ruta': np.any(matriz_contencion, axis=1).sum(),
                    'puntos_en_todas_rutas': np.all(matriz_contencion, axis=1).sum(),
                    'rutas_con_algun_punto': np.any(matriz_contencion, axis=0).sum(),
                    'rutas_con_todos_puntos': np.all(matriz_contencion, axis=0).sum()
                },
                'matriz_contencion': matriz_contencion.tolist(),
                'matriz_distancias': matriz_distancias.tolist(),
                'analisis_por_punto': [{
                    'punto_idx': i,
                    'punto': (point.x, point.y),
                    'rutas_contenedoras': np.where(matriz_contencion[i])[0].tolist(),
                    'total_rutas_contenedoras': np.sum(matriz_contencion[i]),
                    'distancias': matriz_distancias[i].tolist()
                } for i, point in enumerate(points)],
                'analisis_por_ruta': [{
                    'ruta_idx': j,
                    'puntos_contenidos': np.where(matriz_contencion[:, j])[0].tolist(),
                    'total_puntos_contenidos': np.sum(matriz_contencion[:, j]),
                    'distancias': matriz_distancias[:, j].tolist()
                } for j in range(len(rutas_buffer))]
            }
        else:
            raise ValueError(f"Modo '{modo}' no reconocido")
    @staticmethod
    def check_point_in_buffers(punto, rutas_buffer, modo='any'):
        """
        Verifica si un punto está dentro de una o más Trayectoria según el modo especificado.
        :param punto: Tupla (x, y) o Point de Shapely que representa el punto a verificar
        :param rutas_buffer: Lista de objetos Trayectoria
        :param modo: String que indica el modo de verificación:
                    'any' - True si el punto está en al menos una ruta (default)
                    'all' - True si el punto está en todas las rutas
                    'count' - Devuelve el número de rutas que contienen el punto
                    'which' - Devuelve lista de índices de las rutas que contienen el punto
                    'details' - Devuelve diccionario con información detallada
        :return: Depende del modo seleccionado
        """
        if isinstance(punto, (tuple, list)):
            punto = Point(punto)
        elif not isinstance(punto, Point):
            raise ValueError("El punto debe ser una tupla (x,y) o un objeto Point de Shapely")
        if not isinstance(rutas_buffer, (list, tuple)):
            rutas_buffer = [rutas_buffer]
        if not all(isinstance(rb, Trayectoria) for rb in rutas_buffer):
            raise ValueError("Todas las rutas deben ser instancias de Trayectoria")
        contenido = [rb.contains(punto) for rb in rutas_buffer]
        if modo == 'any':
            return any(contenido)
        elif modo == 'all':
            return all(contenido)
        elif modo == 'count':
            return sum(contenido)
        elif modo == 'which':
            return [i for i, contains in enumerate(contenido) if contains]
        elif modo == 'details':
            return {
                'total_rutas': len(rutas_buffer),
                'rutas_contenedoras': [i for i, contains in enumerate(contenido) if contains],
                'numero_rutas_contenedoras': sum(contenido),
                'en_todas': all(contenido),
                'en_alguna': any(contenido),
                'distancias': [rb.length(punto) for rb in rutas_buffer]
            }
        else:
            raise ValueError(f"Modo '{modo}' no reconocido")
    def get_centerline(self):
        """
        Obtiene la línea central que forma la ruta.
        :return: LineString de Shapely
        """
        return LineString(self.coordenadas)
    def get_statistics(self):
        """
        Calcula estadísticas importantes de la ruta.
        :return: Diccionario con estadísticas
        """
        centerline = self.get_centerline()
        return {
            'longitud_ruta': centerline.length,
            'area_buffer': self.area.area,
            'perimetro_buffer': self.area.length,
            'num_puntos': len(self.coordenadas),
            'bbox': self.area.bounds,  # (minx, miny, maxx, maxy)
            'centroide': (self.area.centroid.x, self.area.centroid.y)
        }
    def simplify(self, tolerance=0.1):
        """
        Crea una nueva Trayectoria con coordenadas simplificadas.
        :param tolerance: Tolerancia para la simplificación
        :return: Nueva instancia de Trayectoria simplificada
        """
        simplified_line = LineString(self.coordenadas).simplify(tolerance)
        return Trayectoria(list(simplified_line.coords),
                         self.ancho_buffer,
                         self.puntos_suavizado)
    def split_at_point(self, punto):
        """
        Divide la ruta en dos en el punto más cercano.
        :param punto: Punto donde dividir (x, y)
        :return: Tupla de dos Trayectoria
        """
        line = LineString(self.coordenadas)
        point = Point(punto)
        nearest_point = line.interpolate(line.project(point))
        split_distance = line.project(nearest_point)
        line1 = LineString(line.coords[:line.project(point, normalized=True)])
        line2 = LineString(line.coords[line.project(point, normalized=True):])
        return (Trayectoria(list(line1.coords), self.ancho_buffer, self.puntos_suavizado),
                Trayectoria(list(line2.coords), self.ancho_buffer, self.puntos_suavizado))
    def get_gradient(self):
        """
        Calcula el gradiente (cambio) de la ruta en cada segmento.
        :return: Lista de gradientes entre puntos consecutivos
        """
        gradients = []
        for i in range(len(self.coordenadas) - 1):
            p1 = self.coordenadas[i]
            p2 = self.coordenadas[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            if dx == 0:
                gradients.append(float('inf') if dy > 0 else float('-inf'))
            else:
                gradients.append(dy/dx)
        return gradients
    def interpolate_points(self, num_points):
        """
        Interpola puntos adicionales a lo largo de la ruta.
        :param num_points: Número de puntos deseados
        :return: Nueva Trayectoria con puntos interpolados
        """
        line = LineString(self.coordenadas)
        distances = np.linspace(0, line.length, num_points)
        points = [line.interpolate(distance) for distance in distances]
        new_coords = [(p.x, p.y) for p in points]
        return Trayectoria(new_coords, self.ancho_buffer, self.puntos_suavizado)       
    def __str__(self):
        """
        Representación en string de la ruta con estadísticas básicas.
        """
        stats = self.get_statistics()
        return (f"Trayectoria con {len(self.coordenadas)} puntos\n"
                f"Longitud de ruta: {stats['longitud_ruta']:.2f}\n"
                f"Área del buffer: {stats['area_buffer']:.2f}\n"
                f"Ancho del buffer: {self.ancho_buffer}")
    def compare_with_linestring(self, linestring, modo='basic'):
        """
        Compara la Trayectoria actual con un LineString de Shapely.
        :param linestring: LineString de Shapely o coordenadas para crear uno
        :param modo: Tipo de comparación ('basic', 'detailed', 'geometric')
        :return: Diccionario con los resultados de la comparación
        """
        if not isinstance(linestring, LineString):
            if isinstance(linestring, (list, tuple)):
                linestring = LineString(linestring)
            else:
                raise ValueError("El parámetro debe ser un LineString o coordenadas válidas")
        ruta_line = LineString(self.coordenadas)
        if modo == 'basic':
            return {
                'misma_longitud': abs(ruta_line.length - linestring.length) < 1e-10,
                'mismo_num_puntos': len(self.coordenadas) == len(list(linestring.coords)),
                'mismos_puntos_inicio_fin': (
                    self.coordenadas[0] == list(linestring.coords)[0] and
                    self.coordenadas[-1] == list(linestring.coords)[-1]
                )
            }
        elif modo == 'detailed':
            coords_linestring = list(linestring.coords)
            min_len = min(len(self.coordenadas), len(coords_linestring))
            distancias = [Point(self.coordenadas[i]).distance(Point(coords_linestring[i]))
                         for i in range(min_len)]
            return {
                'misma_longitud': abs(ruta_line.length - linestring.length) < 1e-10,
                'mismo_num_puntos': len(self.coordenadas) == len(coords_linestring),
                'mismos_puntos_inicio_fin': (
                    self.coordenadas[0] == coords_linestring[0] and
                    self.coordenadas[-1] == coords_linestring[-1]
                ),
                'distancia_maxima_entre_puntos': max(distancias) if distancias else None,
                'distancia_promedio_entre_puntos': sum(distancias)/len(distancias) if distancias else None,
                'diferencia_longitud': abs(ruta_line.length - linestring.length),
                'puntos_ruta': len(self.coordenadas),
                'puntos_linestring': len(coords_linestring)
            }
        elif modo == 'geometric':
            buffer_line = linestring.buffer(self.ancho_buffer)
            return {
                'misma_longitud': abs(ruta_line.length - linestring.length) < 1e-10,
                'mismo_num_puntos': len(self.coordenadas) == len(list(linestring.coords)),
                'area_diferencia': self.area.symmetric_difference(buffer_line).area,
                'area_intersection': self.area.intersection(buffer_line).area,
                'area_union': self.area.union(buffer_line).area,
                'indice_jaccard': (
                    self.area.intersection(buffer_line).area /
                    self.area.union(buffer_line).area
                ),
                'hausdorff_distance': ruta_line.hausdorff_distance(linestring),
                'contiene_linestring': self.area.contains(linestring),
                'linestring_contiene_ruta': buffer_line.contains(ruta_line)
            }
        else:
            raise ValueError(f"Modo '{modo}' no reconocido")
    def buffer_area(self):
        """Calcula el área del buffer en km²"""
        buffer_geom = shape(self.to_geojson()["features"][0]["geometry"])
        return buffer_geom.area / 1e6
