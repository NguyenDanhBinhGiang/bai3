import odoo.exceptions
from odoo import models, fields, api


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    business_project = fields.One2many('business.project', 'sale_order_id', 'Business Project', required=True)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, store=True, default='draft', compute='_check_approved')

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'sent'),
                   ('draft', 'sale'),
                   ('draft', 'done'),
                   ('draft', 'cancel'),
                   ('sent', 'sale'),
                   ('sent', 'done'),
                   ('sent', 'cancel'),
                   ('sale', 'done')]
        return (old_state, new_state) in allowed

    def change_state(self, new_state):
        self.ensure_one()
        if self.is_allowed_transition(self.state, new_state):
            self.state = new_state
        else:
            raise odoo.exceptions.UserError(f"You can't change state from {self.state} to {new_state}")

    @api.depends('business_project.state')
    def _check_approved(self):
        for order in self:
            if order.business_project:
                order.state = 'sent'
                if order.business_project.state == 'approved':
                    order.state = 'sale'
                elif order.business_project.state == 'declined':
                    order.state = 'cancel'
            else:
                order.state = 'draft'

    def open_project_form(self):
        self.ensure_one()
        if self.business_project:
            raise odoo.exceptions.UserError("Quotation already has a project")
        view_id = self.env.ref('bai3.project_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'New project form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'business.project',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            }
        }
