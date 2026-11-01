# Bot de fichaje para Telegram

Bot de Telegram para registrar la jornada laboral desde el móvil: entrada, pausas y salida, con resumen diario y saldo de horas. Los registros se guardan en Cloud Firestore.

**Estado:** funcional, de uso personal.

## Funcionalidades

- Menú con botones: **Iniciar**, **Pausa**, **Reanudar**, **Salir** y **Resumen**.
- Cálculo de la hora de salida prevista y del saldo del día.
- Jornada de 8 horas, o de 7 horas con 15 minutos de pausa por defecto en horario de verano.
- Comandos para corregir registros: `/editar_entrada`, `/editar_salida`, `/editar_pausa_inicio`, `/editar_pausa_fin`.
- `/start` muestra el menú y `/help` las instrucciones.
- Datos por usuario y día en Firestore (`registros/{usuario}/dias/{fecha}`).

## Tecnologías

Python · python-telegram-bot 20 · Firebase Admin SDK · Cloud Firestore · python-dotenv

## Configuración

Variables de entorno (en un `.env` local o en el panel del servicio de despliegue):

| Variable | Contenido |
| --- | --- |
| `BOT_TOKEN` | Token del bot creado con @BotFather |
| `GOOGLE_APPLICATION_CREDENTIALS` | Ruta al JSON de la cuenta de servicio, o el propio JSON |

No subas el `.env` ni el JSON de la cuenta de servicio al repositorio.

## Ejecución

```bash
pip install -r requirements.txt
python main.py
```

El `Procfile` (`web: python main.py`) permite desplegarlo en plataformas tipo Heroku o Render.

## Limitaciones

- El horario de verano y la duración de la jornada están definidos en el código, no son configurables.
- Sin pruebas automatizadas.

## Licencia

Pendiente de decidir.
