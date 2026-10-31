import { db } from './store.svelte';
import type {
	Invoice,
	InvoiceLine,
	Payment,
	PaymentMethod,
	Subscription,
	SubscriptionStatus
} from './types';
import { addDays, addPeriod, paymentTermsDays, todayISO } from '#lib/utils/date';
import { sum } from '#lib/utils/format';
import { roundMoney, taxRate } from './selectors';
import { uid } from '#lib/utils/validation';

export const SUBSCRIPTION_FLOW: SubscriptionStatus[] = [
	'draft',
	'quotation',
	'confirmed',
	'active',
	'paused',
	'closed'
];

export const LIFECYCLE: SubscriptionStatus[] = [
	'draft',
	'quotation',
	'confirmed',
	'active',
	'closed'
];

function nextInvoiceNumber(): string {
	const year = new Date().getFullYear();
	const used = db.data.invoices
		.map((invoice) => Number(invoice.number.split('-')[2]))
		.filter((value) => Number.isFinite(value));
	const next = (used.length ? Math.max(...used) : 0) + 1;
	return `INV-${year}-${String(next).padStart(4, '0')}`;
}

export function setSubscriptionStatus(
	id: string,
	status: SubscriptionStatus
): { ok: boolean; error?: string } {
	const subscription = db.data.subscriptions.find((item) => item.id === id);
	if (!subscription) return { ok: false, error: 'Subscription not found.' };

	const plan = db.data.plans.find((item) => item.id === subscription.planId);

	if (status === 'closed' && plan && plan.autoClose) {
		subscription.status = 'closed';
	} else if (status === 'closed' && plan && !plan.allowEarlyClose) {
		return { ok: false, error: 'This plan cannot be closed early.' };
	} else if (status === 'paused' && plan && !plan.pausable) {
		return { ok: false, error: 'This plan cannot be paused.' };
	} else {
		subscription.status = status;
	}

	if (status === 'active' && (!subscription.startDate || subscription.startDate < todayISO())) {
		subscription.startDate = todayISO();
	}

	db.save();
	return { ok: true };
}

export function renewSubscription(id: string): { ok: boolean; error?: string } {
	const subscription = db.data.subscriptions.find((item) => item.id === id);
	if (!subscription) return { ok: false, error: 'Subscription not found.' };
	const plan = db.data.plans.find((item) => item.id === subscription.planId);
	if (!plan) return { ok: false, error: 'Plan not found.' };
	if (!plan.renewable) return { ok: false, error: 'This plan cannot be renewed.' };

	subscription.endDate = addPeriod(subscription.endDate, plan.billingPeriod);
	subscription.status = 'active';
	db.save();
	return { ok: true };
}

interface BuildInvoiceOptions {
	issueDate?: string;
	dueDate?: string;
}

export function generateInvoice(subscriptionId: string, options: BuildInvoiceOptions = {}) {
	const subscription = db.data.subscriptions.find((item) => item.id === subscriptionId);
	if (!subscription) return { ok: false as const, error: 'Subscription not found.' };
	if (subscription.status !== 'active' && subscription.status !== 'confirmed') {
		return { ok: false as const, error: 'Only active or confirmed subscriptions can be billed.' };
	}

	const issueDate = options.issueDate ?? todayISO();
	const dueDate =
		options.dueDate ?? addDays(issueDate, paymentTermsDays(subscription.paymentTerms) || 0);

	const lines: InvoiceLine[] = subscription.lines.map((line) => {
		const product = db.data.products.find((item) => item.id === line.productId);
		const variant = product?.variants.find((item) => item.id === line.variantId);
		return {
			id: uid('invLine'),
			productId: line.productId,
			description: product
				? variant
					? `${product.name} — ${variant.name}`
					: product.name
				: 'Product',
			quantity: line.quantity,
			unitPrice: line.unitPrice,
			taxId: line.taxId
		};
	});

	const subtotal = roundMoney(sum(lines.map((line) => line.quantity * line.unitPrice)));
	const discount = subscription.discountId
		? (db.data.discounts.find((item) => item.id === subscription.discountId) ?? null)
		: null;

	let discountTotal = 0;
	if (discount) {
		const withinDates =
			discount.startDate <= issueDate && (!discount.endDate || issueDate <= discount.endDate);
		const withinLimit = discount.usedCount < discount.usageLimit;
		if (withinDates && withinLimit) {
			discountTotal =
				discount.type === 'percentage'
					? roundMoney((subtotal * discount.value) / 100)
					: roundMoney(Math.min(discount.value, subtotal));
			discount.usedCount += 1;
		}
	}

	const factor = subtotal > 0 ? (subtotal - discountTotal) / subtotal : 0;
	const taxTotal = roundMoney(
		sum(
			lines.map(
				(line) => line.quantity * line.unitPrice * factor * (taxRate(db.data, line.taxId) / 100)
			)
		)
	);
	const total = roundMoney(subtotal - discountTotal + taxTotal);

	const invoice: Invoice = {
		id: uid('inv'),
		number: nextInvoiceNumber(),
		subscriptionId: subscription.id,
		customerId: subscription.customerId,
		issueDate,
		dueDate,
		status: 'draft',
		lines,
		subtotal,
		discountName: discountTotal > 0 ? (discount?.name ?? null) : null,
		discountTotal,
		taxTotal,
		total,
		amountPaid: 0,
		notes: 'Thank you for your business.',
		createdAt: new Date().toISOString()
	};

	db.data.invoices = [invoice, ...db.data.invoices];
	db.save();
	return { ok: true as const, invoice };
}

export function confirmInvoice(id: string) {
	const invoice = db.data.invoices.find((item) => item.id === id);
	if (!invoice) return { ok: false, error: 'Invoice not found.' };
	if (invoice.status !== 'draft')
		return { ok: false, error: 'Only draft invoices can be confirmed.' };
	invoice.status = 'confirmed';
	db.save();
	return { ok: true };
}

export function cancelInvoice(id: string) {
	const invoice = db.data.invoices.find((item) => item.id === id);
	if (!invoice) return { ok: false, error: 'Invoice not found.' };
	if (invoice.status === 'paid') return { ok: false, error: 'Paid invoices cannot be cancelled.' };
	invoice.status = 'cancelled';
	db.save();
	return { ok: true };
}

export function recordPayment(input: {
	invoiceId: string;
	amount: number;
	method: PaymentMethod;
	date: string;
	note: string;
}): { ok: boolean; error?: string; payment?: Payment } {
	const invoice = db.data.invoices.find((item) => item.id === input.invoiceId);
	if (!invoice) return { ok: false, error: 'Invoice not found.' };
	if (invoice.status === 'cancelled') return { ok: false, error: 'This invoice was cancelled.' };
	if (!Number.isFinite(input.amount) || input.amount <= 0) {
		return { ok: false, error: 'Enter a payment amount greater than zero.' };
	}

	const payment: Payment = {
		id: uid('pay'),
		invoiceId: invoice.id,
		amount: roundMoney(input.amount),
		method: input.method,
		date: input.date,
		note: input.note
	};

	invoice.amountPaid = roundMoney(invoice.amountPaid + payment.amount);
	if (invoice.amountPaid >= invoice.total) {
		invoice.amountPaid = invoice.total;
		invoice.status = 'paid';
	} else if (invoice.status === 'draft') {
		invoice.status = 'confirmed';
	}

	db.data.payments = [payment, ...db.data.payments];
	db.save();
	return { ok: true, payment };
}

export function createSubscription(input: {
	customerId: string;
	planId: string;
	startDate: string;
	endDate: string;
	paymentTerms: string;
	status: SubscriptionStatus;
	discountId: string | null;
	notes: string;
	lines: {
		productId: string;
		variantId: string | null;
		quantity: number;
		unitPrice: number;
		taxId: string;
	}[];
}) {
	const lastNumber = db.data.subscriptions
		.map((item) => Number(item.number.split('-')[2]))
		.filter((value) => Number.isFinite(value));
	const next = (lastNumber.length ? Math.max(...lastNumber) : 0) + 1;

	const subscription: Subscription = {
		id: uid('sub'),
		number: `SUB-${new Date().getFullYear()}-${String(next).padStart(4, '0')}`,
		customerId: input.customerId,
		planId: input.planId,
		startDate: input.startDate,
		endDate: input.endDate,
		paymentTerms: input.paymentTerms,
		status: input.status,
		lines: input.lines.map((line) => ({ ...line, id: uid('subLine') })),
		discountId: input.discountId,
		notes: input.notes,
		createdAt: new Date().toISOString(),
		renewedFrom: null
	};

	db.data.subscriptions = [subscription, ...db.data.subscriptions];
	db.save();
	return subscription;
}
