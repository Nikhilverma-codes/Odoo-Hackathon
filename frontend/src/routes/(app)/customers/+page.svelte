<script lang="ts">
	import { api } from '#lib/data/api';
	import { db } from '#lib/data/store.svelte';
	import type { Customer } from '#lib/data/types';
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import Input from '#lib/components/ui/Input.svelte';
	import Modal from '#lib/components/ui/Modal.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import Pagination from '#lib/components/ui/Pagination.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import Textarea from '#lib/components/ui/Textarea.svelte';
	import { toasts } from '#lib/stores/toasts.svelte';
	import { todayISO } from '#lib/utils/date';
	import { currency } from '#lib/utils/format';
	import { isValidEmail } from '#lib/utils/validation';
	import { invoiceBalance, subscriptionMonthlyValue } from '#lib/data/selectors';

	type FormState = Omit<Customer, 'id'> & { id?: string };

	const emptyForm = (): FormState => ({
		name: '',
		company: '',
		email: '',
		phone: '',
		address: '',
		since: todayISO()
	});

	let search = $state('');
	let page = $state(1);
	const pageSize = 8;

	let modalOpen = $state(false);
	let editing = $state<Customer | null>(null);
	let form = $state<FormState>(emptyForm());
	let formError = $state('');
	let saving = $state(false);

	let rows = $derived(
		db.data.customers
			.map((customer) => {
				const subscriptions = db.data.subscriptions.filter(
					(item) => item.customerId === customer.id
				);
				const activeSubscriptions = subscriptions.filter((item) => item.status === 'active');
				const mrr = activeSubscriptions.reduce(
					(total, subscription) => total + subscriptionMonthlyValue(db.data, subscription),
					0
				);
				const outstanding = db.data.invoices
					.filter(
						(invoice) =>
							invoice.customerId === customer.id &&
							(invoice.status === 'confirmed' || invoice.status === 'draft')
					)
					.reduce((total, invoice) => total + invoiceBalance(invoice), 0);
				return { customer, activeSubscriptions: activeSubscriptions.length, mrr, outstanding };
			})
			.filter((row) =>
				`${row.customer.company} ${row.customer.name} ${row.customer.email}`
					.toLowerCase()
					.includes(search.trim().toLowerCase())
			)
			.sort((a, b) => b.mrr - a.mrr)
	);

	let paged = $derived(rows.slice((page - 1) * pageSize, page * pageSize));

	$effect(() => {
		void search;
		page = 1;
	});

	function openCreate() {
		editing = null;
		form = emptyForm();
		formError = '';
		modalOpen = true;
	}

	function openEdit(customer: Customer) {
		editing = customer;
		form = { ...customer };
		formError = '';
		modalOpen = true;
	}

	async function save() {
		formError = '';
		if (!form.company.trim()) {
			formError = 'Enter the company name.';
			return;
		}
		if (!form.name.trim()) {
			formError = 'Enter the primary contact name.';
			return;
		}
		if (!isValidEmail(form.email)) {
			formError = 'Enter a valid email address.';
			return;
		}

		saving = true;
		const payload: Omit<Customer, 'id'> = {
			name: form.name.trim(),
			company: form.company.trim(),
			email: form.email.trim().toLowerCase(),
			phone: form.phone,
			address: form.address,
			since: form.since
		};

		try {
			if (editing) {
				await api.customers.update(editing.id, payload);
				toasts.success(`${payload.company} updated.`);
			} else {
				await api.customers.create(payload);
				toasts.success(`${payload.company} added.`);
			}
			modalOpen = false;
		} catch (error) {
			formError = error instanceof Error ? error.message : 'Could not save the customer.';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head>
	<title>Customers · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader
		title="Customers"
		description="Every account, their recurring value and what they still owe."
	>
		{#snippet actions()}
			<Button onclick={openCreate}>
				<Icon name="plus" size={16} />
				New customer
			</Button>
		{/snippet}
	</PageHeader>

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
		<div class="w-full sm:max-w-xs">
			<Input placeholder="Search customers…" icon="search" bind:value={search} />
		</div>
		<p class="text-xs text-slate-400 sm:ml-auto">
			{rows.length} of {db.data.customers.length} customers
		</p>
	</div>

	<Table
		columns={[
			{ label: 'Customer' },
			{ label: 'Contact' },
			{ label: 'Active subs', align: 'center' },
			{ label: 'Recurring', align: 'right' },
			{ label: 'Outstanding', align: 'right' },
			{ label: '', align: 'right' }
		]}
		rowCount={paged.length}
		emptyTitle="No customers found"
		emptyDescription="Try a different search or add your first customer."
		emptyIcon="building"
	>
		{#snippet emptyAction()}
			<Button size="sm" onclick={openCreate}>New customer</Button>
		{/snippet}

		{#each paged as row (row.customer.id)}
			<tr class="transition hover:bg-slate-50">
				<td class="px-4 py-3">
					<div class="flex items-center gap-3">
						<Avatar name={row.customer.company} size="sm" />
						<div class="min-w-0">
							<a
								href={`/customers/${row.customer.id}`}
								class="block truncate font-medium text-slate-800 hover:text-brand-600"
							>
								{row.customer.company}
							</a>
							<p class="truncate text-xs text-slate-400">{row.customer.email}</p>
						</div>
					</div>
				</td>
				<td class="px-4 py-3">
					<p class="text-slate-700">{row.customer.name}</p>
					<p class="text-xs text-slate-400">{row.customer.phone || '—'}</p>
				</td>
				<td class="px-4 py-3 text-center">
					<span class="font-medium text-slate-700">{row.activeSubscriptions}</span>
				</td>
				<td class="px-4 py-3 text-right font-medium whitespace-nowrap text-slate-700">
					{currency(row.mrr)}<span class="text-xs font-normal text-slate-400">/mo</span>
				</td>
				<td class="px-4 py-3 text-right whitespace-nowrap">
					<span class={row.outstanding > 0 ? 'font-medium text-rose-600' : 'text-slate-500'}>
						{currency(row.outstanding)}
					</span>
				</td>
				<td class="px-4 py-3">
					<div class="flex items-center justify-end gap-1">
						<Button
							variant="ghost"
							size="icon"
							title="Edit customer"
							onclick={() => openEdit(row.customer)}
						>
							<Icon name="edit" size={15} />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							title="View customer"
							href={`/customers/${row.customer.id}`}
						>
							<Icon name="arrow-right" size={15} />
						</Button>
					</div>
				</td>
			</tr>
		{/each}
	</Table>

	{#if rows.length > pageSize}
		<Pagination {page} {pageSize} total={rows.length} onpage={(next) => (page = next)} />
	{/if}
</div>

<Modal
	open={modalOpen}
	title={editing ? 'Edit customer' : 'New customer'}
	description="Keep customer contact and billing details in one place."
	onclose={() => (modalOpen = false)}
>
	<form
		class="space-y-4"
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
			<Input label="Company" placeholder="Nimbus Retail" required bind:value={form.company} />
			<Input label="Primary contact" placeholder="Priya Sharma" required bind:value={form.name} />
			<Input
				label="Email"
				type="email"
				placeholder="priya@nimbus.co"
				icon="mail"
				required
				bind:value={form.email}
			/>
			<Input label="Phone" placeholder="+1 415 555 0114" bind:value={form.phone} />
		</div>
		<Textarea label="Billing address" placeholder="Street, city, state" bind:value={form.address} />
		<Input label="Customer since" type="date" bind:value={form.since} />
	</form>

	{#snippet footer()}
		<Button variant="outline" onclick={() => (modalOpen = false)} disabled={saving}>Cancel</Button>
		<Button onclick={save} disabled={saving}
			>{saving ? 'Saving…' : editing ? 'Save changes' : 'Add customer'}</Button
		>
	{/snippet}
</Modal>
