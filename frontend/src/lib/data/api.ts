import { db } from './store.svelte';
import { uid } from '#lib/utils/validation';

/**
 * Mock in-memory API.
 *
 * Every function is async and returns plain data, so swapping this module for
 * `fetch()` calls to the real backend is a drop-in change. Reads in the UI are
 * backed by the reactive store (`db.data`) so pages update instantly.
 */

const delay = (ms = 80) => new Promise<void>((resolve) => setTimeout(resolve, ms));

interface Entity {
	id: string;
}

function repo<T extends Entity>(read: () => T[], write: (items: T[]) => void, prefix: string) {
	return {
		async list(): Promise<T[]> {
			await delay();
			return [...read()];
		},
		async get(id: string): Promise<T | null> {
			await delay();
			return read().find((item) => item.id === id) ?? null;
		},
		async create(input: Omit<T, 'id'>): Promise<T> {
			await delay();
			const item = { ...input, id: uid(prefix) } as T;
			write([...read(), item]);
			db.save();
			return item;
		},
		async update(id: string, patch: Partial<T>): Promise<T | null> {
			await delay();
			let updated: T | null = null;
			write(
				read().map((item) => {
					if (item.id !== id) return item;
					updated = { ...item, ...patch };
					return updated;
				})
			);
			db.save();
			return updated;
		},
		async remove(id: string): Promise<void> {
			await delay();
			write(read().filter((item) => item.id !== id));
			db.save();
		}
	};
}

export const api = {
	products: repo<Product>(
		() => db.data.products,
		(items) => (db.data.products = items),
		'prd'
	),
	plans: repo<Plan>(
		() => db.data.plans,
		(items) => (db.data.plans = items),
		'plan'
	),
	taxes: repo<Tax>(
		() => db.data.taxes,
		(items) => (db.data.taxes = items),
		'tax'
	),
	discounts: repo<Discount>(
		() => db.data.discounts,
		(items) => (db.data.discounts = items),
		'disc'
	),
	quoteTemplates: repo<QuoteTemplate>(
		() => db.data.quoteTemplates,
		(items) => (db.data.quoteTemplates = items),
		'qt'
	),
	customers: repo<Customer>(
		() => db.data.customers,
		(items) => (db.data.customers = items),
		'cus'
	),
	subscriptions: repo<Subscription>(
		() => db.data.subscriptions,
		(items) => (db.data.subscriptions = items),
		'sub'
	),
	invoices: repo<Invoice>(
		() => db.data.invoices,
		(items) => (db.data.invoices = items),
		'inv'
	),
	payments: repo<Payment>(
		() => db.data.payments,
		(items) => (db.data.payments = items),
		'pay'
	),
	users: repo<User>(
		() => db.data.users,
		(items) => (db.data.users = items),
		'usr'
	)
};

import type {
	Customer,
	Discount,
	Invoice,
	Payment,
	Plan,
	Product,
	QuoteTemplate,
	Subscription,
	Tax,
	User
} from './types';
