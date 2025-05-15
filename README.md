# Trayectoria

Una biblioteca Python para crear, manipular y analizar rutas geoespaciales y sus áreas de influencia.

## Descripción

`Trayectoria` es una clase Python que permite trabajar con coordenadas geográficas para definir rutas o trayectorias, crear áreas de buffer a su alrededor y realizar operaciones espaciales como verificar si puntos están dentro de estas áreas, calcular estadísticas, visualización en mapas, entre otras funcionalidades.

Esta biblioteca facilita el análisis de corredores espaciales, áreas de influencia alrededor de rutas o caminos, y permite operaciones avanzadas sobre geometrías lineales con sus respectivas zonas de impacto.

## Instalación

### Dependencias

Esta biblioteca requiere las siguientes dependencias:

```bash
pip install numpy matplotlib folium shapely scipy osmnx pandas geopy
```

### Uso Básico

```python
from trayectoria import Trayectoria

# Crear una ruta con coordenadas (lon, lat)
coordenadas = [
    (-99.167689, 19.429026),
    (-99.166616, 19.428150),
    (-99.165243, 19.427432),
    (-99.163655, 19.426879)
]

# Crear una trayectoria con un buffer de 0.02 unidades
ruta = Trayectoria(coordenadas, ancho_buffer=0.02, puntos_suavizado=50)

# Visualizar en un mapa Folium
mapa = ruta.to_folium()
mapa.save('mapa_ruta.html')
```

## Características Principales

### 1. Flexibilidad en la Entrada de Coordenadas

`Trayectoria` acepta coordenadas en múltiples formatos:

- Lista de tuplas/listas `[(lon1, lat1), (lon2, lat2), ...]`
- Lista plana `[lon1, lat1, lon2, lat2, ...]`
- String en formato GeoJSON
- Cadenas de texto con coordenadas separadas por comas
- Objetos LineString de Shapely

```python
# Diferentes formas de inicializar una Trayectoria
ruta1 = Trayectoria([(lon1, lat1), (lon2, lat2)])
ruta2 = Trayectoria([lon1, lat1, lon2, lat2])
ruta3 = Trayectoria("[[lon1, lat1], [lon2, lat2]]")
ruta4 = Trayectoria("lon1, lat1, lon2, lat2")
ruta5 = Trayectoria(LineString([(lon1, lat1), (lon2, lat2)]))
```

### 2. Creación de Áreas de Buffer Suavizadas

La clase crea automáticamente un buffer suavizado alrededor de la ruta, considerando:

- Buffer alrededor de cada punto
- Buffer a lo largo de cada segmento
- Suavizado de los bordes para obtener contornos más naturales

```python
# Ajustar el ancho del buffer y el nivel de suavizado
ruta = Trayectoria(coordenadas, ancho_buffer=0.05, puntos_suavizado=100)
```

### 3. Verificación de Contención de Puntos

Verificar si un punto o conjunto de puntos están dentro del área de buffer:

```python
# Verificar un solo punto
punto = (-99.165, 19.427)
if ruta.contains(punto):
    print("El punto está dentro del área")

# Verificar múltiples puntos
puntos = [(-99.165, 19.427), (-99.170, 19.430)]
resultados = ruta.check_points(puntos, modo='contains')  # Lista de booleanos [True, False]

# Obtener análisis detallado
detalles = ruta.check_points(puntos, modo='details')
```

### 4. Visualización con Folium

Crear mapas interactivos para visualizar la ruta y su área de buffer:

```python
# Crear un mapa centrado en la ruta
mapa = ruta.to_folium(color='blue', fill_opacity=0.3, marker_color='red')

# Guardar el mapa como HTML
mapa.save('ruta_buffer.html')
```

### 5. Operaciones entre Trayectorias

Combinar o comparar diferentes trayectorias:

```python
# Sumar dos trayectorias (combinar rutas)
ruta_combinada = ruta1 + ruta2

# Restar trayectorias (eliminar puntos comunes)
ruta_diferencia = ruta1 - ruta2

# Comparar trayectorias
diferencias = ruta1.get_differences(ruta2)
```

### 6. Análisis de Múltiples Rutas

Analizar cómo varios puntos interactúan con múltiples áreas de buffer:

```python
# Crear varias rutas
ruta1 = Trayectoria(coordenadas1)
ruta2 = Trayectoria(coordenadas2)

# Verificar puntos en múltiples buffers
puntos = [(-99.165, 19.427), (-99.170, 19.430)]
matriz = Trayectoria.check_points_in_buffers(puntos, [ruta1, ruta2], modo='matrix')
resumen = Trayectoria.check_points_in_buffers(puntos, [ruta1, ruta2], modo='summary')
```

### 7. Estadísticas y Análisis

Obtener información detallada sobre la ruta:

```python
# Obtener estadísticas básicas
stats = ruta.get_statistics()
print(f"Longitud de la ruta: {stats['longitud_ruta']} unidades")
print(f"Área del buffer: {stats['area_buffer']} unidades cuadradas")

# Calcular gradientes de la ruta
gradientes = ruta.get_gradient()

# Calcular área del buffer en km²
area_km2 = ruta.buffer_area()
```

### 8. Manipulación de Geometrías

Modificar y transformar la ruta:

```python
# Simplificar la geometría
ruta_simple = ruta.simplify(tolerance=0.001)

# Dividir la ruta en un punto específico
ruta_parte1, ruta_parte2 = ruta.split_at_point((lon, lat))

# Interpolar puntos adicionales
ruta_detallada = ruta.interpolate_points(num_points=100)
```

### 9. Comparación con otras geometrías

```python
from shapely.geometry import LineString

linea = LineString([(lon1, lat1), (lon2, lat2), (lon3, lat3)])
comparacion = ruta.compare_with_linestring(linea, modo='detailed')
```

## Modos de Verificación de Puntos

La clase ofrece varios modos para verificar puntos:

- `'contains'`: Lista de booleanos indicando si cada punto está contenido
- `'any'`: True si al menos un punto está contenido
- `'all'`: True si todos los puntos están contenidos
- `'count'`: Número de puntos contenidos
- `'which'`: Índices de los puntos contenidos
- `'details'`: Diccionario con información detallada

## Ejemplos de Uso

### Análisis de Cobertura de Ruta

```python
import folium
from trayectoria import Trayectoria

# Definir ruta principal
ruta_principal = Trayectoria([
    (-99.167689, 19.429026),
    (-99.166616, 19.428150),
    (-99.165243, 19.427432),
    (-99.163655, 19.426879)
], ancho_buffer=0.02)

# Puntos de interés
puntos_interes = [
    (-99.166, 19.428),  # Dentro del buffer
    (-99.170, 19.430)   # Fuera del buffer
]

# Verificar cobertura
resultados = ruta_principal.check_points(puntos_interes, modo='details')

# Crear mapa
mapa = ruta_principal.to_folium(color='blue')

# Añadir puntos de interés con colores diferentes según si están contenidos
for i, punto in enumerate(puntos_interes):
    contenido = resultados['puntos_contenidos']
    color = 'green' if i in contenido else 'red'
    folium.Marker(
        location=[punto[1], punto[0]],  # Invertir coordenadas para Folium (lat, lon)
        icon=folium.Icon(color=color),
        popup=f"Punto {i}: {'Dentro' if i in contenido else 'Fuera'}"
    ).add_to(mapa)

mapa.save('analisis_cobertura.html')
```

### Combinación de Rutas

```python
# Crear dos rutas separadas
ruta1 = Trayectoria([(-99.17, 19.43), (-99.16, 19.43)])
ruta2 = Trayectoria([(-99.16, 19.43), (-99.15, 19.42)])

# Combinar las rutas
ruta_combinada = ruta1 + ruta2

# Visualizar
mapa = folium.Map(location=[19.425, -99.16], zoom_start=14)
ruta1.to_folium(mapa, color='blue', marker_color='blue')
ruta2.to_folium(mapa, color='green', marker_color='green')
ruta_combinada.to_folium(mapa, color='red', marker_color='red')
mapa.save('rutas_combinadas.html')
```

## Conversión a GeoJSON

```python
# Obtener la representación GeoJSON del área de buffer
geojson_data = ruta.to_geojson()

# Guardar el GeoJSON en un archivo
import json
with open('ruta_buffer.geojson', 'w') as f:
    json.dump(geojson_data, f)
```

## Contribuciones

Las contribuciones son bienvenidas. Por favor, siéntete libre de enviar pull requests o abrir issues para mejoras o correcciones.

## Licencia

[Apache](LICENSE)

