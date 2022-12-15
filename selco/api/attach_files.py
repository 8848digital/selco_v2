import frappe
from frappe.utils.file_manager import save_file
import json

@frappe.whitelist()
def attach_file_to_document():
	if frappe.request.data:
		request_data = json.loads(frappe.request.data)
	if not request_data.get('doctype'):
		return {'status': 'Fail','message': 'Doctype is mandatory'}
	if not request_data.get('docname'):
		return {'status': 'Fail','message': 'Docname is mandatory'}
	if request_data.get('files'):
		for filedata in request_data.get('files'):
			for filename, filecontent in filedata.items():
				if not filename or not filecontent:
					frappe.throw("Define filename and filecontent properly.") 
				save_file(fname=filename, content=filecontent,dt=request_data.get('doctype'), dn=request_data.get('docname'), decode=True, is_private=1)
		return {'status': 'Success','message':"File attached successfully."}
							

