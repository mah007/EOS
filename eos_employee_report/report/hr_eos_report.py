from odoo import models


class EmployeeEosReport(models.AbstractModel):
    _name = 'report.eos_employee_report.employee_eos_report'
    _description = 'Employee End Of Service Report'

    def _get_report_values(self, docids, data=None):
        employees = self.env['hr.employee'].browse(docids)
        docs = []
        for employee in employees:
            docs.append(employee._prepare_eos_report_data())
        return {
            'docs': docs,
            'doc_ids': docids,
            'doc_model': 'hr.employee',
        }
