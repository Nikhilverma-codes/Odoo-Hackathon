<script lang="ts">
	import { db } from '#lib/data/store.svelte';
	import {
		customerById,
		invoiceBalance,
		invoiceState,
		isOverdue,
		metrics
	} from '#lib/data/selectors';
	import type { Invoice } from '#lib/data/types';
	import Button from '#lib/components/ui/Button.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import Input from '#lib/components/ui/Input.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import Pagination from '#lib/components/ui/Pagination.svelte';
	import StatCard from '#lib/components/ui/StatCard.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import PaymentModal from '#lib/components/PaymentModal.svelte';
	import RunBillingModal from '#lib/components/RunBillingModal.svelte';
	import { formatDate, relativeDays } from '#lib/utils/date';
	import { currency, titleCase } from '#lib/utils/format';

	type Filter = 'all' | 'draft' | 'confirmed' | 'overdue' | 'paid' | 'cancelled';

	const filters: Filter[] = ['all', 'draft', 'confirmed', 'overdue', 'paid', 'cancelled'];

	let search = $state('');
	let filter = $state<Filter>('all');
	let page = $state(1);
	const pageSize = 10;

	let paymentOpen = $state(false);
	let paymentTarget = $state<Invoice | null>(null);
	let billingOpen = $state(false);

	let summary = $derived(metrics(db.data));

	let counts = $derived({
		all: db.data.invoices.length,
		draft: db.data.invoices.filter((invoice) => invoice.status === 'draft').length,
		confirmed: db.data.invoices.filter(
			(invoice) => invoice.status === 'confirmed' && !isOverdue(invoice)
		).length,
		overdue: db.data.invoices.filter(isOverdue).length,
		paid: db.data.invoices.filter((invoice) => invoice.status === 'paid').length,
		cancelled: db.data.invoices.filter((invoice) => invoice.status === 'cancelled').length
	});

	let rows = $derived(
		db.data.invoices
			.map((invoice) => ({
				invoice,
				customer: customerById(db.data, invoice.customerId),
				state: invoiceState(invoice)
			}))
			.filter((row) => {
				const matchesFilter =
					filter === 'all'
						? true
						: filter === 'confirmed'
							? row.state === 'confirmed'
							: row.state === filter;
				const haystack =
					`${row.invoice.number} ${row.customer?.company ?? ''} ${row.customer?.name ?? ''}`.toLowerCase();
				return matchesFilter && haystack.includes(search.trim().toLowerCase());
			})
			.sort((a, b) => b.invoice.issueDate.localeCompare(a.invoice.issueDate))
	);

	let paged = $derived(rows.slice((page - 1) * pageSize, page * pageSize));

	$effect(() => {
		void search;
		void filter;
		page = 1;
	});

	function openPayment(invoice: Invoice) {
		paymentTarget = invoice;
		paymentOpen = true;
	}
</script>

<svelte:head>
	<title>Invoices · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader
		title="Invoices"
		description="Track what has been billed, what is overdue and what has been collected."
	>
		{#snippet actions()}
			<Button variant="outline" href="/payments">
				<Icon name="wallet" size={16} />
				Payments
			</Button>
			<Button variant="outline" href="/subscriptions">
				<Icon name="receipt" size={16} />
				Bill a subscription
			</Button>
			<Button onclick={() => (billingOpen = true)}>
				<Icon name="play" size={16} />
				Run billing
			</Button>
		{/snippet}
	</PageHeader>

	<div class="grid gap-4 sm:grid-cols-3">
		<StatCard
			label="Outstanding"
			value={currency(summary.outstanding)}
			icon="receipt"
			tone="amber"
			hint="Draft and confirmed invoices"
		/>
		<StatCard
			label="Overdue"
			value={currency(summary.overdueAmount)}
			icon="exclamation"
			tone="rose"
			hint={`${summary.overdueCount} invoice(s) past due`}
		/>
		<StatCard
			label="Collected this month"
			value={currency(summary.collectedThisMonth)}
			icon="wallet"
			tone="emerald"
			hint="Payments received"
		/>
	</div>

	<div class="flex flex-wrap gap-1.5">
		{#each filters as item (item)}
			{@const label = item === 'all' ? 'All' : titleCase(item)}
			<button
				type="button"
				class="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition"
				class:bg-brand-600={filter === item}
				class:text-white={filter === item}
				class:bg-white={filter !== item}
				class:text-slate-600={filter !== item}
				class:border={filter !== item}
				class:border-slate-200={filter !== item}
				onclick={() => (filter = item)}
			>
				{label}
				<span
					class="rounded-full px-1.5 text-[10px] {filter === item ? 'bg-white/20' : 'bg-slate-100'}"
				>
					{counts[item]}
				</span>
			</button>
		{/each}
	</div>

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
		<div class="w-full sm:max-w-xs">
			<Input placeholder="Search number or customer…" icon="search" bind:value={search} />
		</div>
		<p class="text-xs text-slate-400 sm:ml-auto">{rows.length} invoices</p>
	</div>

	<Table
		columns={[
			{ label: 'Invoice' },
			{ label: 'Customer' },
			{ label: 'Issued' },
			{ label: 'Due' },
			{ label: 'Status' },
			{ label: 'Total', align: 'right' },
			{ label: 'Balance', align: 'right' },
			{ label: '', align: 'right' }
		]}
		rowCount={paged.length}
		emptyTitle="No invoices found"
		emptyDescription="Generate an invoice from an active subscription, or clear the filters."
		emptyIcon="receipt"
	>
		{#each paged as row (row.invoice.id)}
			<tr class="transition hover:bg-slate-50">
				<td class="px-4 py-3">
					<a
						href={`/invoices/${row.invoice.id}`}
						class="font-medium text-slate-800 hover:text-brand-600"
					>
						{row.invoice.number}
					</a>
					<p class="text-xs text-slate-400">{row.invoice.lines.length} line(s)</p>
				</td>
				<td class="px-4 py-3">
					<p class="text-slate-700">{row.customer?.company ?? '—'}</p>
					<p class="text-xs text-slate-400">{row.customer?.name ?? ''}</p>
				</td>
				<td class="px-4 py-3 text-xs whitespace-nowrap text-slate-500">
					{formatDate(row.invoice.issueDate)}
				</td>
				<td class="px-4 py-3 text-xs whitespace-nowrap">
					<span class={row.state === 'overdue' ? 'font-medium text-rose-600' : 'text-slate-500'}>
						{formatDate(row.invoice.dueDate)}
					</span>
					{#if row.state === 'confirmed'}
						<p class="text-[11px] text-slate-400">{relativeDays(row.invoice.dueDate)}</p>
					{/if}
				</td>
				<td class="px-4 py-3"><StatusBadge status={row.state} /></td>
				<td class="px-4 py-3 text-right font-medium whitespace-nowrap text-slate-700">
					{currency(row.invoice.total)}
				</td>
				<td class="px-4 py-3 text-right whitespace-nowrap">
					<span
						class={invoiceBalance(row.invoice) > 0 ? 'font-medium text-rose-600' : 'text-slate-400'}
					>
						{currency(invoiceBalance(row.invoice))}
					</span>
				</td>
				<td class="px-4 py-3">
					<div class="flex items-center justify-end gap-1">
						{#if invoiceBalance(row.invoice) > 0 && row.state !== 'cancelled'}
							<Button
								variant="ghost"
								size="icon"
								title="Record payment"
								onclick={() => openPayment(row.invoice)}
							>
								<Icon name="wallet" size={15} />
							</Button>
						{/if}
						<Button
							variant="ghost"
							size="icon"
							title="View invoice"
							href={`/invoices/${row.invoice.id}`}
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

<PaymentModal
	open={paymentOpen}
	invoice={paymentTarget}
	onclose={() => (paymentOpen = false)}
	onrecorded={() => (paymentTarget = null)}
/>

<RunBillingModal open={billingOpen} onclose={() => (billingOpen = false)} />
