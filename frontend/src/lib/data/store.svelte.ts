import { browser } from '$app/env';
import { createSeedDatabase } from './seed';
import type { Database } from './types';

const STORAGE_KEY = 'brightloop.demo.database.v1';

function load(): Database {
	if (browser) {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (raw) {
			try {
				return JSON.parse(raw) as Database;
			} catch {
				// fall through to a fresh seed
			}
		}
	}
	return createSeedDatabase();
}

let data = $state<Database>(load());

export const db = {
	get data(): Database {
		return data;
	},
	save() {
		if (!browser) return;
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify($state.snapshot(data)));
		} catch {
			// storage may be unavailable (private mode); the in-memory state still works
		}
	},
	reset() {
		data = createSeedDatabase();
		this.save();
	}
};
