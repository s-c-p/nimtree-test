import pandas
from decimal import Decimal
from bs4 import BeautifulSoup

col_attr = {
	"Date": "txn_date",
	"Transaction Type": "txn_type",
	"Vch No.": "vch_no",
	"Ref No": "ref_no",
	"Ref Type": "ref_type",
	"Ref Date": "ref_date",
	"Debtor": "narration",
	"Ref Amount": "ref_amount",
	"Amount": "reported_amt",
	"Particulars": "narration",
	# "Vch Type": ?"",
	"Amount Verified": "amt_verified"
}

class Transaction(object):
	"""base type"""
	def __init__(self, vch_no, txn_date):
		self.vch_type = "Receipt"
		self.vch_no = vch_no
		self.txn_date = txn_date
		return

class Parent(Transaction):
	def __init__(self, vch_no, txn_date, narration):
		super().__init__(vch_no, txn_date)
		self.txn_type = "Parent"
		self.narration: str = narration
		self.reported_amt: Decimal = 0
		self.amt_verified: bool = None

	def __repr__(self):
		return f"Parent({self.vch_no}, {self.txn_date}, {self.narration}, {self.reported_amt}, {self.amt_verified})"

class Child(Transaction):
	def __init__(self, vch_no, txn_date, narration, ref_no, ref_type, ref_amount):
		super().__init__(vch_no, txn_date)
		self.txn_type = "Child"
		self.narration: str = narration
		self.ref_no: str = ref_no
		self.ref_type: str = ref_type
		self.ref_date: str = str() #spec unclear, no e.g. with ref date non-blank
		self.ref_amount: Decimal = ref_amount
	
	def __repr__(self):
		return f"Child({self.vch_no}, {self.txn_date}, {self.narration}, {self.ref_no}, {self.ref_type}, {self.ref_amount})"

class OtherOffspring(Transaction):
	def __init__(self, vch_no, txn_date, narration, reported_amt):
		super().__init__(vch_no, txn_date)
		self.txn_type = "Other"
		# perhaps, this can be put in abc/meta for parent & this class TODO: later
		self.narration: str = narration
		self.reported_amt: Decimal = reported_amt

	def __repr__(self):
		return f"OtherOffspring({self.vch_no}, {self.txn_date}, {self.narration}, {self.reported_amt})"


def build_children(node, narration, vch_no, txn_date):
	children = list()
	child_txns = list()
	for child in node.findAll('billallocations.list'):
		ref_no = child.find('name').text
		ref_type = child.find('billtype').text
		ref_amount = Decimal(child.find('amount').text)
		child_txns.append(ref_amount)
		children.append(
			Child(vch_no, txn_date, narration, ref_no, ref_type, ref_amount)
		)
	return children, child_txns

def build_other(node, narration, vch_no, txn_date):
	return OtherOffspring(
		vch_no, txn_date, narration,
		reported_amt=Decimal(node.find('amount').text)
	)

with open("1-input.xml", mode="rt") as fo:
	xmlstring = fo.read()

ans = list()
soup = BeautifulSoup(xmlstring, "lxml")
for record in soup.findAll('voucher', attrs={'vchtype': 'Receipt'}):
	buffer = list()
	vch_no = record.find('vouchernumber').text
	txn_date = record.find('date').text
	main_narration = record.find('partyledgername').text
	buffer.append(Parent(vch_no, txn_date, main_narration))
	ales = record.findAll('allledgerentries.list')
	for es in ales:
		local_narration = es.find('ledgername').text
		x = es.findAll('billallocations.list')
		try:
			assert len(x) == 1, f"ledger entry #i has more than one bill allocations"
		except AssertionError:
			breakpoint()
		bill_alloc = x[0].text.strip()
		y = es.findAll('bankallocations.list')
		assert len(y) == 1, f"ledger entry #i has more than one bank allocations"
		bank_alloc = y[0].text.strip()
		if bill_alloc and not bank_alloc:
			buffer[0].reported_amt = Decimal(es.find('amount').text)
			x, y = build_children(es, local_narration, vch_no, txn_date)
			buffer.extend(x)
			buffer[0].amt_verified = "Yes" if buffer[0].reported_amt == sum(y) else "No"
		elif bank_alloc and not bill_alloc:
			buffer.append(build_other(es, local_narration, vch_no, txn_date))
		else:
			logging.warn("Strange shape of data")
	ans.extend(buffer)

breakpoint()

df = pandas.DataFrame(columns=col_attr.keys())
for record in ans:
	df.append(
		{
			colname: getattr(record, attrname, "NA")
			for colname, attrname in col_attr.items()
		},
		ignore_index=True
	)

