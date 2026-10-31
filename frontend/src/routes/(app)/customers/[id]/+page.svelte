<script lang="ts">
	import { page } from '$app/state';
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import Button from '#lib/components/ui/Button.svelte';
	import Card from '#lib/components/ui/Card.svelte';
	import EmptyState from '#lib/components/ui/EmptyState.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import StatCard from '#lib/components/ui/StatCard.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import { db } from '#lib/data/store.svelte';
	import {
		customerById,
		invoiceBalance,
		invoiceState,
		planById,
		subscriptionMonthlyValue,
		subscriptionTotal
	} from '#lib/data/selectors';
	import { formatDate, relativeDays } from '#lib/utils/date';
	import { currency } from '#lib/utils/format';

	let customer = $derived(customerById(db.data, page.params.id ?? null));

	let subscriptions = $derived(
		db.data.subscriptions.filter((item) => item.customerId === customer?.id)
	);
	let invoices = $derived(
		db.data.invoices
			.filter((item) => item.customerId === customer?.id)
			.sort((a, b) => b.issueDate.localeCompare(a.issueDate))
	);
	let payments = $derived(
		db.data.payments.filter((payment) =>
			db.data.invoices.some(
				(invoice) => invoice.id === payment.invoiceId && invoice.customerId === customer?.id
			)
		)
	);

	let activeSubscriptions = $derived(subscriptions.filter((item) => item.status === 'active'));
	let mrr = $derived(
		activeSubscriptions.reduce(
			(total, subscription) => total + subscriptionMonthlyValue(db.data, subscription),
			0
		)
	);
	let lifetime = $derived(payments.reduce((total, payment) => total + payment.amount, 0));
	let outstanding = $derived(
		invoices
			.filter((invoice) => invoice.status === 'confirmed' || invoice.status === 'draft')
			.reduce((total, invoice) => total + invoiceBalance(invoice), 0)
	);
</script>

<svelte:head>
	<title>{customer?.company ?? 'Customer'} · Brightloop</title>
</svelte:head>

{#if customer}
	<div class="space-y-6">
		<PageHeader
			title={customer.company}
			description={`${customer.name} · Customer since ${formatDate(customer.since)}`}
			backHref="/customers"
			backLabel="Customers"
		>
			{#snippet actions()}
				<Button variant="outline" href={`/subscriptions/new?customer=${customer.id}`}>
					<Icon name="plus" size={16} />
					New subscription
				</Button>
			{/snippet}
		</PageHeader>

		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
			<StatCard
				label="Recurring revenue"
				value={`${currency(mrr)}/mo`}
				icon="repeat"
				tone="brand"
				hint={`${activeSubscriptions.length} active subscriptions`}
			/>
			<StatCard
				label="Lifetime collected"
				value={currency(lifetime)}
				icon="wallet"
				tone="emerald"
				hint={`${payments.length} payments`}
			/>
			<StatCard
				label="Outstanding"
				value={currency(outstanding)}
				icon="receipt"
				tone="rose"
				hint={`${invoices.length} invoices issued`}
			/>
			<StatCard
				label="Subscriptions"
				value={String(subscriptions.length)}
				icon="repeat"
				tone="violet"
				hint="All statuses"
			/>
		</div>

		<div class="grid gap-6 xl:grid-cols-3">
			<Card>
				<div class="flex items-center gap-3">
					<Avatar name={customer.company} size="lg" />
					<div class="min-w-0">
						<p class="truncate text-sm font-semibold text-slate-900">{customer.company}</p>
						<p class="truncate text-xs text-slate-400">{customer.name}</p>
					</div>
				</div>
				<dl class="mt-5 space-y-3 text-sm">
					<div class="flex items-start gap-2">
						<Icon name="mail" size={15} class="mt-0.5 text-slate-400" />
						<div>
							<dt class="text-[11px] tracking-wide text-slate-400 uppercase">Email</dt>
							<dd class="text-slate-700">{customer.email}</dd>
						</div>
					</div>
					<div class="flex items-start gap-2">
						<Icon name="user" size={15} class="mt-0.5 text-slate-400" />
						<div>
							<dt class="text-[11px] tracking-wide text-slate-400 uppercase">Phone</dt>
							<dd class="text-slate-700">{customer.phone || '—'}</dd>
						</div>
					</div>
					<div class="flex items-start gap-2">
						<Icon name="building" size={15} class="mt-0.5 text-slate-400" />
						<div>
							<dt class="text-[11px] tracking-wide text-slate-400 uppercase">Billing address</dt>
							<dd class="text-slate-700">{customer.address || '—'}</dd>
						</div>
					</div>
				</dl>
			</Card>

			<Card class="xl:col-span-2" padded={false}>
				<div class="flex items-center justify-between px-5 py-4">
					<div>
						<h2 class="text-sm font-semibold text-slate-900">Subscriptions</h2>
						<p class="text-xs text-slate-400">Active and historical plans</p>
					</div>
					<Button variant="ghost" size="sm" href={`/subscriptions/new?customer=${customer.id}`}>
						<Icon name="plus" size={14} />
						New
					</Button>
				</div>
				<Table
					columns={[
						{ label: 'Number' },
						{ label: 'Plan' },
						{ label: 'Status' },
						{ label: 'Renews' },
						{ label: 'Value', align: 'right' }
					]}
					rowCount={subscriptions.length}
					class="rounded-none border-0 shadow-none"
					emptyTitle="No subscriptions yet"
					emptyIcon="repeat"
				>
					{#each subscriptions as subscription (subscription.id)}
						<tr class="transition hover:bg-slate-50">
							<td class="px-4 py-3">
								<a
									href={`/subscriptions/${subscription.id}`}
									class="font-medium text-slate-800 hover:text-brand-600"
								>
									{subscription.number}
								</a>
							</td>
							<td class="px-4 py-3 text-slate-600"
								>{planById(db.data, subscription.planId)?.name ?? '—'}</td
							>
							<td class="px-4 py-3"><StatusBadge status={subscription.status} /></td>
							<td class="px-4 py-3 text-xs text-slate-500">
								{formatDate(subscription.endDate)}
								<span class="block text-slate-400">{relativeDays(subscription.endDate)}</span>
							</td>
							<td class="px-4 py-3 text-right font-medium text-slate-700">
								{currency(subscriptionTotal(subscription))}
							</td>
						</tr>
					{/each}
				</Table>
			</Card>
		</div>

		<Card padded={false}>
			<div class="flex items-center justify-between px-5 py-4">
				<div>
					<h2 class="text-sm font-semibold text-slate-900">Invoice history</h2>
					<p class="text-xs text-slate-400">Every invoice issued to this customer</p>
				</div>
				<Button variant="ghost" size="sm" href="/invoices">All invoices</Button>
			</div>
			<Table
				columns={[
					{ label: 'Invoice' },
					{ label: 'Issued' },
					{ label: 'Due' },
					{ label: 'Status' },
					{ label: 'Total', align: 'right' },
					{ label: 'Balance', align: 'right' }
				]}
				rowCount={invoices.length}
				class="rounded-none border-0 shadow-none"
				emptyTitle="No invoices yet"
				emptyIcon="receipt"
			>
				{#each invoices as invoice (invoice.id)}
					<tr class="transition hover:bg-slate-50">
						<td class="px-4 py-3">
							<a
								href={`/invoices/${invoice.id}`}
								class="font-medium text-slate-800 hover:text-brand-600"
							>
								{invoice.number}
							</a>
						</td>
						<td class="px-4 py-3 text-slate-500">{formatDate(invoice.issueDate)}</td>
						<td class="px-4 py-3 text-slate-500">{formatDate(invoice.dueDate)}</td>
						<td class="px-4 py-3"><StatusBadge status={invoiceState(invoice)} /></td>
						<td class="px-4 py-3 text-right font-medium text-slate-700"
							>{currency(invoice.total)}</td
						>
						<td class="px-4 py-3 text-right">
							<span class={invoiceBalance(invoice) > 0 ? 'text-rose-600' : 'text-slate-400'}>
								{currency(invoiceBalance(invoice))}
							</span>
						</td>
					</tr>
				{/each}
			</Table>
		</Card>
	</div>
{:else}
	<Card>
		<EmptyState
			icon="building"
			title="Customer not found"
			description="This customer may have been removed."
		>
			{#snippet action()}
				<Button href="/customers" variant="outline">Back to customers</Button>
			{/snippet}
		</EmptyState>
	</Card>
{/if}
