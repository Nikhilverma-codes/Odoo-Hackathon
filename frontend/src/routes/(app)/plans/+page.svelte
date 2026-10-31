<script lang="ts">
	import { api } from '#lib/data/api';
	import { db } from '#lib/data/store.svelte';
	import type { Plan } from '#lib/data/types';
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
	import Toggle from '#lib/components/ui/Toggle.svelte';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { todayISO } from '#lib/utils/date';
	import { currency } from '#lib/utils/format';

	type FormState = Omit<Plan, 'id'> & { id?: string };

	const emptyForm = (): FormState => ({
		name: '',
		productId: '',
		price: 0,
		billingPeriod: 'monthly',
		minQuantity: 1,
		availableFrom: todayISO(),
		availableTo: todayISO().slice(0, 4) + '-12-31',
		autoClose: false,
		allowEarlyClose: true,
		pausable: true,
		renewable: true,
		active: true
	});

	let search = $state('');
	let page = $state(1);
	const pageSize = 7;

	let modalOpen = $state(false);
	let editing = $state<Plan | null>(null);
	let form = $state<FormState>(emptyForm());
	let formError = $state('');
	let saving = $state(false);
	let deleteTarget = $state<Plan | null>(null);
	let deleting = $state(false);

	let productOptions = $derived(
		db.data.products.map((product) => ({ value: product.id, label: product.name }))
	);

	let plans = $derived(
		db.data.plans.filter((plan) => {
			const product = db.data.products.find((item) => item.id === plan.productId);
			return `${plan.name} ${product?.name ?? ''}`
				.toLowerCase()
				.includes(search.trim().toLowerCase());
		})
	);

	let paged = $derived(plans.slice((page - 1) * pageSize, page * pageSize));

	$effect(() => {
		void search;
		page = 1;
	});

	function productName(id: string): string {
		return db.data.products.find((product) => product.id === id)?.name ?? '—';
	}

	function openCreate() {
		editing = null;
		form = emptyForm();
		formError = '';
		modalOpen = true;
	}

	function openEdit(plan: Plan) {
		editing = plan;
		form = { ...plan };
		formError = '';
		modalOpen = true;
	}

	async function save() {
		formError = '';
		if (!form.name.trim()) {
			formError = 'Give the plan a name.';
			return;
		}
		if (!form.productId) {
			formError = 'Choose the product this plan sells.';
			return;
		}
		if (Number(form.price) < 0 || Number(form.minQuantity) < 1) {
			formError = 'Price must be zero or more and minimum quantity at least 1.';
			return;
		}

		saving = true;
		const payload: Omit<Plan, 'id'> = {
			name: form.name.trim(),
			productId: form.productId,
			price: Number(form.price) || 0,
			billingPeriod: form.billingPeriod,
			minQuantity: Number(form.minQuantity) || 1,
			availableFrom: form.availableFrom,
			availableTo: form.availableTo,
			autoClose: form.autoClose,
			allowEarlyClose: form.allowEarlyClose,
			pausable: form.pausable,
			renewable: form.renewable,
			active: form.active
		};

		if (editing) {
			await api.plans.update(editing.id, payload);
			toasts.success(`${payload.name} updated.`);
		} else {
			await api.plans.create(payload);
			toasts.success(`${payload.name} created.`);
		}
		saving = false;
		modalOpen = false;
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		await api.plans.remove(deleteTarget.id);
		deleting = false;
		toasts.success(`${deleteTarget.name} deleted.`);
		deleteTarget = null;
	}
</script>

<svelte:head>
	<title>Plans · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader title="Plans" description="Create the plans customers can subscribe to.">
		{#snippet actions()}
			<Button onclick={openCreate}>
				<Icon name="plus" size={16} />
				New plan
			</Button>
		{/snippet}
	</PageHeader>

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
		<div class="w-full sm:max-w-xs">
			<Input placeholder="Search plans…" icon="search" bind:value={search} />
		</div>
		<p class="text-xs text-slate-400 sm:ml-auto">
			{plans.length} of {db.data.plans.length} plans
		</p>
	</div>

	<Table
		columns={[
			{ label: 'Plan' },
			{ label: 'Price', align: 'right' },
			{ label: 'Billing' },
			{ label: 'Min qty', align: 'center' },
			{ label: 'Status' },
			{ label: '', align: 'right' }
		]}
		rowCount={paged.length}
		emptyTitle="No plans yet"
		emptyDescription="Create a plan to start selling a product on a subscription."
		emptyIcon="tag"
	>
		{#snippet emptyAction()}
			<Button size="sm" onclick={openCreate}>New plan</Button>
		{/snippet}

		{#each paged as plan (plan.id)}
			<tr class="transition hover:bg-slate-50">
				<td class="px-4 py-3">
					<p class="font-medium text-slate-800">{plan.name}</p>
					<p class="text-xs text-slate-400">{productName(plan.productId)}</p>
				</td>
				<td class="px-4 py-3 text-right font-medium whitespace-nowrap text-slate-700">
					{currency(plan.price)}
				</td>
				<td class="px-4 py-3">
					<Badge tone="brand">{plan.billingPeriod}</Badge>
				</td>
				<td class="px-4 py-3 text-center text-slate-500">{plan.minQuantity}</td>
				<td class="px-4 py-3">
					<Badge tone={plan.active ? 'green' : 'slate'} dot>
						{plan.active ? 'Active' : 'Inactive'}
					</Badge>
				</td>
				<td class="px-4 py-3">
					<div class="flex items-center justify-end gap-1">
						<Button variant="ghost" size="icon" title="Edit plan" onclick={() => openEdit(plan)}>
							<Icon name="edit" size={15} />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							title="Delete plan"
							class="text-rose-500 hover:bg-rose-50 hover:text-rose-600"
							onclick={() => (deleteTarget = plan)}
						>
							<Icon name="trash" size={15} />
						</Button>
					</div>
				</td>
			</tr>
		{/each}
	</Table>

	{#if plans.length > pageSize}
		<Pagination {page} {pageSize} total={plans.length} onpage={(next) => (page = next)} />
	{/if}
</div>

<Modal
	open={modalOpen}
	title={editing ? 'Edit plan' : 'New plan'}
	description="Set the product, price and billing cadence."
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
			<Input label="Plan name" placeholder="Growth Monthly" required bind:value={form.name} />
			<Select
				label="Product"
				placeholder="Choose a product"
				bind:value={form.productId}
				options={productOptions}
			/>
			<Input label="Price" type="number" min={0} step="0.01" bind:value={form.price} />
			<Select
				label="Billing period"
				placeholder="Choose a period"
				bind:value={form.billingPeriod}
				options={[
					{ value: 'daily', label: 'Daily' },
					{ value: 'weekly', label: 'Weekly' },
					{ value: 'monthly', label: 'Monthly' },
					{ value: 'yearly', label: 'Yearly' }
				]}
			/>
			<Input label="Minimum quantity" type="number" min={1} bind:value={form.minQuantity} />
		</div>

		<Toggle
			label="Active"
			description="Inactive plans cannot be selected on new subscriptions."
			bind:checked={form.active}
		/>
	</form>

	{#snippet footer()}
		<Button variant="outline" onclick={() => (modalOpen = false)} disabled={saving}>Cancel</Button>
		<Button onclick={save} disabled={saving}
			>{saving ? 'Saving…' : editing ? 'Save changes' : 'Create plan'}</Button
		>
	{/snippet}
</Modal>

<ConfirmDialog
	open={deleteTarget !== null}
	title="Delete plan"
	message={`Delete ${deleteTarget?.name ?? 'this plan'}? Existing subscriptions keep their history.`}
	confirmLabel="Delete plan"
	loading={deleting}
	onconfirm={confirmDelete}
	oncancel={() => (deleteTarget = null)}
/>
