/**
 * Adapter between the FastAPI JSON payloads (snake_case, integer ids) and the
 * view models the UI already renders (camelCase, string ids).
 *
 * Reads are loaded in one shot after sign-in; writes are handled by the
 * operations module in a later integration step.
 */

import { apiRequest, getAllPages } from './api-client';
import type {
	BillingPeriod,
	Customer,
	Database,
	Discount,
	DiscountScope,
	DiscountType,
	Invoice,
	InvoiceLine,
	InvoiceStatus,
	Payment,
	PaymentMethod,
	Plan,
	Product,
	ProductVariant,
	QuoteTemplate,
	QuoteTemplateLine,
	Role,
	Subscription,
	SubscriptionLine,
	SubscriptionStatus,
	Tax,
	User
} from './types';

const sid = (value: number | null | undefined): string => (value == null ? '' : String(value));

function idList(values: string[]): string[] {
	return values.filter(Boolean);
}

/* ------------------------------------------------------------------ */
/* Raw backend shapes                                                  */
/* ------------------------------------------------------------------ */

export interface RawUser {
	id: number;
	email: string;
	full_name: string;
	role: 'admin' | 'staff' | 'customer';
	is_active: boolean;
	customer_id: number | null;
	created_at: string;
}

interface RawTax {
	id: number;
	name: string;
	rate: number;
	is_active: boolean;
}

interface RawVariant {
	id: number;
	name: string;
	price_delta: number;
	is_active: boolean;
}

export interface RawProduct {
	id: number;
	name: string;
	type: string;
	sales_price: number;
	cost_price: number;
	notes: string | null;
	is_active: boolean;
	variants: RawVariant[];
}

export interface RawPlan {
	id: number;
	code: string;
	name: string;
	product: { id: number } | null;
	price: number;
	interval: BillingPeriod;
	min_quantity: number;
	available_from: string | null;
	available_to: string | null;
	auto_close_on_expiry: boolean;
	allow_early_close: boolean;
	allow_pause: boolean;
	allow_renew: boolean;
	is_active: boolean;
}

export interface RawCustomer {
	id: number;
	name: string;
	contact_name: string | null;
	email: string;
	phone: string | null;
	billing_address: string | null;
	is_active: boolean;
	created_at: string;
}

interface RawSubscriptionLine {
	id: number;
	product: { id: number } | null;
	variant: { id: number } | null;
	description: string | null;
	quantity: number;
	unit_price: number;
	tax_rate: number;
}

interface RawSubscriptionDiscountLink {
	discount: { id: number };
	removed_at: string | null;
}

export interface RawSubscription {
	id: number;
	number: string;
	status: SubscriptionStatus;
	customer: { id: number };
	plan: { id: number };
	start_date: string;
	expiry_date: string | null;
	payment_terms_days: number;
	notes: string | null;
	created_at: string;
	renewed_from_id: number | null;
	lines: RawSubscriptionLine[];
	discounts: RawSubscriptionDiscountLink[];
}

interface RawInvoiceLine {
	id: number;
	product: { id: number } | null;
	description: string;
	quantity: number;
	unit_price: number;
	tax_rate: number;
}

interface RawPayment {
	id: number;
	method: string;
	amount: number;
	paid_on: string;
	reference: string | null;
	note: string | null;
}

export interface RawInvoice {
	id: number;
	number: string;
	status: InvoiceStatus;
	customer: { id: number };
	subscription_id: number | null;
	issue_date: string;
	due_date: string;
	subtotal: number;
	discount_total: number;
	tax_total: number;
	total: number;
	amount_paid: number;
	notes: string | null;
	created_at: string;
	lines: RawInvoiceLine[];
	payments: RawPayment[];
}

interface RawDiscount {
	id: number;
	name: string;
	type: DiscountType;
	value: number;
	scope: DiscountScope;
	product: { id: number } | null;
	min_purchase_amount: number;
	min_quantity: number;
	start_date: string | null;
	end_date: string | null;
	max_uses: number | null;
	used_count: number;
	is_active: boolean;
}

interface RawTemplateLine {
	id: number;
	product: { id: number } | null;
	quantity: number;
	unit_price: number | null;
}

interface RawTemplate {
	id: number;
	name: string;
	plan: { id: number };
	validity_days: number;
	notes: string | null;
	lines: RawTemplateLine[];
}

/* ------------------------------------------------------------------ */
/* Mappers                                                             */
/* ------------------------------------------------------------------ */

export function mapUser(raw: RawUser): User {
	// The UI only knows two roles; staff get the internal workspace view while
	// the backend still enforces the finer-grained permissions.
	const role: Role = raw.role === 'customer' ? 'customer' : 'admin';
	return {
		id: sid(raw.id),
		name: raw.full_name,
		email: raw.email,
		password: '',
		role,
		systemRole: raw.role,
		customerId: raw.customer_id == null ? null : sid(raw.customer_id),
		active: raw.is_active,
		createdAt: raw.created_at
	};
}

function mapTax(raw: RawTax): Tax {
	return {
		id: sid(raw.id),
		name: raw.name,
		rate: raw.rate,
		active: raw.is_active
	};
}

export const PRODUCT_TYPE_FROM_BACKEND: Record<string, string> = {
	module: 'Software',
	addon: 'Add-on',
	service: 'Service',
	support: 'Service',
	hardware: 'Hardware'
};

export const PRODUCT_TYPE_TO_BACKEND: Record<string, string> = {
	Software: 'module',
	'Add-on': 'addon',
	Service: 'service',
	Hardware: 'hardware'
};

function mapVariant(raw: RawVariant): ProductVariant {
	return {
		id: sid(raw.id),
		name: raw.name,
		priceDelta: raw.price_delta
	};
}

function mapProduct(raw: RawProduct): Product {
	return {
		id: sid(raw.id),
		name: raw.name,
		type: PRODUCT_TYPE_FROM_BACKEND[raw.type] ?? raw.type,
		salesPrice: raw.sales_price,
		costPrice: raw.cost_price,
		notes: raw.notes ?? '',
		active: raw.is_active,
		variants: raw.variants.filter((variant) => variant.is_active).map(mapVariant)
	};
}

function mapPlan(raw: RawPlan): Plan {
	return {
		id: sid(raw.id),
		code: raw.code,
		name: raw.name,
		productId: sid(raw.product?.id),
		price: raw.price,
		billingPeriod: raw.interval,
		minQuantity: raw.min_quantity,
		availableFrom: raw.available_from ?? '',
		availableTo: raw.available_to ?? '',
		autoClose: raw.auto_close_on_expiry,
		allowEarlyClose: raw.allow_early_close,
		pausable: raw.allow_pause,
		renewable: raw.allow_renew,
		active: raw.is_active
	};
}

function mapCustomer(raw: RawCustomer): Customer {
	return {
		id: sid(raw.id),
		name: raw.contact_name ?? raw.name,
		company: raw.name,
		email: raw.email,
		phone: raw.phone ?? '',
		address: raw.billing_address ?? '',
		since: (raw.created_at ?? '').slice(0, 10)
	};
}

function mapDiscount(raw: RawDiscount): Discount {
	return {
		id: sid(raw.id),
		name: raw.name,
		type: raw.type,
		value: raw.value,
		minPurchase: raw.min_purchase_amount,
		minQuantity: raw.min_quantity,
		startDate: raw.start_date ?? '',
		endDate: raw.end_date ?? '',
		usageLimit: raw.max_uses ?? 0,
		usedCount: raw.used_count,
		scope: raw.scope,
		productIds: idList([raw.product ? sid(raw.product.id) : '']),
		active: raw.is_active
	};
}

function mapTemplateLine(raw: RawTemplateLine): QuoteTemplateLine {
	return {
		id: sid(raw.id),
		productId: sid(raw.product?.id),
		quantity: raw.quantity,
		unitPrice: raw.unit_price ?? 0,
		taxId: ''
	};
}

function mapTemplate(raw: RawTemplate): QuoteTemplate {
	return {
		id: sid(raw.id),
		name: raw.name,
		planId: sid(raw.plan?.id),
		validityDays: raw.validity_days,
		notes: raw.notes ?? '',
		lines: raw.lines.map(mapTemplateLine)
	};
}

const TERMS_BY_DAYS: Record<number, string> = {
	0: 'due_on_receipt',
	15: 'net_15',
	30: 'net_30',
	45: 'net_45',
	60: 'net_60'
};

function paymentTermsKey(days: number): string {
	return TERMS_BY_DAYS[days] ?? `net_${days}`;
}

const PAYMENT_METHODS: Record<string, PaymentMethod> = {
	card: 'card',
	bank_transfer: 'bank',
	cash: 'cash',
	paypal: 'bank',
	direct_debit: 'bank',
	other: 'upi'
};

function taxIdForRate(taxes: Tax[], rate: number | null | undefined): string {
	if (rate == null) return '';
	return taxes.find((tax) => Math.abs(tax.rate - rate) < 0.0001)?.id ?? '';
}

function mapSubscription(raw: RawSubscription, taxes: Tax[]): Subscription {
	const activeDiscount = raw.discounts.find((link) => link.removed_at === null);
	const lines: SubscriptionLine[] = raw.lines.map((line) => ({
		id: sid(line.id),
		productId: sid(line.product?.id),
		variantId: line.variant ? sid(line.variant.id) : null,
		quantity: line.quantity,
		unitPrice: line.unit_price,
		taxId: taxIdForRate(taxes, line.tax_rate)
	}));

	return {
		id: sid(raw.id),
		number: raw.number,
		customerId: sid(raw.customer?.id),
		planId: sid(raw.plan?.id),
		startDate: raw.start_date ?? '',
		endDate: raw.expiry_date ?? '',
		paymentTerms: paymentTermsKey(raw.payment_terms_days),
		status: raw.status,
		lines,
		discountId: activeDiscount ? sid(activeDiscount.discount.id) : null,
		notes: raw.notes ?? '',
		createdAt: raw.created_at,
		renewedFrom: raw.renewed_from_id == null ? null : sid(raw.renewed_from_id)
	};
}

function mapInvoiceLine(raw: RawInvoiceLine, taxes: Tax[]): InvoiceLine {
	return {
		id: sid(raw.id),
		productId: sid(raw.product?.id),
		description: raw.description,
		quantity: raw.quantity,
		unitPrice: raw.unit_price,
		taxId: taxIdForRate(taxes, raw.tax_rate)
	};
}

function mapInvoice(raw: RawInvoice, taxes: Tax[]): Invoice {
	return {
		id: sid(raw.id),
		number: raw.number,
		subscriptionId: sid(raw.subscription_id),
		customerId: sid(raw.customer?.id),
		issueDate: raw.issue_date,
		dueDate: raw.due_date,
		status: raw.status,
		lines: raw.lines.map((line) => mapInvoiceLine(line, taxes)),
		subtotal: raw.subtotal,
		discountName: raw.discount_total > 0 ? 'Discount' : null,
		discountTotal: raw.discount_total,
		taxTotal: raw.tax_total,
		total: raw.total,
		amountPaid: raw.amount_paid,
		notes: raw.notes ?? '',
		createdAt: raw.created_at
	};
}

function mapPayments(invoices: RawInvoice[]): Payment[] {
	const payments: Payment[] = [];
	for (const invoice of invoices) {
		for (const payment of invoice.payments) {
			payments.push({
				id: sid(payment.id),
				invoiceId: sid(invoice.id),
				amount: payment.amount,
				method: PAYMENT_METHODS[payment.method] ?? 'bank',
				date: payment.paid_on,
				note: payment.note ?? payment.reference ?? ''
			});
		}
	}
	return payments;
}

/* ------------------------------------------------------------------ */
/* Loader                                                              */
/* ------------------------------------------------------------------ */

async function optional<T>(request: Promise<T>, fallback: T): Promise<T> {
	try {
		return await request;
	} catch {
		return fallback;
	}
}

export interface Workspace {
	users: User[];
	products: Product[];
	plans: Plan[];
	taxes: Tax[];
	discounts: Discount[];
	quoteTemplates: QuoteTemplate[];
	customers: Customer[];
	subscriptions: Subscription[];
	invoices: Invoice[];
	payments: Payment[];
}

export async function loadWorkspace(role: Role): Promise<Partial<Database>> {
	const [rawProducts, rawPlans, rawTaxes] = await Promise.all([
		getAllPages<RawProduct>('/products'),
		getAllPages<RawPlan>('/plans'),
		getAllPages<RawTax>('/taxes')
	]);

	const taxes = rawTaxes.map(mapTax);
	const products = rawProducts.map(mapProduct);
	const plans = rawPlans.map(mapPlan);

	const [rawCustomers, rawSubscriptions, rawInvoices, rawDiscounts, rawTemplates, rawUsers] =
		await Promise.all([
			role === 'customer'
				? apiRequest<RawCustomer>('/customers/me').then((me) => [me] as RawCustomer[])
				: getAllPages<RawCustomer>('/customers'),
			getAllPages<RawSubscription>('/subscriptions'),
			getAllPages<RawInvoice>('/invoices'),
			optional(getAllPages<RawDiscount>('/discounts'), [] as RawDiscount[]),
			optional(getAllPages<RawTemplate>('/quotation-templates'), [] as RawTemplate[]),
			optional(getAllPages<RawUser>('/users'), [] as RawUser[])
		]);

	return {
		users: rawUsers.map(mapUser),
		products,
		plans,
		taxes,
		discounts: rawDiscounts.map(mapDiscount),
		quoteTemplates: rawTemplates.map(mapTemplate),
		customers: rawCustomers.map(mapCustomer),
		subscriptions: rawSubscriptions.map((raw) => mapSubscription(raw, taxes)),
		invoices: rawInvoices.map((raw) => mapInvoice(raw, taxes)),
		payments: mapPayments(rawInvoices)
	};
}
