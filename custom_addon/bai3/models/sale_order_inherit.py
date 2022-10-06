import odoo.exceptions
from odoo import models, fields, api


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    business_plan = fields.One2many('business.plan', 'sale_order_id', 'Business plan',
                                    required=True, ondelete='restrict')
    # Store the business plan id for displaying only
    display_business_plan_tag = fields.Many2one('business.plan', 'Business plan',
                                                compute='_compute_business_plan_tag')

    @api.depends('business_plan')
    def _compute_business_plan_tag(self):
        for record in self:
            record.display_business_plan_tag = record.business_plan

    # noinspection PyUnresolvedReferences
    def action_confirm(self):
        for record in self:
            if len(record.business_plan) < 1:
                raise odoo.exceptions.UserError(f"Order {record.name} does not have any plan!")
            if record.business_plan.state != 'approved':
                raise odoo.exceptions.UserError("Order's plan has not been approved!")

        super(SaleOrderInherit, self).action_confirm()

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
