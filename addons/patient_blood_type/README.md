# Tipos de Sangre en Facturación (`patient_blood_type`)

Módulo para **Odoo 17 Community** desarrollado como evaluación técnica. Agrega un catálogo de
tipos de sangre de pacientes y lo integra con las facturas del módulo de Facturación (`account`).

## Requerimientos del examen y dónde están implementados

| # | Requerimiento | Implementación |
|---|---------------|----------------|
| 1 | Menú **Datos › Datos de los pacientes › Tipo de Sangre** | `views/blood_type_views.xml` (`menu_root`, `menu_patient_data`, `menu_blood_type`) |
| 2 | Modelo de tipos de sangre con vistas lista y formulario (campos *Tipo* y *Activo*) | `models/blood_type.py` (`patient.blood.type`), vistas en `views/blood_type_views.xml`, 8 registros iniciales en `data/blood_type_data.xml` |
| 3 | Campo desplegable **Tipo de Sangre** en la factura, no editable al validar | `models/account_move.py` (`blood_type_id`) y `views/account_move_views.xml` (`readonly="state != 'draft'"`). La regla también se valida en servidor (`write`) |
| 4 | Botón **Comentario** solo con la factura en estado "Abierto", después de *Registrar pago* | `views/account_move_views.xml` — visible cuando `state == 'posted'` y `payment_state in ('not_paid', 'partial')`, las mismas condiciones del botón *Registrar pago* |
| 5 | Pop-up con tres desplegables filtrados (restante / restantes + / restantes -) | `wizard/blood_type_comment_wizard.py` (TransientModel) y `wizard/blood_type_comment_wizard_views.xml`. Dominios en la vista + validación `@api.constrains` en servidor |
| 6 | **Actualizar comentario** escribe en la factura las tres líneas con la estructura indicada | `action_update_comment()` escribe en `narration` (Términos y condiciones) y deja una nota en el chatter |
| 6 (JS) | Wizard en JavaScript que pide solo la fecha de factura y la actualiza vía RPC | `static/src/js/invoice_date_dialog.js` + `static/src/xml/invoice_date_dialog.xml` (componente OWL `Dialog`) y `action_update_invoice_date()` en `account.move` |
| 7 | Botón para descargar un PDF con los datos | `report/account_move_report.xml` (acción `ir.actions.report`) y `report/account_move_report_templates.xml` (plantilla QWeb). Botón **Descargar PDF** en la factura; también disponible en el menú *Imprimir* |

## Instalación

### Con Docker (recomendado)

Desde la raíz del repositorio:

```bash
docker compose up -d
docker compose logs -f odoo      # esperar "HTTP service (werkzeug) running"
```

1. Abrir http://localhost:8069 y crear la base de datos (master password `admin`).
2. Menú **Aplicaciones**, buscar *Tipos de Sangre en Facturación* y pulsar **Activar**.
   La dependencia `account` (Facturación) se instala automáticamente.

### Manual

Copiar la carpeta `patient_blood_type` a una ruta incluida en `addons_path`, reiniciar Odoo,
actualizar la lista de aplicaciones e instalar el módulo.

## Cómo probar cada punto

1. **Menú y modelo:** menú *Datos › Datos de los pacientes › Tipo de Sangre*. Deben aparecer
   O+, O-, A+, A-, B+, B-, AB+, AB-. *Crear* abre el formulario con *Tipo* y *Activo*.
2. **Factura:** *Facturación › Clientes › Facturas › Nuevo*. Bajo *Fecha de vencimiento* aparece
   *Tipo de Sangre*. Elegir un cliente, agregar una línea, seleccionar un tipo y **Confirmar**:
   el campo queda en solo lectura.
3. **Comentario:** con la factura confirmada y sin pagar aparece el botón **Comentario** junto a
   *Registrar pago*. Abre el pop-up *TIPOS DE SANGRE RESTANTES*: el primer desplegable excluye el
   tipo de la factura; el segundo solo muestra positivos; el tercero solo negativos. *Actualizar
   comentario* escribe al pie de la factura:

   ```
   SANGRE RESTANTE: O-
   SANGRE RESTANTE (+): B+
   SANGRE RESTANTE (-): AB-
   ```

4. **Wizard JS:** en una factura en borrador, botón **Editar fecha**: se abre el diálogo
   *Edicion fecha de factura*; al **Guardar**, la fecha se actualiza por RPC y el formulario se
   recarga.
5. **PDF:** botón **Descargar PDF** en la factura (o menú *Imprimir › Ficha de factura - Tipo de
   sangre*).

## Tests automatizados

14 tests (`tests/test_blood_type.py`) cubren el modelo, la herencia, el asistente y el reporte:

```bash
docker compose run --rm odoo odoo -d examen_odoo -u patient_blood_type \
    --test-enable --test-tags /patient_blood_type --stop-after-init
```

## Decisiones técnicas

- **Odoo 17 frente a las capturas del enunciado (Odoo 12).** Se respetó la intención de cada
  punto adaptando la ubicación cuando la interfaz cambió:
  - *Vendedor* ya no está en el encabezado de la factura sino en la pestaña *Otra información*;
    el campo *Tipo de Sangre* se colocó inmediatamente debajo de *Fecha de vencimiento*.
  - El estado "Abierto" (factura validada y pendiente de pago) equivale en Odoo 17 a
    `state = posted` con `payment_state` en `not_paid` / `partial`.
- **`rpc.query` no existe en Odoo 17.** Era la API legacy de `web.rpc`, eliminada al migrar el
  cliente web a OWL. Su equivalente es el servicio `rpc` (`useService("rpc")`), que realiza la
  misma llamada JSON-RPC a `/web/dataset/call_kw/<modelo>/<método>`. El diálogo se implementó como
  componente OWL sobre `Dialog` y se registra como *client action* en el registro de acciones.
- **La fecha de factura solo se edita en borrador.** Una factura validada ya tiene efectos
  contables y, en el contexto peruano, tributarios (SUNAT); el método `action_update_invoice_date`
  lo valida en servidor y devuelve un mensaje claro.
- **TransientModel para el asistente.** La selección del usuario no requiere persistencia; Odoo
  limpia automáticamente estos registros.
- **Campo `rh_factor` computado y almacenado** (positivo/negativo a partir del signo del tipo):
  permite filtrar con dominios en lugar de comparar cadenas, y se reutiliza en los filtros de
  búsqueda.
- **Validación en dos capas.** Los dominios de la vista filtran los desplegables; las mismas
  reglas se verifican con `@api.constrains` para que no dependan del cliente.
- **`narration` es un campo Html.** El comentario se construye con `markupsafe.Markup`, que
  escapa los textos y evita inyección de HTML.
- **Seguridad.** Todos los usuarios internos pueden leer el catálogo; solo el grupo
  *Facturación* (`account.group_account_invoice`) puede crear, editar o eliminar tipos de sangre.
- **Datos iniciales con `noupdate="1"`**, para que las actualizaciones del módulo no
  sobreescriban cambios hechos por el usuario.

## Estructura

```
patient_blood_type/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── blood_type.py                       # patient.blood.type
│   └── account_move.py                     # herencia de account.move
├── wizard/
│   ├── blood_type_comment_wizard.py        # TransientModel del pop-up
│   └── blood_type_comment_wizard_views.xml
├── views/
│   ├── blood_type_views.xml                # lista, formulario, búsqueda, acción y menús
│   └── account_move_views.xml              # campo y botones en la factura
├── security/ir.model.access.csv
├── data/blood_type_data.xml                # 8 tipos de sangre iniciales
├── report/
│   ├── account_move_report.xml             # acción del reporte PDF
│   └── account_move_report_templates.xml   # plantilla QWeb
├── static/
│   ├── description/icon.png
│   └── src/
│       ├── js/invoice_date_dialog.js       # componente OWL + client action
│       └── xml/invoice_date_dialog.xml     # plantilla OWL
└── tests/test_blood_type.py
```
