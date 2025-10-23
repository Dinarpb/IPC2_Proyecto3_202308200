# Contenido para: backend/app.py

from flask import Flask, jsonify, request
import xml.etree.ElementTree as ET

app = Flask(__name__)

# --- Almacenamiento en memoria (de la vez anterior) ---
Recursos = []
Categorias = []
Clientes = []
recursos_ids = set()
categorias_ids = set()
clientes_nits = set()

# --- NUEVO: Almacenamiento para Consumos ---
Consumos = []
# Usamos un set de tuplas (nit, instancia, fecha) para identificar consumos únicos
consumos_unicos = set()


@app.route("/configuracion", methods=["POST"])
def cargar_configuracion():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No se proporcionó ningún archivo"}), 400

    # Contadores para items *nuevos*
    nuevos_recursos = 0
    nuevas_categorias = 0
    nuevos_clientes = 0
    nuevas_instancias = 0

    try:
        xml_content = file.read().decode("UTF-8")
        root = ET.fromstring(xml_content)

        # --- Procesar Recursos ---
        lista_recursos = root.find("listaRecursos")
        if lista_recursos is not None:
            for recurso in lista_recursos.findall("recurso"):
                recurso_id = recurso.get("id")
                if recurso_id not in recursos_ids:
                    nuevo_recurso = {
                        "id": recurso_id,
                        "nombre": recurso.find("nombre").text,
                        "abreviatura": recurso.find("abreviatura").text,
                        "metrica": recurso.find("metrica").text,
                        "tipo": recurso.find("tipo").text,
                        "valorXhora": float(recurso.find("valorXhora").text),
                    }
                    Recursos.append(nuevo_recurso)
                    recursos_ids.add(recurso_id)
                    nuevos_recursos += 1

        # --- Procesar Categorías ---
        lista_categorias = root.find("listaCategorias")
        if lista_categorias is not None:
            for categoria in lista_categorias.findall("categoria"):
                categoria_id = categoria.get("id")
                if categoria_id not in categorias_ids:
                    nueva_categoria = {
                        "id": categoria_id,
                        "nombre": categoria.find("nombre").text,
                        "descripcion": categoria.find("descripcion").text,
                        "cargaTrabajo": categoria.find("cargaTrabajo").text,
                        "configuraciones": [],
                    }

                    lista_config = categoria.find("listaConfiguraciones")
                    if lista_config is not None:
                        for config in lista_config.findall("configuracion"):
                            nueva_config = {
                                "id": config.get("id"),
                                "nombre": config.find("nombre").text,
                                "descripcion": config.find("descripcion").text,
                                "recursos": [],
                            }
                            rec_config_list = config.find("recursosConfiguracion")
                            if rec_config_list is not None:
                                for rec in rec_config_list.findall("recurso"):
                                    recurso_config = {
                                        "id": rec.get("id"),
                                        "cantidad": int(rec.text),
                                    }
                                    nueva_config["recursos"].append(recurso_config)
                            nueva_categoria["configuraciones"].append(nueva_config)

                    Categorias.append(nueva_categoria)
                    categorias_ids.add(categoria_id)
                    nuevas_categorias += 1

        # --- Procesar Clientes e Instancias ---
        lista_clientes = root.find("listaClientes")
        if lista_clientes is not None:
            for cliente in lista_clientes.findall("cliente"):
                cliente_nit = cliente.get("nit")

                existing_client = next(
                    (c for c in Clientes if c["nit"] == cliente_nit), None
                )

                if not existing_client:
                    existing_client = {
                        "nit": cliente_nit,
                        "nombre": cliente.find("nombre").text,
                        "usuario": cliente.find("usuario").text,
                        "clave": cliente.find("clave").text,
                        "direccion": cliente.find("direccion").text,
                        "correoElectronico": cliente.find("correoElectronico").text,
                        "instancias": [],
                    }
                    Clientes.append(existing_client)
                    clientes_nits.add(cliente_nit)
                    nuevos_clientes += 1

                lista_instancias = cliente.find("listaInstancias")
                if lista_instancias is not None:
                    instancias_existentes_ids = {
                        i["id"] for i in existing_client["instancias"]
                    }

                    for instancia in lista_instancias.findall("instancia"):
                        instancia_id = instancia.get("id")

                        if instancia_id not in instancias_existentes_ids:
                            nueva_instancia = {
                                "id": instancia_id,
                                "idConfiguracion": instancia.find(
                                    "idConfiguracion"
                                ).text,
                                "nombre": instancia.find("nombre").text,
                                "fechaInicio": instancia.find("fechaInicio").text,
                                "estado": instancia.find("estado").text,
                                "fechaFinal": instancia.find("fechaFinal").text,
                            }
                            existing_client["instancias"].append(nueva_instancia)
                            nuevas_instancias += 1

        # Devolver el conteo de *nuevos* items
        return jsonify(
            {
                "mensaje": "Archivo de configuración procesado",
                "nuevos_recursos": nuevos_recursos,
                "nuevas_categorias": nuevas_categorias,
                "nuevos_clientes": nuevos_clientes,
                "nuevas_instancias": nuevas_instancias,
            }
        )
    except ET.ParseError as e:
        return jsonify({"error": f"XML mal formado: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al procesar el archivo: {e}"}), 500


# --- NUEVO ENDPOINT PARA CONSUMOS ---
@app.route("/consumo", methods=["POST"])
def cargar_consumo():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No se proporcionó ningún archivo"}), 400

    nuevos_consumos = 0
    try:
        xml_content = file.read().decode("UTF-8")
        root = ET.fromstring(xml_content)

        # Iterar sobre cada elemento <consumo>
        for consumo in root.findall("consumo"):
            nit_cliente = consumo.get("nitCliente")
            id_instancia = consumo.get("idInstancia")
            tiempo = consumo.find("tiempo").text
            fecha_hora = consumo.find("fechaHora").text

            # Clave única para identificar este consumo
            clave_unica = (nit_cliente, id_instancia, fecha_hora)

            if clave_unica not in consumos_unicos:
                # Es un consumo nuevo
                nuevo_consumo = {
                    "nitCliente": nit_cliente,
                    "idInstancia": id_instancia,
                    "tiempo": float(tiempo),
                    "fechaHora": fecha_hora,
                }
                Consumos.append(nuevo_consumo)
                consumos_unicos.add(clave_unica)
                nuevos_consumos += 1

        return jsonify(
            {
                "mensaje": "Archivo de consumo procesado exitosamente",
                "nuevos_consumos": nuevos_consumos,
            }
        )
    except ET.ParseError as e:
        return jsonify({"error": f"XML mal formado: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Error al procesar el archivo: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
