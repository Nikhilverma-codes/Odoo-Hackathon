import type {
	Customer,
	Database,
	Discount,
	Invoice,
	InvoiceLine,
	Payment,
	Plan,
	Product,
	QuoteTemplate,
	Subscription,
	SubscriptionLine,
	Tax,
	User
} from './types';
import { addDays, paymentTermsDays, toISODate } from '#lib/utils/date';
import { sum } from '#lib/utils/format';

const now = new Date();
const nowISO = now.toISOString();

function fromNow(days: number): string {
	const date = new Date(now);
	date.setDate(date.getDate() + days);
	return toISODate(date);
}

function fromNowMonths(months: number): string {
	const date = new Date(now);
	const day = date.getDate();
	date.setDate(1);
	date.setMonth(date.getMonth() + months);
	date.setDate(Math.min(day, new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()));
	return toISODate(date);
}

function round(value: number): number {
	return Math.round(value * 100) / 100;
}

const users: User[] = [
	{
		id: 'usr_admin',
		name: 'Aarav Mehta',
		email: 'admin@brightloop.io',
		password: 'Admin@123',
		role: 'admin',
		customerId: null,
		active: true,
		createdAt: nowISO
	},
	{
		id: 'usr_cust1',
		name: 'Priya Sharma',
		email: 'priya@nimbus.co',
		password: 'Customer@123',
		role: 'customer',
		customerId: 'cus_1',
		active: true,
		createdAt: nowISO
	},
	{
		id: 'usr_cust2',
		name: 'Marcus Lee',
		email: 'marcus@apexlogistics.com',
		password: 'Customer@123',
		role: 'customer',
		customerId: 'cus_2',
		active: true,
		createdAt: nowISO
	}
];

const products: Product[] = [
	{
		id: 'prd_1',
		name: 'Brightloop CRM',
		type: 'Software',
		salesPrice: 49,
		costPrice: 12,
		notes: 'Customer relationship suite with pipelines, quotes and automation.',
		active: true,
		variants: [
			{ id: 'var_1a', name: 'Standard', priceDelta: 0 },
			{ id: 'var_1b', name: 'Professional', priceDelta: 30 },
			{ id: 'var_1c', name: 'Enterprise', priceDelta: 90 }
		]
	},
	{
		id: 'prd_2',
		name: 'Brightloop ERP',
		type: 'Software',
		salesPrice: 149,
		costPrice: 40,
		notes: 'Full ERP suite: accounting, inventory, manufacturing and projects.',
		active: true,
		variants: [
			{ id: 'var_2a', name: 'Standard', priceDelta: 0 },
			{ id: 'var_2b', name: 'Odoo', priceDelta: 560 },
			{ id: 'var_2c', name: 'Custom', priceDelta: 1200 }
		]
	},
	{
		id: 'prd_3',
		name: 'Brightloop Analytics',
		type: 'Software',
		salesPrice: 79,
		costPrice: 18,
		notes: 'Dashboards, cohort analysis and revenue reporting.',
		active: true,
		variants: [
			{ id: 'var_3a', name: 'Starter', priceDelta: 0 },
			{ id: 'var_3b', name: 'Growth', priceDelta: 25 }
		]
	},
	{
		id: 'prd_4',
		name: 'Brightloop Support Desk',
		type: 'Add-on',
		salesPrice: 29,
		costPrice: 8,
		notes: 'Shared inbox, SLAs and customer satisfaction surveys.',
		active: true,
		variants: [
			{ id: 'var_4a', name: 'Basic', priceDelta: 0 },
			{ id: 'var_4b', name: 'Priority', priceDelta: 20 }
		]
	},
	{
		id: 'prd_5',
		name: 'Brightloop Payments',
		type: 'Service',
		salesPrice: 59,
		costPrice: 15,
		notes: 'Recurring billing, dunning and reconciliation.',
		active: true,
		variants: [{ id: 'var_5a', name: 'Standard', priceDelta: 0 }]
	},
	{
		id: 'prd_6',
		name: 'Brightloop Mobile',
		type: 'Software',
		salesPrice: 39,
		costPrice: 10,
		notes: 'Mobile companion app for field teams.',
		active: false,
		variants: [
			{ id: 'var_6a', name: 'iOS / Android', priceDelta: 0 },
			{ id: 'var_6b', name: 'White label', priceDelta: 150 }
		]
	}
];

const taxes: Tax[] = [
	{ id: 'tax_1', name: 'VAT 15%', rate: 15, active: true },
	{ id: 'tax_2', name: 'GST 18%', rate: 18, active: true },
	{ id: 'tax_3', name: 'Tax exempt', rate: 0, active: true }
];

const plans: Plan[] = [
	{
		id: 'plan_1',
		name: 'Starter Monthly',
		productId: 'prd_1',
		price: 49,
		billingPeriod: 'monthly',
		minQuantity: 1,
		availableFrom: '2025-01-01',
		availableTo: '2027-12-31',
		autoClose: false,
		allowEarlyClose: true,
		pausable: true,
		renewable: true,
		active: true
	},
	{
		id: 'plan_2',
		name: 'Growth Monthly',
		productId: 'prd_1',
		price: 149,
		billingPeriod: 'monthly',
		minQuantity: 1,
		availableFrom: '2025-01-01',
		availableTo: '2027-12-31',
		autoClose: false,
		allowEarlyClose: true,
		pausable: true,
		renewable: true,
		active: true
	},
	{
		id: 'plan_3',
		name: 'Enterprise Yearly',
		productId: 'prd_2',
		price: 1490,
		billingPeriod: 'yearly',
		minQuantity: 1,
		availableFrom: '2025-01-01',
		availableTo: '2028-12-31',
		autoClose: false,
		allowEarlyClose: false,
		pausable: false,
		renewable: true,
		active: true
	},
	{
		id: 'plan_4',
		name: 'Analytics Weekly',
		productId: 'prd_3',
		price: 39,
		billingPeriod: 'weekly',
		minQuantity: 1,
		availableFrom: '2025-06-01',
		availableTo: '2027-06-30',
		autoClose: false,
		allowEarlyClose: true,
		pausable: true,
		renewable: true,
		active: true
	},
	{
		id: 'plan_5',
		name: 'Daily Ops',
		productId: 'prd_3',
		price: 5,
		billingPeriod: 'daily',
		minQuantity: 5,
		availableFrom: '2025-01-01',
		availableTo: '2026-12-31',
		autoClose: true,
		allowEarlyClose: false,
		pausable: false,
		renewable: false,
		active: true
	},
	{
		id: 'plan_6',
		name: 'Annual CRM',
		productId: 'prd_1',
		price: 490,
		billingPeriod: 'yearly',
		minQuantity: 1,
		availableFrom: '2025-01-01',
		availableTo: '2028-12-31',
		autoClose: false,
		allowEarlyClose: true,
		pausable: true,
		renewable: true,
		active: true
	}
];

const discounts: Discount[] = [
	{
		id: 'disc_1',
		name: 'Annual prepay 10%',
		type: 'percentage',
		value: 10,
		minPurchase: 0,
		minQuantity: 1,
		startDate: fromNow(-30),
		endDate: fromNow(335),
		usageLimit: 100,
		usedCount: 12,
		scope: 'subscription',
		productIds: [],
		active: true
	},
	{
		id: 'disc_2',
		name: 'Volume 25 seats',
		type: 'fixed',
		value: 500,
		minPurchase: 0,
		minQuantity: 25,
		startDate: fromNow(-90),
		endDate: fromNow(180),
		usageLimit: 50,
		usedCount: 4,
		scope: 'product',
		productIds: ['prd_1', 'prd_2'],
		active: true
	},
	{
		id: 'disc_3',
		name: 'Summer promo',
		type: 'percentage',
		value: 20,
		minPurchase: 200,
		minQuantity: 1,
		startDate: fromNow(-120),
		endDate: fromNow(-10),
		usageLimit: 200,
		usedCount: 87,
		scope: 'subscription',
		productIds: [],
		active: false
	},
	{
		id: 'disc_4',
		name: 'Loyalty credit',
		type: 'fixed',
		value: 100,
		minPurchase: 0,
		minQuantity: 1,
		startDate: fromNow(-200),
		endDate: fromNow(60),
		usageLimit: 20,
		usedCount: 20,
		scope: 'subscription',
		productIds: [],
		active: true
	}
];

const quoteTemplates: QuoteTemplate[] = [
	{
		id: 'qt_1',
		name: 'Enterprise ERP rollout',
		planId: 'plan_3',
		validityDays: 30,
		notes: 'Includes onboarding and a dedicated success manager.',
		lines: [
			{ id: 'qtl_1', productId: 'prd_2', quantity: 1, unitPrice: 2050, taxId: 'tax_1' },
			{ id: 'qtl_2', productId: 'prd_4', quantity: 5, unitPrice: 49, taxId: 'tax_1' }
		]
	},
	{
		id: 'qt_2',
		name: 'Growth CRM bundle',
		planId: 'plan_2',
		validityDays: 14,
		notes: 'Seats can be added at any time and are prorated.',
		lines: [
			{ id: 'qtl_3', productId: 'prd_1', quantity: 10, unitPrice: 149, taxId: 'tax_1' },
			{ id: 'qtl_4', productId: 'prd_5', quantity: 1, unitPrice: 59, taxId: 'tax_1' }
		]
	}
];

const customers: Customer[] = [
	{
		id: 'cus_1',
		name: 'Priya Sharma',
		company: 'Nimbus Retail',
		email: 'priya@nimbus.co',
		phone: '+1 415 555 0114',
		address: '220 Market Street, San Francisco, CA',
		since: fromNow(-420)
	},
	{
		id: 'cus_2',
		name: 'Marcus Lee',
		company: 'Apex Logistics',
		email: 'marcus@apexlogistics.com',
		phone: '+1 312 555 0187',
		address: '88 Wacker Drive, Chicago, IL',
		since: fromNow(-360)
	},
	{
		id: 'cus_3',
		name: 'Elena Rossi',
		company: 'Lumen Health',
		email: 'elena@lumenhealth.io',
		phone: '+1 617 555 0132',
		address: '14 Longwood Ave, Boston, MA',
		since: fromNow(-300)
	},
	{
		id: 'cus_4',
		name: 'James Carter',
		company: 'Harbor & Co',
		email: 'james@harborco.com',
		phone: '+1 206 555 0145',
		address: '900 Alaskan Way, Seattle, WA',
		since: fromNow(-250)
	},
	{
		id: 'cus_5',
		name: 'Aisha Khan',
		company: 'Vertex Labs',
		email: 'aisha@vertexlabs.dev',
		phone: '+1 512 555 0166',
		address: '501 Congress Ave, Austin, TX',
		since: fromNow(-180)
	},
	{
		id: 'cus_6',
		name: 'Ravi Patel',
		company: 'Sunrise Foods',
		email: 'ravi@sunrisefoods.co',
		phone: '+1 786 555 0129',
		address: '77 Biscayne Blvd, Miami, FL',
		since: fromNow(-140)
	},
	{
		id: 'cus_7',
		name: 'Sofia Alvarez',
		company: 'Kite Studio',
		email: 'sofia@kitestudio.design',
		phone: '+1 213 555 0193',
		address: '450 Sunset Blvd, Los Angeles, CA',
		since: fromNow(-90)
	},
	{
		id: 'cus_8',
		name: 'Oliver Bennett',
		company: 'Northwind Traders',
		email: 'oliver@northwindtraders.com',
		phone: '+1 646 555 0158',
		address: '1 Wall Street, New York, NY',
		since: fromNow(-60)
	}
];

let lineCounter = 0;

function subLine(
	productId: string,
	quantity: number,
	unitPrice: number,
	taxId = 'tax_1',
	variantId: string | null = null
): SubscriptionLine {
	lineCounter += 1;
	return {
		id: `subLine_${lineCounter}`,
		productId,
		variantId,
		quantity,
		unitPrice,
		taxId
	};
}

const subscriptions: Subscription[] = [
	{
		id: 'sub_1',
		number: 'SUB-2026-0001',
		customerId: 'cus_1',
		planId: 'plan_2',
		startDate: fromNowMonths(-8),
		endDate: fromNowMonths(4),
		paymentTerms: 'net_30',
		status: 'active',
		lines: [subLine('prd_1', 12, 149, 'tax_1', 'var_1b'), subLine('prd_4', 3, 39)],
		discountId: 'disc_1',
		notes: 'Quarterly business review every January.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_2',
		number: 'SUB-2026-0002',
		customerId: 'cus_2',
		planId: 'plan_3',
		startDate: fromNowMonths(-10),
		endDate: fromNowMonths(2),
		paymentTerms: 'net_45',
		status: 'active',
		lines: [subLine('prd_2', 1, 2050, 'tax_2', 'var_2b')],
		discountId: null,
		notes: 'Odoo brand variant selected.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_3',
		number: 'SUB-2026-0003',
		customerId: 'cus_3',
		planId: 'plan_1',
		startDate: fromNowMonths(-6),
		endDate: fromNowMonths(6),
		paymentTerms: 'net_30',
		status: 'active',
		lines: [subLine('prd_1', 25, 49)],
		discountId: 'disc_2',
		notes: 'Volume discount applies above 25 seats.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_4',
		number: 'SUB-2026-0004',
		customerId: 'cus_4',
		planId: 'plan_4',
		startDate: fromNowMonths(-4),
		endDate: fromNowMonths(8),
		paymentTerms: 'due_on_receipt',
		status: 'active',
		lines: [subLine('prd_3', 6, 64, 'tax_1', 'var_3b')],
		discountId: null,
		notes: 'Weekly reporting for the warehouse team.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_5',
		number: 'SUB-2026-0005',
		customerId: 'cus_5',
		planId: 'plan_6',
		startDate: fromNowMonths(-3),
		endDate: fromNowMonths(9),
		paymentTerms: 'net_60',
		status: 'active',
		lines: [subLine('prd_1', 40, 490, 'tax_1', 'var_1c')],
		discountId: 'disc_2',
		notes: 'Annual prepay, 40 seats.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_6',
		number: 'SUB-2026-0006',
		customerId: 'cus_6',
		planId: 'plan_1',
		startDate: fromNowMonths(-2),
		endDate: fromNowMonths(10),
		paymentTerms: 'net_15',
		status: 'active',
		lines: [subLine('prd_1', 5, 49)],
		discountId: null,
		notes: '',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_7',
		number: 'SUB-2026-0007',
		customerId: 'cus_7',
		planId: 'plan_2',
		startDate: fromNow(6),
		endDate: fromNowMonths(13),
		paymentTerms: 'net_30',
		status: 'confirmed',
		lines: [subLine('prd_1', 8, 149)],
		discountId: null,
		notes: '',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_8',
		number: 'SUB-2026-0008',
		customerId: 'cus_8',
		planId: 'plan_3',
		startDate: fromNow(14),
		endDate: fromNowMonths(13),
		paymentTerms: 'net_45',
		status: 'confirmed',
		lines: [subLine('prd_2', 1, 1490, 'tax_2')],
		discountId: null,
		notes: 'Pending security review.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_9',
		number: 'SUB-2026-0009',
		customerId: 'cus_1',
		planId: 'plan_4',
		startDate: fromNow(3),
		endDate: fromNowMonths(4),
		paymentTerms: 'net_15',
		status: 'confirmed',
		lines: [subLine('prd_3', 10, 39)],
		discountId: null,
		notes: '',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_10',
		number: 'SUB-2026-0010',
		customerId: 'cus_3',
		planId: 'plan_2',
		startDate: fromNow(10),
		endDate: fromNowMonths(11),
		paymentTerms: 'net_30',
		status: 'quotation',
		lines: [subLine('prd_1', 15, 149, 'tax_1', 'var_1b'), subLine('prd_5', 1, 59)],
		discountId: 'disc_1',
		notes: 'Waiting on procurement approval.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_11',
		number: 'SUB-2026-0011',
		customerId: 'cus_5',
		planId: 'plan_5',
		startDate: fromNow(-5),
		endDate: fromNow(-2),
		paymentTerms: 'due_on_receipt',
		status: 'closed',
		lines: [subLine('prd_3', 10, 5)],
		discountId: null,
		notes: 'Trial completed and closed automatically.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_12',
		number: 'SUB-2026-0012',
		customerId: 'cus_4',
		planId: 'plan_1',
		startDate: fromNowMonths(-14),
		endDate: fromNowMonths(-2),
		paymentTerms: 'net_30',
		status: 'closed',
		lines: [subLine('prd_1', 3, 49)],
		discountId: null,
		notes: 'Customer moved to Growth Monthly.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_13',
		number: 'SUB-2026-0013',
		customerId: 'cus_6',
		planId: 'plan_4',
		startDate: fromNowMonths(-5),
		endDate: fromNowMonths(3),
		paymentTerms: 'net_15',
		status: 'paused',
		lines: [subLine('prd_3', 2, 39)],
		discountId: null,
		notes: 'Paused while the team migrates data.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_14',
		number: 'SUB-2026-0014',
		customerId: 'cus_8',
		planId: 'plan_1',
		startDate: fromNow(0),
		endDate: fromNowMonths(12),
		paymentTerms: 'net_30',
		status: 'draft',
		lines: [subLine('prd_1', 2, 49)],
		discountId: null,
		notes: '',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_15',
		number: 'SUB-2026-0015',
		customerId: 'cus_2',
		planId: 'plan_5',
		startDate: fromNow(2),
		endDate: fromNow(9),
		paymentTerms: 'due_on_receipt',
		status: 'draft',
		lines: [subLine('prd_3', 20, 5)],
		discountId: null,
		notes: 'Short operational sprint.',
		createdAt: nowISO,
		renewedFrom: null
	},
	{
		id: 'sub_16',
		number: 'SUB-2026-0016',
		customerId: 'cus_7',
		planId: 'plan_6',
		startDate: fromNowMonths(-1),
		endDate: fromNowMonths(11),
		paymentTerms: 'net_30',
		status: 'active',
		lines: [subLine('prd_1', 4, 490)],
		discountId: null,
		notes: 'Yearly plan with monthly internal billing.',
		createdAt: nowISO,
		renewedFrom: null
	}
];

const invoiceLines: InvoiceLine[] = [];
const invoices: Invoice[] = [];
const payments: Payment[] = [];

function productName(productId: string, variantId: string | null): string {
	const product = products.find((item) => item.id === productId);
	if (!product) return 'Product';
	const variant = product.variants.find((item) => item.id === variantId);
	return variant ? `${product.name} — ${variant.name}` : product.name;
}

function taxRate(taxId: string): number {
	return taxes.find((tax) => tax.id === taxId)?.rate ?? 0;
}

let invoiceCounter = 0;
let paymentCounter = 0;

function createInvoice(
	subscription: Subscription,
	issueDate: string,
	status: Invoice['status'],
	options: {
		dueInDays?: number;
		paidDate?: string;
		partial?: number;
		method?: Payment['method'];
	} = {}
): Invoice {
	invoiceCounter += 1;
	const id = `inv_${invoiceCounter}`;
	const dueDate = addDays(
		issueDate,
		options.dueInDays ?? paymentTermsDays(subscription.paymentTerms)
	);

	const lines: InvoiceLine[] = subscription.lines.map((line, index) => {
		const invoiceLine: InvoiceLine = {
			id: `invLine_${invoiceCounter}_${index}`,
			productId: line.productId,
			description: productName(line.productId, line.variantId),
			quantity: line.quantity,
			unitPrice: line.unitPrice,
			taxId: line.taxId
		};
		invoiceLines.push(invoiceLine);
		return invoiceLine;
	});

	const subtotal = round(sum(lines.map((line) => line.quantity * line.unitPrice)));
	const discount = subscription.discountId
		? (discounts.find((item) => item.id === subscription.discountId) ?? null)
		: null;

	let discountTotal = 0;
	if (discount) {
		discountTotal =
			discount.type === 'percentage'
				? round((subtotal * discount.value) / 100)
				: round(Math.min(discount.value, subtotal));
	}

	const factor = subtotal > 0 ? (subtotal - discountTotal) / subtotal : 0;
	const taxTotal = round(
		sum(lines.map((line) => line.quantity * line.unitPrice * factor * (taxRate(line.taxId) / 100)))
	);
	const total = round(subtotal - discountTotal + taxTotal);
	const amountPaid = status === 'paid' ? total : round(options.partial ?? 0);

	const invoice: Invoice = {
		id,
		number: `INV-2026-${String(invoiceCounter).padStart(4, '0')}`,
		subscriptionId: subscription.id,
		customerId: subscription.customerId,
		issueDate,
		dueDate,
		status,
		lines,
		subtotal,
		discountName: discount?.name ?? null,
		discountTotal,
		taxTotal,
		total,
		amountPaid,
		notes: 'Thank you for your business.',
		createdAt: `${issueDate}T09:00:00.000Z`
	};

	invoices.push(invoice);

	if (amountPaid > 0) {
		paymentCounter += 1;
		payments.push({
			id: `pay_${paymentCounter}`,
			invoiceId: id,
			amount: amountPaid,
			method: options.method ?? 'bank',
			date: options.paidDate ?? issueDate,
			note: status === 'paid' ? 'Payment received' : 'Part payment received'
		});
	}

	return invoice;
}

const activeSubscriptions = subscriptions.filter((item) => item.status === 'active');

activeSubscriptions.forEach((subscription, index) => {
	createInvoice(subscription, fromNowMonths(-3), 'paid', {
		paidDate: fromNowMonths(-3)
	});
	createInvoice(subscription, fromNowMonths(-2), 'paid', {
		paidDate: fromNowMonths(-2)
	});
	createInvoice(subscription, fromNowMonths(-1), 'paid', {
		paidDate: fromNowMonths(-1)
	});

	if (index === 0) {
		createInvoice(subscription, fromNow(-42), 'confirmed', { dueInDays: 30 });
	} else if (index === 1) {
		createInvoice(subscription, fromNow(-28), 'confirmed', { dueInDays: 30, partial: 300 });
	} else if (index === 2) {
		createInvoice(subscription, fromNow(-2), 'draft', { dueInDays: 30 });
	} else if (index === 3) {
		createInvoice(subscription, fromNow(-12), 'paid', { dueInDays: 0 });
	} else if (index === 4) {
		createInvoice(subscription, fromNow(-48), 'confirmed', { dueInDays: 30 });
	}
});

subscriptions
	.filter((item) => item.status === 'confirmed')
	.forEach((subscription) => {
		createInvoice(subscription, fromNow(-1), 'draft', { dueInDays: 30 });
	});

subscriptions
	.filter((item) => item.status === 'closed')
	.forEach((subscription, index) => {
		createInvoice(subscription, fromNowMonths(-3 - index), 'paid', {
			dueInDays: 30,
			paidDate: fromNowMonths(-3 - index)
		});
		createInvoice(subscription, fromNowMonths(-1 - index), 'paid', {
			dueInDays: 30,
			paidDate: fromNowMonths(-1 - index)
		});
	});

subscriptions
	.filter((item) => item.status === 'paused')
	.forEach((subscription) => {
		createInvoice(subscription, fromNowMonths(-2), 'paid', {
			dueInDays: 15,
			paidDate: fromNowMonths(-2)
		});
	});

export function createSeedDatabase(): Database {
	return {
		users: structuredClone(users),
		products: structuredClone(products),
		plans: structuredClone(plans),
		taxes: structuredClone(taxes),
		discounts: structuredClone(discounts),
		quoteTemplates: structuredClone(quoteTemplates),
		customers: structuredClone(customers),
		subscriptions: structuredClone(subscriptions),
		invoices: structuredClone(invoices),
		payments: structuredClone(payments),
		resetTokens: []
	};
}
