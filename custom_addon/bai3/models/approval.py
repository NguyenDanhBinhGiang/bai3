import odoo.exceptions
from odoo import models, fields, api


class Approval(models.Model):
    _name = 'approval'
    _rec_name = 'user_id'
    # _inherit = ['mail.thread']
    _sql_constraints = [
        ('check_user_id', 'CHECK(user_id is not null)', 'user_id must not be null')
    ]

    user_id = fields.Many2one('res.users', required=True)
    business_plan_id = fields.Many2many('business.plan', 'business_approval_rel',
                                        'business_plan_id', 'approvals_id', ondelete='cascade')
    approve_state = fields.Selection([
        ('draft', 'Waiting for review'),
        ('approved', 'Approved'),
        ('declined', 'Declined')],
        string='Status', readonly=True, index=True, default='draft')
    btn_visible = fields.Boolean(compute='_compute_btn_visible', invisible=True)

    @api.depends('user_id')
    def _compute_btn_visible(self):
        for record in self:
            is_correct_user = (record.env.user.id == record.user_id.id)
            plan_is_waiting_for_approve = record.business_plan_id.state == 'sent'
            approval_gave = record.approve_state != 'draft'
            record.btn_visible = is_correct_user and plan_is_waiting_for_approve and not approval_gave

    def write(self, vals):
        if not self.user_has_groups('bai3.business_plan_manager'):
            if 'approve_state' in vals:
                raise odoo.exceptions.UserError('You do not have permission!')
        super(Approval, self).write(vals)

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'draft'),
                   ('draft', 'approved'),
                   ('draft', 'declined'),
                   ('approved', 'draft'),
                   ('declined', 'draft')]
        return (old_state, new_state) in allowed

    def change_state(self, new_state):
        self.ensure_one()
        if self.is_allowed_transition(self.approve_state, new_state):
            self.approve_state = new_state
        else:
            raise odoo.exceptions.UserError(f"You can't change state from {self.approve_state} to {new_state}")

    def make_draft(self):
        self.change_state('draft')

    def make_approved(self):
        if not self.user_id == self.env.user:
            raise odoo.exceptions.UserError("You can not approve for other people!")
        self.change_state('approved')
        self.business_plan_id.sudo().message_post(body=f'{self.env.user.name} approved the plan',
                                                  partner_ids=[self.business_plan_id.create_uid.partner_id.id],
                                                  message_type='notification')
        pass

    def make_declined(self):
        if not self.user_id == self.env.user:
            raise odoo.exceptions.UserError("You can not decline for other people!")
        self.change_state('declined')
        self.business_plan_id.sudo().message_post(body=f'{self.env.user.name} declined the plan',
                                                  partner_ids=[self.business_plan_id.create_uid.partner_id.id],
                                                  message_type='notification')
        pass
