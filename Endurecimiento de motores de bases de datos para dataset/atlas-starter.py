# atlas-starter.py
# -------------------------------------------------------------
# Conexión a MongoDB Atlas + CRUD de ejemplo (PyMongo moderno)
# -------------------------------------------------------------

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
import os
import random
import sys

# === 1) CONFIGURACIÓN: usuario/cluster y forma de proveer contraseña ===
USER = "amorac_A"
CLUSTER_HOST = "iasamc.g7bklh1.mongodb.net"  # tu host de Atlas (ya establecido)
APP_NAME = "IASAMC"

# Preferencia: toma la contraseña de variable de entorno para no hardcodearla
#   En PowerShell:  $env:MONGODB_PASSWORD="TU_CONTRASEÑA"
#   En CMD:         set MONGODB_PASSWORD=TU_CONTRASEÑA
#   (o descomenta la línea HARDCODE más abajo para pruebas rápidas)
PASSWORD = os.getenv("MONGODB_PASSWORD")

# HARDCODE (opcional para pruebas rápidas - NO recomendado en producción):
# PASSWORD = "TU_CONTRASEÑA"

if not PASSWORD:
    print("❌ Falta la contraseña. Define la variable de entorno MONGODB_PASSWORD o edita el script.")
    sys.exit(1)

# Codifica por si tu contraseña tiene caracteres especiales
enc_user = quote_plus(USER)
enc_pass = quote_plus(PASSWORD)

# URI con parámetros recomendados
URI = (
    f"mongodb+srv://{enc_user}:{enc_pass}@{CLUSTER_HOST}/"
    f"?retryWrites=true&w=majority&appName={APP_NAME}"
)

# === 2) CREAR CLIENTE Y PROBAR CONEXIÓN (ping) ===
client = MongoClient(URI, server_api=ServerApi("1"))

try:
    client.admin.command("ping")
    print("✅ Conexión exitosa: Atlas respondió al ping.")
except Exception as e:
    print("❌ Error al conectar con Atlas:", e)
    sys.exit(2)

# === 3) SELECCIONAR BD Y COLECCIÓN ===
db = client["practica"]
col = db["vectores"]

# === 4) INSERTAR DOCUMENTOS (CREATE) ===
# Ejemplos de “vectores” para la práctica (4 dimensiones simuladas)
docs = [
    {
        "id": f"v{i}",
        "vec": [round(random.uniform(-1, 1), 3) for _ in range(4)],
        "label": "familia_demo" if i % 2 == 0 else "familia_alt",
        "meta": {"dataset": "malimg_demo", "autor": "Adolfo", "idx": i},
    }
    for i in range(1, 5)
]

result_insert = col.insert_many(docs)
print(f"🟢 Insertados {len(result_insert.inserted_ids)} documentos.")

# === 5) LECTURA BÁSICA (READ) ===
print("\n📄 Documentos (primeros 5):")
for d in col.find({}, {"_id": 0}).limit(5):
    print(d)

# === 6) BÚSQUEDA FILTRADA ===
print("\n🔎 Documentos con label='familia_demo':")
for d in col.find({"label": "familia_demo"}, {"_id": 0}):
    print(d)

# === 7) ACTUALIZACIÓN (UPDATE) ===
print("\n✏️  Actualizando el campo meta.note en id='v1'...")
upd_res = col.update_one({"id": "v1"}, {"$set": {"meta.note": "ejemplo actualizado"}})
print(f"Modificados: {upd_res.modified_count}")

print("Documento v1 tras update:")
doc_v1 = col.find_one({"id": "v1"}, {"_id": 0})
print(doc_v1)

# === 8) BORRADO (DELETE) ===
print("\n🧹 Eliminando documentos con label='familia_alt'...")
del_res = col.delete_many({"label": "familia_alt"})
print(f"Eliminados: {del_res.deleted_count}")

# Conteo final
count_total = col.count_documents({})
print(f"\n📊 Total de documentos restantes en 'practica.vectores': {count_total}")

# === 9) CIERRE LIMPIO ===
client.close()
print("\n✅ CRUD completo ejecutado con éxito.")
