from odoo import fields, models
from odoo.exceptions import UserError


class EmployeeEOSLeaveWizard(models.TransientModel):
    _name = 'eos.employee.leave.wizard'
    _description = 'Select Leave Type for EOS'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.context.get('default_employee_id') or self.env.context.get('active_id'),
    )
    leave_type_id = fields.Many2one(
        'hr.leave.type',
        string='Leave Type',
        domain=[('time_type', '=', 'leave')],
        required=False,
    )

    def action_print(self):
        self.ensure_one()
        if not self.employee_id:
            raise UserError('Please select an employee to print the report.')

        action = self.env.ref('eos_employee_report.action_report_employee_eos', raise_if_not_found=False)
        if not action:
            raise UserError('The End of Service report action is missing. Please update the module.')

        data = {
            'employee_id': self.employee_id.id,
            'leave_type_id': self.leave_type_id.id if self.leave_type_id else False,
        }

        # Explicitly propagate the active employee context so the report receives docids
        # even when triggered from the wizard dialog.
        ctx = dict(self.env.context or {})
        ctx.update(
            active_id=self.employee_id.id,
            active_ids=[self.employee_id.id],
            active_model='hr.employee',
        )

        return action.with_context(ctx).report_action(self.employee_id, data=data)
