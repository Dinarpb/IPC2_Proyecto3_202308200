# Contenido para: backend/app.py

from flask import Flask, jsonify, request
import xml.etree.ElementTree as ET
import re

app = Flask(__name__)

Recursos = []
Categorias = []
Clientes = []
Consumos = []

recursos_ids = set()
categorias_ids = set()
clientes_nits = set()
consumos_unicos = set()


def extraer_fecha(texto):
    if not texto:
        return None
    match = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
    return match.group(1) if match else None


def extraer_fecha_hora(texto):
    if not texto:
        return None
    match = re.search(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2})", texto)
    return match.group(1) if match else None


@app.route("/configuracion", methods=["POST"])
def cargar_configuracion():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No se proporcionó ningún archivo"}), 400

    nuevos_recursos = 0
    nuevas_categorias = 0
    nuevas_configuraciones = 0
    nuevos_clientes = 0
    nuevas_instancias = 0
    instancias_actualizadas = 0
    log_mensajes = []

    try:
        xml_content = file.read().decode("UTF-8")
        root = ET.fromstring(xml_content)

        lista_recursos = root.find("listaRecursos")
        if lista_recursos is not None:
            for recurso in lista_recursos.findall("recurso"):
                recurso_id = recurso.get("id")
                if recurso_id in recursos_ids:
                    continue

                tipo_recurso = "HARDWARE"
                try:
                    tipo_recurso_raw = recurso.find("tipo").text.upper()
                    if tipo_recurso_raw in ["HARDWARE", "SOFTWARE"]:
                        tipo_recurso = tipo_recurso_raw
                    else:
                        log_mensajes.append(
                            f"ADVERTENCIA: Recurso ID {recurso_id}. Tipo '{tipo_recurso_raw}' no es válido. Se asumirá 'HARDWARE'."
                        )
                except AttributeError:
                    log_mensajes.append(
                        f"ADVERTENCIA: Recurso ID {recurso_id} no tiene tipo. Se asumirá 'HARDWARE'."
                    )

                nuevo_recurso = {
                    "id": recurso_id,
                    "nombre": recurso.find("nombre").text,
                    "abreviatura": recurso.find("abreviatura").text,
                    "metrica": recurso.find("metrica").text,
                    "tipo": tipo_recurso,
                    "valorXhora": float(recurso.find("valorXhora").text),
                }
                Recursos.append(nuevo_recurso)
                recursos_ids.add(recurso_id)
                nuevos_recursos += 1

        lista_categorias = root.find("listaCategorias")
        if lista_categorias is not None:
            for categoria in lista_categorias.findall("categoria"):
                categoria_id = categoria.get("id")

                existing_category = next(
                    (c for c in Categorias if c["id"] == categoria_id), None
                )

                if not existing_category:
                    existing_category = {
                        "id": categoria_id,
                        "nombre": categoria.find("nombre").text,
                        "descripcion": categoria.find("descripcion").text,
                        "cargaTrabajo": categoria.find("cargaTrabajo").text,
                        "configuraciones": [],
                    }
                    Categorias.append(existing_category)
                    categorias_ids.add(categoria_id)
                    nuevas_categorias += 1

                config_ids_existentes = {
                    c["id"] for c in existing_category["configuraciones"]
                }
                lista_config = categoria.find("listaConfiguraciones")
                if lista_config is not None:
                    for config in lista_config.findall("configuracion"):
                        config_id = config.get("id")
                        if config_id in config_ids_existentes:
                            continue

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

                        existing_category["configuraciones"].append(nueva_config)
                        nuevas_configuraciones += 1

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

                    for instancia in lista_instancias.findall("instancia"):
                        instancia_id = instancia.get("id")

                        existing_instance = next(
                            (
                                i
                                for i in existing_client["instancias"]
                                if i["id"] == instancia_id
                            ),
                            None,
                        )

                        if existing_instance:
                            estado_instancia_raw = instancia.find("estado").text.upper()
                            if (
                                estado_instancia_raw == "CANCELADA"
                                and existing_instance["estado"] == "VIGENTE"
                            ):
                                existing_instance["estado"] = "CANCELADA"
                                fecha_final_raw = instancia.find("fechaFinal").text
                                fecha_final = extraer_fecha(fecha_final_raw)
                                if not fecha_final:
                                    log_mensajes.append(
                                        f"ADVERTENCIA: Instancia CANCELADA ID {instancia_id} (Cliente {cliente_nit}). 'fechaFinal' no válida. Se guardará como Nulo."
                                    )
                                existing_instance["fechaFinal"] = fecha_final
                                instancias_actualizadas += 1

                        else:
                            # --- LÓGICA DE CREACIÓN (la que ya teníamos) ---
                            estado_instancia = "VIGENTE"
                            try:
                                estado_instancia_raw = instancia.find(
                                    "estado"
                                ).text.upper()
                                if estado_instancia_raw in ["VIGENTE", "CANCELADA"]:
                                    estado_instancia = estado_instancia_raw
                                else:
                                    log_mensajes.append(
                                        f"ADVERTENCIA: Instancia ID {instancia_id} (Cliente {cliente_nit}). Estado '{estado_instancia_raw}' no válido. Se asumirá 'VIGENTE'."
                                    )
                            except AttributeError:
                                log_mensajes.append(
                                    f"ADVERTENCIA: Instancia ID {instancia_id} (Cliente {cliente_nit}) no tiene estado. Se asumirá 'VIGENTE'."
                                )

                            fecha_inicio_raw = instancia.find("fechaInicio").text
                            fecha_inicio = extraer_fecha(fecha_inicio_raw)
                            if not fecha_inicio:
                                log_mensajes.append(
                                    f"ADVERTENCIA: Instancia ID {instancia_id} (Cliente {cliente_nit}). 'fechaInicio' no válida. Se guardará como Nulo."
                                )

                            fecha_final = None
                            if estado_instancia == "CANCELADA":
                                fecha_final_raw = instancia.find("fechaFinal").text
                                fecha_final = extraer_fecha(fecha_final_raw)
                                if not fecha_final:
                                    log_mensajes.append(
                                        f"ADVERTENCIA: Instancia CANCELADA ID {instancia_id} (Cliente {cliente_nit}). 'fechaFinal' no válida. Se guardará como Nulo."
                                    )

                            nueva_instancia = {
                                "id": instancia_id,
                                "idConfiguracion": instancia.find(
                                    "idConfiguracion"
                                ).text,
                                "nombre": instancia.find("nombre").text,
                                "fechaInicio": fecha_inicio,
                                "estado": estado_instancia,
                                "fechaFinal": fecha_final,
                            }
                            existing_client["instancias"].append(nueva_instancia)
                            nuevas_instancias += 1

        return jsonify(
            {
                "mensaje": "Archivo de configuración procesado",
                "nuevos_recursos": nuevos_recursos,
                "nuevas_categorias": nuevas_categorias,
                "nuevas_configuraciones": nuevas_configuraciones,
                "nuevos_clientes": nuevos_clientes,
                "nuevas_instancias": nuevas_instancias,
                "instancias_actualizadas": instancias_actualizadas,
                "log_mensajes": log_mensajes,
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Error al procesar el archivo: {e}",
                    "log_mensajes": log_mensajes,
                }
            ),
            500,
        )


@app.route("/consumo", methods=["POST"])
def cargar_consumo():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No se proporcionó ningún archivo"}), 400

    nuevos_consumos = 0
    log_mensajes = []

    try:
        xml_content = file.read().decode("UTF-8")
        root = ET.fromstring(xml_content)

        for consumo in root.findall("consumo"):
            nit_cliente = consumo.get("nitCliente")
            id_instancia = consumo.get("idInstancia")

            tiempo = 0.0
            try:
                tiempo = float(consumo.find("tiempo").text)
            except (ValueError, TypeError, AttributeError):
                log_mensajes.append(
                    f"ADVERTENCIA: Consumo para NIT {nit_cliente} (Instancia {id_instancia}) tiene un 'tiempo' no válido. Se usará 0.0."
                )

            fecha_hora_raw = consumo.find("fechaHora").text
            fecha_hora = extraer_fecha_hora(fecha_hora_raw)

            if not fecha_hora:
                log_mensajes.append(
                    f"ADVERTENCIA: Consumo para NIT {nit_cliente} (Instancia {id_instancia}). 'fechaHora' no válida. Se guardará como Nulo."
                )

            clave_unica = (nit_cliente, id_instancia, fecha_hora_raw)

            if clave_unica not in consumos_unicos:
                nuevo_consumo = {
                    "nitCliente": nit_cliente,
                    "idInstancia": id_instancia,
                    "tiempo": tiempo,
                    "fechaHora": fecha_hora,
                }
                Consumos.append(nuevo_consumo)
                consumos_unicos.add(clave_unica)
                nuevos_consumos += 1

        return jsonify(
            {
                "mensaje": "Archivo de consumo procesado exitosamente",
                "nuevos_consumos": nuevos_consumos,
                "log_mensajes": log_mensajes,
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Error al procesar el archivo: {e}",
                    "log_mensajes": log_mensajes,
                }
            ),
            500,
        )


@app.route("/sistema/reset", methods=["POST"])
def inicializar_sistema():
    Recursos.clear()
    Categorias.clear()
    Clientes.clear()
    Consumos.clear()
    recursos_ids.clear()
    categorias_ids.clear()
    clientes_nits.clear()
    consumos_unicos.clear()
    return jsonify(
        {"mensaje": "Sistema inicializado. Todos los datos han sido borrados."}
    )


@app.route("/sistema/datos", methods=["GET"])
def consultar_datos():
    return jsonify(
        {
            "recursos_disponibles": Recursos,
            "categorias_disponibles": Categorias,
            "clientes_registrados": Clientes,
            "consumos_registrados": Consumos,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
