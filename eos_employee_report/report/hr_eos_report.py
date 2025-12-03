from odoo import models
from odoo.exceptions import UserError


class EmployeeEosReport(models.AbstractModel):
    _name = 'report.eos_employee_report.employee_eos_report'
    _description = 'Employee End Of Service Report'

    def _get_report_values(self, docids, data=None):
        data = data or {}

        # Ensure we have employee IDs to work with, even if the report is triggered from a wizard
        # where `docids` might be empty.
        employee_ids = docids or []
        if not employee_ids:
            employee_ids = [data.get('employee_id')] if data.get('employee_id') else []

        if not employee_ids:
            active_ids = self.env.context.get('active_ids') or []
            if self.env.context.get('active_model') == 'hr.employee':
                employee_ids = active_ids

        if not employee_ids:
            raise UserError('No employees found to render the End of Service report.')

        employees = self.env['hr.employee'].browse(employee_ids)
        leave_type_id = data.get('leave_type_id')
        docs = [employee._prepare_eos_report_data(leave_type_id=leave_type_id) for employee in employees]

        return {
            'docs': docs,
            'doc_ids': employees.ids,
            'doc_model': 'hr.employee',
        }
