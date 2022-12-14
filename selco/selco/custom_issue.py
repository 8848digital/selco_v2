import frappe

def on_cancel_event(doc, method=None):
	cancel_delete_service_record(doc)

def cancel_delete_service_record(doc):
	if doc.workflow_state == "Complaint Assigned To CSE":
		data = get_service_record(doc.name, {"docstatus": 0})
		delete_service_record(data)
	elif doc.workflow_state in ["Complaint Closed By CSD", "Complaint Closed By Branch"]:
		data = get_service_record(doc.name, {"docstatus": 1})
		cancel_service_record(data)

def get_service_record(selco_complaint_number, get_filters):
	filters = get_filters
	filters.update({"selco_complaint_number": selco_complaint_number})

	return frappe.get_all("Service Record", filters=filters)

def delete_service_record(data):
	for row in data:
		frappe.delete_doc("Service Record", row.name)

def cancel_service_record(data):
	for row in data:
		frappe.get_doc("Service Record", row.name).cancel()