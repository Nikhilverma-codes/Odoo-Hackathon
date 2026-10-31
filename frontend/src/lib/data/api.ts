import { auth } from '#lib/auth/auth.svelte';
import { apiRequest } from './api-client';
import {
	loadWorkspace,
	PRODUCT_TYPE_TO_BACKEND,
	type RawCustomer,
	type RawPlan,
	type RawProduct
} from './backend';
import { db } from './store.svelte';
import type { Customer, Plan, Product, ProductVariant } from './types';

/**
 * Write-side repository for the FastAPI backend.
 *
 * Reads are served from the reactive workspace (`db.data`) so pages keep their
 * synchronous selectors; every mutation is sent to the API and the workspace is
 * refreshed afterwards so server-generated ids, totals and statuses win.
 */

function numericId(value: string | null | undefined): number | null {
	if (!value || !/^\d+$/.test(value)) return null;
	return Number(value);
}

function dateOrNull(value: string): string | null {
	return value.trim() ? value : null;
}

export async function refreshWorkspace(): Promise<void> {
	const role = auth.role;
	if (!role) return;
	db.setData(await loadWorkspace(role));
}

function planCode(name: string, plans: Plan[]): string {
	const base =
		name
			.toUpperCase()
			.replace(/[^A-Z0-9]+/g, '-')
			.replace(/^-+|-+$/g, '')
			.slice(0, 32) || 'PLAN';
	let code = base;
	let suffix = 2;
	const used = new Set(plans.map((plan) => plan.code?.toUpperCase()).filter(Boolean));
	while (used.has(code)) {
		code = `${base}-${suffix}`;
		suffix += 1;
	}
	return code;
}

function productPayload(input: Omit<Product, 'id'>) {
	return {
		name: input.name,
		type: PRODUCT_TYPE_TO_BACKEND[input.type] ?? 'service',
		sales_price: input.salesPrice,
		cost_price: input.costPrice,
		notes: input.notes.trim() || null,
		is_active: input.active
	};
}

function variantPayload(variant: ProductVariant) {
	return {
		name: variant.name,
		price_delta: variant.priceDelta,
		is_active: true
	};
}

const products = {
	async list(): Promise<Product[]> {
		return db.data.products;
	},
	async get(id: string): Promise<Product | null> {
		return db.data.products.find((product) => product.id === id) ?? null;
	},
	async create(input: Omit<Product, 'id'>): Promise<Product> {
		const created = await apiRequest<RawProduct>('/products', {
			method: 'POST',
			body: productPayload(input)
		});
		for (const variant of input.variants) {
			await apiRequest(`/products/${created.id}/variants`, {
				method: 'POST',
				body: variantPayload(variant)
			});
		}
		await refreshWorkspace();
		const product = db.data.products.find((item) => item.id === String(created.id));
		if (!product) throw new Error('The product was saved but could not be reloaded.');
		return product;
	},
	async update(id: string, patch: Partial<Product>): Promise<Product | null> {
		const current = db.data.products.find((product) => product.id === id);
		if (!current) throw new Error('Product not found.');

		const next: Omit<Product, 'id'> = { ...current, ...patch };
		await apiRequest<RawProduct>(`/products/${id}`, {
			method: 'PATCH',
			body: productPayload(next)
		});

		const variants = patch.variants ?? current.variants;
		const kept = new Set(
			variants
				.map((variant) => numericId(variant.id))
				.filter((value): value is number => value !== null)
		);

		for (const variant of current.variants) {
			const variantId = numericId(variant.id);
			if (variantId !== null && !kept.has(variantId)) {
				await apiRequest(`/products/variants/${variantId}`, { method: 'DELETE' });
			}
		}

		for (const variant of variants) {
			const variantId = numericId(variant.id);
			if (variantId !== null && current.variants.some((item) => item.id === variant.id)) {
				await apiRequest(`/products/variants/${variantId}`, {
					method: 'PATCH',
					body: variantPayload(variant)
				});
			} else {
				await apiRequest(`/products/${id}/variants`, {
					method: 'POST',
					body: variantPayload(variant)
				});
			}
		}

		await refreshWorkspace();
		return db.data.products.find((product) => product.id === id) ?? null;
	},
	async remove(id: string): Promise<void> {
		await apiRequest(`/products/${id}`, { method: 'DELETE' });
		await refreshWorkspace();
	}
};

const plans = {
	async list(): Promise<Plan[]> {
		return db.data.plans;
	},
	async get(id: string): Promise<Plan | null> {
		return db.data.plans.find((plan) => plan.id === id) ?? null;
	},
	async create(input: Omit<Plan, 'id'>): Promise<Plan> {
		const created = await apiRequest<RawPlan>('/plans', {
			method: 'POST',
			body: {
				code: planCode(input.name, db.data.plans),
				name: input.name,
				product_id: Number(input.productId),
				price: input.price,
				interval: input.billingPeriod,
				min_quantity: input.minQuantity,
				available_from: dateOrNull(input.availableFrom),
				available_to: dateOrNull(input.availableTo),
				auto_close_on_expiry: input.autoClose,
				allow_early_close: input.allowEarlyClose,
				allow_pause: input.pausable,
				allow_renew: input.renewable,
				is_active: input.active
			}
		});
		await refreshWorkspace();
		const plan = db.data.plans.find((item) => item.id === String(created.id));
		if (!plan) throw new Error('The plan was saved but could not be reloaded.');
		return plan;
	},
	async update(id: string, patch: Partial<Plan>): Promise<Plan | null> {
		const current = db.data.plans.find((plan) => plan.id === id);
		if (!current) throw new Error('Plan not found.');
		const next: Omit<Plan, 'id'> = { ...current, ...patch };

		await apiRequest<RawPlan>(`/plans/${id}`, {
			method: 'PATCH',
			body: {
				name: next.name,
				product_id: Number(next.productId),
				price: next.price,
				interval: next.billingPeriod,
				min_quantity: next.minQuantity,
				available_from: dateOrNull(next.availableFrom),
				available_to: dateOrNull(next.availableTo),
				auto_close_on_expiry: next.autoClose,
				allow_early_close: next.allowEarlyClose,
				allow_pause: next.pausable,
				allow_renew: next.renewable,
				is_active: next.active
			}
		});
		await refreshWorkspace();
		return db.data.plans.find((plan) => plan.id === id) ?? null;
	},
	async remove(id: string): Promise<void> {
		await apiRequest(`/plans/${id}`, { method: 'DELETE' });
		await refreshWorkspace();
	}
};

const customers = {
	async list(): Promise<Customer[]> {
		return db.data.customers;
	},
	async get(id: string): Promise<Customer | null> {
		return db.data.customers.find((customer) => customer.id === id) ?? null;
	},
	async create(input: Omit<Customer, 'id'>): Promise<Customer> {
		const created = await apiRequest<RawCustomer>('/customers', {
			method: 'POST',
			body: {
				name: input.company.trim() || input.name,
				contact_name: input.name.trim() || null,
				email: input.email.trim().toLowerCase(),
				phone: input.phone.trim() || null,
				billing_address: input.address.trim() || null
			}
		});
		await refreshWorkspace();
		const customer = db.data.customers.find((item) => item.id === String(created.id));
		if (!customer) throw new Error('The customer was saved but could not be reloaded.');
		return customer;
	},
	async update(id: string, patch: Partial<Customer>): Promise<Customer | null> {
		const current = db.data.customers.find((customer) => customer.id === id);
		if (!current) throw new Error('Customer not found.');
		const next: Omit<Customer, 'id'> = { ...current, ...patch };

		await apiRequest<RawCustomer>(`/customers/${id}`, {
			method: 'PATCH',
			body: {
				name: next.company.trim() || next.name,
				contact_name: next.name.trim() || null,
				email: next.email.trim().toLowerCase(),
				phone: next.phone.trim() || null,
				billing_address: next.address.trim() || null
			}
		});
		await refreshWorkspace();
		return db.data.customers.find((customer) => customer.id === id) ?? null;
	}
};

export const api = { products, plans, customers };
