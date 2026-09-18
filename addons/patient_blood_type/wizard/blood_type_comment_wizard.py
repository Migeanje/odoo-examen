from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BloodTypeCommentWizard(models.TransientModel):
    """Asistente que agrega a la factura el comentario de tipos de sangre restantes.

    Es un TransientModel: la selección del usuario no necesita persistir, Odoo
    elimina estos registros automáticamente pasado un tiempo.
    """

    _name = 'patient.blood.type.comment.wizard'
    _description = 'Asistente de comentario de tipos de sangre'

    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura',
        required=True,
        readonly=True,
        ondelete='cascade',
        default=lambda self: self.env.context.get('active_id'),
    )
    invoice_blood_type_id = fields.Many2one(
        related='move_id.blood_type_id',
        string='Tipo de sangre de la factura',
    )
    remaining_blood_type_id = fields.Many2one(
        comodel_name='patient.blood.type',
        string='Tipo sangre restante',
        required=True,
    )
    remaining_positive_blood_type_id = fields.Many2one(
        comodel_name='patient.blood.type',
        string='Tipos de sangre restante (+)',
        required=True,
    )
    remaining_negative_blood_type_id = fields.Many2one(
        comodel_name='patient.blood.type',
        string='Tipos de sangre restantes (-)',
        required=True,
    )

    # ------------------------------------------------------------------
    # Validaciones de servidor (los dominios de la vista son solo la primera barrera)
    # ------------------------------------------------------------------
    @api.constrains(
        'remaining_blood_type_id',
        'remaining_positive_blood_type_id',
        'remaining_negative_blood_type_id',
    )
    def _check_remaining_blood_types(self):
        for wizard in self:
            excluded = wizard.invoice_blood_type_id
            selected = (
                wizard.remaining_blood_type_id
                | wizard.remaining_positive_blood_type_id
                | wizard.remaining_negative_blood_type_id
            )
            if excluded and excluded in selected:
                raise ValidationError(_(
                    'El tipo de sangre de la factura (%s) no puede seleccionarse como tipo restante.',
                    excluded.name,
                ))
            if wizard.remaining_positive_blood_type_id.rh_factor != 'positive':
                raise ValidationError(_('"Tipos de sangre restante (+)" solo admite tipos positivos.'))
            if wizard.remaining_negative_blood_type_id.rh_factor != 'negative':
                raise ValidationError(_('"Tipos de sangre restantes (-)" solo admite tipos negativos.'))

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _get_comment_lines(self):
        """Líneas del comentario, con la estructura exigida por el requerimiento."""
        self.ensure_one()
        return [
            'SANGRE RESTANTE: %s' % self.remaining_blood_type_id.name,
            'SANGRE RESTANTE (+): %s' % self.remaining_positive_blood_type_id.name,
            'SANGRE RESTANTE (-): %s' % self.remaining_negative_blood_type_id.name,
        ]

    def action_update_comment(self):
        """Botón "Actualizar comentario": escribe el comentario en la factura."""
        self.ensure_one()
        lines = self._get_comment_lines()
        # `narration` es un campo Html: Markup.join escapa los textos y evita inyección HTML.
        body = Markup('<p>%s</p>') % Markup('<br/>').join(lines)
        self.move_id.narration = body
        # Trazabilidad: el cambio queda registrado también en el chatter de la factura.
        self.move_id.message_post(
            body=Markup('<b>%s</b>%s') % (_('Comentario de tipos de sangre actualizado'), body),
            subtype_xmlid='mail.mt_note',
        )
        return {'type': 'ir.actions.act_window_close'}
