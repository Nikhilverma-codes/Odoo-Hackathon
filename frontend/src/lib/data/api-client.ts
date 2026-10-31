/**
 * Thin fetch wrapper for the Brightloop FastAPI backend.
 *
 * In development Vite proxies `/api` to http://127.0.0.1:8000, so the default
 * prefix is same-origin. Set `VITE_API_BASE_URL` (e.g. http://127.0.0.1:8000/api/v1)
 * when the API lives elsewhere.
 */

const API_PREFIX = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/+$/, '');

const TOKEN_KEY = 'brightloop.api.token.v1';

export class ApiError extends Error {
	readonly status: number;
	readonly detail: unknown;

	constructor(status: number, message: string, detail?: unknown) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.detail = detail;
	}
}

export function getToken(): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
	if (typeof localStorage === 'undefined') return;
	localStorage.removeItem(TOKEN_KEY);
}

interface RequestOptions {
	method?: string;
	body?: unknown;
	signal?: AbortSignal;
}

function errorMessage(status: number, statusText: string, detail: unknown): string {
	if (typeof detail === 'string' && detail.trim()) return detail;
	if (Array.isArray(detail)) {
		const messages = detail
			.map((item) => {
				if (item && typeof item === 'object' && 'msg' in item) {
					const entry = item as { msg?: unknown; loc?: unknown[] };
					const field = Array.isArray(entry.loc) ? entry.loc.slice(1).join('.') : '';
					return field ? `${field}: ${String(entry.msg)}` : String(entry.msg);
				}
				return String(item);
			})
			.filter(Boolean);
		if (messages.length) return messages.join(', ');
	}
	if (status === 401) return 'Your session has expired. Please sign in again.';
	if (status === 403) return 'You do not have access to this resource.';
	if (status === 404) return 'The requested resource was not found.';
	return statusText || `Request failed (${status})`;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
	const headers: Record<string, string> = { Accept: 'application/json' };
	if (options.body !== undefined) headers['Content-Type'] = 'application/json';

	const token = getToken();
	if (token) headers.Authorization = `Bearer ${token}`;

	const response = await fetch(`${API_PREFIX}${path}`, {
		method: options.method ?? 'GET',
		headers,
		body: options.body === undefined ? undefined : JSON.stringify(options.body),
		signal: options.signal
	});

	if (!response.ok) {
		let detail: unknown = null;
		try {
			const payload = await response.json();
			detail = payload?.detail ?? payload;
		} catch {
			// non-JSON error body
		}
		throw new ApiError(
			response.status,
			errorMessage(response.status, response.statusText, detail),
			detail
		);
	}

	if (response.status === 204) return undefined as T;
	return (await response.json()) as T;
}

export interface Page<T> {
	items: T[];
	total: number;
	page: number;
	page_size: number;
	pages: number;
}

export interface QueryValue {
	[key: string]: string | number | boolean | null | undefined;
}

export function toQuery(params: QueryValue): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === null || value === undefined || value === '') continue;
		search.set(key, String(value));
	}
	const query = search.toString();
	return query ? `?${query}` : '';
}

/** Walk every page of a paginated endpoint. */
export async function getAllPages<T>(path: string, params: QueryValue = {}): Promise<T[]> {
	const items: T[] = [];
	let page = 1;
	let pages = 1;

	do {
		const query = toQuery({ ...params, page, page_size: 200 });
		const result = await apiRequest<Page<T>>(`${path}${query}`);
		items.push(...result.items);
		pages = result.pages;
		page += 1;
	} while (page <= pages);

	return items;
}
