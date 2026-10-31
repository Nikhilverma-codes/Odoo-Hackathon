import { apiRequest } from './api-client';
import { refreshWorkspace } from './api';
import type { RawInvoice, RawSubscription } from './backend';
import { db } from './store.svelte';
import type { Invoice, Payment, PaymentMethod, Subscription, SubscriptionStatus } from './types';
import { paymentTermsDays } from '#lib/utils/date';

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

function numericId(value: string | null | undefined): number | null {
	if (!value || !/^\d+$/.test(value)) return null;
	return Number(value);
}

function messageOf(error: unknown): string {
	if (error instanceof Error && error.message) return error.message;
	return 'Something went wrong. Please try again.';
}

const API_PAYMENT_METHODS: Record<PaymentMethod, string> = {
	bank: 'bank_transfer',
	card: 'card',
	cash: 'cash',
	upi: 'other'
};

function subscriptionById(id: string): Subscription {
	const subscription = db.data.subscriptions.find((item) => item.id === id);
	if (!subscription) throw new Error('Subscription not found.');
	return subscription;
}

export async function setSubscriptionStatus(
	id: string,
	status: SubscriptionStatus
): Promise<{ ok: boolean; error?: string }> {
	try {
		const current = subscriptionById(id);
		if (status === 'closed') {
			await apiRequest(`/subscriptions/${id}/close`, {
				method: 'POST',
				body: { reason: null }
			});
		} else if (status === 'active' && current.status === 'paused') {
			await apiRequest(`/subscriptions/${id}/resume`, { method: 'POST' });
		} else if (status === 'active') {
			await apiRequest(`/subscriptions/${id}/activate`, { method: 'POST' });
		} else if (status === 'paused') {
			await apiRequest(`/subscriptions/${id}/pause`, { method: 'POST' });
		} else {
			await apiRequest(`/subscriptions/${id}/status`, {
				method: 'POST',
				body: { status, note: null }
			});
		}
		await refreshWorkspace();
		return { ok: true };
	} catch (error) {
		return { ok: false, error: messageOf(error) };
	}
}

export async function renewSubscription(
	id: string
): Promise<{ ok: boolean; error?: string; subscription?: Subscription }> {
	try {
		subscriptionById(id);
		const renewal = await apiRequest<RawSubscription>(`/subscriptions/${id}/renew`, {
			method: 'POST',
			body: {}
		});
		await refreshWorkspace();
		const subscription =
			db.data.subscriptions.find((item) => item.id === String(renewal.id)) ??
			db.data.subscriptions.find((item) => item.id === id);
		return { ok: true, subscription };
	} catch (error) {
		return { ok: false, error: messageOf(error) };
	}
}

export async function generateInvoice(
	subscriptionId: string
): Promise<{ ok: true; invoice: Invoice } | { ok: false; error: string }> {
	try {
		subscriptionById(subscriptionId);
		const raw = await apiRequest<RawInvoice>(
			`/subscriptions/${subscriptionId}/invoices?auto_confirm=false`,
			{ method: 'POST' }
		);
		await refreshWorkspace();
		const invoice = db.data.invoices.find((item) => item.id === String(raw.id));
		if (!invoice) throw new Error('The invoice was saved but could not be reloaded.');
		return { ok: true, invoice };
	} catch (error) {
		return { ok: false, error: messageOf(error) };
	}
}

export interface BillingRunResult {
	asOf: string;
	dryRun: boolean;
	scanned: number;
	invoiced: number;
	skipped: number;
	closed: number;
	invoiceIds: string[];
	invoiceNumbers: string[];
	errors: string[];
}

interface RawBillingRun {
	as_of: string;
	dry_run: boolean;
	scanned: number;
	invoiced: number;
	skipped: number;
	closed: number;
	invoice_ids: number[];
	invoice_numbers: string[];
	errors: string[];
}

export async function runBilling(input: {
	asOf: string;
	autoConfirm: boolean;
	dryRun?: boolean;
}): Promise<{ ok: true; result: BillingRunResult } | { ok: false; error: string }> {
	try {
		const raw = await apiRequest<RawBillingRun>('/invoices/run-billing', {
			method: 'POST',
			body: {
				as_of: input.asOf,
				auto_confirm: input.autoConfirm,
				dry_run: input.dryRun ?? false
			}
		});
		if (!input.dryRun) {
			await refreshWorkspace();
		}
		return {
			ok: true,
			result: {
				asOf: raw.as_of,
				dryRun: raw.dry_run,
				scanned: raw.scanned,
				invoiced: raw.invoiced,
				skipped: raw.skipped,
				closed: raw.closed,
				invoiceIds: raw.invoice_ids.map(String),
				invoiceNumbers: raw.invoice_numbers,
				errors: raw.errors
			}
		};
	} catch (error) {
		return { ok: false, error: messageOf(error) };
	}
}

export async function confirmInvoice(id: string): Promise<{ ok: boolean; error?: string }> {
	try {
		await apiRequest(`/invoices/${id}/confirm`, { method: 'POST' });
		await refreshWorkspace();
		return { ok: true };
	} catch (error) {
		return { ok: false, error: messageOf(error) };
	}
}

export async function cancelInvoice(id: string): Promise<{ ok: boolean; error?: string }> {
	try {
		await apiRequest(`/invoices/${id}/cancel`, {
			method: 'POST',
			body: { reason: null }
		});
		await refreshWorkspace();
		return { ok: true };
	} catch (error) {
		return { ok: false, error: messageOf(error) };
	}
}

export async function recordPayment(input: {
	invoiceId: string;
	amount: number;
	method: PaymentMethod;
	date: string;
	note: string;
}): Promise<{ ok: boolean; error?: string; payment?: Payment }> {
	try {
		const invoice = db.data.invoices.find((item) => item.id === input.invoiceId);
		if (!invoice) return { ok: false, error: 'Invoice not found.' };
		if (invoice.status === 'cancelled') return { ok: false, error: 'This invoice was cancelled.' };
		if (!Number.isFinite(input.amount) || input.amount <= 0) {
			return { ok: false, error: 'Enter a payment amount greater than zero.' };
		}

		if (invoice.status === 'draft') {
			await apiRequest(`/invoices/${input.invoiceId}/confirm`, { method: 'POST' });
		}

		const raw = await apiRequest<{ id: number; amount: number }>(
			`/invoices/${input.invoiceId}/payments`,
			{
				method: 'POST',
				body: {
					method: API_PAYMENT_METHODS[input.method],
					amount: input.amount,
					paid_on: input.date,
					note: input.note.trim() || null
				}
			}
		);
		await refreshWorkspace();
		const payment =
			db.data.payments.find((item) => item.id === String(raw.id)) ??
			({
				id: String(raw.id),
				invoiceId: input.invoiceId,
				amount: raw.amount,
				method: input.method,
				date: input.date,
				note: input.note
			} satisfies Payment);
		return { ok: true, payment };
	} catch (error) {
		return { ok: false, error: messageOf(error) };
	}
}

export async function createSubscription(input: {
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
}): Promise<Subscription> {
	const created = await apiRequest<RawSubscription>('/subscriptions', {
		method: 'POST',
		body: {
			customer_id: Number(input.customerId),
			plan_id: Number(input.planId),
			start_date: input.startDate,
			expiry_date: input.endDate || null,
			payment_terms_days: paymentTermsDays(input.paymentTerms),
			status: input.status,
			notes: input.notes.trim() || null,
			lines: input.lines.map((line) => ({
				product_id: Number(line.productId),
				variant_id: numericId(line.variantId),
				quantity: line.quantity,
				unit_price: line.unitPrice,
				tax_id: numericId(line.taxId)
			})),
			discount_ids:
				numericId(input.discountId) === null ? [] : [numericId(input.discountId) as number]
		}
	});
	await refreshWorkspace();
	const subscription = db.data.subscriptions.find((item) => item.id === String(created.id));
	if (!subscription) throw new Error('The subscription was saved but could not be reloaded.');
	return subscription;
}
