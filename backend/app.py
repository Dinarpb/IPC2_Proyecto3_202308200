from flask import Flask, jsonify, request
import xml.etree.ElementTree as ET

app = Flask(__name__)

configuracion = []
Recursos = []
Categorias = []
Clientes = []


@app.route("/configuracion", methods=["POST"])
def cargar_configuracion():
    file = request.files.get("file")
    if file:
        # Limpiar las listas
        configuracion.clear()
        Recursos.clear()
        Categorias.clear()
        Clientes.clear()

        # Leer y parsear el XML
        xml = file.read().decode("UTF-8")
        root = ET.fromstring(xml)

        # Procesar Recursos
        for recurso in root.find("listaRecursos").findall("recurso"):
            nuevo_recurso = {
                "id": recurso.get("id"),
                "nombre": recurso.find("nombre").text,
                "abreviatura": recurso.find("abreviatura").text,
                "metrica": recurso.find("metrica").text,
                "tipo": recurso.find("tipo").text,
                "valorXhora": float(recurso.find("valorXhora").text),
            }
            Recursos.append(nuevo_recurso)

        # Procesar Categorías y sus configuraciones
        for categoria in root.find("listaCategorias").findall("categoria"):
            nueva_categoria = {
                "id": categoria.get("id"),
                "nombre": categoria.find("nombre").text,
                "descripcion": categoria.find("descripcion").text,
                "cargaTrabajo": categoria.find("cargaTrabajo").text,
                "configuraciones": [],
            }

            # Procesar configuraciones de cada categoría
            for config in categoria.find("listaConfiguraciones").findall(
                "configuracion"
            ):
                nueva_config = {
                    "id": config.get("id"),
                    "nombre": config.find("nombre").text,
                    "descripcion": config.find("descripcion").text,
                    "recursos": [],
                }

                # Procesar recursos de cada configuración
                for rec in config.find("recursosConfiguracion").findall("recurso"):
                    recurso_config = {"id": rec.get("id"), "cantidad": int(rec.text)}
                    nueva_config["recursos"].append(recurso_config)

                nueva_categoria["configuraciones"].append(nueva_config)

            Categorias.append(nueva_categoria)

        # Procesar Clientes
        for cliente in root.find("listaClientes").findall("cliente"):
            nuevo_cliente = {
                "nit": cliente.get("nit"),
                "nombre": cliente.find("nombre").text,
                "usuario": cliente.find("usuario").text,
                "clave": cliente.find("clave").text,
                "direccion": cliente.find("direccion").text,
                "correoElectronico": cliente.find("correoElectronico").text,
                "instancias": [],
            }

            # Procesar instancias de cada cliente
            for instancia in cliente.find("listaInstancias").findall("instancia"):
                nueva_instancia = {
                    "id": instancia.get("id"),
                    "idConfiguracion": instancia.find("idConfiguracion").text,
                    "nombre": instancia.find("nombre").text,
                    "fechaInicio": instancia.find("fechaInicio").text,
                    "estado": instancia.find("estado").text,
                    "fechaFinal": instancia.find("fechaFinal").text,
                }
                nuevo_cliente["instancias"].append(nueva_instancia)

            Clientes.append(nuevo_cliente)

        return jsonify(
            {
                "mensaje": "Archivo de configuración cargado exitosamente",
                "recursos": len(Recursos),
                "categorias": len(Categorias),
                "clientes": len(Clientes),
            }
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
