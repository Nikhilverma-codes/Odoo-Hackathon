<script lang="ts">
	import { api } from '#lib/data/api';
	import { db } from '#lib/data/store.svelte';
	import type { Product, ProductVariant } from '#lib/data/types';
	import Badge from '#lib/components/ui/Badge.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import ConfirmDialog from '#lib/components/ui/ConfirmDialog.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import Input from '#lib/components/ui/Input.svelte';
	import Modal from '#lib/components/ui/Modal.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import Pagination from '#lib/components/ui/Pagination.svelte';
	import Select from '#lib/components/ui/Select.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import Textarea from '#lib/components/ui/Textarea.svelte';
	import Toggle from '#lib/components/ui/Toggle.svelte';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { currency } from '#lib/utils/format';
	import { uid } from '#lib/utils/validation';

	type FormState = Omit<Product, 'id'> & { id?: string };

	const emptyForm = (): FormState => ({
		name: '',
		type: 'Software',
		salesPrice: 0,
		costPrice: 0,
		notes: '',
		active: true,
		variants: [{ id: uid('var'), name: 'Standard', priceDelta: 0 }]
	});

	let search = $state('');
	let statusFilter = $state('all');
	let page = $state(1);
	const pageSize = 7;

	let modalOpen = $state(false);
	let editing = $state<Product | null>(null);
	let form = $state<FormState>(emptyForm());
	let formError = $state('');
	let saving = $state(false);
	let deleteTarget = $state<Product | null>(null);
	let deleting = $state(false);

	let products = $derived(
		db.data.products.filter((product) => {
			const matchesSearch = `${product.name} ${product.type}`
				.toLowerCase()
				.includes(search.trim().toLowerCase());
			const matchesStatus =
				statusFilter === 'all' || (statusFilter === 'active' ? product.active : !product.active);
			return matchesSearch && matchesStatus;
		})
	);

	let paged = $derived(products.slice((page - 1) * pageSize, page * pageSize));

	$effect(() => {
		void search;
		void statusFilter;
		page = 1;
	});

	function openCreate() {
		editing = null;
		form = emptyForm();
		formError = '';
		modalOpen = true;
	}

	function openEdit(product: Product) {
		editing = product;
		form = {
			...product,
			variants: product.variants.map((variant) => ({ ...variant }))
		};
		formError = '';
		modalOpen = true;
	}

	function addVariant() {
		form.variants = [...form.variants, { id: uid('var'), name: '', priceDelta: 0 }];
	}

	function removeVariant(id: string) {
		form.variants = form.variants.filter((variant) => variant.id !== id);
	}

	async function save() {
		formError = '';
		if (!form.name.trim()) {
			formError = 'Give the product a name.';
			return;
		}
		if (form.variants.some((variant) => !variant.name.trim())) {
			formError = 'Every variant needs a name.';
			return;
		}

		saving = true;
		const payload: Omit<Product, 'id'> = {
			name: form.name.trim(),
			type: form.type,
			salesPrice: Number(form.salesPrice) || 0,
			costPrice: Number(form.costPrice) || 0,
			notes: form.notes,
			active: form.active,
			variants: form.variants.map<ProductVariant>((variant) => ({
				id: variant.id,
				name: variant.name.trim(),
				priceDelta: Number(variant.priceDelta) || 0
			}))
		};

		try {
			if (editing) {
				await api.products.update(editing.id, payload);
				toasts.success(`${payload.name} updated.`);
			} else {
				await api.products.create(payload);
				toasts.success(`${payload.name} added to the catalog.`);
			}
			modalOpen = false;
		} catch (error) {
			formError = error instanceof Error ? error.message : 'Could not save the product.';
		} finally {
			saving = false;
		}
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		try {
			await api.products.remove(deleteTarget.id);
			toasts.success(`${deleteTarget.name} deleted.`);
			deleteTarget = null;
		} catch (error) {
			toasts.error(error instanceof Error ? error.message : 'Could not delete the product.');
		} finally {
			deleting = false;
		}
	}
</script>

<svelte:head>
	<title>Products · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader
		title="Products"
		description="The catalog everything bills from. Add variants to change pricing by brand or edition."
	>
		{#snippet actions()}
			<Button onclick={openCreate}>
				<Icon name="plus" size={16} />
				New product
			</Button>
		{/snippet}
	</PageHeader>

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
		<div class="w-full sm:max-w-xs">
			<Input placeholder="Search products…" icon="search" bind:value={search} />
		</div>
		<div class="sm:w-44">
			<Select
				placeholder=""
				bind:value={statusFilter}
				options={[
					{ value: 'all', label: 'All products' },
					{ value: 'active', label: 'Active only' },
					{ value: 'inactive', label: 'Inactive only' }
				]}
			/>
		</div>
		<p class="text-xs text-slate-400 sm:ml-auto">
			{products.length} of {db.data.products.length} products
		</p>
	</div>

	<Table
		columns={[
			{ label: 'Product' },
			{ label: 'Type' },
			{ label: 'Sales price', align: 'right' },
			{ label: 'Cost price', align: 'right' },
			{ label: 'Variants' },
			{ label: 'Status' },
			{ label: '', align: 'right' }
		]}
		rowCount={paged.length}
		emptyTitle="No products match your filters"
		emptyDescription="Adjust the search or add a new product to the catalog."
		emptyIcon="box"
	>
		{#snippet emptyAction()}
			<Button size="sm" onclick={openCreate}>New product</Button>
		{/snippet}

		{#each paged as product (product.id)}
			<tr class="transition hover:bg-slate-50">
				<td class="px-4 py-3">
					<div class="flex items-center gap-3">
						<span
							class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600"
						>
							<Icon name="box" size={16} />
						</span>
						<div class="min-w-0">
							<p class="truncate font-medium text-slate-800">{product.name}</p>
							<p class="max-w-xs truncate text-xs text-slate-400">{product.notes}</p>
						</div>
					</div>
				</td>
				<td class="px-4 py-3">
					<Badge tone="slate">{product.type}</Badge>
				</td>
				<td class="px-4 py-3 text-right font-medium whitespace-nowrap text-slate-700">
					{currency(product.salesPrice)}
				</td>
				<td class="px-4 py-3 text-right whitespace-nowrap text-slate-500">
					{currency(product.costPrice)}
				</td>
				<td class="px-4 py-3">
					<div class="flex flex-wrap gap-1">
						{#each product.variants.slice(0, 2) as variant (variant.id)}
							<span class="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-500">
								{variant.name}{variant.priceDelta ? ` +${currency(variant.priceDelta)}` : ''}
							</span>
						{/each}
						{#if product.variants.length > 2}
							<span class="text-[11px] text-slate-400">+{product.variants.length - 2}</span>
						{/if}
					</div>
				</td>
				<td class="px-4 py-3">
					<Badge tone={product.active ? 'green' : 'slate'} dot>
						{product.active ? 'Active' : 'Inactive'}
					</Badge>
				</td>
				<td class="px-4 py-3">
					<div class="flex items-center justify-end gap-1">
						<Button
							variant="ghost"
							size="icon"
							title="Edit product"
							onclick={() => openEdit(product)}
						>
							<Icon name="edit" size={15} />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							title="Delete product"
							class="text-rose-500 hover:bg-rose-50 hover:text-rose-600"
							onclick={() => (deleteTarget = product)}
						>
							<Icon name="trash" size={15} />
						</Button>
					</div>
				</td>
			</tr>
		{/each}
	</Table>

	{#if products.length > pageSize}
		<Pagination {page} {pageSize} total={products.length} onpage={(next) => (page = next)} />
	{/if}
</div>

<Modal
	open={modalOpen}
	title={editing ? 'Edit product' : 'New product'}
	description="Products are sold through plans. Variants adjust the price per option."
	size="lg"
	onclose={() => (modalOpen = false)}
>
	<form
		class="space-y-5"
		onsubmit={(event) => {
			event.preventDefault();
			save();
		}}
	>
		{#if formError}
			<p class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
				{formError}
			</p>
		{/if}

		<div class="grid gap-4 sm:grid-cols-2">
			<Input label="Product name" placeholder="Brightloop CRM" required bind:value={form.name} />
			<Select
				label="Type"
				placeholder="Choose a type"
				bind:value={form.type}
				options={[
					{ value: 'Software', label: 'Software' },
					{ value: 'Hardware', label: 'Hardware' },
					{ value: 'Service', label: 'Service' },
					{ value: 'Add-on', label: 'Add-on' }
				]}
			/>
			<Input label="Sales price" type="number" min={0} step="0.01" bind:value={form.salesPrice} />
			<Input label="Cost price" type="number" min={0} step="0.01" bind:value={form.costPrice} />
		</div>

		<Textarea
			label="Notes"
			placeholder="Describe what this product includes…"
			bind:value={form.notes}
		/>

		<div>
			<div class="mb-2 flex items-center justify-between">
				<div>
					<p class="text-xs font-medium text-slate-600">Variants</p>
					<p class="text-xs text-slate-400">e.g. choosing the Odoo brand adds 560 to the price.</p>
				</div>
				<Button variant="outline" size="sm" onclick={addVariant}>
					<Icon name="plus" size={14} />
					Add variant
				</Button>
			</div>
			<div class="space-y-2">
				{#each form.variants as variant (variant.id)}
					<div class="flex items-center gap-2">
						<Input placeholder="Variant name" bind:value={variant.name} class="flex-1" />
						<Input
							type="number"
							step="0.01"
							placeholder="Price delta"
							bind:value={variant.priceDelta}
							class="w-36"
						/>
						<Button
							variant="ghost"
							size="icon"
							title="Remove variant"
							class="text-rose-500 hover:bg-rose-50"
							onclick={() => removeVariant(variant.id)}
							disabled={form.variants.length === 1}
						>
							<Icon name="trash" size={15} />
						</Button>
					</div>
				{/each}
			</div>
		</div>

		<Toggle
			label="Active"
			description="Inactive products stay in the catalog but cannot be sold on new plans."
			bind:checked={form.active}
		/>
	</form>

	{#snippet footer()}
		<Button variant="outline" onclick={() => (modalOpen = false)} disabled={saving}>Cancel</Button>
		<Button onclick={save} disabled={saving}
			>{saving ? 'Saving…' : editing ? 'Save changes' : 'Create product'}</Button
		>
	{/snippet}
</Modal>

<ConfirmDialog
	open={deleteTarget !== null}
	title="Delete product"
	message={`Delete ${deleteTarget?.name ?? 'this product'}? Plans referencing it will keep their data but lose the product link.`}
	confirmLabel="Delete product"
	loading={deleting}
	onconfirm={confirmDelete}
	oncancel={() => (deleteTarget = null)}
/>
