import type { Role } from '#lib/data/types';

export interface NavItem {
	label: string;
	href: string;
	icon: string;
	roles: Role[];
}

export interface NavSection {
	title: string;
	items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
	{
		title: 'Overview',
		items: [{ label: 'Dashboard', href: '/dashboard', icon: 'grid', roles: ['admin'] }]
	},
	{
		title: 'Billing',
		items: [
			{ label: 'Products', href: '/products', icon: 'box', roles: ['admin'] },
			{ label: 'Plans', href: '/plans', icon: 'tag', roles: ['admin'] },
			{ label: 'Customers', href: '/customers', icon: 'building', roles: ['admin'] },
			{ label: 'Subscriptions', href: '/subscriptions', icon: 'repeat', roles: ['admin'] },
			{ label: 'Invoices', href: '/invoices', icon: 'receipt', roles: ['admin'] },
			{ label: 'Payments', href: '/payments', icon: 'credit-card', roles: ['admin'] }
		]
	},
	{
		title: 'My services',
		items: [
			{ label: 'Overview', href: '/portal', icon: 'grid', roles: ['customer'] },
			{
				label: 'My subscriptions',
				href: '/portal/subscriptions',
				icon: 'repeat',
				roles: ['customer']
			},
			{ label: 'My invoices', href: '/portal/invoices', icon: 'receipt', roles: ['customer'] }
		]
	}
];

export function sectionsFor(role: Role | null): NavSection[] {
	if (!role) return [];
	return NAV_SECTIONS.map((section) => ({
		...section,
		items: section.items.filter((item) => item.roles.includes(role))
	})).filter((section) => section.items.length > 0);
}

export function titleFor(pathname: string): string {
	const matches = NAV_SECTIONS.flatMap((section) => section.items)
		.filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))
		.sort((a, b) => b.href.length - a.href.length);

	if (matches.length > 0) {
		if (pathname === '/subscriptions/new') return 'New subscription';
		return matches[0].label;
	}
	return 'Brightloop';
}
