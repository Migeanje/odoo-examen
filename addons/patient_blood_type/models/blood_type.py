from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BloodType(models.Model):
    """Catálogo de tipos de sangre de los pacientes (O+, O-, A+, ...)."""

    _name = 'patient.blood.type'
    _description = 'Tipo de Sangre'
    _order = 'sequence, id'

    name = fields.Char(string='Tipo', required=True)
    active = fields.Boolean(string='Activo', default=True)
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Define el orden en que se muestran los tipos de sangre.',
    )
    rh_factor = fields.Selection(
        selection=[('positive', 'Positivo'), ('negative', 'Negativo')],
        string='Factor RH',
        compute='_compute_rh_factor',
        store=True,
        help='Se calcula a partir del signo final del tipo (+ / -). '
             'Permite filtrar positivos y negativos con dominios en lugar de comparar textos.',
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'El tipo de sangre ya existe.'),
    ]

    @api.depends('name')
    def _compute_rh_factor(self):
        for record in self:
            name = (record.name or '').strip()
            if name.endswith('+'):
                record.rh_factor = 'positive'
            elif name.endswith('-'):
                record.rh_factor = 'negative'
            else:
                record.rh_factor = False

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            name = (record.name or '').strip()
            if not name or name[-1] not in ('+', '-'):
                raise ValidationError(_(
                    "El tipo de sangre debe terminar en '+' o '-' (por ejemplo: O+, AB-)."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self._normalize_name(vals.get('name'))
        return super().create(vals_list)

    def write(self, vals):
        if 'name' in vals:
            vals['name'] = self._normalize_name(vals['name'])
        return super().write(vals)

    @api.model
    def _normalize_name(self, name):
        """Guarda el tipo sin espacios y en mayúsculas ('ab+ ' -> 'AB+')."""
        return (name or '').strip().upper()
