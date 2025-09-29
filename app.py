from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
import json, os
from functools import wraps
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permite llamadas desde otros orígenes (configurable)

datos = []
pacientes = []

DB_FILE = "informacion_medica.json"
API_KEYS_FILE = "api_keys.json"  # opcional: almacenar keys localmente (ver notas)

# ---------- helpers para datos ----------
def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

# ---------- API key simple ----------
# Puedes definir las API KEYS en variable de entorno: ANGELER_API_KEYS="key1,key2"
def load_api_keys():
    keys_env = os.environ.get("ANGELER_API_KEYS", "")
    keys = [k.strip() for k in keys_env.split(",") if k.strip()]
    # también cargamos de archivo si existe (opcional)
    if os.path.exists(API_KEYS_FILE):
        try:
            with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
                keys += stored.get("keys", [])
        except Exception:
            pass
    return set(keys)

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-KEY") or request.args.get("api_key")
        valid_keys = load_api_keys()
        if not api_key or api_key not in valid_keys:
            return jsonify({"error": "Unauthorized - invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated

def cargar_pacientes():
    """
    Devuelve una lista de pacientes en formato:
    [ {"nombre": "<clave>", ...campos...}, ... ]
    Esto facilita iterar en templates con: for p in pacientes
    """
    datos = cargar_datos()
    if isinstance(datos, dict):
        return [{"nombre": nombre, **info} for nombre, info in datos.items()]
    # si por alguna razón ya guardas una lista, la devolvemos tal cual
    return datos


# ---------- RUTAS HTML EXISTENTES ----------
@app.route("/")
def index():
    pacientes = cargar_pacientes()  # ✅ lista de diccionarios
    return render_template("index.html", pacientes=pacientes)

@app.route("/pacientes")
def listar_pacientes():
    pacientes = cargar_pacientes()  # ✅ corregido
    return render_template("pacientes.html", pacientes=pacientes)

@app.route("/registrar", methods=["POST"])
def registrar():
    nombre = request.form["nombre"]

    datos = cargar_datos()
    datos[nombre] = {
        "Edad": request.form["edad"],
        "Enfermedades": request.form.get("enfermedades", "").split(",") if request.form.get("enfermedades") else [],
        "Medicamentos": request.form.get("medicamentos", "").split(",") if request.form.get("medicamentos") else [],
        "Alergias": request.form.get("alergias", "").split(",") if request.form.get("alergias") else [],
        "TipoSangre": request.form.get("tipo_sangre", ""),
        "Contacto": {
            "Nombre": request.form.get("contacto_nombre", ""),
            "Telefono": request.form.get("contacto_tel", "")
        },
        "Descripcion": request.form.get("descripcion", "")
    }

    guardar_datos(datos)
    return redirect(url_for("index"))

@app.route("/paciente/<nombre>")
def consultar_paciente(nombre):
    datos = cargar_datos()
    paciente = datos.get(nombre, None)
    return render_template("detalle.html", nombre=nombre, paciente=paciente)

@app.route("/nuevo")
def nuevo_paciente():
    return render_template("formulario.html")



# ---------- NUEVOS ENDPOINTS API (JSON) ----------
# 1) Listar pacientes (solo nombres o con info completa si quieres)
@app.route("/api/pacientes", methods=["GET"])
@require_api_key
def api_list_pacientes():
    datos = cargar_datos()
    # opcional: ?summary=true devuelve solo nombres y edad
    summary = request.args.get("summary","false").lower() == "true"
    if summary:
        summary_list = [{"nombre": n, "Edad": datos[n].get("Edad")} for n in datos]
        return jsonify(summary_list)
    return jsonify(datos)

# 2) Obtener detalle de un paciente
@app.route("/api/paciente/<nombre>", methods=["GET"])
@require_api_key
def api_get_paciente(nombre):
    datos = cargar_datos()
    paciente = datos.get(nombre)
    if not paciente:
        return jsonify({"error": "Paciente no encontrado"}), 404
    return jsonify({nombre: paciente})

# 3) Crear o actualizar paciente (Angeler puede POST JSON)
# Example JSON body:
# {
#   "nombre": "Juan",
#   "Edad": "80",
#   "Enfermedades": ["Diabetes"],
#   "Medicamentos": ["Metformina"],
#   "Contacto de Emergencia": {"Nombre": "Ana", "Teléfono": "999"}
# }
@app.route("/api/paciente", methods=["POST", "PUT"])
@require_api_key
def api_create_update_paciente():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "JSON inválido"}), 400

    nombre = payload.get("nombre")
    if not nombre:
        return jsonify({"error": "El campo 'nombre' es requerido"}), 400

    datos = cargar_datos()
    datos[nombre] = {
        "Edad": payload.get("Edad", ""),
        "Enfermedades": payload.get("Enfermedades", []),
        "Medicamentos": payload.get("Medicamentos", []),
        "Contacto de Emergencia": payload.get("Contacto de Emergencia", {})
    }
    guardar_datos(datos)
    return jsonify({"ok": True, "paciente": {nombre: datos[nombre]}}), 201

# 4) Eliminar paciente (opcional, protegido)
@app.route("/api/paciente/<nombre>", methods=["DELETE"])
@require_api_key
def api_delete_paciente(nombre):
    datos = cargar_datos()
    if nombre not in datos:
        return jsonify({"error": "Paciente no encontrado"}), 404
    datos.pop(nombre)
    guardar_datos(datos)
    return jsonify({"ok": True}), 200

# ---------- FIN API ----------

# Nota: no uses app.run() cuando despliegues con gunicorn; Render ejecuta gunicorn para ti.
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
