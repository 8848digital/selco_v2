import frappe
import json

@frappe.whitelist()
def get_payment_collection():
	data = frappe.get_list("Payment Collection Form",{'docstatus':['!=',2]})
	data_list = []
	for row in data:
		data_list.append(frappe.get_all("Payment Collection Form",{"name":row.name},['*'])[0])
	if data_list:
		return {'status': "Success","data": data_list}

@frappe.whitelist(methods=["PUT"])
def update_payment_collection():
	if frappe.request.data:
		request_data = json.loads(frappe.request.data)
		if not request_data.get("name"):
			frappe.throw("Define name to update the record")
		if not frappe.db.exists("Payment Collection Form",request_data.get("name")):
			frappe.throw("Payment Collection Form {} not exists.".format(request_data.get("name")))
		doc = frappe.get_doc("Payment Collection Form",request_data.get("name"))
		if not doc.has_permission("read") or not doc.has_permission("write"):
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		if doc.docstatus == 1:
			frappe.throw("Payment Collection Form {} is Submitted.Can not edit submitted document".format(request_data.get("name")))
		if doc.docstatus == 2:
			frappe.throw("Payment Collection Form {} is Cancelled.Can not edit cancelled document".format(request_data.get("name")))
		
		parent_field_list = ['selco_branch','selco_taluk','selco_local_area','selco_sales_invoice_number','selco_sales_invoice_date','selco_sales_invoice_value','selco_cse_name','selco_cse_date','selco_cse_signature','selco_customer_id','selco_customer_date','submitted','selco_customer_name','selco_customer_detail_address','selco_customer_contact_number','selco_customer_landline_number','selco_customer_signature','selco_posting_date','selco_type_of_system','selco_amount_collected','selco_location','selco_number_of_years_of_amc']

		for field in parent_field_list:
			if request_data.get(field):
				if field == "submitted":
					doc.submitted = request_data.get(field)
				else:
					doc.db_set(field, request_data.get(field))
		try:
			doc.save()
		except Exception as e:
			error_msg_doc = frappe.new_doc("API Error Log")
			error_msg_doc.reference_doctype = doc.doctype
			error_msg_doc.reference_docname = doc.name
			error_msg_doc.error_message = str(e)
			error_msg_doc.save(ignore_permissions=True)
			return {'status': "Fail", "message": str(e)}

		if doc.get('submitted'):
			try:
				doc.submit()
			except Exception as e:
				error_submit_msg_doc = frappe.new_doc("API Error Log")
				error_submit_msg_doc.reference_doctype = doc.doctype
				error_submit_msg_doc.reference_docname = doc.name
				error_submit_msg_doc.error_message = str(e)
				error_submit_msg_doc.save(ignore_permissions=True)
				return {'status': "Fail", "message": str(e)}
		frappe.db.commit()
		doc.reload()
		return {'status': "Success", "data": doc}