# Contenido para: frontend/web/views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
import requests
import io
import re
import datetime

API_URL = "http://localhost:3000/"


def index(request):
    custom_message = None
    if request.method == "POST":
        file = None
        endpoint = None
        message_type = None

        if "configuracion_file" in request.FILES:
            file = request.FILES["configuracion_file"]
            endpoint = "configuracion"
            message_type = "configuracion"

        elif "consumo_file" in request.FILES:
            file = request.FILES["consumo_file"]
            endpoint = "consumo"
            message_type = "consumo"

        if file and endpoint:
            files = {"file": (file.name, file.read(), file.content_type)}
            try:
                response = requests.post(API_URL + endpoint, files=files)
                data = response.json()

                logs = data.get("log_mensajes", [])
                for log in logs:
                    messages.warning(request, log)

                if response.status_code == 200:

                    if message_type == "configuracion":
                        custom_message = (
                            f"{data.get('nuevos_clientes', 0)} nuevos clientes creados, "
                            f"{data.get('nuevas_instancias', 0)} nuevas instancias creadas, "
                            f"{data.get('nuevas_configuraciones', 0)} nuevas config. creadas, "
                            f"{data.get('nuevos_recursos', 0)} nuevos recursos creados, "
                            f"{data.get('nuevas_categorias', 0)} nueva(s) categoría(s) creada(s), "
                            f"{data.get('instancias_actualizadas', 0)} instancia(s) actualizada(s)"
                        )
                        request.session["datos_cargados"] = True

                    elif message_type == "consumo":
                        custom_message = f"{data.get('nuevos_consumos', 0)} nuevos consumos registrados."

                else:
                    custom_message = (
                        f"Error del backend: {data.get('error', response.text)}"
                    )

            except requests.exceptions.RequestException as e:
                custom_message = f"Error de conexión con el API: {e}"
            except Exception as e:
                custom_message = f"Error al procesar la respuesta: {e}"

        elif not custom_message:
            custom_message = "No se seleccionó un archivo válido."

    return render(request, "index.html", {"message": custom_message})


def operaciones(request):
    if not request.session.get("datos_cargados"):
        messages.error(
            request,
            "Debes cargar un archivo de configuración antes de acceder a Operaciones.",
        )
        return redirect("index")
    return render(request, "operaciones.html")


def inicializar_sistema(request):
    if request.method == "POST":
        try:
            response = requests.post(API_URL + "sistema/reset")
            if response.status_code == 200:
                data = response.json()
                messages.success(request, data.get("mensaje", "Sistema inicializado."))
                if "datos_cargados" in request.session:
                    del request.session["datos_cargados"]
            else:
                messages.error(request, f"Error del backend: {response.text}")
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Error de conexión con el API: {e}")

    return redirect("operaciones")


def consultar_datos(request):
    context = {"datos": None, "error": None}
    if not request.session.get("datos_cargados"):
        context["error"] = (
            "No hay datos cargados. Sube un archivo de configuración en la página de inicio."
        )
        return render(request, "consultar_datos.html", context)
    try:
        response = requests.get(API_URL + "sistema/datos")
        if response.status_code == 200:
            context["datos"] = response.json()
        else:
            context["error"] = f"Error del backend: {response.text}"
    except requests.exceptions.RequestException as e:
        context["error"] = f"Error de conexión con el API: {e}"

    return render(request, "consultar_datos.html", context)


def crear_datos(request):
    """
    Maneja los formularios para crear nuevos datos (Recursos, Categorías, Clientes)
    enviándolos como XML al endpoint /configuracion.
    """
    context = {"datos": None, "error": None}

    context["today_date"] = datetime.date.today().strftime("%Y-%m-%d")

    if request.session.get("datos_cargados"):
        try:
            response = requests.get(API_URL + "sistema/datos")
            if response.status_code == 200:
                context["datos"] = response.json()
            else:
                context["error"] = f"Error del backend: {response.text}"
        except requests.exceptions.RequestException as e:
            context["error"] = f"Error de conexión con el API: {e}"

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        xml_string = None

        try:
            if form_type == "recurso":
                xml_string = _build_xml_for_recurso(request.POST)
            elif form_type == "categoria":
                xml_string = _build_xml_for_categoria(request.POST)
            elif form_type == "cliente":
                xml_string = _build_xml_for_cliente(request.POST)
            elif form_type == "configuracion":
                xml_string = _build_xml_for_configuracion(request.POST)
            elif form_type == "instancia":
                xml_string = _build_xml_for_instancia(request.POST)
            elif form_type == "cancelar_instancia":
                xml_string = _build_xml_for_cancelar_instancia(request.POST)

            if xml_string:
                success, response_data = _post_xml_to_api(xml_string)

                logs = response_data.get("log_mensajes", [])
                for log in logs:
                    messages.warning(request, log)

                if success:
                    nuevos = (
                        response_data.get("nuevos_recursos", 0)
                        + response_data.get("nuevas_categorias", 0)
                        + response_data.get("nuevas_configuraciones", 0)
                        + response_data.get("nuevos_clientes", 0)
                        + response_data.get("nuevas_instancias", 0)
                    )
                    actualizadas = response_data.get("instancias_actualizadas", 0)

                    messages.success(
                        request,
                        f"¡Éxito! {nuevos} registro(s) creado(s) y {actualizadas} instancia(s) actualizada(s).",
                    )

                    response = requests.get(API_URL + "sistema/datos")
                    context["datos"] = response.json()

                else:
                    messages.error(
                        request,
                        f"Error de la API: {response_data.get('error', 'Error desconocido')}",
                    )

            else:
                messages.error(request, "Tipo de formulario desconocido.")

        except Exception as e:
            messages.error(request, f"Error al procesar el formulario: {e}")

    return render(request, "crear_datos.html", context)


def _post_xml_to_api(xml_string):
    xml_bytes = io.BytesIO(xml_string.encode("UTF-8"))
    files = {"file": ("datos_nuevos.xml", xml_bytes, "application/xml")}

    try:
        response = requests.post(API_URL + "configuracion", files=files)
        data = response.json()

        if response.status_code == 200:
            return True, data
        else:
            return False, data

    except requests.exceptions.RequestException as e:
        return False, {"error": f"Error de conexión: {e}"}
    except Exception as e:
        return False, {"error": f"Error al enviar XML: {e}"}


def _build_xml_for_recurso(post_data):
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<archivoConfiguraciones>
    <listaRecursos>
        <recurso id="{post_data.get('id_recurso')}">
            <nombre>{post_data.get('nombre')}</nombre>
            <abreviatura>{post_data.get('abreviatura')}</abreviatura>
            <metrica>{post_data.get('metrica')}</metrica>
            <tipo>{post_data.get('tipo')}</tipo>
            <valorXhora>{post_data.get('valorXhora')}</valorXhora>
        </recurso>
    </listaRecursos>
</archivoConfiguraciones>
    """
    return xml


def _build_xml_for_categoria(post_data):
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<archivoConfiguraciones>
    <listaCategorias>
        <categoria id="{post_data.get('id_categoria')}">
            <nombre>{post_data.get('nombre')}</nombre>
            <descripcion>{post_data.get('descripcion')}</descripcion>
            <cargaTrabajo>{post_data.get('cargaTrabajo')}</cargaTrabajo>
            <listaConfiguraciones></listaConfiguraciones>
        </categoria>
    </listaCategorias>
</archivoConfiguraciones>
    """
    return xml


def _build_xml_for_cliente(post_data):
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<archivoConfiguraciones>
    <listaClientes>
        <cliente nit="{post_data.get('nit')}">
            <nombre>{post_data.get('nombre')}</nombre>
            <usuario>{post_data.get('usuario')}</usuario>
            <clave>{post_data.get('clave')}</clave>
            <direccion>{post_data.get('direccion')}</direccion>
            <correoElectronico>{post_data.get('correo')}</correoElectronico>
            <listaInstancias></listaInstancias>
        </cliente>
    </listaClientes>
</archivoConfiguraciones>
    """
    return xml


def _build_xml_for_configuracion(post_data):
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<archivoConfiguraciones>
    <listaCategorias>
        <categoria id="{post_data.get('categoria_id')}">
            <nombre></nombre> 
            <descripcion></descripcion>
            <cargaTrabajo></cargaTrabajo>
            <listaConfiguraciones>
                <configuracion id="{post_data.get('id_config')}">
                    <nombre>{post_data.get('nombre')}</nombre>
                    <descripcion>{post_data.get('descripcion')}</descripcion>
                    <recursosConfiguracion>
                        <recurso id="{post_data.get('recurso_1_id')}">{post_data.get('recurso_1_cant')}</recurso>
                        <recurso id="{post_data.get('recurso_2_id')}">{post_data.get('recurso_2_cant')}</recurso>
                    </recursosConfiguracion>
                </configuracion>
            </listaConfiguraciones>
        </categoria>
    </listaCategorias>
</archivoConfiguraciones>
    """
    return xml


def _convertir_fecha_para_xml(fecha_raw_yyyy_mm_dd):
    """
    Convierte una fecha de 'YYYY-MM-DD' a 'dd/mm/YYYY'.
    """
    try:
        fecha_obj = datetime.datetime.strptime(fecha_raw_yyyy_mm_dd, "%Y-%m-%d").date()
        return fecha_obj.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return fecha_raw_yyyy_mm_dd


def _build_xml_for_instancia(post_data):
    fecha_inicio_xml = _convertir_fecha_para_xml(post_data.get("fechaInicio"))

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<archivoConfiguraciones>
    <listaClientes>
        <cliente nit="{post_data.get('cliente_nit')}">
            <nombre></nombre>
            <usuario></usuario>
            <clave></clave>
            <direccion></direccion>
            <correoElectronico></correoElectronico>
            <listaInstancias>
                <instancia id="{post_data.get('id_instancia')}">
                    <idConfiguracion>{post_data.get('configuracion_id')}</idConfiguracion>
                    <nombre>{post_data.get('nombre')}</nombre>
                    <fechaInicio>{fecha_inicio_xml}</fechaInicio>
                    <estado>VIGENTE</estado>
                    <fechaFinal></fechaFinal>
                </instancia>
            </listaInstancias>
        </cliente>
    </listaClientes>
</archivoConfiguraciones>
    """
    return xml


def _build_xml_for_cancelar_instancia(post_data):
    cliente_nit, instancia_id = post_data.get("instancia_a_cancelar").split("|")
    fecha_final_xml = _convertir_fecha_para_xml(post_data.get("fechaFinal"))

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<archivoConfiguraciones>
    <listaClientes>
        <cliente nit="{cliente_nit}">
            <nombre></nombre>
            <usuario></usuario>
            <clave></clave>
            <direccion></direccion>
            <correoElectronico></correoElectronico>
            <listaInstancias>
                <instancia id="{instancia_id}">
                    <idConfiguracion></idConfiguracion>
                    <nombre></nombre>
                    <fechaInicio></fechaInicio>
                    <estado>CANCELADA</estado>
                    <fechaFinal>{fecha_final_xml}</fechaFinal>
                </instancia>
            </listaInstancias>
        </cliente>
    </listaClientes>
</archivoConfiguraciones>
    """
    return xml


def proceso_facturacion(request):
    return render(request, "facturacion.html")


def reportes_pdf(request):
    return render(request, "reportes.html")
