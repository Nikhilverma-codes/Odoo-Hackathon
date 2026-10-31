import { browser } from '$app/env';
import { db } from '#lib/data/store.svelte';
import type { Role, User } from '#lib/data/types';
import { isValidEmail, passwordIssues, uid } from '#lib/utils/validation';
import { addDays, toISODate } from '#lib/utils/date';

const SESSION_KEY = 'brightloop.demo.session.v1';

function loadSession(): string | null {
	if (!browser) return null;
	return localStorage.getItem(SESSION_KEY);
}

let userId = $state<string | null>(loadSession());

function persistSession() {
	if (!browser) return;
	if (userId) localStorage.setItem(SESSION_KEY, userId);
	else localStorage.removeItem(SESSION_KEY);
}

type Result = { ok: boolean; error?: string };

export const auth = {
	get user(): User | null {
		if (!userId) return null;
		const user = db.data.users.find((item) => item.id === userId && item.active) ?? null;
		if (!user || String(user.role) === 'staff') return null;
		return user;
	},

	get role(): Role | null {
		return this.user?.role ?? null;
	},

	get isAuthenticated(): boolean {
		return this.user !== null;
	},

	login(email: string, password: string): Result & { user?: User } {
		const normalized = email.trim().toLowerCase();
		const user = db.data.users.find(
			(item) => item.email.toLowerCase() === normalized && item.active
		);

		if (!user || user.password !== password) {
			return { ok: false, error: 'Incorrect email or password.' };
		}

		const role = String(user.role);
		if (role !== 'admin' && role !== 'customer') {
			return { ok: false, error: 'Incorrect email or password.' };
		}

		userId = user.id;
		persistSession();
		return { ok: true, user };
	},

	register(input: {
		name: string;
		email: string;
		password: string;
		company?: string;
	}): Result & { user?: User } {
		const email = input.email.trim().toLowerCase();
		if (!input.name.trim()) return { ok: false, error: 'Please enter your name.' };
		if (!isValidEmail(email)) return { ok: false, error: 'Please enter a valid email address.' };
		if (db.data.users.some((item) => item.email.toLowerCase() === email)) {
			return { ok: false, error: 'An account with this email already exists.' };
		}
		const issues = passwordIssues(input.password);
		if (issues.length > 0) return { ok: false, error: issues[0] };

		const customerId = uid('cus');
		const company = input.company?.trim() || input.name.trim();
		const customer = {
			id: customerId,
			name: input.name.trim(),
			company,
			email,
			phone: '',
			address: '',
			since: toISODate(new Date())
		};

		const user: User = {
			id: uid('usr'),
			name: input.name.trim(),
			email,
			password: input.password,
			role: 'customer',
			customerId,
			active: true,
			createdAt: new Date().toISOString()
		};

		db.data.customers = [...db.data.customers, customer];
		db.data.users = [...db.data.users, user];
		db.save();
		userId = user.id;
		persistSession();
		return { ok: true, user };
	},

	logout() {
		userId = null;
		persistSession();
	},

	requestReset(email: string): Result & { token?: string } {
		const normalized = email.trim().toLowerCase();
		const user = db.data.users.find((item) => item.email.toLowerCase() === normalized);
		if (!user) return { ok: false, error: 'No account found for this email.' };

		const token = uid('reset').toUpperCase();
		db.data.resetTokens = [
			...db.data.resetTokens.filter((item) => item.email !== normalized),
			{
				email: normalized,
				token,
				expiresAt: addDays(new Date(), 1) + 'T23:59:59.000Z'
			}
		];
		db.save();
		return { ok: true, token };
	},

	resetPassword(token: string, password: string): Result {
		const entry = db.data.resetTokens.find((item) => item.token === token.trim().toUpperCase());
		if (!entry) return { ok: false, error: 'This reset link is invalid or has expired.' };
		if (new Date(entry.expiresAt).getTime() < Date.now()) {
			return { ok: false, error: 'This reset link has expired. Request a new one.' };
		}
		const issues = passwordIssues(password);
		if (issues.length > 0) return { ok: false, error: issues[0] };

		const user = db.data.users.find((item) => item.email === entry.email);
		if (!user) return { ok: false, error: 'Account not found.' };

		user.password = password;
		db.data.resetTokens = db.data.resetTokens.filter((item) => item.token !== entry.token);
		db.save();
		return { ok: true };
	},

	changePassword(current: string, next: string): Result {
		const user = this.user;
		if (!user) return { ok: false, error: 'You are not signed in.' };
		if (user.password !== current) return { ok: false, error: 'Current password is incorrect.' };
		const issues = passwordIssues(next);
		if (issues.length > 0) return { ok: false, error: issues[0] };
		user.password = next;
		db.save();
		return { ok: true };
	}
};
