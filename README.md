# Dispositivos biomédicos y APIs en Realidad Mixta (TFM)

Este repositorio contiene la implementación práctica de mi **Trabajo Fin de Máster (TFM)**. El proyecto consiste en el desarrollo de un *middleware* biomédico modular que actúa como una capa de abstracción de hardware (HAL), unificando la captura de constantes vitales desde dispositivos de salud comerciales e integrándolos de manera interoperable y en tiempo real con entornos de visualización interactivos 3D en **Realidad Aumentada y Virtual (Unity)**.

---

## Características Clave

* **Abstracción de Hardware Unificada**: Base de datos relacional estructurada por catálogos dinámicos que desacopla la persistencia de los fabricantes de hardware.
* **Sincronización Asíncrona**: Tareas planificadas en segundo plano en FastAPI para importar periódicamente las lecturas biomédicas mediante flujos seguros OAuth 2.0.
* **Interoperabilidad Clínica Nativa**: Endpoints compatibles con la especificación HL7 FHIR traduciendo magnitudes a códigos LOINC y UCUM.
* **Visualización Inmersiva 3D**: Cliente de Unity que realiza peticiones asíncronas no bloqueantes e integra paneles holográficos flotantes orientados al visor del usuario.
* **Consola de Administración Web**: Interfaz web construida en FastAPI con Jinja2, securizada mediante autenticación JWT para gestionar perfiles y vincular cuentas OAuth.
* **Despliegue Portable**: Todo el ecosistema de soporte orquestado mediante contenedores con Docker Compose.

---

## 🛠️ Requisitos de Ejecución

### Backend
1. Tener instalado **Docker** y **Docker Compose**.
2. Crear un archivo `.env` en la raíz con las credenciales de tu aplicación en el portal de desarrolladores de Withings:
   ```env
   CLIENT_ID=tu_client_id
   CLIENT_SECRET=tu_client_secret
   CALLBACK_URL=http://localhost:8000/auth/callback
   SECRET_KEY=tu_clave_secreta_jwt
   ```
3. Levantar la infraestructura de servicios:
   ```bash
   docker-compose up -d
   ```
4. Instalar las dependencias de Python y arrancar el servidor FastAPI:
   ```bash
   pip install -r requirements.txt
   uvicorn api:app --reload
   ```

### Unity Client
1. Tener instalado **Unity Hub** y **Unity 2022.3 LTS** (o superior) con soporte para OpenXR.
2. Abrir la carpeta `unity-vr` como un proyecto existente.
3. El paquete `com.vitals.vr` se importará automáticamente como dependencia local.
4. Ejecutar la escena principal y configurar la IP del servidor en el panel de login VR para iniciar la monitorización en tiempo real.
