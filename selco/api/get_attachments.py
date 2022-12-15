import frappe
from frappe.desk.form.load import get_attachments

@frappe.whitelist()
def get_doc_attachments(doctype, docname):
	if not doctype:
		return {'status': 'Fail','message': "Define Doctype to get attachments."}
	if not docname:
		return {'status': 'Fail','message': "Define Docname to get attachments."}

	if not frappe.db.exists(doctype,docname):
		return {'status': 'Fail','message': f"{doctype} {docname} not exists."}
	attachments = get_attachments(doctype,docname)
	return {'status': 'Success','data': attachments} 