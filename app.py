from flask import Flask, render_template, request, redirect, url_for, jsonify
import json, os
from functools import wraps
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permitir llamadas desde otros orígenes

DB_FILE = "informacion_medica.json"
API_KEYS_FILE = "api_keys.json"

# ---------- Helpers ----------
def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def load_api_keys():
    keys_env = os.environ.get("ANGELER_API_KEYS", "")
    keys = [k.strip() for k in keys_env.split(",") if k.strip()]
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

# ---------- Rutas HTML ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/pacientes")
def listar_pacientes():
    datos = cargar_datos()
    lista_pacientes = []
    for nombre, info in datos.items():
        lista_pacientes.append({
            "nombre": nombre,
            "edad": info.get("Edad"),
            "enfermedades": ", ".join(info.get("Enfermedades", [])) if info.get("Enfermedades") else "Ninguna",
            "medicamentos": ", ".join(info.get("Medicamentos", [])) if info.get("Medicamentos") else "Ninguno",
            "alergias": ", ".join(info.get("Alergias", [])) if info.get("Alergias") else "Ninguna",
            "tipo_sangre": info.get("Tipo de Sangre", "No especificado"),
            "contacto_nombre": info.get("Contacto de Emergencia", {}).get("Nombre", ""),
            "contacto_tel": info.get("Contacto de Emergencia", {}).get("Teléfono", ""),
            "descripcion": info.get("Descripcion", "")
        })
    return render_template("pacientes.html", pacientes=lista_pacientes)

@app.route("/detalle/<nombre>")
def detalle_paciente(nombre):
    datos = cargar_datos()
    paciente = datos.get(nombre)
    if paciente:
        return render_template("detalle.html", nombre=nombre, paciente=paciente)
    return "Paciente no encontrado", 404

@app.route("/nuevo")
def nuevo_paciente():
    return render_template("formulario.html")

@app.route("/registrar", methods=["POST"])
def registrar():
    nombre = request.form["nombre"]
    edad = request.form["edad"]
    enfermedades = [e.strip() for e in request.form.get("enfermedades","").split(",") if e.strip()]
    medicamentos = [m.strip() for m in request.form.get("medicamentos","").split(",") if m.strip()]
    alergias = [a.strip() for a in request.form.get("alergias","").split(",") if a.strip()]
    tipo_sangre = request.form.get("tipo_sangre", "")
    contacto_nombre = request.form["contacto_nombre"]
    contacto_tel = request.form["contacto_tel"]
    descripcion = request.form.get("descripcion", "")

    datos = cargar_datos()
    datos[nombre] = {
        "Edad": edad,
        "Enfermedades": enfermedades,
        "Medicamentos": medicamentos,
        "Alergias": alergias,
        "Tipo de Sangre": tipo_sangre,
        "Contacto de Emergencia": {
            "Nombre": contacto_nombre,
            "Teléfono": contacto_tel
        },
        "Descripcion": descripcion
    }
    guardar_datos(datos)
    return redirect(url_for("listar_pacientes"))

# ---------- API ----------
@app.route("/api/pacientes", methods=["GET"])
@require_api_key
def api_list_pacientes():
    datos = cargar_datos()
    summary = request.args.get("summary","false").lower() == "true"
    if summary:
        summary_list = [{"nombre": n, "Edad": datos[n].get("Edad")} for n in datos]
        return jsonify(summary_list)
    return jsonify(datos)

@app.route("/api/paciente/<nombre>", methods=["GET"])
@require_api_key
def api_get_paciente(nombre):
    datos = cargar_datos()
    paciente = datos.get(nombre)
    if not paciente:
        return jsonify({"error": "Paciente no encontrado"}), 404
    return jsonify({nombre: paciente})

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
        "Alergias": payload.get("Alergias", []),
        "Tipo de Sangre": payload.get("Tipo de Sangre", ""),
        "Contacto de Emergencia": payload.get("Contacto de Emergencia", {}),
        "Descripcion": payload.get("Descripcion", "")
    }
    guardar_datos(datos)
    return jsonify({"ok": True, "paciente": {nombre: datos[nombre]}}), 201

@app.route("/api/paciente/<nombre>", methods=["DELETE"])
@require_api_key
def api_delete_paciente(nombre):
    datos = cargar_datos()
    if nombre not in datos:
        return jsonify({"error": "Paciente no encontrado"}), 404
    datos.pop(nombre)
    guardar_datos(datos)
    return jsonify({"ok": True}), 200

# ---------- Main ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
