# -*- coding: utf-8 -*-
# Copyright (c) 2015, Selco and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now,now_datetime
import operator
from erpnext.accounts.party import get_party_account, get_due_date
from datetime import datetime
from datetime import timedelta
from frappe.utils import cint

class SelcoCustomizations(Document):
    pass

@frappe.whitelist()
def service_call_info():
    #triggerS aT 12 O'clocK

    if str(frappe.utils.data.nowtime().split(":")[0]) == '13':
        info=frappe.db.sql("""SELECT B.day1,B.day2,B.day3,B.day4,B.day5,B.day6,B.day7,B.day8,B.day9,B.day10,B.day11,B.day12,B.day13,B.day14,B.day15,B.day16,B.day17,B.day18,B.day19,B.day20,B.day21,B.day22,B.day23,B.day24,B.day25,B.day26,B.day27,B.day28,B.day29,B.day30,B.day31,B.day1+B.day2+B.day3+B.day4+B.day5+B.day6+B.day7+B.day8+B.day9+B.day10+B.day11+B.day12+B.day13+B.day14+B.day15+B.day16+B.day17+B.day18+B.day19+B.day20+B.day21+B.day22+B.day23+B.day24+B.day25+B.day26+B.day27+B.day28+B.day29+B.day30+B.day31,B.service_person FROM `tabService Call` AS A INNER JOIN `tabService Call Details` AS B ON A.name=B.parent WHERE A.month=MONTHNAME(MONTH(ADDDATE(CURDATE(), -1))*100) """,as_list=1)
        #0-30 indeX oF numbeR oF callS
        #31 totaL callS
        #32 servicE persoN

        todate=int(str((datetime.now()+timedelta(days=-1)).date()).split("-")[2])
        #yesterday'S datE
        i=0
        while i<len(info) :
            if frappe.get_cached_value("Service Person",info[i][32],"send_sms") :
                cn=str(frappe.get_cached_value("Service Person",info[i][32],"contact_number"))+"@sms.textlocal.in"
                frappe.sendmail(
                    recipients=[cn],
                    subject="Number of Service Calls",
                    message="Dear "+info[i][32]+". You have made "+str(int(info[i][todate-1]))+" service calls yesterday and a total of "+str(int(info[i][31]))+" service calls till yesterday!"
                    )
            i=i+1

def month_service_person_unique(doc,method):
    for d in doc.service_call_details:
        if frappe.db.sql("""SELECT A.month,B.service_person FROM `tabService Call` AS A, `tabService Call Details` AS B WHERE A.name=B.parent AND A.month=%s AND B.service_person=%s """,(doc.month,d.service_person),as_list=1) :
            frappe.throw("Repeated Record for "+d.service_person+" in "+doc.month)

@frappe.whitelist()
def selco_issue_before_insert(doc,method):
    doc.naming_series = frappe.get_cached_value("Branch",doc.selco_branch,"selco_customer_complaint_naming_series")

@frappe.whitelist()
def selco_warranty_claim_validate(doc,method):
    service_manager_email_id, godown_email_id = frappe.get_cached_value("Branch",
        doc.selco_branch, ["selco_service_manager_email_id", "selco_godown_email_id"])

    doc.selco_senior_service_manager_email_id = service_manager_email_id
    doc.selco_godown_email_id = godown_email_id
    set_issue_workslow(doc)

def set_issue_workslow(doc):
	workflow_dict = {
		'Warranty Claim Format Raised - WC': 'Warranty Claim Format Raised - WC',
		'Warranty Claim Approved - WC': 'Dispatch Pending From Godown',
		'Warranty Claim Rejected - WC': 'Complaint Attended By CSE - Still Open',
		'Dispatched From Godown': 'Dispatched From Godown'
	}

	if doc.selco_complaint_number:
		if doc.workflow_state in workflow_dict:
			frappe.db.set_value('Issue', doc.selco_complaint_number,
				'workflow_state', workflow_dict.get(doc.workflow_state))

@frappe.whitelist()
def selco_issue_validate1(doc,method):
    if doc.workflow_state =="Complaint Open":
        if not doc.selco_customer_address:
            frappe.throw("Please Enter Customer Address")
    if doc.workflow_state =="Complaint Closed By Branch":
        if not doc.selco_service_record:
            frappe.throw(("Please Enter Service Record Details Before Closing the Complaint"))
        cur_date = now_datetime().date()
        doc.selco_complaint_closed_date = cur_date
        doc.status = "Closed"
        doc.resolution_date = now()

@frappe.whitelist()
def selco_delivery_note_validates(doc,method):
    selco_warehouse, selco_cost_center = frappe.get_cached_value("Branch",
        doc.selco_branch, ["selco_warehouse", "selco_cost_center"])

    for d in doc.get('items'):
        d.warehouse = selco_warehouse
        d.cost_center = selco_cost_center
        if not d.rate:
            d.rate = frappe.get_cached_value("Item Price",
                {"price_list": "Branch Sales", "item_code":d.item_code}, "price_list_rate")

@frappe.whitelist()
def selco_delivery_note_before_insert(doc,method):
    if doc.is_return:
        doc.naming_series = "DC-RET/"
    else:
        doc.naming_series = frappe.get_cached_value("Branch",
            doc.selco_branch, "selco_stock_entry_naming_series")

@frappe.whitelist()
def selco_material_request_before_insert(doc,method):
    doc.naming_series = frappe.get_cached_value("Branch",doc.selco_branch,"selco_material_request_naming_series")
    local_warehouse = frappe.get_cached_value("Branch",doc.selco_branch,"selco_git_warehouse")
    for d in doc.get('items'):
        if not d.warehouse:
               d.warehouse = local_warehouse

@frappe.whitelist()
def selco_material_request_validate(doc,method):
    #frappe.msgprint("selco_material_request_updates")
    doc.items.sort(key=operator.attrgetter("item_code"), reverse=False)

    selco_material_approved_and_dispatched(doc,method)

    if doc.workflow_state == "Partially Dispatched From Godown - IBM":
        flag = "N"
        for d in doc.get('items'):
            if d.selco_dispatched_quantity != 0:
                flag = "Y"
        for d in doc.get('items'):
            if flag != "Y":
                d.selco_dispatched_quantity = d.qty

    if doc.workflow_state == "Dispatched From Godown - IBM":
        for d in doc.get('items'):
            d.selco_dispatched_quantity = d.qty

    data = frappe.get_cached_value("Branch", doc.selco_branch,
        ["selco_branch_credit_limit", "selco_senior_sales_manager_email_id",
        "selco_godown_email_id", "selco_agm_email_id"], as_dict=1)

    if data:
        doc.selco_branch_credit_limit = data.selco_branch_credit_limit
        doc.selco_senior_sales_manager_email_id = data.selco_senior_sales_manager_email_id
        doc.selco_godown_email_id = data.selco_godown_email_id
        doc.selco_agms_email_id = data.selco_agm_email_id

@frappe.whitelist()
def selco_material_approved_and_dispatched(doc,method):
    #frappe.msgprint("selco_material_approved_and_dispatched")

    if doc.workflow_state == "Approved - IBM":
         doc.selco_approved_time = now()

    elif doc.workflow_state == "Dispatched From Godown - IBM":
        doc.selco_dispatched_time = now()

@frappe.whitelist()
def selco_purchase_receipt_before_insert(doc,method):
    doc.naming_series = frappe.get_cached_value("Warehouse",
        doc.selco_godown, "selco_mrn_naming_series")

@frappe.whitelist()
def selco_purchase_order_before_insert(doc,method):
    doc.naming_series = frappe.get_cached_value("Warehouse",
        doc.selco_godown, "selco_po_naming_series")

@frappe.whitelist()
def selco_purchase_order_validate(doc,method):
    godown_address_ret = get_default_address_name_and_display("Warehouse", doc.selco_godown)
    doc.selco_godown_address = godown_address_ret.address_name
    doc.selco_godown_address_details = godown_address_ret.address_display

    doc.selco_godown_email = frappe.get_cached_value("Warehouse",doc.selco_godown,"selco_godown_email")

    doc.base_rounded_total= round(doc.base_grand_total)
    advance_local = doc.base_rounded_total * (float(doc.selco_advance_percentage_1) / 100)
    advance_local = round(advance_local)
    balance_local = doc.base_rounded_total - advance_local
    doc.selco_advance_details_currency=advance_local
    doc.selco_balance_details_currency=balance_local

    for d in doc.get('items'):
        d.warehouse = doc.selco_godown

@frappe.whitelist()
def selco_purchase_receipt_validate(doc,method):
    # BRANCH2WAREHOUSE
    # local_branch = frappe.get_cached_value("Warehouse",doc.selco_godown,"selco_branch")
    # selco_cost_center = frappe.get_cached_value("Branch",local_branch,"selco_cost_center")
    godown_cost_center = frappe.get_cached_value("Warehouse", doc.selco_godown, "selco_cost_center")

    for d in doc.get('items'):
        d.cost_center = godown_cost_center #BRANCH2WAREHOUSE
        d.warehouse = doc.selco_godown
    for d in doc.get('taxes'):
        d.cost_center = godown_cost_center #BRANCH2WAREHOUSE


    doc.set('selco_purchase_receipt_item_print', [])

    flag=0
    row = doc.append('selco_purchase_receipt_item_print', {})
    row.selco_item_code = doc.items[0].item_code
    row.selco_item_name = doc.items[0].item_name
    row.selco_received_quantity = doc.items[0].received_qty
    row.selco_accepted_quantity = doc.items[0].qty
    row.selco_rejected_quantity = doc.items[0].rejected_qty
    row.selco_rate = doc.items[0].rate

    for i,rowi in enumerate(doc.get('items')):
        if (i != 0):
            for j,rowj in enumerate(doc.get('selco_purchase_receipt_item_print')):
                if (doc.items[i].item_code == doc.selco_purchase_receipt_item_print[j].selco_item_code and doc.items[i].item_name == doc.selco_purchase_receipt_item_print[j].selco_item_name):
                   flag=1
                   doc.selco_purchase_receipt_item_print[j].selco_received_quantity = doc.selco_purchase_receipt_item_print[j].selco_received_quantity+doc.items[i].received_qty
                   doc.selco_purchase_receipt_item_print[j].selco_accepted_quantity = doc.selco_purchase_receipt_item_print[j].selco_accepted_quantity+doc.items[i].qty
                   doc.selco_purchase_receipt_item_print[j].selco_rejected_quantity = doc.selco_purchase_receipt_item_print[j].selco_rejected_quantity+doc.items[i].rejected_qty

            if(flag!= 1):
               r = doc.append('selco_purchase_receipt_item_print', {})
               r.selco_item_code = doc.items[i].item_code
               r.selco_item_name = doc.items[i].item_name
               r.selco_received_quantity = doc.items[i].received_qty
               r.selco_accepted_quantity = doc.items[i].qty
               r.selco_rejected_quantity = doc.items[i].rejected_qty
               r.selco_rate = doc.items[i].rate
               #frappe.msgprint(str(flag))
            flag=0
    po_list = []
    po_list_date = []
    for item_selco in doc.items:
        if item_selco.purchase_order not in po_list:
            po_list.append(item_selco.purchase_order)
            po_list_date.append(frappe.utils.formatdate(frappe.get_cached_value('Purchase Order', item_selco.purchase_order, 'transaction_date'),"dd-MM-yyyy"))
    doc.selco_list_of_po= ','.join([str(i) for i in po_list])
    doc.selco_list_of_po_date= ','.join([str(i) for i in po_list_date])
    #End of Insert By basawaraj On 7th september for printing the list of PO when PR is done by importing items from multiple PO
    if doc.selco_type_of_purchase == "Normal":
        for d in doc.get('items'):
            if not d.purchase_order :
                frappe.throw("Purchase Order Is Mandatory")

@frappe.whitelist()
def selco_stock_entry_updates(doc,method):
    if not doc.selco_branch:
        frappe.throw(_("Select branch for stock entry {0}").format(doc.name))

    branch_data = frappe.get_cached_value("Branch", doc.selco_branch,
        ['selco_cost_center', 'selco_warehouse', 'selco_repair_warehouse', 'selco_receipt_note_naming_series',
        'selco_stock_entry_naming_series', 'selco_rejection_in_naming_series', 'selco_rejection_out_naming_series',
        'selco_bill_of_material_naming_series'], as_dict=1)

    for label in ["Cost Center", "Warehouse", "Repair Warehouse"]:
        field = 'selco_{0}'.format(frappe.scrub(label))
        if not branch_data.get(field):
            frappe.throw(_("Please set {0} in the selected Branch {1}")
                .format(label, doc.selco_branch))

    if doc.purpose in ['Receive at Warehouse', 'Send to Warehouse']:
        if doc.is_new():
            doc.naming_series = (branch_data.selco_receipt_note_naming_series
                if doc.stock_entry_type=="Receive at Warehouse" else branch_data.selco_stock_entry_naming_series)

        warehouse = (branch_data.selco_warehouse
            if doc.selco_type_of_material=="Good Stock" else branch_data.selco_repair_warehouse)

        git_warehouse = git_warehouse = frappe.get_cached_value("Branch",
            doc.selco_branch, 'selco_git_warehouse')

        if doc.selco_being_dispatched_to:
            git_warehouse = frappe.get_cached_value("Branch",
                doc.selco_being_dispatched_to, 'selco_git_warehouse')

        for d in doc.get('items'):
            d.cost_center = branch_data.selco_cost_center
            if not d.s_warehouse:
                d.s_warehouse = (git_warehouse
                    if doc.purpose=="Receive at Warehouse" else warehouse)

            if not d.t_warehouse:
                d.t_warehouse = (warehouse
                    if doc.purpose=="Receive at Warehouse" else git_warehouse)

        if doc.selco_type_of_material != "Good Stock" and git_warehouse != "Demo Warehouse - SELCO":
                d.is_sample_item = 1

    elif doc.purpose in ["Material Receipt", "Material Issue"]:
        if doc.is_new():
            doc.naming_series = (branch_data.selco_rejection_in_naming_series
                if doc.purpose == 'Material Receipt' else branch_data.selco_rejection_out_naming_series)

        warehouse_field = "t_warehouse" if doc.purpose == 'Material Receipt' else "s_warehouse"

        for d in doc.get('items'):
            d.cost_center = branch_data.selco_cost_center
            if not d.get(warehouse_field):
                d.set(warehouse_field, branch_data.selco_repair_warehouse)
            d.is_sample_item = 1

    if doc.stock_entry_type == "Send to Warehouse":
        doc.selco_recipient_email_id = frappe.get_cached_value("Branch",doc.selco_being_dispatched_to,"selco_branch_email_id")

@frappe.whitelist()
def selco_stock_entry_validate(doc,method):
    from frappe.contacts.doctype.address.address import get_address_display, get_default_address
    if doc.stock_entry_type == "Send to Warehouse":
        local_warehouse = frappe.get_cached_value("Branch",doc.selco_being_dispatched_to,"selco_warehouse")
        doc.selco_recipient_address_link = get_default_address("Warehouse", local_warehouse) #frappe.get_cached_value("Warehouse",local_warehouse,"address")
        doc.selco_recipient_address = "<b>" + doc.selco_being_dispatched_to.upper() + " BRANCH</b><br>"
        doc.selco_recipient_address+= "SELCO SOLAR LIGHT PVT. LTD.<br>"
        doc.selco_recipient_address+= str(get_address_display(doc.selco_recipient_address_link))
    elif doc.stock_entry_type=="Receive at Warehouse":
        sender = frappe.get_cached_value("Stock Entry",doc.selco_suppliers_ref,"selco_branch")
        sender_warehouse = frappe.get_cached_value("Branch",sender,"selco_warehouse")
        doc.sender_address_link = get_default_address("Warehouse", sender_warehouse) #frappe.get_cached_value("Warehouse",sender_warehouse,"address")
        doc.sender_address = "<b>" + str(sender) + " SELCO BRANCH</b><br>"
        doc.sender_address += "SELCO SOLAR LIGHT PVT. LTD.<br>"
        doc.sender_address += str(get_address_display(doc.sender_address_link))

@frappe.whitelist()
def get_items_from_outward_stock_entry(selco_doc_num,selco_branch):
    selco_var_dc = frappe.get_doc("Stock Entry",selco_doc_num)
    if selco_var_dc.selco_type_of_stock_entry != "Demo - Material Issue" and selco_var_dc.selco_being_dispatched_to != selco_branch:
        frappe.throw("Incorrect DC Number");
    from_warehouse = selco_var_dc.to_warehouse
    if selco_var_dc.selco_type_of_material=="Good Stock":
        to_warehouse = frappe.get_cached_value("Branch",selco_var_dc.selco_being_dispatched_to,"selco_warehouse")
    else:
        to_warehouse = frappe.get_cached_value("Branch",selco_var_dc.selco_being_dispatched_to,"selco_repair_warehouse")
    return { 'dc' : selco_var_dc,'from_warehouse' : from_warehouse, 'to_warehouse' :to_warehouse }

@frappe.whitelist()
def get_items_from_rejection_in(selco_rej_in,selco_branch):
    selco_var_dc = frappe.get_doc("Stock Entry",selco_rej_in)
    return { 'dc' : selco_var_dc }

@frappe.whitelist()
def selco_customer_before_insert(doc, method):
    doc.naming_series = frappe.get_cached_value("Branch",
        doc.selco_branch, "selco_customer_naming_series")

@frappe.whitelist()
def selco_customer_validate(doc,method):
    if not ( doc.selco_customer_contact_number or doc.selco_landline_mobile_2 ):
        frappe.throw("Enter either Customer Contact Number ( Mobile 1 ) or Mobile 2 / Landline")
    if doc.selco_customer_contact_number:
        if len(doc.selco_customer_contact_number) != 10:
            frappe.throw("Invalid Customer Contact Number ( Mobile 1 ) - Please enter exact 10 digits of mobile no ex : 9900038803")
        selco_validate_if_customer_contact_number_exists(doc.selco_customer_contact_number,doc.name)
    if doc.selco_landline_mobile_2:
        selco_validate_if_customer_contact_number_exists(doc.selco_landline_mobile_2,doc.name)

def selco_validate_if_customer_contact_number_exists(contact_number,customer_id):
    #frappe.msgprint(frappe.session.user)
    var4 = frappe.get_cached_value("Customer", {"selco_customer_contact_number": (contact_number)})
    var5 = unicode(var4) or u''
    var6 = frappe.get_cached_value("Customer", {"selco_customer_contact_number": (contact_number)}, "customer_name")
    if var5 != "None" and customer_id != var5:
        frappe.throw("Customer with contact no " + contact_number + " already exists \n Customer ID : " + var5 + "\n Customer Name : " + var6)

    var14 = frappe.get_cached_value("Customer", {"selco_landline_mobile_2": (contact_number)})
    var15 = unicode(var14) or u''
    var16 = frappe.get_cached_value("Customer", {"selco_landline_mobile_2": (contact_number)}, "customer_name")
    if var15 != "None" and customer_id != var15:
        frappe.throw("Customer with contact no " + contact_number + " already exists \n Customer ID : " + var15 + "\n Customer Name : " + var16)

@frappe.whitelist()
def selco_sales_invoice_before_insert(doc,method):
    customer_data = frappe.get_cached_value("Customer",
        doc.customer, ["selco_customer_contact_number", "selco_customer_tin_number"], as_dict=1)

    doc.selco_customer_contact_number = customer_data.get("selco_customer_contact_number")
    doc.selco_customer_tin_number = customer_data.get("selco_customer_tin_number")
    if doc.is_return == 1:
        doc.naming_series = frappe.get_cached_value("Branch",doc.selco_branch,"selco_credit_note_naming_series")
    else:
        if doc.selco_type_of_invoice in ["System Sales Invoice", "Spare Sales Invoice"]:
            doc.naming_series = frappe.get_cached_value("Branch",doc.selco_branch,"selco_sales_invoice_naming_series")
        elif doc.selco_type_of_invoice == "Write Off":
            doc.naming_series = frappe.get_cached_value("Branch",doc.selco_branch,"selco_write_off_naming_series")
        elif doc.selco_type_of_invoice == "Service Bill":
            doc.naming_series = frappe.get_cached_value("Branch",doc.selco_branch,"selco_service_bill_naming_series")
        elif doc.selco_type_of_invoice == "Bill of Sale":
            doc.naming_series = frappe.get_cached_value("Branch",doc.selco_branch,"selco_bill_of_sales_naming_series")

@frappe.whitelist()
def selco_sales_invoice_validate(doc,method):
    #selco_warehouse  = frappe.get_cached_value("Branch",doc.branch,"selco_warehouse")
    selco_cost_center = frappe.get_cached_value("Branch", doc.selco_branch, "selco_cost_center")

    for d in doc.get('items'):
        d.cost_center = selco_cost_center
        d.income_account = doc.selco_sales_account

    for d in doc.get('taxes'):
        d.cost_center = selco_cost_center

    for i,c in enumerate(doc.get('taxes')):
        if doc.taxes[i].account_head == "Discount Karnataka 14.5% - SELCO":
           if doc.taxes[i].tax_amount>0:
              doc.taxes[i].tax_amount = doc.taxes[i].tax_amount * -1

def selco_payment_entry_before_insert(doc,method):
    if doc.payment_type == "Receive":
        data = frappe.get_cached_value("Branch", doc.selco_branch,
            ["selco_receipt_naming_series", "selco_collection_account"], as_dict=1)

        doc.naming_series = data.selco_receipt_naming_series
        doc.paid_to = data.selco_collection_account

        if (doc.mode_of_payment == "Bank"
            and doc.selco_amount_credited_to_platinum_account):
            doc.paid_to = frappe.get_cached_value("Branch","Head Office","selco_collection_account")

    elif doc.payment_type == "Pay":
        if doc.mode_of_payment == "Bank":
            data = frappe.get_cached_value("Branch", doc.selco_branch,
                ["selco_bank_payment_naming_series", "selco_expenditure_account"], as_dict=1)

            doc.naming_series = data.selco_bank_payment_naming_series
            doc.paid_from = data.selco_expenditure_account

def selco_payment_entry_validate(doc,method):
    if doc.payment_type == "Receive":
        if doc.selco_money_received_by == "Cash":
            doc.mode_of_payment = "Cash"
            doc.paid_to = frappe.get_cached_value("Branch",doc.selco_branch,"selco_collection_account")
        else:
            doc.mode_of_payment = "Bank"
            doc.paid_to = frappe.get_cached_value("Branch",doc.selco_branch,"selco_collection_account")

    local_sum = 0
    local_sum = doc.paid_amount

    for deduction in doc.deductions:
        local_sum = local_sum + deduction.amount

    doc.received_amount_with_deduction = local_sum

def selco_payment_entry_before_delete(doc,method):
    if "System Manager" not in frappe.get_roles():
        frappe.throw("You cannot delete Payment Entries")

def selco_journal_entry_before_insert(doc, method):
    naming_series_dict = {
        'Contra Entry': 'selco_contra_naming_series', 'Cash Entry': 'selco_cash_payment_naming_series',
        'Debit Note': 'selco_debit_note__naming_series', 'Credit Note': 'selco_credit_note_naming_series',
        'Journal Entry': 'selco_journal_entry_naming_series', 'Write Off Entry': 'selco_write_off_naming_series',
        'Bank Entry': 'selco_bank_payment_naming_series', 'Receipt': 'selco_receipt_naming_series',
        'Commission Journal': 'selco_commission_journal_naming_series'
    }

    naming_series_field = naming_series_dict.get(doc.voucher_type)
    if not naming_series_field: return

    data = frappe.get_cached_value("Branch",
        doc.selco_branch, ["selco_cost_center", naming_series_field], as_dict=1)

    doc.naming_series = data.get(naming_series_field)
    for account in doc.accounts:
        account.cost_center = data.selco_cost_center

@frappe.whitelist()
def selco_journal_entry_validate(doc,method):
    local_cost_center = frappe.get_cached_value("Branch",doc.selco_branch,"selco_cost_center")
    if doc.selco_use_different_cost_center == 1:
        local_cost_center = doc.selco_alternative_cost_center
    for account in doc.accounts:
        account.cost_center = local_cost_center

@frappe.whitelist()
def selco_purchase_invoice_before_insert(doc,method):
    if doc.is_return == 1:
        doc.naming_series = "DN/HO/18-19/"

    doc.naming_series = frappe.get_cached_value("Warehouse", doc.selco_godown, "selco_purchase_invoice_naming_series")


@frappe.whitelist()
def selco_purchase_invoice_validate(doc, method):
    from erpnext.accounts.party import get_due_date

    doc.due_date = get_due_date(doc.selco_supplier_invoice_date,"Supplier",doc.supplier)

@frappe.whitelist()
def selco_lead_before_insert(doc,method):
    doc.naming_series = frappe.get_cached_value("Branch",doc.selco_branch,"selco_lead_naming_series")
    if doc.selco_project_enquiry == 1:
        doc.naming_series = "ENQ/18-19/"

@frappe.whitelist()
def selco_lead_validate(doc,method):
    if not ( doc.selco_customer_contact_number__mobile_1 or doc.selco_customer_contact_number__mobile_2_landline ):
        frappe.throw("Enter either Customer Contact Number ( Mobile 1 ) or Mobile 2 / Landline")
    if doc.selco_customer_contact_number__mobile_1 :
        if len(doc.selco_customer_contact_number__mobile_1 ) != 10:
            frappe.throw("Invalid Customer Contact Number ( Mobile 1 ) - Please enter exact 10 digits of mobile no ex : 9900038803")
        selco_validate_if_lead_contact_number_exists(doc.selco_customer_contact_number__mobile_1 ,doc.name)
    if doc.selco_customer_contact_number__mobile_2_landline:
        selco_validate_if_lead_contact_number_exists(doc.selco_customer_contact_number__mobile_2_landline,doc.name)

def selco_validate_if_lead_contact_number_exists(contact_number,lead_id):
    var4 = frappe.get_cached_value("Lead", {"selco_customer_contact_number__mobile_2_landline": (contact_number)})
    var5 = unicode(var4) or u''
    var6 = frappe.get_cached_value("Lead", {"selco_customer_contact_number__mobile_2_landline": (contact_number)}, "lead_name")
    if var5 != "None" and lead_id != var5:
        frappe.throw("Lead with contact no " + contact_number + " already exists \n Lead ID : " + var5 + "\n Lead Name : " + var6)

    var14 = frappe.get_cached_value("Lead", {"selco_customer_contact_number__mobile_1": (contact_number)})
    var15 = unicode(var14) or u''
    var16 = frappe.get_cached_value("Lead", {"selco_customer_contact_number__mobile_1": (contact_number)}, "lead_name")
    if var15 != "None" and lead_id != var15:
        frappe.throw("Lead with contact no " + contact_number + " already exists \n Lead ID : " + var15 + "\n Lead Name : " + var16)

@frappe.whitelist()
def send_birthday_wishes():
    list_of_bday = frappe.db.sql('SELECT salutation,employee_name,designation,branch FROM `tabEmployee` where DAY(date_of_birth) = DAY(CURDATE()) AND MONTH(date_of_birth) = MONTH(CURDATE()) AND status="Active" ',as_list=True)
    bday_wish = ""
    if list_of_bday:
        for employee in list_of_bday:
            bday_wish += "<b> Dear " + employee[0] + "." + employee[1].upper() + " (" + employee[2] + "," + employee[3] +  ") " + "</b>" + "<br>"
        bday_wish += "<br>" + "सुदिनम् सुदिना जन्मदिनम् तव | भवतु मंगलं जन्मदिनम् || चिरंजीव कुरु कीर्तिवर्धनम् | चिरंजीव कुरुपुण्यावर्धनम् || विजयी भवतु सर्वत्र सर्वदा | जगति भवतु तव सुयशगानम् || <br><br>"
        bday_wish +="​ಸೂರ್ಯನಿಂದ ನಿಮ್ಮೆಡೆಗೆ ಬರುವ ಪ್ರತಿಯೊಂದು ರಶ್ಮಿಯೂ ನಿಮ್ಮ ಬಾಳಿನ ಸಂತಸದ ಕ್ಷಣವಾಗಲಿ ಎಂದು ಹಾರೈಸುತ್ತಾ ಜನುಮ ದಿನದ  ಹಾರ್ದಿಕ ​ಶುಭಾಶಯಗಳು​.​<br><br>"
        bday_wish +="Wishing you a wonderful day on your birthday. Let this be sacred and auspicious day for you. Wish you long live with a good fame and wish you long live with your good deeds. Wish you always make ever great achievements and let the world praise you for your success. Happy Birthday to our most beloved​. ​ ​SELCO Family wishes you Happy birthday.........!!!!!​​​ <br><br>"
        bday_wish +="Best Regards<br>"
        bday_wish +="SELCO Family​​<br>"
        local_recipient = []
        local_recipient.append("venugopal@selco-india.com")
        local_recipient.append("hr@selco-india.com")
        frappe.sendmail(
            recipients = local_recipient,
            subject="ಹುಟ್ಟುಹಬ್ಬದ ಶುಭಾಶಯಗಳು...............!!! - ERP",
            message=bday_wish)

@frappe.whitelist()
def send_po_reminder():
    list_of_po = frappe.db.sql('SELECT name FROM `tabPurchase Order` where workflow_state = "AGM Approval Pending - PO" ',as_list=True)
    po_reminder = "Please note below mentioned POs are in <b>AGM Approval Pending Status</b>, Please approve the same.<br/>"
    if list_of_po:
        for name in list_of_po:
            po_reminder += name[0]
            po_reminder += '<br/>'
        local_recipient = []
        local_recipient.append("jpai@selco-india.com")
        frappe.sendmail(
            recipients = local_recipient,
            subject="Purchase Order Approval Pending",
            message=po_reminder)

def stock_entry_reference_qty_update(doc, method):
    for item in doc.items:
        if doc.stock_entry_type=="Receive at Warehouse" and doc.selco_suppliers_ref:
            item.reference_rej_in_or_rej_ot = doc.selco_suppliers_ref

        if item.reference_rej_in_or_rej_ot:
            data = frappe.get_all('Stock Entry Detail',
                fields = ["ifnull(sum(qty), 0) as qty"],
                filters = {'docstatus': 1, 'reference_rej_in_or_rej_ot': item.reference_rej_in_or_rej_ot,
                    'item_code': item.item_code}, as_dict=1)

            if data:
                name, ste_qty = frappe.get_cached_value('Stock Entry Detail',
                    {'parent': item.reference_rej_in_or_rej_ot,
                    'item_code': item.item_code}, ['name', 'qty'], as_dict=1)

                if data[0].qty > ste_qty:
                    frappe.throw(_("Please enter correct quantity in the stock entry {0}")
                        .format(doc.name))

                frappe.db.set_value('Stock Entry Detail', name,
                    'reference_rej_in_or_rej_quantity', data[0].qty)

@frappe.whitelist()
def get_stock_entry(doctype, txt, searchfield, start, page_len, filters):
    cond = "1=1"
    if filters.get('selco_supplier_or_customer'):
        cond = """se.selco_supplier_or_customer_id = %(selco_supplier_or_customer_id)s
            and se.selco_type_of_stock_entry = %(selco_type_of_stock_entry)s"""
    elif filters.get('selco_type_of_stock_entry') == 'GRN':
        cond = """se.selco_type_of_stock_entry = 'Outward DC'
            and se.selco_inward_or_outward = 'Outward'
            and se.selco_being_dispatched_to = %(selco_branch)s """

    return frappe.db.sql(""" SELECT distinct sed.parent
        FROM
            `tabStock Entry Detail` sed,
            `tabStock Entry` se
        WHERE
            se.name = sed.parent and se.docstatus = 1 and
            ifnull(reference_rej_in_or_rej_quantity, 0) < qty and
            sed.parent like %(txt)s and se.name != %(name)s and {cond}
        LIMIT %(start)s, %(page_len)s """.format(cond = cond), {
            'txt': '%' + txt + '%',
            "name": filters.get("name"),
			"start": start, "page_len": page_len,
            "selco_supplier_or_customer_id": filters.get('selco_supplier_or_customer_id'),
            "selco_type_of_stock_entry": filters.get("selco_type_of_stock_entry"),
            "selco_branch": filters.get("selco_branch")
        })

@frappe.whitelist()
def selco_create_customer(selco_branch,customer_group,customer_name,selco_customer_contact_number,selco_landline_mobile_2,selco_gender,selco_electrification_status):
    local_cust = frappe.new_doc("Customer")
    local_cust.selco_branch = selco_branch
    local_cust.customer_group = customer_group
    local_cust.customer_name = customer_name
    local_cust.selco_customer_contact_number = selco_customer_contact_number
    local_cust.selco_landline_mobile_2 = selco_landline_mobile_2
    local_cust.selco_gender = selco_gender
    local_cust.selco_electrification_status = selco_electrification_status
    local_cust.insert()
    return local_cust.name,local_cust.customer_name

@frappe.whitelist()
def selco_add_new_address(selco_branch,address_type,address_line1,address_line2,city,selco_district,country,customer,address_title):
    from frappe.contacts.doctype.address.address import get_address_display
    local_address = frappe.new_doc("Address")
    local_address.selco_branch = selco_branch
    local_address.address_type = address_type
    local_address.address_line1 = address_line1
    local_address_line2 = address_line2
    local_address.city = city
    local_address.selco_district = selco_district
    local_address.country = country
    local_address.customer = customer

    local_address.address_title= address_title
    local_address.insert()
    return local_address.name,str(get_address_display(local_address.name))

@frappe.whitelist()
def get_default_address_name_and_display(doctype, docname):
    from frappe.contacts.doctype.address.address import get_address_display, get_default_address

    out = frappe._dict({"address_name": None, "address_display": None})
    default_address = get_default_address(doctype, docname)

    if default_address:
        out.address_name = default_address
        out.address_display = get_address_display(default_address)

    return out
