import odoo.exceptions
from odoo import models, fields, api


class Approval(models.Model):
    _name = 'approval'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner')
    business_project_id = fields.Many2many('business.project', 'business_approval_rel',
                                           'business_project_id', 'approvals_id')
    approve_state = fields.Selection([
        ('draft', 'Waiting for review'),
        ('approved', 'Approved'),
        ('declined', 'Declined')],
        string='Status', readonly=True, index=True, default='draft')
    btn_visible = fields.Boolean(compute='_compute_btn_visible')

    @api.depends('partner_id')
    def _compute_btn_visible(self):
        for record in self:
            is_correct_user = (record.env.user.partner_id == record.partner_id)
            project_is_waiting_for_approve = record.business_project_id.state == 'sent'
            record.btn_visible = is_correct_user and project_is_waiting_for_approve

    def write(self, vals):
        if not self.user_has_groups('bai3.business_project_manager'):
            if 'approve_state' in vals:
                raise odoo.exceptions.UserError('You do not have permission!')
        super(Approval, self).write(vals)

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'approved'),
                   ('draft', 'declined')]
        return (old_state, new_state) in allowed

    def change_state(self, new_state):
        self.ensure_one()
        if not self.partner_id == self.env.user.partner_id:
            raise odoo.exceptions.UserError("You can not approve for other people!")
        if self.is_allowed_transition(self.approve_state, new_state):
            self.approve_state = new_state
        else:
            raise odoo.exceptions.UserError(f"You can't change state from {self.approve_state} to {new_state}")

    def make_approved(self):
        self.change_state('approved')

    def make_declined(self):
        self.change_state('declined')
