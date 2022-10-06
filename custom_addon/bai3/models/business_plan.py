import odoo.exceptions
from odoo import models, fields, api


class BusinessPlan(models.Model):
    _name = 'business.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    state = fields.Selection([
        ('draft', 'New'),
        ('sent', 'Waiting for confirmation'),
        ('approved', 'Approved'),
        ('declined', 'Declined')],
        string='Status', readonly=True, index=True, default='draft', compute='_compute_state', store=True)
    sale_order_id = fields.Many2one('sale.order', required=True, readonly=True, ondelete='restrict')
    name = fields.Char(compute='_compute_name', store=True)
    detail = fields.Text('Business info', required=True)
    approvals_id = fields.Many2many('approval', 'business_approval_rel', 'approvals_id', 'business_plan_id',
                                    ondelete='cascade')

    # rec_name = fields.Text(compute='_compute_rec_name', invisible=True)
    """Computed fields for form attribute"""
    readonly_state = fields.Boolean(compute='_compute_readonly', invisible=True, default=False)
    sent_btn_visible = fields.Boolean(compute='_compute_sent_btn_visible', invisible=True, default=True)

    def _compute_sent_btn_visible(self):
        for record in self:
            record.sent_btn_visible = self.env.user == record.create_uid

    @api.constrains('approvals_id')
    def constrain_approval(self):
        for record in self:
            if len(record.approvals_id) < 1:
                raise odoo.exceptions.UserError("Approve list empty")

    @api.depends('name', 'sale_order_id.name')
    def _compute_name(self):
        for record in self:
            record.name = f"Sale order/{record.sale_order_id.name}"

    @api.depends('state')
    def _compute_readonly(self):
        for record in self:
            record.readonly_state = record.state not in ['draft',
                                                         'declined']  # or self.env.user.id == record.create_uid

    @api.depends('approvals_id.approve_state')
    def _compute_state(self):
        for record in self:
            if record.approvals_id:
                approve_result = [x.approve_state == 'approved' for x in record.approvals_id]
                decline_result = [x.approve_state == 'declined' for x in record.approvals_id]
                if any(decline_result):
                    try:
                        record.change_state('declined')
                        self.sudo().message_post(body=f'Business plan \"{record.name}\" has been declined',
                                                 partner_ids=[record.create_uid.partner_id.id],
                                                 message_type='notification')
                    except odoo.exceptions.UserError as e:
                        raise e
                        pass
                elif all(approve_result):
                    try:
                        record.change_state('approved')
                        self.sudo().message_post(body=f'Business plan \"{record.name}\" has been approved',
                                                 partner_ids=[record.create_uid.partner_id.id],
                                                 message_type='notification')
                    except odoo.exceptions.UserError as e:
                        raise e
                        pass

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'sent'),
                   ('draft', 'approved'),
                   ('draft', 'declined'),
                   ('sent', 'approved'),
                   ('sent', 'declined'),
                   ('declined', 'sent')]
        return (old_state, new_state) in allowed

    def change_state(self, new_state):
        self.ensure_one()
        if self.is_allowed_transition(self.state, new_state):
            self.state = new_state
        else:
            raise odoo.exceptions.UserError(f"You can't change state from {self.state} to {new_state}")

    def make_sent(self):
        self.ensure_one()
        for a in self.approvals_id:
            a.sudo().make_draft()
        message_list = self.approvals_id.mapped('user_id.partner_id.id')
        self.sudo().message_post(body='Business plan need approval',
                                 partner_ids=message_list,
                                 message_type='notification')
        self.change_state('sent')
        pass

    def write(self, vals):
        if self.readonly_state:
            raise odoo.exceptions.UserError('You can not edit project detail after sending it')

        super(BusinessPlan, self).write(vals)

