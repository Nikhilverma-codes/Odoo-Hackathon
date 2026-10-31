import type { Database } from './types';

function emptyDatabase(): Database {
	return {
		users: [],
		products: [],
		plans: [],
		taxes: [],
		discounts: [],
		quoteTemplates: [],
		customers: [],
		subscriptions: [],
		invoices: [],
		payments: [],
		resetTokens: []
	};
}

let data = $state<Database>(emptyDatabase());

export const db = {
	get data(): Database {
		return data;
	},

	/** Merge a freshly loaded workspace into the reactive store. */
	setData(patch: Partial<Database>) {
		data = { ...data, ...patch };
	},

	replace(next: Database) {
		data = next;
	},

	/** Kept for the legacy in-memory operations; backend writes happen later. */
	save() {},

	reset() {
		data = emptyDatabase();
	}
};
