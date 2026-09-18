from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import html2plaintext, mute_logger

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestBloodType(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.BloodType = cls.env['patient.blood.type']
        cls.Wizard = cls.env['patient.blood.type.comment.wizard']
        cls.o_positive = cls.env.ref('patient_blood_type.blood_type_o_positive')
        cls.o_negative = cls.env.ref('patient_blood_type.blood_type_o_negative')
        cls.b_positive = cls.env.ref('patient_blood_type.blood_type_b_positive')
        cls.ab_negative = cls.env.ref('patient_blood_type.blood_type_ab_negative')

    def _create_invoice(self, post=False, blood_type=None):
        invoice = self.init_invoice('out_invoice', amounts=[100.0])
        if blood_type:
            invoice.blood_type_id = blood_type
        if post:
            invoice.action_post()
        return invoice

    # ------------------------------------------------------------------
    # Modelo patient.blood.type
    # ------------------------------------------------------------------
    def test_initial_data_loaded(self):
        """Los 8 tipos de sangre se cargan en el orden de la especificación."""
        expected = ['O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-']
        names = [name for name in self.BloodType.search([]).mapped('name') if name in expected]
        self.assertEqual(names, expected)

    def test_rh_factor_is_computed_from_name(self):
        self.assertEqual(self.o_positive.rh_factor, 'positive')
        self.assertEqual(self.ab_negative.rh_factor, 'negative')

    def test_name_is_normalized(self):
        record = self.BloodType.create({'name': ' rh nulo- '})
        self.assertEqual(record.name, 'RH NULO-')
        self.assertEqual(record.rh_factor, 'negative')

    def test_name_must_end_with_sign(self):
        with self.assertRaises(ValidationError):
            self.BloodType.create({'name': 'O'})

    @mute_logger('odoo.sql_db')
    def test_name_must_be_unique(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.BloodType.create({'name': 'O+'})

    # ------------------------------------------------------------------
    # Herencia de account.move
    # ------------------------------------------------------------------
    def test_blood_type_locked_after_posting(self):
        invoice = self._create_invoice(post=True, blood_type=self.o_positive)
        with self.assertRaises(UserError):
            invoice.blood_type_id = self.b_positive
        # Escribir el mismo valor no debe fallar (no hay cambio real).
        invoice.blood_type_id = self.o_positive

    def test_comment_wizard_action(self):
        invoice = self._create_invoice(post=True, blood_type=self.o_positive)
        action = invoice.action_open_blood_type_comment_wizard()
        self.assertEqual(action['res_model'], 'patient.blood.type.comment.wizard')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(action['context']['default_move_id'], invoice.id)

    def test_update_invoice_date_only_in_draft(self):
        invoice = self._create_invoice()
        invoice.action_update_invoice_date('2024-05-20')
        self.assertEqual(invoice.invoice_date, fields.Date.to_date('2024-05-20'))

        invoice.action_post()
        with self.assertRaises(UserError):
            invoice.action_update_invoice_date('2024-05-21')
        with self.assertRaises(UserError):
            self._create_invoice().action_update_invoice_date(False)

    def test_invoice_date_dialog_action(self):
        invoice = self._create_invoice()
        action = invoice.action_open_invoice_date_dialog()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'patient_blood_type.invoice_date_dialog')
        self.assertEqual(action['params']['move_id'], invoice.id)
        self.assertEqual(action['params']['invoice_date'], fields.Date.to_string(invoice.invoice_date))

    # ------------------------------------------------------------------
    # Wizard de comentario
    # ------------------------------------------------------------------
    def test_wizard_writes_comment_with_exact_structure(self):
        invoice = self._create_invoice(post=True, blood_type=self.o_positive)
        wizard = self.Wizard.with_context(active_id=invoice.id).create({
            'remaining_blood_type_id': self.o_negative.id,
            'remaining_positive_blood_type_id': self.b_positive.id,
            'remaining_negative_blood_type_id': self.ab_negative.id,
        })
        self.assertEqual(wizard.move_id, invoice)
        self.assertEqual(wizard._get_comment_lines(), [
            'SANGRE RESTANTE: O-',
            'SANGRE RESTANTE (+): B+',
            'SANGRE RESTANTE (-): AB-',
        ])

        result = wizard.action_update_comment()
        self.assertEqual(result['type'], 'ir.actions.act_window_close')
        # El campo Html se sanea al guardar (<br/> -> <br>), por eso se compara el texto plano.
        self.assertEqual(
            html2plaintext(invoice.narration).splitlines(),
            ['SANGRE RESTANTE: O-', 'SANGRE RESTANTE (+): B+', 'SANGRE RESTANTE (-): AB-'],
        )
        note = invoice.message_ids.filtered(lambda m: 'SANGRE RESTANTE (+): B+' in str(m.body))
        self.assertTrue(note, 'El comentario debe quedar registrado en el chatter')

    def test_wizard_rejects_invoice_blood_type(self):
        invoice = self._create_invoice(post=True, blood_type=self.o_positive)
        with self.assertRaises(ValidationError):
            self.Wizard.create({
                'move_id': invoice.id,
                'remaining_blood_type_id': self.o_positive.id,  # excluido: es el de la factura
                'remaining_positive_blood_type_id': self.b_positive.id,
                'remaining_negative_blood_type_id': self.ab_negative.id,
            })

    def test_wizard_rejects_wrong_rh_factor(self):
        invoice = self._create_invoice(post=True, blood_type=self.o_positive)
        with self.assertRaises(ValidationError):
            self.Wizard.create({
                'move_id': invoice.id,
                'remaining_blood_type_id': self.o_negative.id,
                'remaining_positive_blood_type_id': self.ab_negative.id,  # negativo en campo (+)
                'remaining_negative_blood_type_id': self.b_positive.id,   # positivo en campo (-)
            })

    def test_wizard_without_invoice_blood_type_excludes_nothing(self):
        invoice = self._create_invoice(post=True)
        wizard = self.Wizard.create({
            'move_id': invoice.id,
            'remaining_blood_type_id': self.o_positive.id,
            'remaining_positive_blood_type_id': self.b_positive.id,
            'remaining_negative_blood_type_id': self.ab_negative.id,
        })
        self.assertFalse(wizard.invoice_blood_type_id)

    # ------------------------------------------------------------------
    # Reporte
    # ------------------------------------------------------------------
    def test_report_renders(self):
        invoice = self._create_invoice(post=True, blood_type=self.o_positive)
        invoice.narration = '<p>SANGRE RESTANTE: O-</p>'
        html, _content_type = self.env['ir.actions.report']._render_qweb_html(
            'patient_blood_type.report_blood_type_invoice', invoice.ids
        )
        html = html.decode()
        self.assertIn('Ficha de factura', html)
        self.assertIn('O+', html)
        self.assertIn('SANGRE RESTANTE: O-', html)
