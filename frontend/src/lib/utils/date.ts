const DAY = 24 * 60 * 60 * 1000;

export function parseDate(value: string): Date {
	if (!value) return new Date();
	return value.length === 10 ? new Date(`${value}T00:00:00`) : new Date(value);
}

export function toISODate(date: Date): string {
	const copy = new Date(date.getTime() - date.getTimezoneOffset() * 60 * 1000);
	return copy.toISOString().slice(0, 10);
}

export function todayISO(): string {
	return toISODate(new Date());
}

export function addDays(value: string | Date, days: number): string {
	const date = typeof value === 'string' ? parseDate(value) : new Date(value);
	date.setDate(date.getDate() + days);
	return toISODate(date);
}

export function addMonths(value: string | Date, months: number): string {
	const date = typeof value === 'string' ? parseDate(value) : new Date(value);
	const day = date.getDate();
	date.setDate(1);
	date.setMonth(date.getMonth() + months);
	date.setDate(Math.min(day, new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()));
	return toISODate(date);
}

export function addPeriod(value: string | Date, period: 'daily' | 'weekly' | 'monthly' | 'yearly') {
	switch (period) {
		case 'daily':
			return addDays(value, 1);
		case 'weekly':
			return addDays(value, 7);
		case 'monthly':
			return addMonths(value, 1);
		case 'yearly':
			return addMonths(value, 12);
	}
}

export function formatDate(value: string): string {
	if (!value) return '—';
	return parseDate(value).toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
		year: 'numeric'
	});
}

export function formatDateShort(value: string): string {
	if (!value) return '—';
	return parseDate(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function formatMonth(value: string): string {
	return parseDate(value).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

export function daysUntil(value: string): number {
	const target = parseDate(value).getTime();
	const now = new Date();
	const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
	return Math.round((target - start) / DAY);
}

export function daysBetween(from: string, to: string): number {
	return Math.round((parseDate(to).getTime() - parseDate(from).getTime()) / DAY);
}

export function isPast(value: string): boolean {
	return daysUntil(value) < 0;
}

export function isSameMonth(value: string, reference: Date): boolean {
	const date = parseDate(value);
	return date.getMonth() === reference.getMonth() && date.getFullYear() === reference.getFullYear();
}

export function monthKey(value: string): string {
	const date = parseDate(value);
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

export function monthKeyLabel(key: string): string {
	const [year, month] = key.split('-').map(Number);
	return new Date(year, month - 1, 1).toLocaleDateString('en-US', {
		month: 'short',
		year: 'numeric'
	});
}

export function relativeDays(value: string): string {
	const days = daysUntil(value);
	if (days === 0) return 'Today';
	if (days === 1) return 'Tomorrow';
	if (days === -1) return 'Yesterday';
	if (days > 0) return `In ${days} days`;
	return `${Math.abs(days)} days ago`;
}

export function paymentTermsLabel(value: string): string {
	const labels: Record<string, string> = {
		due_on_receipt: 'Due on receipt',
		net_15: 'Net 15',
		net_30: 'Net 30',
		net_45: 'Net 45',
		net_60: 'Net 60'
	};
	return labels[value] ?? value;
}

export function paymentTermsDays(value: string): number {
	const days: Record<string, number> = {
		due_on_receipt: 0,
		net_15: 15,
		net_30: 30,
		net_45: 45,
		net_60: 60
	};
	return days[value] ?? 0;
}
