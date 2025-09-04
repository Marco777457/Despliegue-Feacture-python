from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)

DB_FILE = "informacion_medica.json"

# Cargar datos
def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Guardar datos
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
    enfermedades = request.form["enfermedades"].split(",")
    medicamentos = request.form["medicamentos"].split(",")
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # usa el puerto de Render o 5000 por defecto
    app.run(host="0.0.0.0", port=port, debug=True)
