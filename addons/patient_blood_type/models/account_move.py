from odoo import _, fields, models
from odoo.exceptions import UserError

INVOICE_TYPES = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')


class AccountMove(models.Model):
    _inherit = 'account.move'

    blood_type_id = fields.Many2one(
        comodel_name='patient.blood.type',
        string='Tipo de Sangre',
        ondelete='restrict',
        tracking=True,
        copy=False,
        index='btree_not_null',
    )

    # ------------------------------------------------------------------
    # Restricciones
    # ------------------------------------------------------------------
    def write(self, vals):
        """El tipo de sangre solo se puede modificar en facturas en borrador.

        La vista ya lo muestra como solo lectura una vez validada la factura;
        esta validación garantiza la misma regla desde el servidor (RPC, importaciones, etc.).
        """
        if 'blood_type_id' in vals:
            locked = self.filtered(
                lambda move: move.state != 'draft' and move.blood_type_id.id != vals['blood_type_id']
            )
            if locked:
                raise UserError(_(
                    'No se puede modificar el tipo de sangre de una factura validada: %s',
                    ', '.join(locked.mapped('display_name')),
                ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Botones
    # ------------------------------------------------------------------
    def action_open_blood_type_comment_wizard(self):
        """Botón "Comentario": abre el asistente de tipos de sangre restantes."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tipo de sangre'),
            'res_model': 'patient.blood.type.comment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }

    def action_open_invoice_date_dialog(self):
        """Botón "Editar fecha": abre el diálogo OWL (client action en JavaScript)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'patient_blood_type.invoice_date_dialog',
            'params': {
                'move_id': self.id,
                'invoice_date': fields.Date.to_string(self.invoice_date) if self.invoice_date else False,
            },
        }

    def action_update_invoice_date(self, invoice_date):
        """Actualiza la fecha de la factura. Invocado por RPC desde el diálogo OWL.

        :param str invoice_date: fecha en formato ISO (AAAA-MM-DD).
        """
        self.ensure_one()
        if not invoice_date:
            raise UserError(_('Debe indicar la fecha de factura.'))
        if self.state != 'draft':
            raise UserError(_(
                'Solo se puede modificar la fecha de una factura en borrador. '
                'Una factura validada ya tiene efectos contables y tributarios.'
            ))
        self.write({'invoice_date': fields.Date.to_date(invoice_date)})
        return True
