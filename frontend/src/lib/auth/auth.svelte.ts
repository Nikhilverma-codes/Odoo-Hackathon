import { browser } from '$app/env';
import { apiRequest, clearToken, getToken, setToken } from '#lib/data/api-client';
import { loadWorkspace, mapUser, type RawUser } from '#lib/data/backend';
import { db } from '#lib/data/store.svelte';
import type { Role, User } from '#lib/data/types';

const USER_KEY = 'brightloop.api.user.v1';

interface AuthResponse {
	token: { access_token: string; token_type: string; expires_in: number };
	user: RawUser;
}

function loadUser(): User | null {
	if (!browser) return null;
	if (!getToken()) return null;
	const raw = localStorage.getItem(USER_KEY);
	if (!raw) return null;
	try {
		return JSON.parse(raw) as User;
	} catch {
		return null;
	}
}

function persistUser(user: User | null): void {
	if (!browser) return;
	if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
	else localStorage.removeItem(USER_KEY);
}

function messageOf(error: unknown): string {
	if (error instanceof Error && error.message) return error.message;
	return 'Something went wrong. Please try again.';
}

type Result = { ok: boolean; error?: string };

let user = $state<User | null>(loadUser());
let ready = $state(false);
let initializing: Promise<void> | null = null;

async function hydrate(next: User): Promise<void> {
	const workspace = await loadWorkspace(next.role);
	db.setData(workspace);
}

export const auth = {
	get user(): User | null {
		return user;
	},

	get role(): Role | null {
		return user?.role ?? null;
	},

	get isAuthenticated(): boolean {
		return user !== null && getToken() !== null;
	},

	/** True once the session check + workspace load has settled. */
	get ready(): boolean {
		return ready;
	},

	/**
	 * Restore a session on page load: validate the stored JWT against
	 * `/auth/me` and reload the workspace from the backend.
	 */
	async initialize(): Promise<void> {
		if (ready && user && getToken()) return;
		if (initializing) return initializing;

		initializing = (async () => {
			try {
				if (!getToken()) {
					user = null;
					persistUser(null);
					return;
				}
				const me = await apiRequest<RawUser>('/auth/me');
				const next = mapUser(me);
				await hydrate(next);
				user = next;
				persistUser(next);
			} catch {
				user = null;
				clearToken();
				persistUser(null);
				db.reset();
			} finally {
				ready = true;
				initializing = null;
			}
		})();

		return initializing;
	},

	async login(email: string, password: string): Promise<Result & { user?: User }> {
		try {
			const result = await apiRequest<AuthResponse>('/auth/login', {
				method: 'POST',
				body: { email: email.trim().toLowerCase(), password }
			});
			setToken(result.token.access_token);
			const next = mapUser(result.user);
			try {
				await hydrate(next);
			} catch (error) {
				clearToken();
				throw error;
			}
			user = next;
			persistUser(next);
			ready = true;
			return { ok: true, user: next };
		} catch (error) {
			return { ok: false, error: messageOf(error) };
		}
	},

	async register(input: {
		name: string;
		email: string;
		password: string;
		company?: string;
	}): Promise<Result & { user?: User }> {
		try {
			const result = await apiRequest<AuthResponse>('/auth/register', {
				method: 'POST',
				body: {
					email: input.email.trim().toLowerCase(),
					full_name: input.name.trim(),
					company_name: input.company?.trim() || undefined,
					password: input.password
				}
			});
			setToken(result.token.access_token);
			const next = mapUser(result.user);
			await hydrate(next);
			user = next;
			persistUser(next);
			ready = true;
			return { ok: true, user: next };
		} catch (error) {
			return { ok: false, error: messageOf(error) };
		}
	},

	logout() {
		user = null;
		clearToken();
		persistUser(null);
		db.reset();
	},

	async requestReset(email: string): Promise<Result & { token?: string }> {
		try {
			const result = await apiRequest<{ message: string; reset_token?: string | null }>(
				'/auth/forgot-password',
				{ method: 'POST', body: { email: email.trim().toLowerCase() } }
			);
			return { ok: true, token: result.reset_token ?? undefined };
		} catch (error) {
			return { ok: false, error: messageOf(error) };
		}
	},

	async resetPassword(token: string, password: string): Promise<Result> {
		try {
			await apiRequest('/auth/reset-password', {
				method: 'POST',
				body: { token: token.trim(), password }
			});
			return { ok: true };
		} catch (error) {
			return { ok: false, error: messageOf(error) };
		}
	},

	async changePassword(current: string, next: string): Promise<Result> {
		try {
			await apiRequest('/auth/me/password', {
				method: 'POST',
				body: { current_password: current, new_password: next }
			});
			return { ok: true };
		} catch (error) {
			return { ok: false, error: messageOf(error) };
		}
	}
};
