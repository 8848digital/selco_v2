import frappe

def on_cancel_event(doc, method=None):
	update_issue_status(doc)

def update_issue_status(doc):
	if doc.selco_complaint_number:
		workflow_state = frappe.get_cached_value("Issue",
			doc.selco_complaint_number, "workflow_state")

		if workflow_state in ["Complaint Closed By CSD",
			"Complaint Closed By Branch", "Complaint Attended By CSE - Still Open"]:
			frappe.db.set_value("Issue", doc.selco_complaint_number,
				"workflow_state", "Complaint Assigned to CSE")

			frappe.db.set_value("Issue", doc.selco_complaint_number,
				"status", "Open")

			frappe.db.sql("""
				DELETE FROM `tabService Record Details Issue`
					where service_record_no = %s
			""", doc.name)

