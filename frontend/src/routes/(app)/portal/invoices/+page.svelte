<script lang="ts">
	import { auth } from '#lib/auth/auth.svelte';
	import { db } from '#lib/data/store.svelte';
	import { customerById, invoiceBalance, invoiceState, isOverdue } from '#lib/data/selectors';
	import Button from '#lib/components/ui/Button.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import Input from '#lib/components/ui/Input.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import StatCard from '#lib/components/ui/StatCard.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import { formatDate, relativeDays } from '#lib/utils/date';
	import { currency, sum } from '#lib/utils/format';

	let user = $derived(auth.user);
	let customer = $derived(customerById(db.data, user?.customerId ?? null));
	let search = $state('');

	let invoices = $derived(
		customer
			? db.data.invoices
					.filter((invoice) => invoice.customerId === customer.id && invoice.status !== 'draft')
					.sort((a, b) => b.issueDate.localeCompare(a.issueDate))
			: []
	);

	let rows = $derived(
		invoices.filter((invoice) => invoice.number.toLowerCase().includes(search.trim().toLowerCase()))
	);

	let openInvoices = $derived(
		invoices.filter((invoice) => invoice.status !== 'cancelled' && invoiceBalance(invoice) > 0)
	);
	let overdueInvoices = $derived(invoices.filter(isOverdue));
	let paidInvoices = $derived(invoices.filter((invoice) => invoice.status === 'paid'));

	let outstanding = $derived(sum(openInvoices.map(invoiceBalance)));
	let overdueAmount = $derived(sum(overdueInvoices.map(invoiceBalance)));
	let paidTotal = $derived(sum(paidInvoices.map((invoice) => invoice.total)));
</script>

<svelte:head>
	<title>My invoices · Brightloop</title>
</svelte:head>

<div class="space-y-5">
	<PageHeader
		title="My invoices"
		description={customer
			? `Invoices issued to ${customer.company}.`
			: 'Invoices issued to your account.'}
	>
		{#snippet actions()}
			<Button variant="outline" href="/portal/subscriptions">
				<Icon name="repeat" size={16} />
				My subscriptions
			</Button>
		{/snippet}
	</PageHeader>

	<div class="grid gap-4 sm:grid-cols-3">
		<StatCard
			label="Outstanding"
			value={currency(outstanding)}
			icon="receipt"
			tone={outstanding > 0 ? 'amber' : 'emerald'}
			hint={`${openInvoices.length} open invoice(s)`}
		/>
		<StatCard
			label="Overdue"
			value={currency(overdueAmount)}
			icon="exclamation"
			tone={overdueAmount > 0 ? 'rose' : 'emerald'}
			hint={`${overdueInvoices.length} invoice(s) past due`}
		/>
		<StatCard
			label="Paid"
			value={currency(paidTotal)}
			icon="check-circle"
			tone="emerald"
			hint={`${paidInvoices.length} paid invoice(s)`}
		/>
	</div>

	<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
		<div class="w-full sm:max-w-xs">
			<Input placeholder="Search invoice number…" icon="search" bind:value={search} />
		</div>
		<p class="text-xs text-slate-400 sm:ml-auto">{rows.length} invoices</p>
	</div>

	<Table
		columns={[
			{ label: 'Invoice' },
			{ label: 'Issued' },
			{ label: 'Due' },
			{ label: 'Status' },
			{ label: 'Total', align: 'right' },
			{ label: 'Balance', align: 'right' },
			{ label: '', align: 'right' }
		]}
		rowCount={rows.length}
		emptyTitle="No invoices found"
		emptyDescription="Invoices issued to your account will appear here."
		emptyIcon="receipt"
	>
		{#each rows as invoice (invoice.id)}
			{@const state = invoiceState(invoice)}
			<tr class="transition hover:bg-slate-50">
				<td class="px-4 py-3">
					<a
						href={`/portal/invoices/${invoice.id}`}
						class="font-medium text-slate-800 hover:text-brand-600"
					>
						{invoice.number}
					</a>
					<p class="text-xs text-slate-400">{invoice.lines.length} line(s)</p>
				</td>
				<td class="px-4 py-3 text-xs whitespace-nowrap text-slate-500">
					{formatDate(invoice.issueDate)}
				</td>
				<td class="px-4 py-3 text-xs whitespace-nowrap">
					<span class={state === 'overdue' ? 'font-medium text-rose-600' : 'text-slate-500'}>
						{formatDate(invoice.dueDate)}
					</span>
					{#if state === 'confirmed'}
						<p class="text-[11px] text-slate-400">{relativeDays(invoice.dueDate)}</p>
					{/if}
				</td>
				<td class="px-4 py-3"><StatusBadge status={state} /></td>
				<td class="px-4 py-3 text-right font-medium whitespace-nowrap text-slate-700">
					{currency(invoice.total)}
				</td>
				<td class="px-4 py-3 text-right whitespace-nowrap">
					<span
						class={invoiceBalance(invoice) > 0 ? 'font-medium text-rose-600' : 'text-slate-400'}
					>
						{currency(invoiceBalance(invoice))}
					</span>
				</td>
				<td class="px-4 py-3">
					<div class="flex justify-end">
						<Button
							variant="ghost"
							size="icon"
							title="View invoice"
							href={`/portal/invoices/${invoice.id}`}
						>
							<Icon name="arrow-right" size={15} />
						</Button>
					</div>
				</td>
			</tr>
		{/each}
	</Table>

	<p class="rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500">
		Payments are applied by Brightloop after they are received. Include the invoice number with your
		transfer.
	</p>
</div>
