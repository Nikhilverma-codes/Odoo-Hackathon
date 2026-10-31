<script lang="ts">
	import { db } from '#lib/data/store.svelte';
	import { customerById, metrics } from '#lib/data/selectors';
	import type { PaymentMethod } from '#lib/data/types';
	import PaymentModal from '#lib/components/PaymentModal.svelte';
	import Badge from '#lib/components/ui/Badge.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import Input from '#lib/components/ui/Input.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import Pagination from '#lib/components/ui/Pagination.svelte';
	import StatCard from '#lib/components/ui/StatCard.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import { formatDate } from '#lib/utils/date';
	import { currency, sum, titleCase } from '#lib/utils/format';

	type Filter = 'all' | PaymentMethod;

	const methods: PaymentMethod[] = ['bank', 'card', 'cash', 'upi'];

	const methodTone: Record<PaymentMethod, 'blue' | 'violet' | 'amber' | 'green'> = {
		bank: 'blue',
		card: 'violet',
		cash: 'amber',
		upi: 'green'
	};

	let search = $state('');
	let filter = $state<Filter>('all');
	let page = $state(1);
	const pageSize = 12;
	let paymentOpen = $state(false);

	let summary = $derived(metrics(db.data));
	let totalCollected = $derived(sum(db.data.payments.map((payment) => payment.amount)));
	let average = $derived(
		db.data.payments.length > 0 ? totalCollected / db.data.payments.length : 0
	);

	let counts = $derived({
		all: db.data.payments.length,
		bank: db.data.payments.filter((payment) => payment.method === 'bank').length,
		card: db.data.payments.filter((payment) => payment.method === 'card').length,
		cash: db.data.payments.filter((payment) => payment.method === 'cash').length,
		upi: db.data.payments.filter((payment) => payment.method === 'upi').length
	});

	let rows = $derived(
		db.data.payments
			.map((payment) => {
				const invoice = db.data.invoices.find((item) => item.id === payment.invoiceId) ?? null;
				return {
					payment,
					invoice,
					customer: invoice ? customerById(db.data, invoice.customerId) : null
				};
			})
			.filter((row) => {
				const matchesFilter = filter === 'all' || row.payment.method === filter;
				const haystack =
					`${row.invoice?.number ?? ''} ${row.customer?.company ?? ''} ${row.customer?.name ?? ''} ${row.payment.note}`.toLowerCase();
				return matchesFilter && haystack.includes(search.trim().toLowerCase());
			})
			.sort((a, b) => b.payment.date.localeCompare(a.payment.date))
	);

	let paged = $derived(rows.slice((page - 1) * pageSize, page * pageSize));

	$effect(() => {
		void search;
		void filter;
		page = 1;
	});
</script>

<svelte:head>
	<title>Payments · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader
		title="Payments"
		description="Every payment received, across bank transfers, cards, cash and UPI."
	>
		{#snippet actions()}
			<Button variant="outline" href="/invoices">
				<Icon name="receipt" size={16} />
				Invoices
			</Button>
			<Button onclick={() => (paymentOpen = true)}>
				<Icon name="plus" size={16} />
				Record payment
			</Button>
		{/snippet}
	</PageHeader>

	<div class="grid gap-4 sm:grid-cols-3">
		<StatCard
			label="Collected this month"
			value={currency(summary.collectedThisMonth)}
			icon="wallet"
			tone="emerald"
			hint="Payments received"
		/>
		<StatCard
			label="Total collected"
			value={currency(totalCollected)}
			icon="credit-card"
			tone="brand"
			hint={`${db.data.payments.length} payments`}
		/>
		<StatCard
			label="Average payment"
			value={currency(average)}
			icon="chart"
			tone="violet"
			hint="Across all recorded payments"
		/>
	</div>

	<div class="flex flex-wrap gap-1.5">
		{#each ['all', ...methods] as item (item)}
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
				onclick={() => (filter = item as Filter)}
			>
				{label}
				<span
					class="rounded-full px-1.5 text-[10px] {filter === item ? 'bg-white/20' : 'bg-slate-100'}"
				>
					{counts[item as Filter]}
				</span>
			</button>
		{/each}
	</div>

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
		<div class="w-full sm:max-w-xs">
			<Input placeholder="Search invoice, customer or note…" icon="search" bind:value={search} />
		</div>
		<p class="text-xs text-slate-400 sm:ml-auto">{rows.length} payments</p>
	</div>

	<Table
		columns={[
			{ label: 'Payment' },
			{ label: 'Invoice' },
			{ label: 'Customer' },
			{ label: 'Method' },
			{ label: 'Date' },
			{ label: 'Amount', align: 'right' },
			{ label: '', align: 'right' }
		]}
		rowCount={paged.length}
		emptyTitle="No payments found"
		emptyDescription="Record a payment against an invoice to get started."
		emptyIcon="wallet"
	>
		{#snippet emptyAction()}
			<Button size="sm" onclick={() => (paymentOpen = true)}>Record payment</Button>
		{/snippet}

		{#each paged as row (row.payment.id)}
			<tr class="transition hover:bg-slate-50">
				<td class="px-4 py-3">
					<p class="max-w-[14rem] truncate font-medium text-slate-800">
						{row.payment.note || 'Payment received'}
					</p>
					<p class="text-[11px] text-slate-400">{row.payment.id}</p>
				</td>
				<td class="px-4 py-3">
					{#if row.invoice}
						<a
							href={`/invoices/${row.invoice.id}`}
							class="font-medium text-slate-700 hover:text-brand-600"
						>
							{row.invoice.number}
						</a>
					{:else}
						<span class="text-slate-400">—</span>
					{/if}
				</td>
				<td class="px-4 py-3">
					<p class="text-slate-700">{row.customer?.company ?? '—'}</p>
					<p class="text-xs text-slate-400">{row.customer?.name ?? ''}</p>
				</td>
				<td class="px-4 py-3">
					<Badge tone={methodTone[row.payment.method]}>{titleCase(row.payment.method)}</Badge>
				</td>
				<td class="px-4 py-3 text-xs whitespace-nowrap text-slate-500">
					{formatDate(row.payment.date)}
				</td>
				<td class="px-4 py-3 text-right font-medium whitespace-nowrap text-emerald-600">
					+{currency(row.payment.amount)}
				</td>
				<td class="px-4 py-3">
					<div class="flex justify-end">
						<Button
							variant="ghost"
							size="icon"
							title="View invoice"
							disabled={!row.invoice}
							href={row.invoice ? `/invoices/${row.invoice.id}` : undefined}
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

<PaymentModal open={paymentOpen} onclose={() => (paymentOpen = false)} />
