{
    'name': 'Tipos de Sangre en Facturación',
    'summary': 'Catálogo de tipos de sangre de pacientes integrado con las facturas',
    'description': """
Evaluación técnica Odoo 17
==========================

- Menú Datos > Datos de los pacientes > Tipo de Sangre.
- Modelo patient.blood.type con vistas lista y formulario.
- Herencia de la factura (account.move): campo Tipo de Sangre, botón Comentario
  con asistente de tipos de sangre restantes, diálogo OWL para editar la fecha
  de factura vía RPC y reporte PDF (QWeb).
""",
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'author': 'Miguel',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/blood_type_data.xml',
        'views/blood_type_views.xml',
        'wizard/blood_type_comment_wizard_views.xml',
        'report/account_move_report_templates.xml',
        'report/account_move_report.xml',
        # Se carga al final porque el botón "Descargar PDF" referencia la acción del reporte.
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'patient_blood_type/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
}
