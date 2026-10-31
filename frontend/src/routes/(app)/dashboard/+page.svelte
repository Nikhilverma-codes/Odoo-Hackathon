<script lang="ts">
	import Button from '#lib/components/ui/Button.svelte';
	import Card from '#lib/components/ui/Card.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import PageHeader from '#lib/components/ui/PageHeader.svelte';
	import StatCard from '#lib/components/ui/StatCard.svelte';
	import StatusBadge from '#lib/components/ui/StatusBadge.svelte';
	import Table from '#lib/components/ui/Table.svelte';
	import Avatar from '#lib/components/ui/Avatar.svelte';
	import RunBillingModal from '#lib/components/RunBillingModal.svelte';
	import { db } from '#lib/data/store.svelte';
	import {
		customerById,
		invoiceBalance,
		invoiceState,
		metrics,
		planById,
		subscriptionMonthlyValue,
		upcomingRenewals
	} from '#lib/data/selectors';
	import { currency, formatNumber } from '#lib/utils/format';
	import { formatDate, relativeDays } from '#lib/utils/date';

	let data = $derived(db.data);
	let summary = $derived(metrics(data));
	let renewals = $derived(upcomingRenewals(data, 5));
	let billingOpen = $state(false);
	let recent = $derived(
		[...data.invoices].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 6)
	);
</script>

<svelte:head>
	<title>Dashboard · Brightloop</title>
</svelte:head>

<div class="space-y-6">
	<PageHeader
		title="Billing overview"
		description="Everything happening across subscriptions, invoices and revenue this month."
	>
		{#snippet actions()}
			<Button variant="outline" href="/payments">
				<Icon name="credit-card" size={16} />
				Record payment
			</Button>
			<Button variant="outline" onclick={() => (billingOpen = true)}>
				<Icon name="play" size={16} />
				Run billing
			</Button>
			<Button href="/subscriptions/new">
				<Icon name="plus" size={16} />
				New subscription
			</Button>
		{/snippet}
	</PageHeader>

	<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
		<StatCard
			label="Monthly recurring revenue"
			value={currency(summary.mrr)}
			hint={`ARR ${currency(summary.arr)}`}
			icon="repeat"
			tone="brand"
			trend={8.2}
		/>
		<StatCard
			label="Active subscriptions"
			value={formatNumber(summary.activeSubscriptions)}
			hint={`${formatNumber(summary.customers)} customers on the books`}
			icon="check-circle"
			tone="emerald"
			trend={4.6}
		/>
		<StatCard
			label="Outstanding balance"
			value={currency(summary.outstanding)}
			hint={`${formatNumber(summary.invoiceCount)} invoices issued`}
			icon="receipt"
			tone="sky"
		/>
		<StatCard
			label="Overdue invoices"
			value={formatNumber(summary.overdueCount)}
			hint={`${currency(summary.overdueAmount)} at risk`}
			icon="exclamation"
			tone="rose"
		/>
	</div>

	<div class="grid gap-6 xl:grid-cols-3">
		<Card class="xl:col-span-2" padded={false}>
			<div class="flex items-center justify-between px-5 py-4">
				<div>
					<h2 class="text-sm font-semibold text-slate-900">Recent invoices</h2>
					<p class="text-xs text-slate-400">Latest activity from the billing engine</p>
				</div>
				<Button variant="ghost" size="sm" href="/invoices">
					View all
					<Icon name="arrow-right" size={14} />
				</Button>
			</div>
			<Table
				columns={[
					{ label: 'Invoice' },
					{ label: 'Customer' },
					{ label: 'Status' },
					{ label: 'Due' },
					{ label: 'Total', align: 'right' }
				]}
				rowCount={recent.length}
				class="rounded-none border-0 shadow-none"
			>
				{#each recent as invoice (invoice.id)}
					{@const customer = customerById(data, invoice.customerId)}
					<tr class="transition hover:bg-slate-50">
						<td class="px-4 py-3 whitespace-nowrap">
							<a
								href={`/invoices/${invoice.id}`}
								class="font-medium text-slate-800 hover:text-brand-600"
							>
								{invoice.number}
							</a>
						</td>
						<td class="px-4 py-3 text-slate-600">{customer?.company ?? '—'}</td>
						<td class="px-4 py-3">
							<StatusBadge status={invoiceState(invoice)} />
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-slate-500">
							{formatDate(invoice.dueDate)}
						</td>
						<td class="px-4 py-3 text-right whitespace-nowrap">
							<span class="font-semibold text-slate-800">{currency(invoice.total)}</span>
							{#if invoiceBalance(invoice) > 0 && invoice.status !== 'cancelled'}
								<p class="text-[11px] text-rose-500">{currency(invoiceBalance(invoice))} due</p>
							{/if}
						</td>
					</tr>
				{/each}
			</Table>
		</Card>

		<Card padded={false}>
			<div class="flex items-center justify-between px-5 py-4">
				<div>
					<h2 class="text-sm font-semibold text-slate-900">Upcoming renewals</h2>
					<p class="text-xs text-slate-400">Next five subscriptions to renew</p>
				</div>
				<Icon name="calendar" size={18} class="text-slate-400" />
			</div>
			<ul class="divide-y divide-slate-100">
				{#each renewals as subscription (subscription.id)}
					{@const customer = customerById(data, subscription.customerId)}
					{@const plan = planById(data, subscription.planId)}
					<li class="flex items-center gap-3 px-5 py-3">
						<Avatar name={customer?.company ?? 'Customer'} size="sm" />
						<div class="min-w-0 flex-1">
							<p class="truncate text-sm font-medium text-slate-800">
								{customer?.company ?? 'Customer'}
							</p>
							<p class="truncate text-xs text-slate-400">
								{plan?.name ?? 'Plan'} · {currency(subscriptionMonthlyValue(data, subscription))}/mo
							</p>
						</div>
						<div class="text-right">
							<p class="text-xs font-medium text-slate-700">{relativeDays(subscription.endDate)}</p>
							<p class="text-[11px] text-slate-400">{formatDate(subscription.endDate)}</p>
						</div>
					</li>
				{/each}
			</ul>
			<div class="border-t border-slate-100 px-5 py-3">
				<Button variant="ghost" size="sm" href="/subscriptions" class="w-full">
					Manage subscriptions
					<Icon name="arrow-right" size={14} />
				</Button>
			</div>
		</Card>
	</div>

	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		{#each [{ label: 'Collected this month', value: currency(summary.collectedThisMonth), icon: 'wallet' }, { label: 'Customers', value: formatNumber(summary.customers), icon: 'building' }, { label: 'Invoices issued', value: formatNumber(summary.invoiceCount), icon: 'receipt' }, { label: 'At-risk revenue', value: currency(summary.overdueAmount), icon: 'exclamation' }] as item (item.label)}
			<div class="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
				<span
					class="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-500"
				>
					<Icon name={item.icon} size={16} />
				</span>
				<div class="min-w-0">
					<p class="truncate text-xs text-slate-400">{item.label}</p>
					<p class="text-sm font-semibold text-slate-800">{item.value}</p>
				</div>
			</div>
		{/each}
	</div>
</div>

<RunBillingModal open={billingOpen} onclose={() => (billingOpen = false)} />
