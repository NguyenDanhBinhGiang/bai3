import odoo.exceptions
from odoo import models, fields, api


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    business_plan = fields.One2many('business.plan', 'sale_order_id', 'Business plan',
                                    required=True, ondelete='restrict')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, store=True, default='draft', compute='_check_approved')

    # Store the business plan id for display only
    display_business_plan_tag = fields.Many2one('business.plan', 'Business plan',
                                                compute='_compute_business_plan_tag')

    @api.depends('business_plan')
    def _compute_business_plan_tag(self):
        for record in self:
            record.display_business_plan_tag = record.business_plan

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

    @api.depends('business_plan.state')
    def _check_approved(self):
        for order in self:
            if order.business_plan:
                order.state = 'sent'
                if order.business_plan.state == 'approved':
                    order.state = 'sale'
                elif order.business_plan.state == 'declined':
                    order.state = 'cancel'
            else:
                order.state = 'draft'

    # noinspection PyUnresolvedReferences
    def open_plan_form(self):
        self.ensure_one()
        if self.business_plan:
            raise odoo.exceptions.UserError("Quotation already has a plan")
        view_id = self.env.ref('bai3.plan_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'New plan form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'business.plan',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            }
        }
