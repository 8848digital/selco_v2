import frappe

def on_cancel_event(doc, method=None):
	if doc.status in ["Completed", "To Bill"]:
		delete_installation_note(doc)

def delete_installation_note(doc):
	data = frappe.get_all("Installation Note Item",
		fields = ["distinct parent as parent"],
		filters={"prevdoc_docname": doc.name, "docstatus": 0, "prevdoc_doctype": "Delivery Note"})

	for row in data:
		frappe.delete_doc("Installation Note", row.parent)