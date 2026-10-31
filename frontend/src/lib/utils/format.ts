export function cn(...classes: Array<string | false | null | undefined>): string {
	return classes.filter(Boolean).join(' ');
}

const currencyFormatter = new Intl.NumberFormat('en-US', {
	style: 'currency',
	currency: 'USD',
	minimumFractionDigits: 2,
	maximumFractionDigits: 2
});

const compactFormatter = new Intl.NumberFormat('en-US', {
	style: 'currency',
	currency: 'USD',
	notation: 'compact',
	maximumFractionDigits: 1
});

const numberFormatter = new Intl.NumberFormat('en-US');

export function currency(value: number): string {
	return currencyFormatter.format(Number.isFinite(value) ? value : 0);
}

export function compactCurrency(value: number): string {
	return compactFormatter.format(Number.isFinite(value) ? value : 0);
}

export function formatNumber(value: number): string {
	return numberFormatter.format(Number.isFinite(value) ? value : 0);
}

export function percent(value: number): string {
	return `${Number.isFinite(value) ? value.toFixed(1) : '0.0'}%`;
}

export function titleCase(value: string): string {
	return value.replace(/[_-]/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

export function initials(name: string): string {
	return name
		.split(' ')
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase() ?? '')
		.join('');
}

const avatarPalette = [
	'bg-brand-100 text-brand-700',
	'bg-emerald-100 text-emerald-700',
	'bg-amber-100 text-amber-700',
	'bg-sky-100 text-sky-700',
	'bg-rose-100 text-rose-700',
	'bg-violet-100 text-violet-700'
];

export function avatarColor(name: string): string {
	let hash = 0;
	for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
	return avatarPalette[hash % avatarPalette.length];
}

export function sum(values: number[]): number {
	return values.reduce((total, value) => total + value, 0);
}
