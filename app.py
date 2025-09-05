from flask import Flask, render_template, request, redirect, url_for
import json, os

app = Flask(__name__)

DB_FILE = "informacion_medica.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_datos(datos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

@app.route("/")
def index():
    datos = cargar_datos()
    return render_template("index.html", pacientes=datos)

@app.route("/registrar", methods=["POST"])
def registrar():
    nombre = request.form["nombre"]
    edad = request.form["edad"]
    enfermedades = [e.strip() for e in request.form["enfermedades"].split(",") if e.strip()]
    medicamentos = [m.strip() for m in request.form["medicamentos"].split(",") if m.strip()]
    contacto_nombre = request.form["contacto_nombre"]
    contacto_tel = request.form["contacto_tel"]

    datos = cargar_datos()
    datos[nombre] = {
        "Edad": edad,
        "Enfermedades": enfermedades,
        "Medicamentos": medicamentos,
        "Contacto de Emergencia": {
            "Nombre": contacto_nombre,
            "Teléfono": contacto_tel
        }
    }
    guardar_datos(datos)
    return redirect(url_for("index"))

@app.route("/paciente/<nombre>")
def consultar_paciente(nombre):
    datos = cargar_datos()
    paciente = datos.get(nombre, None)
    return render_template("detalle.html", nombre=nombre, paciente=paciente)

# Solo define el app, no pongas app.run() porque Render usa gunicorn
