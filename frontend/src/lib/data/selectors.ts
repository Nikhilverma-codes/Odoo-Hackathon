import type {
	Customer,
	Database,
	Invoice,
	Plan,
	Product,
	Subscription,
	SubscriptionStatus
} from './types';
import { isPast, monthKey, monthKeyLabel, parseDate } from '#lib/utils/date';
import { sum } from '#lib/utils/format';

const periodFactor: Record<Plan['billingPeriod'], number> = {
	daily: 30,
	weekly: 52 / 12,
	monthly: 1,
	yearly: 1 / 12
};

export function roundMoney(value: number): number {
	return Math.round(value * 100) / 100;
}

export function planById(db: Database, id: string | null): Plan | null {
	return id ? (db.plans.find((plan) => plan.id === id) ?? null) : null;
}

export function productById(db: Database, id: string | null): Product | null {
	return id ? (db.products.find((product) => product.id === id) ?? null) : null;
}

export function customerById(db: Database, id: string | null): Customer | null {
	return id ? (db.customers.find((customer) => customer.id === id) ?? null) : null;
}

export function taxRate(db: Database, taxId: string): number {
	return db.taxes.find((tax) => tax.id === taxId)?.rate ?? 0;
}

export function subscriptionTotal(subscription: Subscription): number {
	return roundMoney(sum(subscription.lines.map((line) => line.quantity * line.unitPrice)));
}

export function subscriptionMonthlyValue(db: Database, subscription: Subscription): number {
	const plan = planById(db, subscription.planId);
	const factor = plan ? periodFactor[plan.billingPeriod] : 1;
	return roundMoney(subscriptionTotal(subscription) * factor);
}

export function invoiceBalance(invoice: Invoice): number {
	return Math.max(0, roundMoney(invoice.total - invoice.amountPaid));
}

export function isOverdue(invoice: Invoice): boolean {
	return invoice.status === 'confirmed' && isPast(invoice.dueDate);
}

export function invoiceState(invoice: Invoice): Invoice['status'] | 'overdue' {
	return isOverdue(invoice) ? 'overdue' : invoice.status;
}

export interface Metrics {
	activeSubscriptions: number;
	mrr: number;
	arr: number;
	collectedThisMonth: number;
	outstanding: number;
	overdueCount: number;
	overdueAmount: number;
	customers: number;
	invoiceCount: number;
}

export function metrics(db: Database): Metrics {
	const active = db.subscriptions.filter((item) => item.status === 'active');
	const current = new Date();

	const collectedThisMonth = roundMoney(
		sum(
			db.payments
				.filter((payment) => {
					const date = parseDate(payment.date);
					return (
						date.getMonth() === current.getMonth() && date.getFullYear() === current.getFullYear()
					);
				})
				.map((payment) => payment.amount)
		)
	);

	const openInvoices = db.invoices.filter(
		(invoice) => invoice.status === 'confirmed' || invoice.status === 'draft'
	);
	const overdue = db.invoices.filter(isOverdue);

	const mrr = roundMoney(sum(active.map((item) => subscriptionMonthlyValue(db, item))));

	return {
		activeSubscriptions: active.length,
		mrr,
		arr: roundMoney(mrr * 12),
		collectedThisMonth,
		outstanding: roundMoney(sum(openInvoices.map(invoiceBalance))),
		overdueCount: overdue.length,
		overdueAmount: roundMoney(sum(overdue.map(invoiceBalance))),
		customers: db.customers.length,
		invoiceCount: db.invoices.length
	};
}

export interface TrendPoint {
	key: string;
	label: string;
	value: number;
}

export function revenueByMonth(db: Database, months = 6): TrendPoint[] {
	const now = new Date();
	const points: TrendPoint[] = [];

	for (let offset = months - 1; offset >= 0; offset--) {
		const date = new Date(now.getFullYear(), now.getMonth() - offset, 1);
		const key = monthKey(date.toISOString());
		const value = roundMoney(
			sum(
				db.payments
					.filter((payment) => monthKey(payment.date) === key)
					.map((payment) => payment.amount)
			)
		);
		points.push({ key, label: monthKeyLabel(key), value });
	}

	return points;
}

export function subscriptionStatusCounts(
	subscriptions: Subscription[]
): Record<SubscriptionStatus, number> {
	const statuses: SubscriptionStatus[] = [
		'draft',
		'quotation',
		'confirmed',
		'active',
		'paused',
		'closed'
	];
	const counts = Object.fromEntries(statuses.map((status) => [status, 0])) as Record<
		SubscriptionStatus,
		number
	>;
	for (const subscription of subscriptions) counts[subscription.status] += 1;
	return counts;
}

export interface TopCustomer {
	customer: Customer;
	revenue: number;
	activeSubscriptions: number;
}

export function topCustomers(db: Database, limit = 5): TopCustomer[] {
	const rows = db.customers.map((customer) => {
		const revenue = roundMoney(
			sum(
				db.invoices
					.filter((invoice) => invoice.customerId === customer.id)
					.map((invoice) => invoice.amountPaid)
			)
		);
		const activeSubscriptions = db.subscriptions.filter(
			(subscription) => subscription.customerId === customer.id && subscription.status === 'active'
		).length;
		return { customer, revenue, activeSubscriptions };
	});

	return rows.sort((a, b) => b.revenue - a.revenue).slice(0, limit);
}

export interface BillingSummary {
	subscription: Subscription;
	customer: Customer | null;
	plan: Plan | null;
	monthlyValue: number;
}

export function activeBilling(db: Database): BillingSummary[] {
	return db.subscriptions
		.filter((subscription) => subscription.status === 'active')
		.map((subscription) => ({
			subscription,
			customer: customerById(db, subscription.customerId),
			plan: planById(db, subscription.planId),
			monthlyValue: subscriptionMonthlyValue(db, subscription)
		}))
		.sort((a, b) => b.monthlyValue - a.monthlyValue);
}

export function upcomingRenewals(db: Database, limit = 5): Subscription[] {
	return db.subscriptions
		.filter((subscription) => subscription.status === 'active')
		.sort((a, b) => parseDate(a.endDate).getTime() - parseDate(b.endDate).getTime())
		.slice(0, limit);
}
