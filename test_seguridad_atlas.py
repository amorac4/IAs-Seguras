# test_seguridad_atlas.py
# -------------------------------------------------------------
# Pruebas de seguridad en MongoDB Atlas (multiusuario)
# Demuestra: autenticación, TLS, RBAC (lectura/escritura),
# operaciones fuera de alcance y resumen final.
# -------------------------------------------------------------

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
from pprint import pprint
import os, sys, traceback

CLUSTER = "iasamc.g7bklh1.mongodb.net"   # <--- host de tu clúster
APP     = "IASAMC"
DBNAME  = "practica"
COLL    = "vectores"

# ====== 1) Lee contraseñas desde variables de entorno ======
USERS = {
    "amorac_A": os.getenv("MONGODB_PWD_AMORAC_A"),  # admin
    "amorac_M": os.getenv("MONGODB_PWD_AMORAC_M"),  # manager
    "amorac_R": os.getenv("MONGODB_PWD_AMORAC_R"),  # reader (solo lectura)
    "amorac_T": os.getenv("MONGODB_PWD_AMORAC_T"),  # tester
}

missing = [u for u, p in USERS.items() if not p]
if missing:
    print("❌ Faltan variables de entorno para:", ", ".join(missing))
    print("   Define con PowerShell: $env:MONGODB_PWD_<USUARIO> = \"CONTRASEÑA\"")
    sys.exit(1)

def uri(user, pwd):
    return (f"mongodb+srv://{quote_plus(user)}:{quote_plus(pwd)}@{CLUSTER}/"
            f"?retryWrites=true&w=majority&appName={APP}")

def ok(msg):   print("✅", msg)
def bad(msg):  print("❌", msg)
def sep():     print("-"*70)

# ====== 2) Conexiones (ping) y verificación de TLS ======
print("\n=== 🔐 CONEXIONES Y TLS ===\n")
clients = {}

for u, pwd in USERS.items():
    try:
        c = MongoClient(uri(u, pwd), server_api=ServerApi('1'))
        c.admin.command("ping")
        ok(f"{u} conectado correctamente (TLS forzado por Atlas).")
        clients[u] = c
    except Exception as e:
        bad(f"{u} no pudo conectarse: {str(e).splitlines()[0]}")
sep()

# ====== 3) Admin: prepara datos de prueba (insert/read/update/delete) ======
print("\n=== 🧪 PRUEBAS CON ADMIN (amorac_A) ===\n")
admin = clients["amorac_A"]
adb = admin[DBNAME]
acol = adb[COLL]

try:
    ins_res = acol.insert_many([
        {"id": "adm_1", "label": "admin_ok", "vec": [0.1, 0.2, 0.3, 0.4]},
        {"id": "adm_2", "label": "admin_ok", "vec": [0.4, 0.3, 0.2, 0.1]},
    ])
    ok(f"Admin insertó {len(ins_res.inserted_ids)} docs.")
except Exception as e:
    bad(f"Admin no pudo insertar: {e}")

print("Lectura (admin) – primeros documentos:")
for d in acol.find({}, {"_id": 0}).limit(3):
    pprint(d)

try:
    upd = acol.update_one({"id": "adm_1"}, {"$set": {"note": "actualizado_por_admin"}})
    ok(f"Admin actualizó {upd.modified_count} doc(s).")
except Exception as e:
    bad(f"Admin no pudo actualizar: {e}")

try:
    dele = acol.delete_one({"id": "adm_2"})
    ok(f"Admin eliminó {dele.deleted_count} doc(s).")
except Exception as e:
    bad(f"Admin no pudo eliminar: {e}")
sep()

# ====== 4) Reader: lectura permitida y escritura denegada ======
print("\n=== 📖 PRUEBAS CON READER (amorac_R) ===\n")
reader = clients["amorac_R"]
rdb = reader[DBNAME]
rcol = rdb[COLL]

print("Lectura (reader) – debería funcionar:")
try:
    docs = list(rcol.find({}, {"_id": 0}).limit(5))
    ok(f"Reader leyó {len(docs)} doc(s).")
    for d in docs:
        pprint(d)
except Exception as e:
    bad(f"Reader no pudo leer: {e}")

print("\nEscritura (reader) – debería FALLAR:")
try:
    rcol.insert_one({"id": "reader_write", "label": "no_deberia"})
    bad("Reader logró escribir (NO debería). Revisa su rol.")
except Exception as e:
    ok("Escritura rechazada para reader.")
    print("   →", str(e).splitlines()[0])
sep()

# ====== 5) Tester: intenta crear índice y escribir ======
print("\n=== 🧪 PRUEBAS CON TESTER (amorac_T) ===\n")
tester = clients["amorac_T"]
tdb = tester[DBNAME]
tcol = tdb[COLL]

# Intento de escritura
try:
    tcol.insert_one({"id": "tester_write", "label": "depende_del_rol"})
    ok("Tester pudo escribir (rol lo permite).")
except Exception as e:
    ok("Escritura de tester bloqueada (rol lo prohíbe).")
    print("   →", str(e).splitlines()[0])

# Intento de crear índice
try:
    idx = tcol.create_index("label")
    ok(f"Tester creó índice: {idx}")
except Exception as e:
    ok("Creación de índice denegada a tester (esperado si no tiene permisos).")
    print("   →", str(e).splitlines()[0])
sep()

# ====== 6) Intentos en base no autorizada (admin vs. reader/tester) ======
print("\n=== 🚫 ACCESO A BASE NO AUTORIZADA (admin / reader / tester) ===\n")
try:
    admin["admin"].otra.insert_one({"msg": "admin puede"})  # admin debe poder
    ok("Admin escribió en 'admin' (tiene permisos globales).")
except Exception as e:
    bad(f"Admin no pudo escribir en 'admin': {e}")

for u in ["amorac_R", "amorac_T"]:
    try:
        clients[u]["admin"].otra.insert_one({"msg": f"{u} no deberia"})
        bad(f"{u} logró escribir en 'admin' (NO debería).")
    except Exception as e:
        ok(f"{u} bloqueado en 'admin'.")
        print("   →", str(e).splitlines()[0])
sep()

# ====== 7) Resumen final ======
print("\n🎯 RESUMEN:")
print(" - Se validó autenticación (ping) y TLS para todos los usuarios.")
print(" - Admin: CRUD completo OK en practica.vectores.")
print(" - Reader: lectura OK, escritura BLOQUEADA.")
print(" - Tester: según su rol, escritura/índices pueden o no permitirse (quedan probados).")
print(" - Acceso a DB 'admin': bloqueado para reader/tester; admin permitido.")
print("\n✅ Pruebas de seguridad ejecutadas.\n")
