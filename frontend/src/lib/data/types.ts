export type Role = 'admin' | 'customer';

export type BillingPeriod = 'daily' | 'weekly' | 'monthly' | 'yearly';

export type SubscriptionStatus =
	'draft' | 'quotation' | 'confirmed' | 'active' | 'paused' | 'closed';

export type InvoiceStatus = 'draft' | 'confirmed' | 'paid' | 'cancelled';

export type PaymentMethod = 'bank' | 'card' | 'cash' | 'upi';

export type DiscountType = 'fixed' | 'percentage';

export type DiscountScope = 'product' | 'subscription';

export interface User {
	id: string;
	name: string;
	email: string;
	password: string;
	role: Role;
	customerId: string | null;
	active: boolean;
	createdAt: string;
}

export interface ProductVariant {
	id: string;
	name: string;
	priceDelta: number;
}

export interface Product {
	id: string;
	name: string;
	type: string;
	salesPrice: number;
	costPrice: number;
	notes: string;
	active: boolean;
	variants: ProductVariant[];
}

export interface Plan {
	id: string;
	name: string;
	productId: string;
	price: number;
	billingPeriod: BillingPeriod;
	minQuantity: number;
	availableFrom: string;
	availableTo: string;
	autoClose: boolean;
	allowEarlyClose: boolean;
	pausable: boolean;
	renewable: boolean;
	active: boolean;
}

export interface Tax {
	id: string;
	name: string;
	rate: number;
	active: boolean;
}

export interface Discount {
	id: string;
	name: string;
	type: DiscountType;
	value: number;
	minPurchase: number;
	minQuantity: number;
	startDate: string;
	endDate: string;
	usageLimit: number;
	usedCount: number;
	scope: DiscountScope;
	productIds: string[];
	active: boolean;
}

export interface QuoteTemplateLine {
	id: string;
	productId: string;
	quantity: number;
	unitPrice: number;
	taxId: string;
}

export interface QuoteTemplate {
	id: string;
	name: string;
	planId: string;
	validityDays: number;
	notes: string;
	lines: QuoteTemplateLine[];
}

export interface Customer {
	id: string;
	name: string;
	company: string;
	email: string;
	phone: string;
	address: string;
	since: string;
}

export interface SubscriptionLine {
	id: string;
	productId: string;
	variantId: string | null;
	quantity: number;
	unitPrice: number;
	taxId: string;
}

export interface Subscription {
	id: string;
	number: string;
	customerId: string;
	planId: string;
	startDate: string;
	endDate: string;
	paymentTerms: string;
	status: SubscriptionStatus;
	lines: SubscriptionLine[];
	discountId: string | null;
	notes: string;
	createdAt: string;
	renewedFrom: string | null;
}

export interface InvoiceLine {
	id: string;
	productId: string;
	description: string;
	quantity: number;
	unitPrice: number;
	taxId: string;
}

export interface Invoice {
	id: string;
	number: string;
	subscriptionId: string;
	customerId: string;
	issueDate: string;
	dueDate: string;
	status: InvoiceStatus;
	lines: InvoiceLine[];
	subtotal: number;
	discountName: string | null;
	discountTotal: number;
	taxTotal: number;
	total: number;
	amountPaid: number;
	notes: string;
	createdAt: string;
}

export interface Payment {
	id: string;
	invoiceId: string;
	amount: number;
	method: PaymentMethod;
	date: string;
	note: string;
}

export interface ResetToken {
	email: string;
	token: string;
	expiresAt: string;
}

export interface Database {
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
	resetTokens: ResetToken[];
}

export interface Column {
	label: string;
	align?: 'left' | 'right' | 'center';
	width?: string;
}
