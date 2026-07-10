"""
Normalización de provincia/localidad — fix 10/07/2026.

Problema que resuelve: los campos users.ciudad / users.provincia eran texto
libre, así que quedaban duplicados del mismo lugar con distinta grafía
("Rosario" / "rosario", "Buenos Aires" / "Pba", "Cordoba" / "Córdoba").

Solución de acá en más:
  - Provincia: pasa a ser un <select> de las 24 provincias argentinas
    (lista cerrada y conocida — no hace falta "normalizar" nada nuevo, se
    elimina la ambigüedad de raíz).
  - Localidad: sigue siendo texto libre (hay miles de localidades, no se
    puede hardcodear una lista cerrada), pero se normaliza para agrupar
    y se autoalimenta de lo que van cargando los mismos usuarios — ver
    tabla `localidades` en database.py (migración 2t) y clave_normalizada()
    acá abajo.
"""
import re
import unicodedata

PROVINCIAS_AR = [
    "Buenos Aires",
    "Catamarca",
    "Chaco",
    "Chubut",
    "Ciudad Autónoma de Buenos Aires",
    "Córdoba",
    "Corrientes",
    "Entre Ríos",
    "Formosa",
    "Jujuy",
    "La Pampa",
    "La Rioja",
    "Mendoza",
    "Misiones",
    "Neuquén",
    "Río Negro",
    "Salta",
    "San Juan",
    "San Luis",
    "Santa Cruz",
    "Santa Fe",
    "Santiago del Estero",
    "Tierra del Fuego, Antártida e Islas del Atlántico Sur",
    "Tucumán",
]


def clave_normalizada(texto):
    """minúsculas, sin tildes/puntuación, espacios colapsados. Sirve tanto
    para agrupar localidades como para matchear sinónimos de provincia."""
    if not texto:
        return ''
    t = texto.strip().lower()
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode('ascii')
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# Sinónimos/abreviaturas de provincia vistas en carga libre histórica, para la
# migración 2t (limpieza de datos viejos). Clave = clave_normalizada(texto
# libre encontrado), valor = nombre canónico de PROVINCIAS_AR.
_PROVINCIA_SINONIMOS = {
    'caba': 'Ciudad Autónoma de Buenos Aires',
    'capital federal': 'Ciudad Autónoma de Buenos Aires',
    'cap fed': 'Ciudad Autónoma de Buenos Aires',
    'ciudad autonoma de buenos aires': 'Ciudad Autónoma de Buenos Aires',
    'ciudad de buenos aires': 'Ciudad Autónoma de Buenos Aires',
    'cdad de buenos aires': 'Ciudad Autónoma de Buenos Aires',
    'pba': 'Buenos Aires',
    'bs as': 'Buenos Aires',
    'bsas': 'Buenos Aires',
    'bs.as': 'Buenos Aires',
    'prov de buenos aires': 'Buenos Aires',
    'provincia de buenos aires': 'Buenos Aires',
    'gba': 'Buenos Aires',
    'santa fe': 'Santa Fe',
    'sgo del estero': 'Santiago del Estero',
    'santiago del estero': 'Santiago del Estero',
    'tierra del fuego': 'Tierra del Fuego, Antártida e Islas del Atlántico Sur',
    'entre rios': 'Entre Ríos',
    'rio negro': 'Río Negro',
}
# Completa el mapeo con el nombre "de fábrica" de cada provincia (así
# "Cordoba" sin tilde también matchea "Córdoba", etc.) sin tener que listar
# cada variante a mano.
for _p in PROVINCIAS_AR:
    _PROVINCIA_SINONIMOS.setdefault(clave_normalizada(_p), _p)


def provincia_canonica(texto_libre):
    """Devuelve el nombre canónico de PROVINCIAS_AR si lo reconoce, o None
    si no hay match confiable (para no inventar un dato incorrecto)."""
    return _PROVINCIA_SINONIMOS.get(clave_normalizada(texto_libre))
